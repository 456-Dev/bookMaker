"""moondream2 image-description model.

CPU-only. Loaded lazily on first use; held in memory for the rest of the run.
Roughly 3.5 GB RAM, ~3 seconds per description on a Ryzen 9 8945HS.
"""

from pathlib import Path
from typing import Optional

from PIL import Image

from .. import config


class VisionModel:
    def __init__(self, model_id: str = config.VLM_MODEL,
                 revision: str = config.VLM_REVISION):
        self.model_id = model_id
        self.revision = revision
        self.model = None
        self.tokenizer = None

    def _ensure_loaded(self) -> None:
        if self.model is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        # Pin number of threads for CPU inference
        torch.set_num_threads(config.NUM_THREADS)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            revision=self.revision,
            trust_remote_code=True,
            torch_dtype=torch.float32,
        )
        self.model.eval()
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_id, revision=self.revision
        )

    def describe(self, image_path: Path,
                 prompt: str = config.VLM_DESCRIBE_PROMPT,
                 max_new_tokens: int = config.VLM_MAX_TOKENS) -> str:
        self._ensure_loaded()
        image = Image.open(image_path).convert("RGB")
        # moondream2 has a one-shot helper that handles image encoding + chat template
        with _no_grad():
            answer = self.model.answer_question(
                self.model.encode_image(image),
                prompt,
                self.tokenizer,
                max_new_tokens=max_new_tokens,
            )
        return answer.strip()


def _no_grad():
    import torch
    return torch.inference_mode()
