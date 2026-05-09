"""Stage 3: describe the prepared image with the VLM.

The VLM is asked five separate questions and the answers are stitched into a
single paragraph that becomes the per-page description (and, in turn, the
diffusion negative prompt).

Cache layout in each page dir:
    description_q01_subject.txt
    description_q02_location.txt
    description_q03_time.txt
    description_q04_purpose.txt
    description_q05_camera.txt
    description.txt              (stitched paragraph — cached final output)

Resume:
    - If `description.txt` exists, return it as-is.
    - Otherwise, for each of the five questions, look for the per-question
      cache file. Generate any missing answers, then stitch.
    - An interrupted run loses at most ONE in-flight question (~30s on CPU).
"""

from pathlib import Path
from typing import Callable, Optional

from ..models.vision import VisionModel
from .. import config


def _question_filename(slot: int, key: str) -> str:
    return f"description_q{slot:02d}_{key}.txt"


def _per_question_paths(page_dir: Path) -> list[tuple[str, str, Path]]:
    """Return (key, question, path) for each of the five questions."""
    out: list[tuple[str, str, Path]] = []
    for i, (key, question) in enumerate(config.VLM_DESCRIBE_QUESTIONS, start=1):
        out.append((key, question, page_dir / _question_filename(i, key)))
    return out


def _stitch(answers: list[tuple[str, str]]) -> str:
    """Join the five answers into a single paragraph. Each answer becomes one
    sentence-ish chunk; trailing punctuation is normalized."""
    parts: list[str] = []
    for _, ans in answers:
        a = ans.strip()
        if not a:
            continue
        if a[-1] not in ".!?":
            a += "."
        parts.append(a)
    return " ".join(parts)


def describe_image(
    vlm: VisionModel,
    prepared_path: Path,
    output_path: Path,
    on_question: Optional[Callable[[int, int, str, str, bool], None]] = None,
) -> str:
    """Generate the per-page description by asking the five configured
    questions; cache to disk. Returns the stitched description string.

    `on_question(slot, total, key, answer, was_cached)` is called after each
    question completes — used for progress reporting.
    """
    if output_path.exists():
        return output_path.read_text().strip()

    page_dir = output_path.parent
    page_dir.mkdir(parents=True, exist_ok=True)

    questions = _per_question_paths(page_dir)
    answers: list[tuple[str, str]] = []

    for slot, (key, question, qpath) in enumerate(questions, start=1):
        if qpath.exists():
            ans = qpath.read_text().strip()
            was_cached = True
        else:
            ans = vlm.answer(prepared_path, question,
                             max_new_tokens=config.VLM_MAX_TOKENS).strip()
            qpath.write_text(ans)
            was_cached = False
        answers.append((key, ans))
        if on_question is not None:
            on_question(slot, len(questions), key, ans, was_cached)

    paragraph = _stitch(answers)
    output_path.write_text(paragraph)
    return paragraph
