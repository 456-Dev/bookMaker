"""Run-directory layout + per-page artifact paths.

Layout:
  runs/<timestamp>_<pdf-stem>/
    progress.txt                       - tail-able progress log
    run.json                           - structured manifest of pages, params, variants
    page_001/
      rendered.png                     - PDF page rendered at config.PDF_RENDER_DPI
      prepared.png                     - aspect-ratio-preserving resize for diffusion
      description_q01_subject.txt      - VLM answer: what is in the image
      description_q02_location.txt     - VLM answer: where it was taken
      description_q03_time.txt         - VLM answer: when it was taken
      description_q04_purpose.txt      - VLM answer: why it was taken
      description_q05_camera.txt       - VLM answer: camera settings + lighting + editing
      description.txt                  - five answers stitched into a paragraph
      sequel_01_control.png            - control sequel (positive prompt)
      sequel_02_opposite.png           - "generate the opposite image"
      sequel_03_better.png             - "generate a better image"
      sequel_04_s25_st100_seed1.png    - explicit-param variants begin here
      sequel_05_s25_st100_seed42_opposite.png
      sequel_06_s33_st100_seed69.png
      sequel_07_s40_st50_seed1.png
      sequel_08_s50_st50_seed2.png
      sequel_09_s50_st50_seed3.png
      sequel_10_s60_st50_seed4.png
      sequel_11_s70_st50_seed5.png
      sequel_12_s80_same.png           - "generate the exact same image"
      contact_sheet.png                - 4x3 grid of all 12 variants
    page_002/
      ...
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .. import config


def create_run_dir(input_pdf: Path) -> Path:
    """Create a run directory. Does NOT copy the PDF — manifest stores the
    absolute path instead, so the PDF stays where it is."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = config.RUNS_DIR / f"{timestamp}_{input_pdf.stem}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def page_dir(run_dir: Path, page_idx: int) -> Path:
    """1-based page index. zero-padded directory name."""
    d = run_dir / f"page_{page_idx:03d}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def page_artifact(run_dir: Path, page_idx: int, name: str) -> Path:
    return page_dir(run_dir, page_idx) / name


def write_manifest(run_dir: Path, manifest: dict[str, Any]) -> Path:
    p = run_dir / "run.json"
    with p.open("w") as f:
        json.dump(manifest, f, indent=2, default=str)
    return p


def read_manifest(run_dir: Path) -> dict[str, Any]:
    p = run_dir / "run.json"
    if not p.exists():
        return {}
    with p.open() as f:
        return json.load(f)


def find_latest_run() -> Path | None:
    if not config.RUNS_DIR.exists():
        return None
    candidates = [p for p in config.RUNS_DIR.iterdir() if p.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)
