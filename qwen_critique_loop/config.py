"""Central configuration.

Target hardware: AMD Ryzen 9 8945HS / 32GB RAM / CPU-only inference.
"""

import os
from pathlib import Path

# ---------- Paths ----------
PROJECT_ROOT = Path(__file__).parent
RUNS_DIR = PROJECT_ROOT / "runs"

# ---------- PDF rendering ----------
PDF_RENDER_DPI = 200  # 200 dpi gives ~1650x2200 for a US-letter page

# ---------- Seam carving ----------
# Side length of the square crop. AUTO = min(width, height) of the rendered page.
# Or pass an int (e.g. 768) to force a fixed side length (faster, less detail).
SQUARE_SIDE = "AUTO"

# ---------- Vision / VLM model ----------
# BLIP image captioning — built into transformers (no trust_remote_code),
# ~1GB on disk, ~1 second per caption on Ryzen 9 8945HS. Generates a single
# content caption that fits SD 1.5's 77-token CLIP window.
VLM_MODEL = "Salesforce/blip-image-captioning-large"
VLM_MAX_TOKENS = 60

# ---------- Diffusion model ----------
# SD 1.5 photoreal community model. Self-contained (no separate VAE),
# safety_checker disabled at load time. ~30-60s per 512x512 image on this CPU.
DIFFUSION_MODEL = "Lykon/dreamshaper-7"
DIFFUSION_STEPS = 25
DIFFUSION_GUIDANCE = 7.0
DIFFUSION_RESOLUTION = 512   # SD 1.5 native — going higher on CPU is impractical
IMG2IMG_STRENGTH = 0.5       # 0.5 = clear deviation while keeping composition

# Empty positive prompt by design (option 1a) — the negative prompt
# (image's own description) does the steering, init image holds composition.
POSITIVE_PROMPT = ""

# ---------- CPU thread tuning ----------
# Use all logical cores for torch ops. Set to a smaller number if you want
# to leave headroom for other tasks.
NUM_THREADS = os.cpu_count() or 8

# ---------- Progress display ----------
# Live progress is written to runs/<run>/progress.txt so you can `tail -f`
# from another SSH session.
PROGRESS_FILE = "progress.txt"
