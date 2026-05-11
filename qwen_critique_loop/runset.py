"""Runset format — a JSON-serializable recipe for how to process a page.

A runset bundles the parts of the pipeline that change between experiments:
  - the variant table (per-row strength, steps, seed, prompts, guidance,
    negative-prompt source)
  - the 5+ describe questions
  - diffusion-input sizing (scale_percent + long_side_max safety cap)
  - default guidance for newly-added variants in the UI
  - PDF render DPI

Runtime-only knobs (PDF path, page range, seed, device) stay on the CLI so
one runset can be reused across PDFs and machines.

A runset is intended to be authored either by hand or with `webui/index.html`
and consumed by the CLI via `--runset path/to/file.runset.json`.

Schema version 2:
  {
    "version": 2,
    "name": "<arbitrary string, shown in progress + manifest>",
    "render_dpi": 200,
    "diffusion": {
      "scale_percent": 30.0,      // % of rendered.png dims (aspect preserved)
      "long_side_max": 768,       // safety cap for SD compute
      "guidance": 7.0             // default for new variants (UI only)
    },
    "describe": {
      "max_tokens": 180,
      "questions": [
        {"key": "subject", "question": "..."},
        ...
      ]
    },
    "contact_sheet": {"cols": 4},
    "variants": [
      {
        "slot": 1, "filename": "sequel_01_control.png", "label": "control",
        "strength": 0.50, "steps": 25,
        "seed_override": null,
        "positive_prompt": "realistic street photograph",
        "negative_prompt": null,    // null = use LLM-generated description
        "guidance": 7.0,
        "is_control": true
      },
      ...
    ]
  }

Schema version 1 (legacy) files are auto-migrated on load:
  - diffusion.base_side / long_side_max → diffusion.scale_percent=30, keep long_side_max
  - each variant inherits guidance from v1's diffusion.guidance
  - each variant gets negative_prompt=null (auto LLM description)
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from . import config


SCHEMA_VERSION = 2


@dataclass(frozen=True)
class DiffusionParams:
    # Percent of the rendered image dimensions to feed into diffusion.
    # Both dims are scaled by the same factor (aspect ratio preserved), then
    # rounded to multiples of 8 (SD VAE constraint). If the larger of the two
    # scaled dims exceeds long_side_max, both are scaled down proportionally
    # so the larger equals long_side_max.
    scale_percent: float = 30.0
    long_side_max: int = 768
    # Default guidance scale used for newly-added variants in the UI. Each
    # variant carries its own guidance — this top-level value is not consulted
    # by the pipeline directly.
    guidance: float = 7.0


@dataclass(frozen=True)
class DescribeQuestion:
    key: str
    question: str


@dataclass(frozen=True)
class DescribeParams:
    max_tokens: int = 180
    questions: tuple[DescribeQuestion, ...] = ()


@dataclass(frozen=True)
class Variant:
    slot: int
    filename: str
    label: str
    strength: float
    steps: int
    seed_override: Optional[int]
    positive_prompt: str
    # None ↔ use the auto-generated LLM description as the negative prompt.
    # Empty string ↔ explicitly use an EMPTY negative prompt.
    # Non-empty string ↔ use this literal text as the negative prompt.
    negative_prompt: Optional[str] = None
    guidance: float = 7.0
    is_control: bool = False


@dataclass(frozen=True)
class ContactSheetParams:
    cols: int = 4


@dataclass(frozen=True)
class RunConfig:
    name: str
    render_dpi: int
    diffusion: DiffusionParams
    describe: DescribeParams
    contact_sheet: ContactSheetParams
    variants: tuple[Variant, ...]

    # ----- defaults -----
    @classmethod
    def default(cls, name: str = "default") -> "RunConfig":
        """Build the canonical 12-variant / 5-question runset from config.py."""
        questions = tuple(
            DescribeQuestion(key=k, question=q)
            for (k, q) in config.VLM_DESCRIBE_QUESTIONS
        )
        variants = _default_variants(default_guidance=config.DIFFUSION_GUIDANCE)
        return cls(
            name=name,
            render_dpi=config.PDF_RENDER_DPI,
            diffusion=DiffusionParams(
                scale_percent=30.0,
                long_side_max=768,
                guidance=config.DIFFUSION_GUIDANCE,
            ),
            describe=DescribeParams(
                max_tokens=config.VLM_MAX_TOKENS,
                questions=questions,
            ),
            contact_sheet=ContactSheetParams(cols=4),
            variants=variants,
        )

    # ----- serialization -----
    def to_dict(self) -> dict:
        return {
            "version": SCHEMA_VERSION,
            "name": self.name,
            "render_dpi": self.render_dpi,
            "diffusion": asdict(self.diffusion),
            "describe": {
                "max_tokens": self.describe.max_tokens,
                "questions": [asdict(q) for q in self.describe.questions],
            },
            "contact_sheet": asdict(self.contact_sheet),
            "variants": [asdict(v) for v in self.variants],
        }

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return path

    @classmethod
    def from_dict(cls, raw: dict) -> "RunConfig":
        v = int(raw.get("version", 1))
        if v == 1:
            raw = _migrate_v1_to_v2(raw)
            v = 2
        if v != SCHEMA_VERSION:
            raise ValueError(
                f"runset schema version mismatch: file is v{v}, "
                f"this code expects v{SCHEMA_VERSION}"
            )

        d = raw["diffusion"]
        diffusion = DiffusionParams(
            scale_percent=float(d["scale_percent"]),
            long_side_max=int(d["long_side_max"]),
            guidance=float(d.get("guidance", 7.0)),
        )
        dq = raw["describe"]
        questions = tuple(
            DescribeQuestion(key=str(q["key"]), question=str(q["question"]))
            for q in dq["questions"]
        )
        describe = DescribeParams(
            max_tokens=int(dq.get("max_tokens", 180)),
            questions=questions,
        )
        cs = raw.get("contact_sheet", {"cols": 4})
        contact_sheet = ContactSheetParams(cols=int(cs.get("cols", 4)))

        default_guidance = diffusion.guidance
        variants = tuple(
            Variant(
                slot=int(vd["slot"]),
                filename=str(vd["filename"]),
                label=str(vd["label"]),
                strength=float(vd["strength"]),
                steps=int(vd["steps"]),
                seed_override=(None if vd.get("seed_override") in (None, "")
                               else int(vd["seed_override"])),
                positive_prompt=str(vd.get("positive_prompt", "")),
                negative_prompt=(None if vd.get("negative_prompt", None) is None
                                 else str(vd["negative_prompt"])),
                guidance=float(vd.get("guidance", default_guidance)),
                is_control=bool(vd.get("is_control", False)),
            )
            for vd in raw["variants"]
        )
        if not variants:
            raise ValueError("runset has zero variants")
        return cls(
            name=str(raw.get("name", "unnamed")),
            render_dpi=int(raw.get("render_dpi", 200)),
            diffusion=diffusion,
            describe=describe,
            contact_sheet=contact_sheet,
            variants=variants,
        )

    @classmethod
    def load(cls, path: Path) -> "RunConfig":
        with Path(path).open() as f:
            raw = json.load(f)
        return cls.from_dict(raw)

    # ----- derived helpers -----
    def contact_sheet_dims(self) -> tuple[int, int]:
        """(rows, cols) sized to fit every variant."""
        cols = max(1, int(self.contact_sheet.cols))
        rows = max(1, math.ceil(len(self.variants) / cols))
        return rows, cols


# ----- v1 → v2 migration -----


def _migrate_v1_to_v2(raw: dict) -> dict:
    """In-place-ish migration of a v1 runset dict to v2 shape.

    Old: diffusion = {base_side, long_side_max, guidance}.
    New: diffusion = {scale_percent, long_side_max, guidance}.
    We can't perfectly translate base_side (which set the SHORT side directly
    in pixels) into a percentage without knowing the source image — so we
    default to 30% (matches the previous default-render behavior) and keep
    long_side_max as a safety cap. The user can edit it in the web UI.

    Each variant inherits guidance from the v1 diffusion.guidance, and
    gets negative_prompt=null (auto LLM description) by default.
    """
    new = dict(raw)
    d = dict(raw.get("diffusion", {}))
    default_guidance = float(d.get("guidance", 7.0))
    long_side_max = int(d.get("long_side_max", 768))
    new["diffusion"] = {
        "scale_percent": 30.0,
        "long_side_max": long_side_max,
        "guidance": default_guidance,
    }
    new_variants = []
    for vd in raw.get("variants", []):
        nv = dict(vd)
        nv.setdefault("guidance", default_guidance)
        nv.setdefault("negative_prompt", None)
        new_variants.append(nv)
    new["variants"] = new_variants
    new["version"] = 2

    print(
        "[runset] auto-migrated v1 file to v2: scale_percent=30%, "
        f"long_side_max={long_side_max}, every variant inherited "
        f"guidance={default_guidance} and negative_prompt=null (use LLM "
        "description). Open it in webui/index.html to tune the new fields.",
        file=sys.stderr,
    )
    return new


# ----- default variant table (mirrors the spec discussed in chat) -----


def _default_variants(default_guidance: float) -> tuple[Variant, ...]:
    g = default_guidance
    return (
        Variant(
            slot=1, filename="sequel_01_control.png", label="control",
            strength=config.CONTROL_STRENGTH, steps=config.CONTROL_STEPS,
            seed_override=None,
            positive_prompt=config.CONTROL_POSITIVE_PROMPT,
            negative_prompt=None, guidance=g, is_control=True,
        ),
        Variant(
            slot=2, filename="sequel_02_opposite.png",
            label="opposite  s=0.40",
            strength=0.40, steps=config.SEQUEL_DEFAULT_STEPS,
            seed_override=None,
            positive_prompt="generate the opposite image",
            negative_prompt=None, guidance=g,
        ),
        Variant(
            slot=3, filename="sequel_03_better.png",
            label="better  s=0.40",
            strength=0.40, steps=config.SEQUEL_DEFAULT_STEPS,
            seed_override=None,
            positive_prompt="generate a better image",
            negative_prompt=None, guidance=g,
        ),
        Variant(
            slot=4, filename="sequel_04_s25_st100_seed1.png",
            label="s=0.25  st=100  seed=1",
            strength=0.25, steps=100, seed_override=1, positive_prompt="",
            negative_prompt=None, guidance=g,
        ),
        Variant(
            slot=5, filename="sequel_05_s25_st100_seed42_opposite.png",
            label="opposite  s=0.25  st=100  seed=42",
            strength=0.25, steps=100, seed_override=42,
            positive_prompt="generate the opposite image",
            negative_prompt=None, guidance=g,
        ),
        Variant(
            slot=6, filename="sequel_06_s33_st100_seed69.png",
            label="s=0.33  st=100  seed=69",
            strength=0.33, steps=100, seed_override=69, positive_prompt="",
            negative_prompt=None, guidance=g,
        ),
        Variant(
            slot=7, filename="sequel_07_s40_st50_seed1.png",
            label="s=0.40  seed=1",
            strength=0.40, steps=config.SEQUEL_DEFAULT_STEPS,
            seed_override=1, positive_prompt="",
            negative_prompt=None, guidance=g,
        ),
        Variant(
            slot=8, filename="sequel_08_s50_st50_seed2.png",
            label="s=0.50  seed=2",
            strength=0.50, steps=config.SEQUEL_DEFAULT_STEPS,
            seed_override=2, positive_prompt="",
            negative_prompt=None, guidance=g,
        ),
        Variant(
            slot=9, filename="sequel_09_s50_st50_seed3.png",
            label="s=0.50  seed=3",
            strength=0.50, steps=config.SEQUEL_DEFAULT_STEPS,
            seed_override=3, positive_prompt="",
            negative_prompt=None, guidance=g,
        ),
        Variant(
            slot=10, filename="sequel_10_s60_st50_seed4.png",
            label="s=0.60  seed=4",
            strength=0.60, steps=config.SEQUEL_DEFAULT_STEPS,
            seed_override=4, positive_prompt="",
            negative_prompt=None, guidance=g,
        ),
        Variant(
            slot=11, filename="sequel_11_s70_st50_seed5.png",
            label="s=0.70  seed=5",
            strength=0.70, steps=config.SEQUEL_DEFAULT_STEPS,
            seed_override=5, positive_prompt="",
            negative_prompt=None, guidance=g,
        ),
        Variant(
            slot=12, filename="sequel_12_s80_same.png",
            label="same  s=0.80",
            strength=0.80, steps=config.SEQUEL_DEFAULT_STEPS,
            seed_override=None,
            positive_prompt="generate the exact same image",
            negative_prompt=None, guidance=g,
        ),
    )
