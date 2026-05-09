"""Stage 1: render PDF pages to PNG using pypdfium2.

pypdfium2 is BSD-licensed, has no system dependencies (poppler, ImageMagick,
etc.), and is fast on CPU. Each page is saved as `page_NNN/rendered.png`.
"""

from pathlib import Path
from typing import Iterable

from .. import config


def count_pages(pdf_path: Path) -> int:
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        return len(pdf)
    finally:
        pdf.close()


def render_page(pdf_path: Path, page_idx_zero: int, output_path: Path,
                dpi: int = config.PDF_RENDER_DPI) -> Path:
    """Render one page (0-indexed for pdfium) to `output_path`. Skips work if
    the file already exists (resume support)."""
    if output_path.exists():
        return output_path
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(str(pdf_path))
    try:
        page = pdf[page_idx_zero]
        scale = dpi / 72.0
        pil = page.render(scale=scale).to_pil().convert("RGB")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pil.save(output_path)
    finally:
        pdf.close()
    return output_path


def render_all(pdf_path: Path, page_paths: Iterable[Path],
               dpi: int = config.PDF_RENDER_DPI) -> None:
    """Render every page; safe to re-run (skips existing files)."""
    for i, out in enumerate(page_paths):
        render_page(pdf_path, i, out, dpi=dpi)
