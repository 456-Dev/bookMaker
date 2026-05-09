"""Stage 5: assemble a contact sheet of every sequel variant.

Layout (4 cols × 3 rows):
    +-----------+-----------+-----------+-----------+
    | original  | s25/k0    | s25/k1    | s25/k2    |
    +-----------+-----------+-----------+-----------+
    | control   | s50/k0    | s50/k1    | s50/k2    |
    +-----------+-----------+-----------+-----------+
    |           | s75/k0    | s75/k1    | s75/k2    |
    +-----------+-----------+-----------+-----------+

Tiles letterbox the image inside a fixed-size cell, so non-square sequels
preserve their aspect ratio without distorting the grid layout. Each cell is
the variant image with a label strip below it. The contact sheet itself is
saved as `contact_sheet.png` in the page dir.
"""

from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from .. import config
from .regenerate import variant_filename, CONTROL_FILENAME


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
    """Assemble the 4x3 grid. Resume-safe: skips if output already exists."""
    if output_path.exists():
        return output_path

    font = _load_font(20)

    prepared = page_dir / "prepared.png"
    control = page_dir / CONTROL_FILENAME

    rows: list[list[tuple[Optional[Path], str]]] = []
    strengths = config.SEQUEL_STRENGTHS
    n_seeds = config.SEQUEL_SEEDS_PER_STRENGTH

    for row_idx, strength in enumerate(strengths):
        if row_idx == 0:
            left = (prepared if prepared.exists() else None, "original")
        elif row_idx == 1:
            left = (
                control,
                f"control  s={config.CONTROL_STRENGTH:.2f}  st={config.CONTROL_STEPS}",
            )
        else:
            left = (None, "")

        cells: list[tuple[Optional[Path], str]] = [left]
        for seed_idx in range(n_seeds):
            fn = variant_filename(strength, seed_idx)
            cells.append((page_dir / fn, f"s={strength:.2f}  k{seed_idx}"))
        rows.append(cells)

    cols = 1 + n_seeds
    cell_w = TILE_PX
    cell_h = TILE_PX + LABEL_HEIGHT
    sheet_w = PADDING + cols * (cell_w + PADDING)
    sheet_h = PADDING + len(strengths) * (cell_h + PADDING)
    sheet = Image.new("RGB", (sheet_w, sheet_h), BG_COLOR)

    for r, row in enumerate(rows):
        for c, (path, label) in enumerate(row):
            tile = _tile(path, label, font)
            x = PADDING + c * (cell_w + PADDING)
            y = PADDING + r * (cell_h + PADDING)
            sheet.paste(tile, (x, y))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)
    return output_path
