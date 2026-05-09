"""Run-directory layout + per-page artifact paths.

Layout:
  runs/<timestamp>_<pdf-stem>/
    progress.txt               - tail-able progress log
    run.json                   - structured manifest of pages and stages
    page_001/
      rendered.png
      square.png
      description.txt
      sequel.png
    page_002/
      ...
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from .. import config


def create_run_dir(input_pdf: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = config.RUNS_DIR / f"{timestamp}_{input_pdf.stem}"
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(input_pdf, run_dir / input_pdf.name)
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
