"""
imgSequel — PDF page reimagining pipeline.

For each page in a PDF:
    1. render to PNG                 (pypdfium2)
    2. prepare for diffusion         (aspect-ratio-preserving resize to SD's
                                      pixel budget; output is NOT square —
                                      it matches the original page's aspect)
    3. describe with InstructBLIP    (one VLM call per question in the active
                                      runset, answers cached per question and
                                      stitched into the final description)
    4. img2img regenerate N sequels  (one per row in the runset's variant
                                      table; description is the negative
                                      prompt, init image is `prepared.png`)
    5. assemble a contact sheet      (grid sized to the runset's variant count
                                      and cols setting)

What's configurable in the runset (JSON file):
    - render DPI
    - diffusion sizing (scale_percent + long_side_max safety cap) + default
      guidance for new variants
    - describe questions (key + text + max tokens)
    - variant table — per row: strength, steps, seed_override, positive
      prompt, negative prompt (or null to use the LLM description), guidance
    - contact sheet columns

What's a CLI flag (per-run, not in the runset):
    - PDF path, --pages, --seed, --resume, --device, --runset

Device:
    --device auto (default) picks CUDA → MPS → CPU. M1/M2/M3 Macs get MPS;
    Linux+Nvidia get CUDA; everything else stays on CPU. Override with
    --device cpu | cuda | mps.

Resume:
    Every artifact is checked before being recomputed; crash mid-page-7 and
    a re-run picks up at exactly the stage and variant that hadn't finished.
    `--resume latest` continues the most recent run dir using its saved
    runset.

Usage:
    python -m qwen_critique_loop.main path/to/document.pdf
    python -m qwen_critique_loop.main path/to/document.pdf --pages 1-5
    python -m qwen_critique_loop.main path/to/document.pdf --runset myrun.runset.json
    python -m qwen_critique_loop.main path/to/document.pdf --device mps
    python -m qwen_critique_loop.main --resume latest
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import config
from .runset import RunConfig
from .models.vision import VisionModel
from .models.diffusion import DiffusionModel
from .pipeline.pdf_render import count_pages, render_page
from .pipeline.prepare import prepare_for_diffusion, target_dimensions
from .pipeline.describe import describe_image
from .pipeline.regenerate import regenerate_all, variants_as_dicts
from .pipeline.contact_sheet import build_contact_sheet
from .utils.io import (
    create_run_dir, page_dir,
    write_manifest, read_manifest, find_latest_run,
)
from .utils.progress import ProgressLog


STAGE_RENDER = "rendered.png"
STAGE_PREPARED = "prepared.png"
STAGE_DESC = "description.txt"
STAGE_CONTACT = "contact_sheet.png"
RUNSET_FILENAME = "runset.json"


def _parse_pages(arg: Optional[str], total: int) -> list[int]:
    if not arg:
        return list(range(1, total + 1))
    out: list[int] = []
    for token in arg.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            a, b = token.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(token))
    return [p for p in out if 1 <= p <= total]


def _resolve_resume(arg: str) -> Path:
    if arg == "latest":
        latest = find_latest_run()
        if latest is None:
            raise FileNotFoundError(f"No run directories under {config.RUNS_DIR}")
        return latest
    p = Path(arg).expanduser().resolve()
    if p.exists():
        return p
    alt = config.RUNS_DIR / arg
    if alt.exists():
        return alt
    raise FileNotFoundError(arg)


def _page_seed(base_seed: Optional[int], page_idx: int) -> int:
    """Each page gets its own reference seed. Variants without an explicit
    seed_override use this value."""
    if base_seed is None:
        return page_idx * 1009
    return base_seed + page_idx * 1009


def process_page(
    *,
    page_idx: int,
    total_pages: int,
    pdf_path: Path,
    run_dir: Path,
    vlm: VisionModel,
    diffusion: DiffusionModel,
    progress: ProgressLog,
    seed_base: Optional[int],
    cfg: RunConfig,
) -> dict:
    p_dir = page_dir(run_dir, page_idx)
    rendered_p = p_dir / STAGE_RENDER
    prepared_p = p_dir / STAGE_PREPARED
    desc_p = p_dir / STAGE_DESC
    contact_p = p_dir / STAGE_CONTACT

    progress.page_header(page_idx, total_pages, "")

    # 1. render
    if rendered_p.exists():
        progress.event("  render: skip (cached)")
    else:
        progress.stage_start(f"render page {page_idx} at {cfg.render_dpi} dpi")
        render_page(pdf_path, page_idx - 1, rendered_p, dpi=cfg.render_dpi)
        progress.stage_done()

    # 2. prepare for diffusion (scale% of original, aspect ratio preserved)
    if prepared_p.exists():
        progress.event("  prepare: skip (cached)")
    else:
        from PIL import Image
        with Image.open(rendered_p) as im:
            w, h = im.size
        tw, th = target_dimensions(w, h,
                                   cfg.diffusion.scale_percent,
                                   cfg.diffusion.long_side_max)
        progress.stage_start(
            f"prepare {w}x{h} -> {tw}x{th} "
            f"(scale={cfg.diffusion.scale_percent}%, "
            f"long_side cap={cfg.diffusion.long_side_max})"
        )
        prepare_for_diffusion(rendered_p, prepared_p,
                              cfg.diffusion.scale_percent,
                              cfg.diffusion.long_side_max)
        progress.stage_done()

    # 3. describe — one VLM call per question in the runset
    if desc_p.exists():
        progress.event("  describe: skip (cached)")
        description = desc_p.read_text().strip()
    else:
        progress.stage_start(
            f"describe with InstructBLIP "
            f"({len(cfg.describe.questions)} questions)"
        )

        def on_question(slot: int, total_q: int, key: str,
                        answer: str, was_cached: bool) -> None:
            marker = "skip" if was_cached else "done"
            preview = answer.replace("\n", " ")
            preview = preview[:100] + ("..." if len(preview) > 100 else "")
            progress.event(
                f"    [{slot}/{total_q}] q={key:<10}  {marker}  -> {preview}"
            )

        description = describe_image(
            vlm, prepared_p, desc_p,
            questions=cfg.describe.questions,
            max_tokens=cfg.describe.max_tokens,
            on_question=on_question,
        )
        progress.stage_done(detail=f"({len(description.split())} words)")

    progress.event(
        f"  description: {description[:140]}{'...' if len(description) > 140 else ''}"
    )

    # 4. generate the variants from the runset
    page_seed = _page_seed(seed_base, page_idx)
    n_variants = len(cfg.variants)
    progress.stage_start(
        f"img2img {n_variants} variants (page_seed={page_seed})"
    )

    def on_variant(idx: int, total: int, v: dict) -> None:
        seed_disp = (
            f"seed={v['seed']}" if v["seed_override"] is not None
            else f"seed={v['seed']} (page)"
        )
        neg_tag = "neg=" + v["negative_prompt_source"]
        marker = "skip" if v["skipped"] else "done"
        progress.event(
            f"    [{idx:>2}/{total}] {v['slot']:02d} {v['label']:<32}  "
            f"st={v['steps']:<3}  g={v['guidance']:<4}  {seed_disp:<22}  "
            f"{neg_tag:<10}  {marker}"
        )

    variant_records = regenerate_all(
        diffusion, prepared_p, description, p_dir,
        seed=page_seed,
        variants=cfg.variants,
        on_variant=on_variant,
    )
    progress.stage_done()

    # 5. contact sheet
    if contact_p.exists():
        progress.event("  contact sheet: skip (cached)")
    else:
        progress.stage_start("assemble contact sheet")
        build_contact_sheet(p_dir, contact_p,
                            variants=cfg.variants,
                            cols=cfg.contact_sheet.cols)
        progress.stage_done()

    progress.page_done(page_idx, total_pages, contact_p)
    return {
        "page": page_idx,
        "rendered": str(rendered_p),
        "prepared": str(prepared_p),
        "description": description,
        "page_seed": page_seed,
        "variants": variant_records,
        "contact_sheet": str(contact_p),
    }


def run(pdf_path: Path, run_dir: Path, page_indices: list[int],
        seed_base: Optional[int], cfg: RunConfig,
        device_request: str = "auto") -> dict:
    progress = ProgressLog(run_dir / config.PROGRESS_FILE)
    progress.banner(f"imgSequel run: {run_dir.name}")
    progress.event(f"PDF: {pdf_path}")
    progress.event(f"pages: {len(page_indices)} of {count_pages(pdf_path)} "
                   f"(indices: {page_indices[0]}..{page_indices[-1]})")
    progress.event(f"runset: '{cfg.name}' "
                   f"({len(cfg.describe.questions)} questions, "
                   f"{len(cfg.variants)} variants)")
    progress.event(f"VLM: {config.VLM_MODEL}")

    vlm = VisionModel(device_request=device_request)
    diffusion = DiffusionModel(device_request=device_request)
    diffusion._ensure_loaded()
    progress.event(f"diffusion: {config.DIFFUSION_MODEL} on {diffusion.device} "
                   f"(dtype={str(diffusion.dtype).rsplit('.', 1)[-1]}, "
                   f"{config.NUM_THREADS} cpu threads)")
    progress.event(
        f"diffusion size: scale={cfg.diffusion.scale_percent}% of rendered, "
        f"long side capped at {cfg.diffusion.long_side_max} "
        f"(aspect ratio preserved)"
    )
    # Per-variant guidance/negative-prompt summary
    n_llm = sum(1 for v in cfg.variants if v.negative_prompt is None)
    n_manual = len(cfg.variants) - n_llm
    progress.event(
        f"negative prompts: {n_llm} variant(s) use the LLM description, "
        f"{n_manual} use a manual override"
    )

    # Persist the active runset alongside the manifest so the run is
    # fully self-describing.
    cfg.save(run_dir / RUNSET_FILENAME)

    pages_record: list[dict] = []
    total = len(page_indices)
    for page_idx in page_indices:
        rec = process_page(
            page_idx=page_idx, total_pages=total,
            pdf_path=pdf_path, run_dir=run_dir,
            vlm=vlm, diffusion=diffusion, progress=progress,
            seed_base=seed_base, cfg=cfg,
        )
        pages_record.append(rec)

        manifest = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "pdf_path": str(pdf_path),
            "run_dir": str(run_dir),
            "device_request": device_request,
            "device_used": diffusion.device,
            "dtype_used": str(diffusion.dtype).rsplit(".", 1)[-1],
            "runset_name": cfg.name,
            "runset_file": str(run_dir / RUNSET_FILENAME),
            "runset": cfg.to_dict(),
            "vlm_model": config.VLM_MODEL,
            "diffusion_model": config.DIFFUSION_MODEL,
            "variant_table": variants_as_dicts(cfg.variants),
            "seed_base": seed_base,
            "page_indices_target": page_indices,
            "pages": pages_record,
        }
        write_manifest(run_dir, manifest)

    progress.banner(f"DONE — {len(pages_record)} page(s) processed")
    progress.event(f"artifacts: {run_dir}")
    return manifest


def _load_runset(arg: Optional[str]) -> RunConfig:
    if arg is None:
        return RunConfig.default(name="default")
    path = Path(arg).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"runset file not found: {path}")
    return RunConfig.load(path)


def main():
    parser = argparse.ArgumentParser(description="imgSequel — PDF page reimagining")
    parser.add_argument("pdf", type=Path, nargs="?", default=None,
                        help="Path to input PDF (omit when using --resume)")
    parser.add_argument("--pages", type=str, default=None,
                        help='1-based page selector e.g. "1-5", "3,7,9". '
                             'Default: all pages.')
    parser.add_argument("--seed", type=int, default=None,
                        help="Base seed; per-page seed = base + page_idx*1009")
    parser.add_argument("--resume", type=str, default=None, metavar="DIR",
                        help='Resume an existing run. Pass a path or "latest".')
    parser.add_argument("--runset", type=str, default=None, metavar="FILE",
                        help="Path to a runset JSON file (built with webui/index.html). "
                             "If omitted, uses the built-in default runset.")
    parser.add_argument("--device", type=str, default="auto",
                        choices=["auto", "cpu", "cuda", "mps"],
                        help="Hardware to run on. 'auto' picks cuda > mps > cpu.")
    args = parser.parse_args()

    if args.resume:
        run_dir = _resolve_resume(args.resume)
        manifest = read_manifest(run_dir)
        if not manifest:
            raise SystemExit(f"{run_dir} has no run.json — cannot resume")
        pdf_path = Path(manifest["pdf_path"])
        if not pdf_path.exists():
            raise SystemExit(
                f"original PDF not found at {pdf_path}. "
                f"(Place the file back at that path or update run.json.)"
            )
        page_indices = (manifest.get("page_indices_target")
                        or list(range(1, count_pages(pdf_path) + 1)))
        seed_base = (args.seed if args.seed is not None
                     else manifest.get("seed_base", manifest.get("seed")))

        # Resume uses the runset that was saved with the run, unless the
        # caller explicitly passes a new --runset.
        if args.runset:
            cfg = _load_runset(args.runset)
        else:
            saved_runset = run_dir / RUNSET_FILENAME
            if saved_runset.exists():
                cfg = RunConfig.load(saved_runset)
            elif "runset" in manifest:
                cfg = RunConfig.from_dict(manifest["runset"])
            else:
                cfg = RunConfig.default(name="default")
        run(pdf_path, run_dir, page_indices, seed_base=seed_base,
            cfg=cfg, device_request=args.device)
        return

    if args.pdf is None:
        parser.error("PDF path is required for a fresh run (or pass --resume)")
    if not args.pdf.exists():
        raise SystemExit(f"PDF not found: {args.pdf}")

    total = count_pages(args.pdf)
    page_indices = _parse_pages(args.pages, total)
    if not page_indices:
        raise SystemExit(f"No valid pages selected from PDF with {total} pages")

    cfg = _load_runset(args.runset)
    run_dir = create_run_dir(args.pdf)
    run(args.pdf, run_dir, page_indices, seed_base=args.seed,
        cfg=cfg, device_request=args.device)


if __name__ == "__main__":
    main()
