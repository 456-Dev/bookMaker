"""Locate ffmpeg and ffprobe for the video pipeline.

Resolution order (first working executable wins):
    1. ``IMGSEQUEL_FFMPEG`` / ``IMGSEQUEL_FFPROBE`` — explicit paths
    2. If only ``IMGSEQUEL_FFMPEG`` is set, ``ffprobe`` in the same directory
    3. ``shutil.which("ffmpeg")`` / ``which("ffprobe")``
    4. Typical install locations (Linux/macOS homebrew)
"""

from __future__ import annotations

import os
import shutil
import sys
from functools import lru_cache
from pathlib import Path

_ENV_FFMPEG = "IMGSEQUEL_FFMPEG"
_ENV_FFPROBE = "IMGSEQUEL_FFPROBE"

_SEARCH_DIRS = (
    "/usr/bin",
    "/usr/local/bin",
    "/opt/homebrew/bin",
    "/snap/bin",
)


def _is_executable(path: Path) -> bool:
    try:
        return path.is_file() and os.access(path, os.X_OK)
    except OSError:
        return False


def _collect_candidates(name: str, sibling_of: Path | None) -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []

    def add(p: Path) -> None:
        key = str(p.expanduser().resolve(strict=False))
        if key not in seen:
            seen.add(key)
            out.append(p.expanduser())

    if name == "ffmpeg":
        raw = os.environ.get(_ENV_FFMPEG, "").strip()
        if raw:
            add(Path(raw))
    else:
        raw = os.environ.get(_ENV_FFPROBE, "").strip()
        if raw:
            add(Path(raw))

    if name == "ffprobe" and sibling_of is not None:
        add(sibling_of.parent / "ffprobe")

    w = shutil.which(name)
    if w:
        add(Path(w))

    for d in _SEARCH_DIRS:
        add(Path(d) / name)

    return out


def ffmpeg_install_hint() -> str:
    if sys.platform == "darwin":
        return (
            "Install ffmpeg (e.g. brew install ffmpeg), or set "
            "IMGSEQUEL_FFMPEG / IMGSEQUEL_FFPROBE to full paths."
        )
    return (
        "Install ffmpeg on Debian/Ubuntu:\n"
        "  sudo apt update && sudo apt install -y ffmpeg\n"
        "Or run:\n"
        "  bash scripts/install-ffmpeg.sh\n"
        "Or set IMGSEQUEL_FFMPEG and IMGSEQUEL_FFPROBE to full paths."
    )


@lru_cache(maxsize=1)
def resolve_ffmpeg_ffprobe() -> tuple[Path, Path]:
    """Return (ffmpeg, ffprobe) paths; raise FileNotFoundError if missing."""
    ffmpeg: Path | None = None
    for c in _collect_candidates("ffmpeg", sibling_of=None):
        if _is_executable(c):
            ffmpeg = c.resolve()
            break
    if ffmpeg is None:
        raise FileNotFoundError(
            "ffmpeg not found.\n\n" + ffmpeg_install_hint()
        )

    ffprobe: Path | None = None
    for c in _collect_candidates("ffprobe", sibling_of=ffmpeg):
        if _is_executable(c):
            ffprobe = c.resolve()
            break
    if ffprobe is None:
        raise FileNotFoundError(
            "ffprobe not found (usually installed with ffmpeg).\n\n"
            + ffmpeg_install_hint()
        )

    return ffmpeg, ffprobe