"""Stage 4: img2img generate the 10 sequel variants for a page.

Per page:
  - 9-grid sweep over (strength × steps) from config — empty positive prompt,
    the description goes into the negative prompt
  - 1 control sequel — fixed (strength, steps), same negative, but a positive
    prompt is supplied (config.CONTROL_POSITIVE_PROMPT)

All 10 variants share the same per-page seed so the grid is a clean parameter
sweep and the control isolates the effect of the positive prompt.

Each variant is checked individually before regenerating, so resume picks up
mid-grid if a run was interrupted.

Filename convention:
    sequel_s25_st13.png   = strength 0.25, 13 steps
    sequel_s50_st25.png   = strength 0.50, 25 steps
    ...
    sequel_control.png    = control variant
"""

from pathlib import Path
from typing import Callable, Optional

from ..models.diffusion import DiffusionModel
from .. import config


def variant_filename(strength: float, steps: int) -> str:
    return f"sequel_s{int(round(strength * 100)):02d}_st{steps:02d}.png"


CONTROL_FILENAME = "sequel_control.png"


def all_variants() -> list[dict]:
    """Return a list of dicts describing all 10 variants in canonical order."""
    out: list[dict] = []
    for strength in config.SEQUEL_STRENGTHS:
        for steps in config.SEQUEL_STEPS:
            out.append({
                "filename": variant_filename(strength, steps),
                "strength": strength,
                "steps": steps,
                "positive_prompt": config.POSITIVE_PROMPT,
                "is_control": False,
            })
    out.append({
        "filename": CONTROL_FILENAME,
        "strength": config.CONTROL_STRENGTH,
        "steps": config.CONTROL_STEPS,
        "positive_prompt": config.CONTROL_POSITIVE_PROMPT,
        "is_control": True,
    })
    return out


def regenerate_all(
    diffusion: DiffusionModel,
    square_path: Path,
    description: str,
    page_dir: Path,
    seed: int,
    on_variant: Optional[Callable[[int, int, dict], None]] = None,
) -> list[dict]:
    """Generate every variant; skip any that already exist (resume-safe).

    `on_variant(idx, total, variant)` is called immediately AFTER each variant
    completes (or is skipped) — used for progress reporting.
    """
    variants = all_variants()
    total = len(variants)
    results: list[dict] = []

    for i, v in enumerate(variants, start=1):
        out = page_dir / v["filename"]
        record = {
            **v,
            "path": str(out),
            "skipped": out.exists(),
            "seed": seed,
        }
        if not out.exists():
            diffusion.img2img(
                init_image_path=square_path,
                output_path=out,
                positive_prompt=v["positive_prompt"],
                negative_prompt=description,
                strength=v["strength"],
                steps=v["steps"],
                guidance=config.DIFFUSION_GUIDANCE,
                side=config.DIFFUSION_RESOLUTION,
                seed=seed,
            )
        results.append(record)
        if on_variant is not None:
            on_variant(i, total, record)

    return results
