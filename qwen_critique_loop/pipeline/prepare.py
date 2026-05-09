"""Stage 2: prepare the rendered page for diffusion (no longer square).

The rendered PDF page is resized — preserving aspect ratio — to fit SD 1.5's
budget. The shorter side becomes `config.DIFFUSION_BASE_SIDE`, the longer side
scales proportionally and is rounded to a multiple of 8 (SD's VAE constraint).
If the long side would exceed `config.DIFFUSION_LONG_SIDE_MAX`, we clamp it
and let the short side shrink to keep the aspect ratio intact.

The output is `prepared.png` — an aspect-ratio-faithful, diffusion-ready
version of the rendered page. Every downstream stage (description, sequels,
contact sheet) uses this file as the canonical "original".
"""

from pathlib import Path

from PIL import Image

from .. import config


def _round_to_multiple_of_8(x: float) -> int:
    """SD 1.5's VAE downsamples by 8; both dims must be multiples of 8."""
    n = int(round(x / 8.0)) * 8
    return max(8, n)


def target_dimensions(width: int, height: int) -> tuple[int, int]:
    """Compute (target_w, target_h) preserving aspect ratio.

    Strategy: short side → DIFFUSION_BASE_SIDE; long side scales proportionally
    and is rounded to a multiple of 8. If the resulting long side exceeds
    DIFFUSION_LONG_SIDE_MAX, clamp it and shrink the short side to match.
    """
    base = int(config.DIFFUSION_BASE_SIDE)
    long_cap = int(config.DIFFUSION_LONG_SIDE_MAX)

    if width >= height:
        long_src, short_src = width, height
        long_is_w = True
    else:
        long_src, short_src = height, width
        long_is_w = False

    aspect = long_src / short_src
    short_t = base
    long_t = base * aspect

    if long_t > long_cap:
        long_t = long_cap
        short_t = long_cap / aspect

    short_t8 = _round_to_multiple_of_8(short_t)
    long_t8 = _round_to_multiple_of_8(long_t)

    return (long_t8, short_t8) if long_is_w else (short_t8, long_t8)


def prepare_for_diffusion(rendered_path: Path, output_path: Path) -> Path:
    """Resize the rendered page to its diffusion-ready dimensions. Resume-safe."""
    if output_path.exists():
        return output_path

    img = Image.open(rendered_path).convert("RGB")
    tw, th = target_dimensions(img.width, img.height)

    if (tw, th) != img.size:
        img = img.resize((tw, th), Image.LANCZOS)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    return output_path
