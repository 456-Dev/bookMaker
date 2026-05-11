"""Stage 5: assemble a contact sheet of every sequel variant.

The grid adapts to the number of variants in the active `RunConfig`. With
the default 12-variant table and `cols=4` the layout is 4×3:
    +---------+---------+---------+---------+
    | 01 ctrl | 02 opst | 03 bttr | 04 s25  |
    +---------+---------+---------+---------+
    | 05 opst | 06 s33  | 07 s40  | 08 s50  |
    +---------+---------+---------+---------+
    | 09 s50  | 10 s60  | 11 s70  | 12 same |
    +---------+---------+---------+---------+

Variants are placed in slot order, row-major. Tiles letterbox their image
inside a square cell so non-square sequels keep their aspect ratio without
distorting the grid layout.

The original is intentionally NOT shown — `prepared.png` lives one directory
up alongside the sheet, so checking the input is a single file open.
"""

import math
from pathlib import Path
from typing import Optional, Sequence

from PIL import Image, ImageDraw, ImageFont

from ..runset import Variant


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


def build_contact_sheet(page_dir: Path, output_path: Path,
                        variants: Sequence[Variant],
                        cols: int = 4) -> Path:
    """Assemble a grid covering every variant. Resume-safe: skips if
    output already exists. Rows are computed to fit `len(variants)` at the
    requested `cols`; any trailing empty cells render as placeholders."""
    if output_path.exists():
        return output_path

    font = _load_font(20)

    cols = max(1, int(cols))
    rows = max(1, math.ceil(len(variants) / cols))

    cell_w = TILE_PX
    cell_h = TILE_PX + LABEL_HEIGHT
    sheet_w = PADDING + cols * (cell_w + PADDING)
    sheet_h = PADDING + rows * (cell_h + PADDING)
    sheet = Image.new("RGB", (sheet_w, sheet_h), BG_COLOR)

    for idx in range(rows * cols):
        r, c = divmod(idx, cols)
        x = PADDING + c * (cell_w + PADDING)
        y = PADDING + r * (cell_h + PADDING)
        if idx < len(variants):
            v = variants[idx]
            label = f"{v.slot:02d}  {v.label}"
            tile = _tile(page_dir / v.filename, label, font)
        else:
            tile = _tile(None, "", font)
        sheet.paste(tile, (x, y))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)
    return output_path
