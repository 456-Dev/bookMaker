# Qwen × SDXL Critique Loop

A local pipeline that uses **Qwen2.5-VL 72B** (via MLX) and a **Stable Diffusion XL** model
to critique a photograph, generate an "improved" version, then blind-test which is better.

Designed for Apple Silicon (M1/M2/M3 Max with 64 GB unified memory).

## Pipeline

```
input image
    │
    ▼
[1] Qwen2.5-VL  ──►  photographic critique (composition, lighting, color, …)
    │
    ▼
[2] Qwen2.5-VL  ──►  improved SDXL prompt (sees both image + critique)
    │
    ▼
[3] SDXL        ──►  sequel image
    │
    ▼
[4] Qwen2.5-VL  ──►  blind A/B test (does NOT know which is which)
    │
    ▼
verdict: original | sequel | tie
```

Every run lands in `runs/<timestamp>_<image_stem>/` containing the original, the sequel,
a structured `run.json`, and a human-readable `summary.md`.

## Setup

```bash
# 1. Python 3.11 recommended
python3.11 -m venv .venv
source .venv/bin/activate

# 2. Install deps
pip install -r requirements.txt

# 3. (First run will download ~40 GB for Qwen 72B-4bit and ~7 GB for SDXL.
#    Models cache to ~/.cache/huggingface)
```

## Usage

```bash
# From the parent directory of qwen_critique_loop/
python -m qwen_critique_loop.main path/to/photo.jpg

# Reproducible diffusion
python -m qwen_critique_loop.main path/to/photo.jpg --seed 42
```

## Configuration

Edit `config.py` to swap models or adjust generation:

| Setting | Purpose |
|---|---|
| `VLM_MODEL` | Swap to `Qwen2.5-VL-32B-Instruct-4bit` if RAM is tight |
| `DIFFUSION_MODEL` | Any SDXL HF repo: `RunDiffusion/Juggernaut-XL-v9`, `SG161222/RealVisXL_V4.0`, `stablediffusionapi/pony-diffusion-v6-xl`, etc. |
| `MEMORY_MODE` | `"sequential"` (safer, ~40 GB peak) or `"concurrent"` (faster, ~50 GB peak) |
| `DIFFUSION_STEPS` | More steps = more detail, slower |
| `ALLOW_TIE_VERDICT` | If False, judge must pick a winner |

## Memory Notes (64 GB M1 Max)

- Qwen2.5-VL-72B (4-bit): **~40 GB**
- SDXL (fp16):             **~7 GB**
- Concurrent peak:         **~50 GB** — possible but leaves little headroom; close browsers.
- Sequential mode unloads each model between stages — slower (re-load ~30 s) but much safer.

If you see swap pressure (check Activity Monitor → Memory → Swap Used), switch to sequential
mode or drop to the 32B VLM.

## Blind Test Integrity

The blind A/B stage is the trust-anchor of this whole experiment. To prevent leakage:

1. Both images are **copied to a clean staging dir** with neutral filenames (`image_A.png`, `image_B.png`).
2. Original/sequel are **randomly assigned** to A/B per run.
3. The judge prompt **never names** which is which.
4. The verdict (`A`/`B`/`TIE`) is parsed first, then unmapped to `original`/`sequel`/`tie` only after.

If you ever want to audit: `runs/<run>/blind_staging/` keeps the exact files the judge saw,
and `run.json` records the mapping.

## Path to Recursion

The pipeline is built so recursion is a thin wrapper. To turn one shot into a generational
loop, write a `recursive.py` that:

1. Calls `run_once(image)` and reads the verdict from the returned record.
2. If `verdict == "sequel"` and `depth < MAX_RECURSION_DEPTH`, call `run_once(sequel_image)`.
3. Otherwise stop.
4. Save a `lineage.json` linking each generation to its parent.

Open questions worth thinking about before recursing:
- **Stop conditions**: stop on first loss? after N consecutive losses? after fixed depth?
- **Drift**: each generation will pull the image away from the original subject. Do you want
  to penalize semantic drift (e.g. include a "fidelity to original subject" criterion in the
  judge rubric)?
- **Seed control**: fix the diffusion seed across generations, or let it vary?
- **Tournament mode**: instead of linear recursion, generate K sequels and have the judge
  pick the best, then iterate on that one.

## Files

```
qwen_critique_loop/
├── README.md
├── requirements.txt
├── config.py             ← all knobs live here
├── main.py               ← orchestrator + CLI
├── models/
│   ├── vision.py         ← Qwen2.5-VL via MLX
│   └── diffusion.py      ← SDXL via diffusers + MPS
├── pipeline/
│   ├── critique.py       ← stage 1
│   ├── prompt_gen.py     ← stage 2
│   ├── generate.py       ← stage 3
│   └── blind_test.py     ← stage 4 (with integrity guarantees)
├── prompts/
│   ├── critique.txt
│   ├── prompt_gen.txt
│   └── blind_test.txt
├── utils/
│   └── io.py             ← run dir + JSON/MD logs
└── runs/                 ← timestamped outputs land here
```

## Troubleshooting

**`mlx_vlm` import error** → Install with `pip install -U mlx-vlm`. Requires macOS 13.5+.

**SDXL download stalls** → HuggingFace can rate-limit. Pre-download with
`huggingface-cli download Lykon/dreamshaper-xl-v2-turbo`.

**Out of memory** → Switch `MEMORY_MODE = "sequential"`, or drop to the 32B Qwen.

**Judge picks the original most of the time** → That's a real signal. Likely causes: critique
isn't translating to actionable prompt changes, or SDXL can't match the realism of a real
photo. Try a more photorealistic SDXL fine-tune (RealVisXL, Juggernaut XL).
