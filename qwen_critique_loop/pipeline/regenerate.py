"""Stage 4: img2img generate the sequel variants for a page.

Per page (with the new seed-sweep design):
  - 9-grid sweep over (strength × seed_index). Steps and prompt are fixed:
    empty positive prompt, the description goes into the negative prompt.
    Each (strength, seed_idx) cell uses a *different* seed, so within a
    strength row you see how stable the model is to noise variation.
  - 1 control sequel — the middle-of-the-road strength/steps with the
    same negative prompt, but using the page's reference seed AND a
    positive prompt. This isolates the effect of the positive prompt vs
    the (s=CONTROL_STRENGTH, seed=k0) grid cell.

Each variant is checked individually before regenerating, so resume picks up
mid-grid if a run was interrupted.

Filename convention:
    sequel_s25_k0.png    = strength 0.25, seed_index 0
    sequel_s25_k1.png    = strength 0.25, seed_index 1
    sequel_s50_k2.png    = strength 0.50, seed_index 2
    ...
    sequel_control.png   = control variant (positive prompt, page seed)
"""

from pathlib import Path
from typing import Callable, Optional

from ..models.diffusion import DiffusionModel
from .. import config


# Large prime so seed_index spreads page seeds far apart in the RNG state.
_SEED_STRIDE = 7919


def variant_filename(strength: float, seed_idx: int) -> str:
    return f"sequel_s{int(round(strength * 100)):02d}_k{seed_idx}.png"


CONTROL_FILENAME = "sequel_control.png"


def variant_seed(page_seed: int, seed_idx: int) -> int:
    """Per-variant seed derived deterministically from the page seed.

    seed_idx 0 returns the page seed itself (so the first column of the grid
    shares a seed with the control, isolating the positive-prompt effect)."""
    return page_seed + seed_idx * _SEED_STRIDE


def all_variants() -> list[dict]:
    """Return a list of dicts describing all variants in canonical order:
    9 grid cells (strength × seed_idx) followed by the control."""
    out: list[dict] = []
    for strength in config.SEQUEL_STRENGTHS:
        for seed_idx in range(config.SEQUEL_SEEDS_PER_STRENGTH):
            out.append({
                "filename": variant_filename(strength, seed_idx),
                "strength": strength,
                "steps": config.SEQUEL_STEPS,
                "seed_idx": seed_idx,
                "positive_prompt": config.POSITIVE_PROMPT,
                "is_control": False,
            })
    out.append({
        "filename": CONTROL_FILENAME,
        "strength": config.CONTROL_STRENGTH,
        "steps": config.CONTROL_STEPS,
        "seed_idx": 0,                       # control reuses k0's seed
        "positive_prompt": config.CONTROL_POSITIVE_PROMPT,
        "is_control": True,
    })
    return out


def regenerate_all(
    diffusion: DiffusionModel,
    prepared_path: Path,
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
        v_seed = variant_seed(seed, v["seed_idx"])
        record = {
            **v,
            "path": str(out),
            "skipped": out.exists(),
            "seed": v_seed,
        }
        if not out.exists():
            diffusion.img2img(
                init_image_path=prepared_path,
                output_path=out,
                positive_prompt=v["positive_prompt"],
                negative_prompt=description,
                strength=v["strength"],
                steps=v["steps"],
                guidance=config.DIFFUSION_GUIDANCE,
                seed=v_seed,
            )
        results.append(record)
        if on_variant is not None:
            on_variant(i, total, record)

    return results
