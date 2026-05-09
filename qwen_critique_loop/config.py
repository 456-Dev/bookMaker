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

# ---------- Cropping ----------
# Method for cropping the rendered page down to a square:
#   "center"     — fast center crop (instantaneous, may cut off important edges)
#   "seam_carve" — content-aware seam carving (~5-15s per page, preserves subjects)
CROP_METHOD = "center"
# Side length of the square crop. AUTO = min(width, height) of the rendered page.
SQUARE_SIDE = "AUTO"

# ---------- Vision / VLM model ----------
# InstructBLIP-FlanT5-XL — instruction-following caption model, built into
# transformers (no trust_remote_code). ~5GB, ~25-40 seconds per description
# on Ryzen 9 8945HS.
VLM_MODEL = "Salesforce/instructblip-flan-t5-xl"
VLM_MAX_TOKENS = 250
VLM_DESCRIBE_PROMPT = (
    "Provide a detailed technical description of this photograph. "
    "Describe the subject (who or what, their pose, expression, clothing, action), "
    "the setting (indoor or outdoor, location, era, identifying features), "
    "the lighting (direction, hardness or softness, color temperature, contrast), "
    "the composition (framing, camera angle, focal length feel, depth of field), "
    "the color palette (dominant hues, saturation, mood of the colors), "
    "the era and style cues (film stock or digital, decade, photographic genre), "
    "and any notable objects, textures, or imperfections. "
    "Use precise photographic terminology. Be specific and concrete."
)

# ---------- Diffusion model ----------
DIFFUSION_MODEL = "Lykon/dreamshaper-7"
DIFFUSION_GUIDANCE = 7.0
DIFFUSION_RESOLUTION = 512   # SD 1.5 native — going higher on CPU is impractical

# ---------- Sequel sweep (per page) ----------
# 9-grid: every combination of strength × steps. All ten sequels share the same
# per-page seed, so the grid is a clean parameter sweep — only strength/steps
# vary across the 9, and the control isolates the positive-prompt effect.
SEQUEL_STRENGTHS = [0.25, 0.50, 0.75]
SEQUEL_STEPS = [13, 25, 50]

# Empty positive prompt by design — the description (negative) does the steering.
POSITIVE_PROMPT = ""

# Control variant: same seed, fixed (strength, steps), but with a positive prompt.
CONTROL_POSITIVE_PROMPT = "realistic street photograph"
CONTROL_STRENGTH = 0.50
CONTROL_STEPS = 25

# ---------- CPU thread tuning ----------
NUM_THREADS = os.cpu_count() or 8

# ---------- Progress display ----------
PROGRESS_FILE = "progress.txt"
