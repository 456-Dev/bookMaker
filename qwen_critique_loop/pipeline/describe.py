"""Stage 3: describe the prepared image with the VLM.

The VLM is asked one question at a time. The list of questions and the
generation-token budget come from the active `RunConfig.describe`. The
answers are stitched into a single paragraph that becomes the per-page
description and the diffusion negative prompt.

Cache layout in each page dir:
    description_q01_<key>.txt    one file per question
    description.txt              stitched paragraph (final cached output)

Resume:
    - If `description.txt` exists, return it as-is.
    - Otherwise, for each question, look for the per-question cache file.
      Generate any missing answers, then stitch.
    - An interrupted run loses at most ONE in-flight question.
"""

from pathlib import Path
from typing import Callable, Optional, Sequence

from ..models.vision import VisionModel
from ..runset import DescribeQuestion


def _question_filename(slot: int, key: str) -> str:
    return f"description_q{slot:02d}_{key}.txt"


def _stitch(answers: Sequence[tuple[str, str]]) -> str:
    """Join the answers into a single paragraph. Each answer becomes one
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
    questions: Sequence[DescribeQuestion],
    max_tokens: int,
    on_question: Optional[Callable[[int, int, str, str, bool], None]] = None,
) -> str:
    """Generate the per-page description by asking the configured questions;
    cache to disk. Returns the stitched description string.

    `on_question(slot, total, key, answer, was_cached)` is called after each
    question completes — used for progress reporting.
    """
    if output_path.exists():
        return output_path.read_text().strip()

    page_dir = output_path.parent
    page_dir.mkdir(parents=True, exist_ok=True)

    if not questions:
        raise ValueError("describe_image requires at least one question")

    answers: list[tuple[str, str]] = []
    total = len(questions)

    for slot, q in enumerate(questions, start=1):
        qpath = page_dir / _question_filename(slot, q.key)
        if qpath.exists():
            ans = qpath.read_text().strip()
            was_cached = True
        else:
            ans = vlm.answer(prepared_path, q.question,
                             max_new_tokens=max_tokens).strip()
            qpath.write_text(ans)
            was_cached = False
        answers.append((q.key, ans))
        if on_question is not None:
            on_question(slot, total, q.key, ans, was_cached)

    paragraph = _stitch(answers)
    output_path.write_text(paragraph)
    return paragraph
