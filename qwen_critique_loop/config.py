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

# ---------- Diffusion-input preparation ----------
# The rendered page is resized (preserving aspect ratio) to fit SD 1.5's budget:
# the SHORTER side becomes DIFFUSION_BASE_SIDE, the longer side scales
# proportionally and is rounded to a multiple of 8 (SD's VAE constraint).
# The AI output is emitted at the same non-square dimensions, so the sequel's
# aspect ratio matches the original page.
DIFFUSION_BASE_SIDE = 512        # SD 1.5 native short side; multiple of 8

# Diffusion budget cap. Pixel counts much above 512x512 explode CPU runtime;
# if a page's aspect is so extreme that the long side would exceed this, we
# clamp the short side down. 512x768 ≈ 393K px, ~50% slower than 512x512.
DIFFUSION_LONG_SIDE_MAX = 768

# ---------- Vision / VLM model ----------
# InstructBLIP-FlanT5-XL — instruction-following caption model, built into
# transformers (no trust_remote_code). ~5GB, ~25-40 seconds per answer on
# Ryzen 9 8945HS. We ask FIVE separate questions per image and stitch the
# answers into a single paragraph; that's ~2-3 minutes per page total.
VLM_MODEL = "Salesforce/instructblip-flan-t5-xl"
VLM_MAX_TOKENS = 180

# Five focused questions, asked one at a time. Each answer is cached on disk
# so an interrupted page picks up at the next unanswered question. The final
# `description.txt` is the five answers joined into a paragraph and is what
# gets fed to diffusion as the negative prompt.
VLM_DESCRIBE_QUESTIONS: list[tuple[str, str]] = [
    ("subject",
     "What is in the image? Describe the subject or subjects in detail — "
     "who or what they are, their pose and expression, what they are wearing, "
     "what they are doing, and any notable objects, props, or animals "
     "present."),
    ("location",
     "Where is the image taken? Describe the location and setting — indoor "
     "or outdoor, type of place, identifying landmarks or background "
     "elements, geography or culture cues, foreground and background, and "
     "the spatial relationship between subject and environment."),
    ("time",
     "When was the image taken? Estimate the era (decade or year range), the "
     "season, the time of day, and any cues from clothing, technology, "
     "vehicles, signage, or photographic medium that support that estimate."),
    ("purpose",
     "Why was the image taken? Speculate on the photograph's purpose and "
     "context — editorial, journalistic, portrait commission, family "
     "snapshot, fashion, documentary, advertising — and what the "
     "photographer was trying to communicate or capture."),
    ("camera",
     "What camera settings was the image taken with? Estimate the camera "
     "format (35mm, medium format, digital), focal length in millimetres, "
     "aperture (f-stop) inferred from depth of field, shutter speed inferred "
     "from motion blur or freeze, ISO inferred from grain or noise, and lens "
     "character — sharpness, distortion, vignetting, bokeh, and lens flare. "
     "Also note the lighting setup (key, fill, rim, color temperature) and "
     "the editing or post-processing style (color grading, contrast curve, "
     "grain, sharpening, film emulation)."),
]

# ---------- Diffusion model ----------
DIFFUSION_MODEL = "Lykon/dreamshaper-7"
DIFFUSION_GUIDANCE = 7.0

# ---------- Sequel default ----------
# Default step count when a variant doesn't specify its own. The 12-variant
# table in pipeline/regenerate.py overrides this per row.
SEQUEL_DEFAULT_STEPS = 50

# Empty positive prompt is the default for sweep variants; the description
# (negative) does the steering.
POSITIVE_PROMPT = ""

# Control variant (variant #1 in the 12-row table). Kept the same across
# rounds so it's a stable comparison point.
CONTROL_POSITIVE_PROMPT = "realistic street photograph"
CONTROL_STRENGTH = 0.50
CONTROL_STEPS = 25

# ---------- CPU thread tuning ----------
NUM_THREADS = os.cpu_count() or 8

# ---------- Progress display ----------
PROGRESS_FILE = "progress.txt"
