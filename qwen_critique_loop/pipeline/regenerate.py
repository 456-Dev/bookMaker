"""Stage 4: img2img generate the 12 sequel variants for a page.

The 12 variants are an explicit, hand-curated table — not a sweep. Every row
specifies its own (strength, steps, seed, positive prompt). The negative
prompt is always the per-page description; the init image is always the
prepared (aspect-ratio-preserving) version of the page.

Variants whose `seed_override` is None use the per-page reference seed; that
ties them to the page so different pages don't all repeat the same noise.

Each variant is checked individually before regenerating, so resume picks up
mid-list if a run was interrupted.

Filename convention:
    sequel_NN_<short_label>.png
where NN is the 1-based slot index (01..12) and short_label captures the
distinguishing parameter(s) of that row.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from ..models.diffusion import DiffusionModel
from .. import config


@dataclass(frozen=True)
class Variant:
    slot: int
    filename: str
    label: str
    strength: float
    steps: int
    seed_override: Optional[int]    # None = use per-page seed
    positive_prompt: str
    is_control: bool = False


# The full 12-row table. Order is the canonical generation order and the
# row-major order in which they are tiled on the contact sheet.
VARIANTS: tuple[Variant, ...] = (
    Variant(
        slot=1, filename="sequel_01_control.png", label="control",
        strength=config.CONTROL_STRENGTH, steps=config.CONTROL_STEPS,
        seed_override=None,
        positive_prompt=config.CONTROL_POSITIVE_PROMPT, is_control=True,
    ),
    Variant(
        slot=2, filename="sequel_02_opposite.png",
        label="opposite  s=0.40",
        strength=0.40, steps=config.SEQUEL_DEFAULT_STEPS,
        seed_override=None,
        positive_prompt="generate the opposite image",
    ),
    Variant(
        slot=3, filename="sequel_03_better.png",
        label="better  s=0.40",
        strength=0.40, steps=config.SEQUEL_DEFAULT_STEPS,
        seed_override=None,
        positive_prompt="generate a better image",
    ),
    Variant(
        slot=4, filename="sequel_04_s25_st100_seed1.png",
        label="s=0.25  st=100  seed=1",
        strength=0.25, steps=100, seed_override=1, positive_prompt="",
    ),
    Variant(
        slot=5, filename="sequel_05_s25_st100_seed42_opposite.png",
        label="opposite  s=0.25  st=100  seed=42",
        strength=0.25, steps=100, seed_override=42,
        positive_prompt="generate the opposite image",
    ),
    Variant(
        slot=6, filename="sequel_06_s33_st100_seed69.png",
        label="s=0.33  st=100  seed=69",
        strength=0.33, steps=100, seed_override=69, positive_prompt="",
    ),
    Variant(
        slot=7, filename="sequel_07_s40_st50_seed1.png",
        label="s=0.40  seed=1",
        strength=0.40, steps=config.SEQUEL_DEFAULT_STEPS,
        seed_override=1, positive_prompt="",
    ),
    Variant(
        slot=8, filename="sequel_08_s50_st50_seed2.png",
        label="s=0.50  seed=2",
        strength=0.50, steps=config.SEQUEL_DEFAULT_STEPS,
        seed_override=2, positive_prompt="",
    ),
    Variant(
        slot=9, filename="sequel_09_s50_st50_seed3.png",
        label="s=0.50  seed=3",
        strength=0.50, steps=config.SEQUEL_DEFAULT_STEPS,
        seed_override=3, positive_prompt="",
    ),
    Variant(
        slot=10, filename="sequel_10_s60_st50_seed4.png",
        label="s=0.60  seed=4",
        strength=0.60, steps=config.SEQUEL_DEFAULT_STEPS,
        seed_override=4, positive_prompt="",
    ),
    Variant(
        slot=11, filename="sequel_11_s70_st50_seed5.png",
        label="s=0.70  seed=5",
        strength=0.70, steps=config.SEQUEL_DEFAULT_STEPS,
        seed_override=5, positive_prompt="",
    ),
    Variant(
        slot=12, filename="sequel_12_s80_same.png",
        label="same  s=0.80",
        strength=0.80, steps=config.SEQUEL_DEFAULT_STEPS,
        seed_override=None,
        positive_prompt="generate the exact same image",
    ),
)


def all_variants() -> list[dict]:
    """Return the canonical-order variant table as plain dicts (for the
    manifest and progress reporting)."""
    return [
        {
            "slot": v.slot,
            "filename": v.filename,
            "label": v.label,
            "strength": v.strength,
            "steps": v.steps,
            "seed_override": v.seed_override,
            "positive_prompt": v.positive_prompt,
            "is_control": v.is_control,
        }
        for v in VARIANTS
    ]


def _resolve_seed(v: Variant, page_seed: int) -> int:
    return page_seed if v.seed_override is None else v.seed_override


def regenerate_all(
    diffusion: DiffusionModel,
    prepared_path: Path,
    description: str,
    page_dir: Path,
    seed: int,
    on_variant: Optional[Callable[[int, int, dict], None]] = None,
) -> list[dict]:
    """Generate every variant; skip any that already exist (resume-safe).

    `seed` is the per-page reference seed. Variants without an explicit
    `seed_override` use this; variants with one ignore it.

    `on_variant(idx, total, variant)` is called immediately AFTER each variant
    completes (or is skipped) — used for progress reporting.
    """
    total = len(VARIANTS)
    results: list[dict] = []

    for i, v in enumerate(VARIANTS, start=1):
        out = page_dir / v.filename
        v_seed = _resolve_seed(v, seed)
        record = {
            "slot": v.slot,
            "filename": v.filename,
            "label": v.label,
            "strength": v.strength,
            "steps": v.steps,
            "seed": v_seed,
            "seed_override": v.seed_override,
            "positive_prompt": v.positive_prompt,
            "is_control": v.is_control,
            "path": str(out),
            "skipped": out.exists(),
        }
        if not out.exists():
            diffusion.img2img(
                init_image_path=prepared_path,
                output_path=out,
                positive_prompt=v.positive_prompt,
                negative_prompt=description,
                strength=v.strength,
                steps=v.steps,
                guidance=config.DIFFUSION_GUIDANCE,
                seed=v_seed,
            )
        results.append(record)
        if on_variant is not None:
            on_variant(i, total, record)

    return results
