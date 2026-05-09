"""SD 1.5 img2img model, CPU-only.

Photoreal SD 1.5 community model at 512x512. Empty positive prompt by design;
the per-page negative prompt is what steers the result. Runs in ~30-60s per
image on a Ryzen 9 8945HS.

The pipeline is shared between img2img calls — loaded once on first use.
"""

from pathlib import Path
from typing import Optional, Union

from PIL import Image

from .. import config


def _resize_for_sd15(img: Image.Image, side: int) -> Image.Image:
    """SD 1.5 prefers square 512x512. Resize to a square at `side` px."""
    return img.resize((side, side), Image.LANCZOS)


class DiffusionModel:
    def __init__(self, model_id: str = config.DIFFUSION_MODEL):
        self.model_id = model_id
        self.pipe = None
        self.device = None
        self.dtype = None

    def _ensure_loaded(self) -> None:
        if self.pipe is not None:
            return
        import torch
        from diffusers import StableDiffusionImg2ImgPipeline, DPMSolverMultistepScheduler
        torch.set_num_threads(config.NUM_THREADS)

        # GPU auto-detect: ROCm (AMD) and CUDA (Nvidia) both report as "cuda"
        # in PyTorch. fp16 on GPU is ~2x faster than fp32 with negligible
        # quality loss for SD 1.5.
        if torch.cuda.is_available():
            self.device = "cuda"
            self.dtype = torch.float16
        else:
            self.device = "cpu"
            self.dtype = torch.float32

        self.pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
            self.model_id,
            torch_dtype=self.dtype,
            safety_checker=None,
            requires_safety_checker=False,
        )
        self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
            self.pipe.scheduler.config
        )
        self.pipe = self.pipe.to(self.device)
        self.pipe.set_progress_bar_config(leave=False)
        # Attention slicing reduces peak memory; helpful on iGPUs that share
        # system RAM and on CPU. Negligible cost on dedicated GPUs.
        self.pipe.enable_attention_slicing("max")

    def img2img(
        self,
        init_image_path: Path,
        output_path: Path,
        positive_prompt: str = config.POSITIVE_PROMPT,
        negative_prompt: str = "",
        steps: int = config.DIFFUSION_STEPS,
        guidance: float = config.DIFFUSION_GUIDANCE,
        strength: float = config.IMG2IMG_STRENGTH,
        side: int = config.DIFFUSION_RESOLUTION,
        seed: Optional[int] = None,
    ) -> Path:
        """Run img2img and save the result. Init image is resized to `side` x `side`
        before generation; the saved sequel is written at that same resolution."""
        self._ensure_loaded()
        import torch

        init = Image.open(init_image_path).convert("RGB")
        init = _resize_for_sd15(init, side)

        generator = torch.Generator(device="cpu").manual_seed(seed) if seed is not None else None

        # SD 1.5 CLIP truncation is at 77 tokens; long descriptions get clipped.
        # That's fine for this use case — the salient nouns dominate the negative.
        result = self.pipe(
            prompt=positive_prompt,
            negative_prompt=negative_prompt,
            image=init,
            num_inference_steps=steps,
            guidance_scale=guidance,
            strength=strength,
            generator=generator,
        )
        out_image = result.images[0]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        out_image.save(output_path)
        return output_path
