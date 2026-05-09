"""BLIP image captioning — simple, reliable, CPU-friendly.

BLIP is a built-in transformers model (no trust_remote_code, no vendored
modeling files). It generates a single caption per image; we use that
caption verbatim as the negative prompt for the diffusion stage.

~1 GB on disk, ~1 second per caption on a Ryzen 9 8945HS.
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
        from transformers import BlipProcessor, BlipForConditionalGeneration
        torch.set_num_threads(config.NUM_THREADS)
        self.processor = BlipProcessor.from_pretrained(self.model_id)
        self.model = BlipForConditionalGeneration.from_pretrained(self.model_id)
        self.model.eval()

    def describe(self, image_path: Path,
                 max_new_tokens: int = config.VLM_MAX_TOKENS) -> str:
        """Return a single content caption for the image."""
        self._ensure_loaded()
        import torch
        image = Image.open(image_path).convert("RGB")
        # The conditional prefix nudges BLIP toward longer, more descriptive
        # captions than its default unconditioned mode.
        inputs = self.processor(image, "a photograph of", return_tensors="pt")
        with torch.inference_mode():
            output_ids = self.model.generate(**inputs, max_new_tokens=max_new_tokens)
        caption = self.processor.decode(output_ids[0], skip_special_tokens=True).strip()
        # Strip the conditional prefix if BLIP echoed it back
        if caption.lower().startswith("a photograph of"):
            caption = caption[len("a photograph of"):].lstrip()
        return caption
