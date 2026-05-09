"""
imgSequel — PDF page reimagining pipeline.

For each page in a PDF:
    1. render to PNG                 (pypdfium2)
    2. prepare for diffusion         (aspect-ratio-preserving resize to SD's
                                      pixel budget; output is NOT square — it
                                      matches the original page's aspect ratio)
    3. describe with InstructBLIP    (FIVE questions: subject, location, time,
                                      purpose, camera. Answers cached per
                                      question; final description is the
                                      stitched paragraph.)
    4. img2img regenerate 12 sequels — explicit hand-curated table:
         01 control                   (s=0.50, st=25, "realistic street photograph", page_seed)
         02 opposite                  (s=0.40, st=50, "generate the opposite image", page_seed)
         03 better                    (s=0.40, st=50, "generate a better image", page_seed)
         04 s=0.25 st=100 seed=1      (empty positive)
         05 s=0.25 st=100 seed=42     ("generate the opposite image")
         06 s=0.33 st=100 seed=69     (empty positive)
         07 s=0.40 st=50  seed=1      (empty positive)
         08 s=0.50 st=50  seed=2      (empty positive)
         09 s=0.50 st=50  seed=3      (empty positive)
         10 s=0.60 st=50  seed=4      (empty positive)
         11 s=0.70 st=50  seed=5      (empty positive)
         12 s=0.80 st=50  same        ("generate the exact same image", page_seed)
       The description is always the negative prompt.
    5. assemble a 4×3 contact sheet of the 12 variants for fast review.

The sequel images are emitted at the same dimensions as the prepared init,
so they preserve the original page's aspect ratio.

Designed for AMD Ryzen 9 8945HS / 32GB / no GPU. Pure CPU inference.

Resume:
- Every artifact is checked before being recomputed. Crash mid-page-7?
  Re-run picks up at exactly the stage and variant that hadn't completed.
  The describe stage caches each of the five answers individually.
- A tail-able `progress.txt` is written into the run dir for SSH check-ins.

Usage:
    python -m qwen_critique_loop.main path/to/document.pdf
    python -m qwen_critique_loop.main path/to/document.pdf --pages 1-5
    python -m qwen_critique_loop.main path/to/document.pdf --seed 42
    python -m qwen_critique_loop.main --resume latest
"""

