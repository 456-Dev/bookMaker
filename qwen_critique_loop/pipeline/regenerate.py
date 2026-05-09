"""Stage 4: img2img with empty positive prompt + description as negative prompt.

The artistic concept (option 1a from design discussion):
    positive prompt = ""             — no attractor
    negative prompt = description    — push AWAY from the image's own content
    init image      = square crop    — anchor composition
    strength        = 0.5            — clear deviation, but composition holds

The result tends to be the original composition with the described content
suppressed: subjects become abstract, recognizable objects fade, the scene
drifts toward whatever the model considers the "absence" of the description.
"""

from pathlib import Path
from typing import Optional

from ..models.diffusion import DiffusionModel
from .. import config


def regenerate(diffusion: DiffusionModel, square_path: Path,
               description: str, output_path: Path,
               seed: Optional[int] = None) -> Path:
    """Run img2img and save the sequel. Resume-safe."""
    if output_path.exists():
        return output_path
    return diffusion.img2img(
        init_image_path=square_path,
        output_path=output_path,
        positive_prompt=config.POSITIVE_PROMPT,   # empty
        negative_prompt=description,              # the image describes itself out
        strength=config.IMG2IMG_STRENGTH,
        steps=config.DIFFUSION_STEPS,
        guidance=config.DIFFUSION_GUIDANCE,
        side=config.DIFFUSION_RESOLUTION,
        seed=seed,
    )
