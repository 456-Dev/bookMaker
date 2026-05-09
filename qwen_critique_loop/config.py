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
# transformers (no trust_remote_code). ~5GB, ~25-40 seconds per description
# on Ryzen 9 8945HS.
VLM_MODEL = "Salesforce/instructblip-flan-t5-xl"
VLM_MAX_TOKENS = 320
VLM_DESCRIBE_PROMPT = (
    "Provide an exhaustive technical breakdown of this photograph as if you "
    "were reverse-engineering it for a reshoot. Be precise and concrete; use "
    "professional photographic and post-production terminology. Cover:\n"
    "1. Subject — who or what, pose, expression, gaze direction, wardrobe, "
    "props, action, and the relationship between subjects.\n"
    "2. Setting — indoor or outdoor, location type, era, geography cues, "
    "background elements, foreground elements, time of day.\n"
    "3. Camera & lens — likely camera format (35mm, medium format, digital), "
    "focal length in mm, aperture (f-stop) inferred from depth of field, "
    "shutter speed inferred from motion blur or freeze, ISO inferred from "
    "grain or noise, lens character (sharpness, distortion, vignetting, "
    "bokeh shape and quality, lens flare).\n"
    "4. Lighting — number and direction of light sources (key, fill, rim, "
    "background), hardness or softness, color temperature in Kelvin, "
    "contrast ratio, presence of practical lights, ambient versus artificial.\n"
    "5. Composition — framing (close-up, medium, wide), camera height and "
    "angle, rule-of-thirds or symmetry, leading lines, negative space, "
    "depth of field, plane of focus.\n"
    "6. Color & tone — dominant hues, saturation level, color palette "
    "relationships (complementary, analogous, monochromatic), shadow tint, "
    "highlight tint, overall mood.\n"
    "7. Editing & post-processing style — color grading approach (teal-orange, "
    "bleach bypass, cross-process, neutral), contrast curve (flat, punchy, "
    "crushed blacks, lifted shadows), grain or noise structure, sharpening, "
    "skin retouching, dodge and burn, film emulation versus clean digital.\n"
    "8. Era and genre cues — film stock if applicable, decade, photographic "
    "genre (fashion, photojournalism, street, portrait, editorial), "
    "stylistic references.\n"
    "9. Notable textures, surface details, imperfections, scratches, dust, "
    "and any artifacts of the medium."
)

# ---------- Diffusion model ----------
DIFFUSION_MODEL = "Lykon/dreamshaper-7"
DIFFUSION_GUIDANCE = 7.0

# ---------- Sequel sweep (per page) ----------
# 9-grid: every combination of strength × seed_index. Steps are fixed (a single
# value); the seed dimension surfaces noise variability at each strength so we
# can see how stable a given (strength, prompt) pair is, rather than how it
# responds to step-count.
SEQUEL_STRENGTHS = [0.25, 0.50, 0.75]
SEQUEL_STEPS = 25                 # fixed step count for every variant
SEQUEL_SEEDS_PER_STRENGTH = 3     # 3 strengths × 3 seeds = 9 variants

# Empty positive prompt by design — the description (negative) does the steering.
POSITIVE_PROMPT = ""

# Control variant: same as a middle-grid cell but with a positive prompt added.
# Uses the page seed (the same seed the first column of the grid uses), so the
# only thing that changes vs that cell is the positive prompt.
CONTROL_POSITIVE_PROMPT = "realistic street photograph"
CONTROL_STRENGTH = 0.50
CONTROL_STEPS = 25

# ---------- CPU thread tuning ----------
NUM_THREADS = os.cpu_count() or 8

# ---------- Progress display ----------
PROGRESS_FILE = "progress.txt"
