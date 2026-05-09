"""Stage 3: describe the square-cropped image with the VLM.

Output is saved as `description.txt` in the page dir. Resume-safe: if the
file already exists, we just read it back.
"""

from pathlib import Path

from ..models.vision import VisionModel
from .. import config


def describe_image(vlm: VisionModel, square_path: Path,
                   output_path: Path) -> str:
    """Describe the image; cache to disk. Returns the description string."""
    if output_path.exists():
        return output_path.read_text().strip()
    desc = vlm.describe(square_path, prompt=config.VLM_DESCRIBE_PROMPT,
                        max_new_tokens=config.VLM_MAX_TOKENS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(desc)
    return desc
