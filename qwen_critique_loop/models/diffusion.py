"""SD 1.5 img2img model, CPU-friendly.

The init image's dimensions drive the output's dimensions: whatever WxH the
init image has (rounded to multiples of 8), that's what we generate at. This
preserves the original page's aspect ratio end-to-end.

Empty positive prompt by design — the per-page negative prompt does the
steering. Runs in roughly 30-90s per image on a Ryzen 9 8945HS depending on
strength, steps, and the image's pixel count.
"""

from pathlib import Path
from typing import Optional

from PIL import Image

from .. import config


def _round_to_multiple_of_8(x: int) -> int:
    n = (x // 8) * 8
    return max(8, n)


def _conform_to_vae(img: Image.Image) -> Image.Image:
    """SD 1.5's VAE requires both dims to be multiples of 8. The prepare stage
    already enforces this, but we re-snap defensively in case a hand-edited
    init image is used."""
    w, h = img.size
    w8, h8 = _round_to_multiple_of_8(w), _round_to_multiple_of_8(h)
    if (w8, h8) != (w, h):
        return img.resize((w8, h8), Image.LANCZOS)
    return img


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
        # Override the saved algorithm_type — dreamshaper-7 ships with `deis`,
        # which newer diffusers versions reject in combination with the saved
        # `final_sigmas_type=zero`. Plain `dpmsolver++` is well-tested and fine
        # for img2img at low step counts.
        self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
            self.pipe.scheduler.config,
            algorithm_type="dpmsolver++",
            final_sigmas_type="sigma_min",
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
        positive_prompt: str = "",
        negative_prompt: str = "",
        steps: int = 25,
        guidance: float = 7.0,
        strength: float = 0.5,
        seed: Optional[int] = None,
    ) -> Path:
        """Run img2img and save the result.

        The init image is used at its current dimensions (snapped to multiples
        of 8). The output is saved at those same dimensions, so the sequel
        preserves the aspect ratio of the prepared init."""
        self._ensure_loaded()
        import torch

        init = Image.open(init_image_path).convert("RGB")
        init = _conform_to_vae(init)

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
