"""Stage 5: assemble a contact sheet of every sequel variant.

Layout (4 cols × 3 rows = 12 tiles, one per variant in slot order):
    +-----------+-----------+-----------+-----------+
    | 01 ctrl   | 02 oppst  | 03 better | 04 s25/100|
    +-----------+-----------+-----------+-----------+
    | 05 oppst  | 06 s33/100| 07 s40/50 | 08 s50/50 |
    +-----------+-----------+-----------+-----------+
    | 09 s50/50 | 10 s60/50 | 11 s70/50 | 12 same   |
    +-----------+-----------+-----------+-----------+

The original is intentionally NOT shown — `prepared.png` lives one directory
up alongside the sheet, so checking the input is a single file open. The
contact sheet is for comparing the 12 reinterpretations side by side. Each
tile letterboxes its image inside a fixed-size square cell, so non-square
sequels keep their aspect ratio without distorting the grid layout.

The contact sheet is saved as `contact_sheet.png` in the page dir.
"""

from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from .regenerate import VARIANTS


COLS = 4
ROWS = 3
TILE_PX = 320           # each cell's image-area side length (square box)
LABEL_HEIGHT = 36
PADDING = 12
BG_COLOR = (24, 27, 33)
TEXT_COLOR = (220, 220, 220)
EMPTY_COLOR = (40, 44, 52)


def _load_font(size: int) -> ImageFont.ImageFont:
    """Try to find a sane sans-serif font; fall back to PIL's default."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _tile(image_path: Optional[Path], label: str, font: ImageFont.ImageFont) -> Image.Image:
    cell_w = TILE_PX
    cell_h = TILE_PX + LABEL_HEIGHT
    cell = Image.new("RGB", (cell_w, cell_h), BG_COLOR)

    if image_path is not None and image_path.exists():
        img = Image.open(image_path).convert("RGB")
        # Letterbox into the TILE_PX x TILE_PX area, preserving aspect ratio.
        img.thumbnail((TILE_PX, TILE_PX), Image.LANCZOS)
        ox = (TILE_PX - img.width) // 2
        oy = (TILE_PX - img.height) // 2
        cell.paste(img, (ox, oy))
    else:
        ph = Image.new("RGB", (TILE_PX, TILE_PX), EMPTY_COLOR)
        cell.paste(ph, (0, 0))

    draw = ImageDraw.Draw(cell)
    bbox = draw.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    tx = (cell_w - tw) // 2
    ty = TILE_PX + (LABEL_HEIGHT - (bbox[3] - bbox[1])) // 2 - 2
    draw.text((tx, ty), label, fill=TEXT_COLOR, font=font)

    return cell


def build_contact_sheet(page_dir: Path, output_path: Path) -> Path:
    """Assemble the 4×3 grid of all 12 variants. Resume-safe: skips if
    output already exists."""
    if output_path.exists():
        return output_path

    font = _load_font(20)

    if len(VARIANTS) != COLS * ROWS:
        raise RuntimeError(
            f"contact sheet expects {COLS*ROWS} variants, got {len(VARIANTS)}"
        )

    cell_w = TILE_PX
    cell_h = TILE_PX + LABEL_HEIGHT
    sheet_w = PADDING + COLS * (cell_w + PADDING)
    sheet_h = PADDING + ROWS * (cell_h + PADDING)
    sheet = Image.new("RGB", (sheet_w, sheet_h), BG_COLOR)

    for idx, v in enumerate(VARIANTS):
        r, c = divmod(idx, COLS)
        path = page_dir / v.filename
        label = f"{v.slot:02d}  {v.label}"
        tile = _tile(path, label, font)
        x = PADDING + c * (cell_w + PADDING)
        y = PADDING + r * (cell_h + PADDING)
        sheet.paste(tile, (x, y))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)
    return output_path
