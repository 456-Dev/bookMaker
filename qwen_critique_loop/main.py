"""
imgSequel — PDF page reimagining pipeline.

For each page in a PDF:
    1. render to PNG               (pypdfium2)
    2. seam-carve to square        (content-aware crop, pure-numpy)
    3. describe with moondream2    (small CPU VLM)
    4. img2img regenerate          (SD 1.5, empty positive + description as negative)

Designed for AMD Ryzen 9 8945HS / 32GB / no GPU. Pure CPU inference.

Resume:
- Every artifact is checked before being recomputed. Crash mid-page-7?
  Re-run picks up at exactly the stage that hadn't completed.
- A tail-able `progress.txt` is written into the run dir for SSH check-ins.

Usage:
    python -m qwen_critique_loop.main path/to/document.pdf
    python -m qwen_critique_loop.main path/to/document.pdf --pages 1-5
    python -m qwen_critique_loop.main path/to/document.pdf --seed 42
    python -m qwen_critique_loop.main --resume latest                     # most recent run
    python -m qwen_critique_loop.main --resume runs/20260505_180942_doc   # specific
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
from .pipeline.regenerate import regenerate
from .utils.io import (
    create_run_dir, page_dir, page_artifact,
    write_manifest, read_manifest, find_latest_run,
)
from .utils.progress import ProgressLog


# Stage names (used as artifact filenames + progress labels)
STAGE_RENDER = "rendered.png"
STAGE_SQUARE = "square.png"
STAGE_DESC = "description.txt"
STAGE_SEQUEL = "sequel.png"


def _parse_pages(arg: Optional[str], total: int) -> list[int]:
    """Parse a `--pages` argument into a 1-based list of page indices.
    None -> all pages. Examples: "1-5", "3,7,9", "1-3,8,10-12"."""
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


def process_page(
    *,
    page_idx: int,
    total_pages: int,
    pdf_path: Path,
    run_dir: Path,
    vlm: VisionModel,
    diffusion: DiffusionModel,
    progress: ProgressLog,
    seed: Optional[int],
) -> dict:
    """Run all stages for a single page; each stage skips if already complete."""
    p_dir = page_dir(run_dir, page_idx)
    rendered_p = p_dir / STAGE_RENDER
    square_p = p_dir / STAGE_SQUARE
    desc_p = p_dir / STAGE_DESC
    sequel_p = p_dir / STAGE_SEQUEL

    completed = [a for a in (rendered_p, square_p, desc_p, sequel_p) if a.exists()]
    progress.page_header(page_idx, total_pages,
                         f"({len(completed)}/4 stages already done)" if completed else "")

    # 1. render
    if rendered_p.exists():
        progress.event("  render: skip (cached)")
    else:
        progress.stage_start(f"render page {page_idx} at {config.PDF_RENDER_DPI} dpi")
        render_page(pdf_path, page_idx - 1, rendered_p, dpi=config.PDF_RENDER_DPI)
        progress.stage_done()

    # 2. seam-carve to square
    if square_p.exists():
        progress.event("  square: skip (cached)")
    else:
        from PIL import Image
        with Image.open(rendered_p) as im:
            w, h = im.size
        side = min(w, h) if config.SQUARE_SIDE == "AUTO" else int(config.SQUARE_SIDE)
        progress.stage_start(f"seam-carve {w}x{h} -> {side}x{side}")
        square_crop(rendered_p, square_p)
        progress.stage_done()

    # 3. describe
    if desc_p.exists():
        progress.event("  describe: skip (cached)")
        description = desc_p.read_text().strip()
    else:
        progress.stage_start("describe with moondream2")
        description = describe_image(vlm, square_p, desc_p)
        progress.stage_done(detail=f"({len(description.split())} words)")

    progress.event(f"  description: {description[:140]}{'...' if len(description) > 140 else ''}")

    # 4. img2img regenerate
    if sequel_p.exists():
        progress.event("  sequel: skip (cached)")
    else:
        progress.stage_start(
            f"img2img {config.DIFFUSION_RESOLUTION}x{config.DIFFUSION_RESOLUTION} "
            f"strength={config.IMG2IMG_STRENGTH} steps={config.DIFFUSION_STEPS}"
        )
        regenerate(diffusion, square_p, description, sequel_p, seed=seed)
        progress.stage_done()

    progress.page_done(page_idx, total_pages, sequel_p)
    return {
        "page": page_idx,
        "rendered": str(rendered_p),
        "square": str(square_p),
        "description": description,
        "sequel": str(sequel_p),
    }


def run(pdf_path: Path, run_dir: Path, page_indices: list[int],
        seed: Optional[int]) -> dict:
    progress = ProgressLog(run_dir / config.PROGRESS_FILE)
    progress.banner(f"imgSequel run: {run_dir.name}")
    progress.event(f"PDF: {pdf_path}")
    progress.event(f"pages: {len(page_indices)} of {count_pages(pdf_path)} "
                   f"(indices: {page_indices[0]}..{page_indices[-1]})")
    progress.event(f"VLM: {config.VLM_MODEL}")
    progress.event(f"diffusion: {config.DIFFUSION_MODEL} on CPU "
                   f"({config.NUM_THREADS} threads)")

    vlm = VisionModel()
    diffusion = DiffusionModel()

    pages_record: list[dict] = []
    total = len(page_indices)
    for i, page_idx in enumerate(page_indices, start=1):
        rec = process_page(
            page_idx=page_idx, total_pages=total,
            pdf_path=pdf_path, run_dir=run_dir,
            vlm=vlm, diffusion=diffusion, progress=progress, seed=seed,
        )
        pages_record.append(rec)

        # Persist the manifest after every page so resume always has a clean state
        manifest = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "pdf_path": str(pdf_path),
            "run_dir": str(run_dir),
            "vlm_model": config.VLM_MODEL,
            "diffusion_model": config.DIFFUSION_MODEL,
            "diffusion_steps": config.DIFFUSION_STEPS,
            "diffusion_strength": config.IMG2IMG_STRENGTH,
            "diffusion_resolution": config.DIFFUSION_RESOLUTION,
            "render_dpi": config.PDF_RENDER_DPI,
            "seed": seed,
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
                        help='1-based page selector e.g. "1-5", "3,7,9", "1-3,8,10-12". '
                             'Default: all pages.')
    parser.add_argument("--seed", type=int, default=None,
                        help="Diffusion seed (deterministic across pages)")
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
            # Try to use the copy we made into the run dir
            local = run_dir / pdf_path.name
            if local.exists():
                pdf_path = local
            else:
                raise SystemExit(f"original PDF not found at {pdf_path} or {local}")
        page_indices = manifest.get("page_indices_target") or list(range(1, count_pages(pdf_path) + 1))
        seed = args.seed if args.seed is not None else manifest.get("seed")
        run(pdf_path, run_dir, page_indices, seed=seed)
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
    run(args.pdf, run_dir, page_indices, seed=args.seed)


if __name__ == "__main__":
    main()
