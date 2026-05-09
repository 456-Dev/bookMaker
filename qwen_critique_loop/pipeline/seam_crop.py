"""Stage 2: crop the rendered page to a square.

Two methods, selected by config.CROP_METHOD:
  - "center"     — instantaneous center crop (default; may cut off edges)
  - "seam_carve" — content-aware seam carving (~5-15s/page, preserves subjects)

The output is always saved as `square.png` in the page dir; downstream
stages don't care which method produced it.
"""

from pathlib import Path

from PIL import Image

from .. import config


def _resolve_side(width: int, height: int) -> int:
    if config.SQUARE_SIDE == "AUTO" or config.SQUARE_SIDE is None:
        return min(width, height)
    return int(config.SQUARE_SIDE)


def square_crop(rendered_path: Path, output_path: Path) -> Path:
    """Crop to a square using the configured method. Resume-safe."""
    if output_path.exists():
        return output_path

    method = (getattr(config, "CROP_METHOD", "center") or "center").lower()
    if method == "seam_carve":
        return _square_seam_carve(rendered_path, output_path)
    return _square_center_crop(rendered_path, output_path)


def _square_center_crop(rendered_path: Path, output_path: Path) -> Path:
    """Take a min(W, H) square from the center of the rendered page."""
    img = Image.open(rendered_path).convert("RGB")
    w, h = img.size
    side = _resolve_side(w, h)

    if w == side and h == side:
        out = img
    else:
        # Crop the central side x side region of the original (clamped if
        # SQUARE_SIDE was forced larger than the shorter dimension).
        crop_side = min(side, w, h)
        left = (w - crop_side) // 2
        top = (h - crop_side) // 2
        out = img.crop((left, top, left + crop_side, top + crop_side))
        if out.size != (side, side):
            out = out.resize((side, side), Image.LANCZOS)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(output_path)
    return output_path


def _square_seam_carve(rendered_path: Path, output_path: Path) -> Path:
    """Content-aware square crop. Slow but preserves the subject."""
    import numpy as np
    img = Image.open(rendered_path).convert("RGB")
    w, h = img.size
    side = _resolve_side(w, h)

    if w == side and h == side:
        img.save(output_path)
        return output_path

    arr = np.array(img)
    if w > h:
        carved = _carve(arr, w - side, axis="vertical")
        if h != side:
            carved = np.array(Image.fromarray(carved).resize((side, side), Image.LANCZOS))
    elif h > w:
        carved = _carve(arr, h - side, axis="horizontal")
        if w != side:
            carved = np.array(Image.fromarray(carved).resize((side, side), Image.LANCZOS))
    else:
        carved = arr

    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(carved).save(output_path)
    return output_path


def _carve(arr, seams: int, axis: str):
    import seam_carving
    if axis == "vertical":
        target_size = (arr.shape[1] - seams, arr.shape[0])
    else:
        target_size = (arr.shape[1], arr.shape[0] - seams)
    return seam_carving.resize(
        arr, target_size,
        energy_mode="forward",
        order="height-first" if axis == "horizontal" else "width-first",
    )
