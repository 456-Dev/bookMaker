"""Stage 4: img2img generate the sequel variants for a page.

The variant table comes from the active `RunConfig.variants`. Every row
specifies its own (strength, steps, seed_override, positive_prompt,
negative_prompt, guidance). The init image is always the prepared page.

Negative prompt resolution:
    - variant.negative_prompt is None → use the per-page LLM description
    - variant.negative_prompt == ""   → use an explicitly EMPTY negative
                                        (the description has no effect)
    - variant.negative_prompt == "…"  → use that literal text as the negative

Seed resolution:
    - variant.seed_override is None → use the per-page reference seed
    - variant.seed_override is set  → use that fixed seed (page-independent)

Each variant is checked individually before regenerating, so resume picks
up mid-list if a run was interrupted.
"""

from pathlib import Path
from typing import Callable, Optional, Sequence

from ..models.diffusion import DiffusionModel
from ..runset import Variant


def variants_as_dicts(variants: Sequence[Variant]) -> list[dict]:
    """Plain-dict view of the table (for manifest writing + progress logging)."""
    return [
        {
            "slot": v.slot,
            "filename": v.filename,
            "label": v.label,
            "strength": v.strength,
            "steps": v.steps,
            "seed_override": v.seed_override,
            "positive_prompt": v.positive_prompt,
            "negative_prompt": v.negative_prompt,
            "guidance": v.guidance,
            "is_control": v.is_control,
        }
        for v in variants
    ]


def _resolve_seed(v: Variant, page_seed: int) -> int:
    return page_seed if v.seed_override is None else v.seed_override


def _resolve_negative(v: Variant, llm_description: str) -> tuple[str, str]:
    """Return (negative_prompt_text, source_label). source_label is 'llm'
    when the variant pulls from the per-page description, otherwise 'manual'
    — used for progress reporting and the manifest."""
    if v.negative_prompt is None:
        return llm_description, "llm"
    return v.negative_prompt, "manual"


def regenerate_all(
    diffusion: DiffusionModel,
    prepared_path: Path,
    description: str,
    page_dir: Path,
    seed: int,
    variants: Sequence[Variant],
    on_variant: Optional[Callable[[int, int, dict], None]] = None,
) -> list[dict]:
    """Generate every variant; skip any that already exist (resume-safe).

    `seed` is the per-page reference seed. Variants without an explicit
    `seed_override` use this; variants with one ignore it.

    `description` is the auto-generated LLM description; variants whose
    `negative_prompt` is None use it as their negative prompt.

    `on_variant(idx, total, variant)` is called immediately AFTER each variant
    completes (or is skipped) — used for progress reporting.
    """
    total = len(variants)
    results: list[dict] = []

    for i, v in enumerate(variants, start=1):
        out = page_dir / v.filename
        v_seed = _resolve_seed(v, seed)
        neg_text, neg_source = _resolve_negative(v, description)
        record = {
            "slot": v.slot,
            "filename": v.filename,
            "label": v.label,
            "strength": v.strength,
            "steps": v.steps,
            "seed": v_seed,
            "seed_override": v.seed_override,
            "positive_prompt": v.positive_prompt,
            "negative_prompt_source": neg_source,
            "negative_prompt_text": neg_text,
            "guidance": v.guidance,
            "is_control": v.is_control,
            "path": str(out),
            "skipped": out.exists(),
        }
        if not out.exists():
            diffusion.img2img(
                init_image_path=prepared_path,
                output_path=out,
                positive_prompt=v.positive_prompt,
                negative_prompt=neg_text,
                strength=v.strength,
                steps=v.steps,
                guidance=v.guidance,
                seed=v_seed,
            )
        results.append(record)
        if on_variant is not None:
            on_variant(i, total, record)

    return results