import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import config
from .models.vision import VisionModel
from .models.diffusion import DiffusionModel
from .pipeline.pdf_render import count_pages, render_page
from .pipeline.prepare import prepare_for_diffusion, target_dimensions
from .pipeline.describe import describe_image
from .pipeline.regenerate import regenerate_all, all_variants
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
    """Each page gets its own reference seed so different pages aren't
    variations of the same noise pattern. Variants without an explicit
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
        progress.stage_start(f"render page {page_idx} at {config.PDF_RENDER_DPI} dpi")
        render_page(pdf_path, page_idx - 1, rendered_p, dpi=config.PDF_RENDER_DPI)
        progress.stage_done()

    # 2. prepare for diffusion (aspect-ratio-preserving resize, not square)
    if prepared_p.exists():
        progress.event("  prepare: skip (cached)")
    else:
        from PIL import Image
        with Image.open(rendered_p) as im:
            w, h = im.size
        tw, th = target_dimensions(w, h)
        progress.stage_start(f"prepare {w}x{h} -> {tw}x{th} (aspect preserved)")
        prepare_for_diffusion(rendered_p, prepared_p)
        progress.stage_done()

    # 3. describe (InstructBLIP, 5 questions stitched into one paragraph)
    if desc_p.exists():
        progress.event("  describe: skip (cached)")
        description = desc_p.read_text().strip()
    else:
        progress.stage_start(
            f"describe with InstructBLIP "
            f"({len(config.VLM_DESCRIBE_QUESTIONS)} questions)"
        )

        def on_question(slot: int, total_q: int, key: str,
                        answer: str, was_cached: bool) -> None:
            marker = "skip" if was_cached else "done"
            preview = answer.replace("\n", " ")
            preview = preview[:100] + ("..." if len(preview) > 100 else "")
            progress.event(
                f"    [{slot}/{total_q}] q={key:<8}  {marker}  -> {preview}"
            )

        description = describe_image(
            vlm, prepared_p, desc_p, on_question=on_question,
        )
        progress.stage_done(detail=f"({len(description.split())} words)")

    progress.event(
        f"  description: {description[:140]}{'...' if len(description) > 140 else ''}"
    )

    # 4. generate the 12 variants
    page_seed = _page_seed(seed_base, page_idx)
    progress.stage_start(
        f"img2img 12 variants (page_seed={page_seed})"
    )

    def on_variant(idx: int, total: int, v: dict) -> None:
        seed_disp = (
            f"seed={v['seed']}" if v["seed_override"] is not None
            else f"seed={v['seed']} (page)"
        )
        marker = "skip" if v["skipped"] else "done"
        progress.event(
            f"    [{idx:>2}/{total}] {v['slot']:02d} {v['label']:<32}  "
            f"st={v['steps']:<3}  {seed_disp:<22}  {marker}"
        )

    variant_records = regenerate_all(
        diffusion, prepared_p, description, p_dir,
        seed=page_seed, on_variant=on_variant,
    )
    progress.stage_done()

    # 5. contact sheet
    if contact_p.exists():
        progress.event("  contact sheet: skip (cached)")
    else:
        progress.stage_start("assemble contact sheet")
        build_contact_sheet(p_dir, contact_p)
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
        seed_base: Optional[int]) -> dict:
    progress = ProgressLog(run_dir / config.PROGRESS_FILE)
    progress.banner(f"imgSequel run: {run_dir.name}")
    progress.event(f"PDF: {pdf_path}")
    progress.event(f"pages: {len(page_indices)} of {count_pages(pdf_path)} "
                   f"(indices: {page_indices[0]}..{page_indices[-1]})")
    progress.event(f"VLM: {config.VLM_MODEL} "
                   f"({len(config.VLM_DESCRIBE_QUESTIONS)} questions/page)")

    vlm = VisionModel()
    diffusion = DiffusionModel()
    diffusion._ensure_loaded()
    progress.event(f"diffusion: {config.DIFFUSION_MODEL} on {diffusion.device} "
                   f"(dtype={str(diffusion.dtype).rsplit('.', 1)[-1]}, "
                   f"{config.NUM_THREADS} cpu threads)")
    progress.event(
        f"variants/page: 12 (see manifest 'variants' for the full table)"
    )
    progress.event(
        f"diffusion size: short side={config.DIFFUSION_BASE_SIDE}, "
        f"long side capped at {config.DIFFUSION_LONG_SIDE_MAX} "
        f"(aspect ratio preserved)"
    )

    pages_record: list[dict] = []
    total = len(page_indices)
    for page_idx in page_indices:
        rec = process_page(
            page_idx=page_idx, total_pages=total,
            pdf_path=pdf_path, run_dir=run_dir,
            vlm=vlm, diffusion=diffusion, progress=progress,
            seed_base=seed_base,
        )
        pages_record.append(rec)

        manifest = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "pdf_path": str(pdf_path),
            "run_dir": str(run_dir),
            "vlm_model": config.VLM_MODEL,
            "vlm_describe_questions": [
                {"key": k, "question": q}
                for (k, q) in config.VLM_DESCRIBE_QUESTIONS
            ],
            "diffusion_model": config.DIFFUSION_MODEL,
            "diffusion_base_side": config.DIFFUSION_BASE_SIDE,
            "diffusion_long_side_max": config.DIFFUSION_LONG_SIDE_MAX,
            "diffusion_guidance": config.DIFFUSION_GUIDANCE,
            "render_dpi": config.PDF_RENDER_DPI,
            "sequel_default_steps": config.SEQUEL_DEFAULT_STEPS,
            "control_positive_prompt": config.CONTROL_POSITIVE_PROMPT,
            "control_strength": config.CONTROL_STRENGTH,
            "control_steps": config.CONTROL_STEPS,
            "variant_table": all_variants(),
            "seed_base": seed_base,
            "page_indices_target": page_indices,
            "pages": pages_record,
        }
        write_manifest(run_dir, manifest)

    progress.banner(f"DONE — {len(pages_record)} page(s) processed")
    progress.event(f"artifacts: {run_dir}")
    return manifest


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
        run(pdf_path, run_dir, page_indices, seed_base=seed_base)
        return

    if args.pdf is None:
        parser.error("PDF path is required for a fresh run (or pass --resume)")
    if not args.pdf.exists():
        raise SystemExit(f"PDF not found: {args.pdf}")

    total = count_pages(args.pdf)
    page_indices = _parse_pages(args.pages, total)
    if not page_indices:
        raise SystemExit(f"No valid pages selected from PDF with {total} pages")

    run_dir = create_run_dir(args.pdf)
    run(args.pdf, run_dir, page_indices, seed_base=args.seed)


if __name__ == "__main__":
    main()
