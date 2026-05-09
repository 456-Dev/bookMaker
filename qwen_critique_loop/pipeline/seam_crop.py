"""Stage 2: content-aware square crop via seam carving.

Uses the `seam-carving` PyPI package — pure numpy, MIT-licensed, no native deps.
Slow at full PDF resolution (a 1650x2200 page takes ~5-15s to remove 550 vertical
seams on this CPU); fast enough for batch use, painful for real-time.

Strategy:
- Side length = min(width, height) of the rendered page (per config.SQUARE_SIDE).
- If the page is already square within 1px, just save a copy.
- Otherwise carve from the longer dimension until square.
- Result is saved as `square.png` in the page dir.
"""

from pathlib import Path

import numpy as np
from PIL import Image

from .. import config


def _resolve_side(width: int, height: int) -> int:
    if config.SQUARE_SIDE == "AUTO" or config.SQUARE_SIDE is None:
        return min(width, height)
    return int(config.SQUARE_SIDE)


def square_crop(rendered_path: Path, output_path: Path) -> Path:
    """Seam-carve the rendered page down to a square. Resume-safe."""
    if output_path.exists():
        return output_path

    img = Image.open(rendered_path).convert("RGB")
    w, h = img.size
    side = _resolve_side(w, h)

    if w == side and h == side:
        img.save(output_path)
        return output_path

    arr = np.array(img)

    # Resize the LONGER dim down to `side` via seam carving; the SHORTER dim
    # is already at or above `side` and will be cropped/resampled to match.
    if w > h:
        # remove vertical seams
        seams_to_remove = w - side
        carved = _carve(arr, seams_to_remove, axis="vertical")
        # carved has shape (h, side, 3); now bring h to side
        if h != side:
            carved_img = Image.fromarray(carved)
            carved_img = carved_img.resize((side, side), Image.LANCZOS)
            carved = np.array(carved_img)
    elif h > w:
        seams_to_remove = h - side
        carved = _carve(arr, seams_to_remove, axis="horizontal")
        if w != side:
            carved_img = Image.fromarray(carved)
            carved_img = carved_img.resize((side, side), Image.LANCZOS)
            carved = np.array(carved_img)
    else:
        carved = arr

    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(carved).save(output_path)
    return output_path


def _carve(arr: np.ndarray, seams: int, axis: str) -> np.ndarray:
    """Remove `seams` seams. axis='vertical' removes vertical seams (reduces width).
    axis='horizontal' removes horizontal seams (reduces height)."""
    import seam_carving
    if axis == "vertical":
        target_size = (arr.shape[1] - seams, arr.shape[0])  # (W, H)
    else:
        target_size = (arr.shape[1], arr.shape[0] - seams)
    return seam_carving.resize(arr, target_size, energy_mode="forward",
                               order="height-first" if axis == "horizontal" else "width-first")
