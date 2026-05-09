"""InstructBLIP image-description model.

InstructBLIP is built into transformers (no trust_remote_code, no vendored
modeling files). It accepts a free-form question prompt and produces a
structured, technical answer.

The pipeline calls `answer()` five times per page with five different
questions (subject, location, time, purpose, camera) and stitches the
answers into the final per-page description that drives the diffusion
negative prompt.

~5 GB on disk, ~25-40 seconds per answer on a Ryzen 9 8945HS.
"""

from pathlib import Path

from PIL import Image

from .. import config


class VisionModel:
    def __init__(self, model_id: str = config.VLM_MODEL):
        self.model_id = model_id
        self.model = None
        self.processor = None

    def _ensure_loaded(self) -> None:
        if self.model is not None:
            return
        import torch
        from transformers import (
            InstructBlipProcessor,
            InstructBlipForConditionalGeneration,
        )
        torch.set_num_threads(config.NUM_THREADS)
        self.processor = InstructBlipProcessor.from_pretrained(self.model_id)
        self.model = InstructBlipForConditionalGeneration.from_pretrained(
            self.model_id
        )
        self.model.eval()

    def answer(self, image_path: Path, question: str,
               max_new_tokens: int = config.VLM_MAX_TOKENS) -> str:
        """Return the model's answer to a single question about the image.

        The model is loaded lazily on the first call and reused across
        subsequent calls for cheap multi-question inference."""
        self._ensure_loaded()
        import torch
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, text=question, return_tensors="pt")
        with torch.inference_mode():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                num_beams=3,
                do_sample=False,
                length_penalty=1.0,
                repetition_penalty=1.5,
            )
        return self.processor.batch_decode(
            output_ids, skip_special_tokens=True
        )[0].strip()

    # Back-compat alias (older call sites used `describe`).
    def describe(self, image_path: Path,
                 max_new_tokens: int = config.VLM_MAX_TOKENS,
                 prompt: str = "Describe this photograph in detail.") -> str:
        return self.answer(image_path, prompt, max_new_tokens=max_new_tokens)
