"""Stage 2: prepare the rendered page for diffusion (aspect ratio preserved).

The rendered PDF page is scaled by `scale_percent` (e.g. 30 → 30%) in both
dimensions, so the aspect ratio of the prepared image matches `rendered.png`
exactly. The result is rounded to multiples of 8 (SD's VAE constraint) and
clamped so the longer side never exceeds `long_side_max` (a safety cap that
keeps you from accidentally launching a 2-hour-per-image job on a
high-DPI render).

The output is `prepared.png` — an aspect-ratio-faithful, diffusion-ready
version of the rendered page. Every downstream stage (description, sequels,
contact sheet) uses this file as the canonical "original".
"""

from pathlib import Path

from PIL import Image


def _round_to_multiple_of_8(x: float) -> int:
    """SD 1.5's VAE downsamples by 8; both dims must be multiples of 8."""
    n = int(round(x / 8.0)) * 8
    return max(8, n)


def target_dimensions(width: int, height: int,
                      scale_percent: float, long_side_max: int) -> tuple[int, int]:
    """Compute (target_w, target_h) preserving aspect ratio.

    1. Multiply both dims by `scale_percent` / 100.
    2. If the larger of the two scaled dims exceeds `long_side_max`, scale
       both down proportionally so the larger equals `long_side_max`.
    3. Round both to the nearest multiple of 8.
    """
    if scale_percent <= 0:
        raise ValueError(f"scale_percent must be > 0 (got {scale_percent})")
    if long_side_max < 8:
        raise ValueError(f"long_side_max must be >= 8 (got {long_side_max})")

    sw = width * scale_percent / 100.0
    sh = height * scale_percent / 100.0

    long_t = max(sw, sh)
    if long_t > long_side_max:
        ratio = long_side_max / long_t
        sw *= ratio
        sh *= ratio

    return _round_to_multiple_of_8(sw), _round_to_multiple_of_8(sh)


def prepare_for_diffusion(rendered_path: Path, output_path: Path,
                          scale_percent: float, long_side_max: int) -> Path:
    """Scale the rendered page to its diffusion-ready dimensions. Resume-safe."""
    if output_path.exists():
        return output_path

    img = Image.open(rendered_path).convert("RGB")
    tw, th = target_dimensions(img.width, img.height, scale_percent, long_side_max)

    if (tw, th) != img.size:
        img = img.resize((tw, th), Image.LANCZOS)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    return output_path
