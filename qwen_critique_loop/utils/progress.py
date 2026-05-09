"""Progress reporting that writes to both stdout and a tail-able log file.

Designed for SSH sessions: open one terminal running the job, open another
terminal running `tail -f runs/<run>/progress.txt` and you can check in any time.
"""

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


class ProgressLog:
    def __init__(self, log_file: Optional[Path] = None):
        self.log_file = log_file
        self.start_time = time.time()
        self._stage_start: Optional[float] = None
        self._stage_label: Optional[str] = None
        if log_file is not None:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            log_file.write_text(f"[{self._ts()}] progress log started\n")

    def _ts(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _elapsed(self) -> str:
        s = int(time.time() - self.start_time)
        h, s = divmod(s, 3600)
        m, s = divmod(s, 60)
        return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"

    def _emit(self, line: str) -> None:
        full = f"[{self._ts()} +{self._elapsed()}] {line}"
        print(full, flush=True)
        if self.log_file is not None:
            with self.log_file.open("a") as f:
                f.write(full + "\n")

    def event(self, msg: str) -> None:
        """One-off log line."""
        self._emit(msg)

    def stage_start(self, label: str) -> None:
        self._stage_start = time.time()
        self._stage_label = label
        self._emit(f"  {label} ...")

    def stage_done(self, detail: str = "") -> None:
        if self._stage_start is None:
            return
        dt = time.time() - self._stage_start
        suffix = f"  {detail}" if detail else ""
        self._emit(f"  {self._stage_label} done in {dt:.1f}s{suffix}")
        self._stage_start = None
        self._stage_label = None

    def page_header(self, page_idx: int, total_pages: int, status: str) -> None:
        bar = self._render_bar(page_idx, total_pages)
        self._emit(f"=== Page {page_idx}/{total_pages}  {bar}  {status} ===")

    def page_done(self, page_idx: int, total_pages: int, sequel_path: Path) -> None:
        eta = self._eta(page_idx, total_pages)
        self._emit(f"   page {page_idx}/{total_pages} -> {sequel_path.name}  ETA total: {eta}")

    def _render_bar(self, done: int, total: int, width: int = 24) -> str:
        if total <= 0:
            return ""
        filled = int(width * done / total)
        return "[" + "#" * filled + "-" * (width - filled) + f"] {100*done/total:>5.1f}%"

    def _eta(self, done: int, total: int) -> str:
        if done <= 0:
            return "—"
        elapsed = time.time() - self.start_time
        per = elapsed / done
        remaining = per * (total - done)
        s = int(remaining)
        h, s = divmod(s, 3600)
        m, s = divmod(s, 60)
        return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"

    def banner(self, msg: str) -> None:
        self._emit("")
        self._emit("===== " + msg + " =====")
