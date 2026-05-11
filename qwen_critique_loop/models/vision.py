"""InstructBLIP image-description model — CPU, CUDA, or MPS (Apple Silicon).

InstructBLIP is built into transformers (no trust_remote_code, no vendored
modeling files). It accepts a free-form question prompt and produces a
structured, technical answer.

The pipeline calls `answer()` once per question per page and stitches the
answers into the final description that drives the diffusion negative prompt.

Approximate per-answer runtime:
    - Ryzen 9 8945HS (CPU):   25-40 s
    - M1 Max (MPS, fp32):      5-12 s
    - Recent Nvidia GPU (CUDA fp16): 2-5 s

~5 GB on disk.
"""

from pathlib import Path

from PIL import Image

from .. import config
from .device import get_device


class VisionModel:
    def __init__(self, model_id: str = config.VLM_MODEL,
                 device_request: str = "auto"):
        self.model_id = model_id
        self.device_request = device_request
        self.model = None
        self.processor = None
        self.device = None
        self.dtype = None

    def _ensure_loaded(self) -> None:
        if self.model is not None:
            return
        import torch
        from transformers import (
            InstructBlipProcessor,
            InstructBlipForConditionalGeneration,
        )
        torch.set_num_threads(config.NUM_THREADS)

        self.device, self.dtype = get_device(self.device_request)  # type: ignore[arg-type]

        self.processor = InstructBlipProcessor.from_pretrained(self.model_id)
        self.model = InstructBlipForConditionalGeneration.from_pretrained(
            self.model_id,
            torch_dtype=self.dtype,
        )
        self.model.eval()
        if self.device != "cpu":
            self.model.to(self.device)

    def answer(self, image_path: Path, question: str,
               max_new_tokens: int = config.VLM_MAX_TOKENS) -> str:
        """Return the model's answer to a single question about the image.

        The model is loaded lazily on the first call and reused across
        subsequent calls for cheap multi-question inference."""
        self._ensure_loaded()
        import torch
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, text=question, return_tensors="pt")
        if self.device != "cpu":
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
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

    # Back-compat alias.
    def describe(self, image_path: Path,
                 max_new_tokens: int = config.VLM_MAX_TOKENS,
                 prompt: str = "Describe this photograph in detail.") -> str:
        return self.answer(image_path, prompt, max_new_tokens=max_new_tokens)
