"""
imgSequel — PDF page reimagining pipeline.

For each page in a PDF:
    1. render to PNG                 (pypdfium2)
    2. seam-carve to square          (content-aware crop, pure-numpy)
    3. describe with InstructBLIP    (detailed technical caption, CPU)
    4. img2img regenerate 10 sequels:
         - 9-grid sweep over (strength, steps) — empty positive prompt,
           description as negative
         - 1 control variant — same negative, same seed, fixed
           (strength, steps), but with a positive prompt
       All 10 share the same per-page seed so the grid is a clean
       parameter sweep and the control isolates the positive-prompt effect.
    5. assemble a contact sheet (4x3 thumbnail grid) for fast review

Designed for AMD Ryzen 9 8945HS / 32GB / no GPU. Pure CPU inference.

Resume:
- Every artifact is checked before being recomputed. Crash mid-page-7?
  Re-run picks up at exactly the stage and variant that hadn't completed.
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
from .pipeline.seam_crop import square_crop
from .pipeline.describe import describe_image
from .pipeline.regenerate import regenerate_all
from .pipeline.contact_sheet import build_contact_sheet
from .utils.io import (
    create_run_dir, page_dir,
    write_manifest, read_manifest, find_latest_run,
)
from .utils.progress import ProgressLog


STAGE_RENDER = "rendered.png"
STAGE_SQUARE = "square.png"
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
    """Each page gets its own seed so different pages aren't variations of the
    same noise pattern. Within a page, all 10 variants share this seed."""
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
    square_p = p_dir / STAGE_SQUARE
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

    # 2. crop to square (method per config.CROP_METHOD)
    if square_p.exists():
        progress.event("  square: skip (cached)")
    else:
        from PIL import Image
        with Image.open(rendered_p) as im:
            w, h = im.size
        side = min(w, h) if config.SQUARE_SIDE == "AUTO" else int(config.SQUARE_SIDE)
        method = config.CROP_METHOD
        progress.stage_start(f"crop ({method}) {w}x{h} -> {side}x{side}")
        square_crop(rendered_p, square_p)
        progress.stage_done()

    # 3. describe (InstructBLIP — slow but detailed)
    if desc_p.exists():
        progress.event("  describe: skip (cached)")
        description = desc_p.read_text().strip()
    else:
        progress.stage_start("describe with InstructBLIP")
        description = describe_image(vlm, square_p, desc_p)
        progress.stage_done(detail=f"({len(description.split())} words)")

    progress.event(
        f"  description: {description[:140]}{'...' if len(description) > 140 else ''}"
    )

    # 4. generate 10 variants (9-grid + control)
    page_seed = _page_seed(seed_base, page_idx)
    progress.stage_start(f"img2img 10 variants (shared seed={page_seed})")

    def on_variant(idx: int, total: int, v: dict) -> None:
        tag = "control" if v["is_control"] else f"s={v['strength']:.2f} st={v['steps']:>2}"
        marker = "skip" if v["skipped"] else "done"
        progress.event(f"    [{idx:>2}/{total}] {tag:<20}  {marker}")

    variant_records = regenerate_all(
        diffusion, square_p, description, p_dir,
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
        "square": str(square_p),
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
    progress.event(f"VLM: {config.VLM_MODEL}")

    vlm = VisionModel()
    diffusion = DiffusionModel()
    diffusion._ensure_loaded()
    progress.event(f"diffusion: {config.DIFFUSION_MODEL} on {diffusion.device} "
                   f"(dtype={str(diffusion.dtype).rsplit('.', 1)[-1]}, "
                   f"{config.NUM_THREADS} cpu threads)")
    progress.event(
        f"variants/page: 9-grid strengths={config.SEQUEL_STRENGTHS} × "
        f"steps={config.SEQUEL_STEPS}  +  1 control "
        f"(s={config.CONTROL_STRENGTH}, st={config.CONTROL_STEPS}, "
        f"positive='{config.CONTROL_POSITIVE_PROMPT}')"
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
            "diffusion_model": config.DIFFUSION_MODEL,
            "diffusion_resolution": config.DIFFUSION_RESOLUTION,
            "diffusion_guidance": config.DIFFUSION_GUIDANCE,
            "render_dpi": config.PDF_RENDER_DPI,
            "sequel_strengths": config.SEQUEL_STRENGTHS,
            "sequel_steps": config.SEQUEL_STEPS,
            "control_positive_prompt": config.CONTROL_POSITIVE_PROMPT,
            "control_strength": config.CONTROL_STRENGTH,
            "control_steps": config.CONTROL_STEPS,
            "describe_prompt": config.VLM_DESCRIBE_PROMPT,
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
