"""Device selection: pick CUDA, MPS (Apple Silicon), or CPU.

Used by both the diffusion model and the InstructBLIP vision model so they
end up on the same accelerator. Honors a user override (`cpu/cuda/mps/auto`)
and falls back to CPU if the requested device isn't available.

MPS notes
---------
- Apple Silicon (M1/M2/M3/M4) shows up as `torch.backends.mps.is_available()`.
- A few transformer ops still don't have MPS kernels; we set the env var
  `PYTORCH_ENABLE_MPS_FALLBACK=1` automatically so those ops transparently
  run on CPU instead of crashing. SD 1.5 itself runs natively on MPS.
- We use float32 on MPS by default. fp16 on MPS works for SD but is buggy
  for InstructBLIP — fp32 is the safe shared default for now.
"""

from __future__ import annotations

import os
from typing import Literal, Optional

DeviceArg = Literal["cpu", "cuda", "mps", "auto"]


def resolve_device(requested: DeviceArg = "auto") -> tuple[str, "object"]:
    """Return (device_str, dtype). dtype is a torch.dtype object.

    `requested` of "auto" picks the best available: cuda > mps > cpu.
    An explicit choice that isn't available falls back to cpu with a
    diagnostic printed to stderr.
    """
    import sys
    import torch

    requested = requested.lower()  # type: ignore[assignment]

    def cuda_ok() -> bool:
        return torch.cuda.is_available()

    def mps_ok() -> bool:
        return hasattr(torch.backends, "mps") and torch.backends.mps.is_available()

    if requested == "auto":
        if cuda_ok():
            picked = "cuda"
        elif mps_ok():
            picked = "mps"
        else:
            picked = "cpu"
    elif requested == "cuda":
        if not cuda_ok():
            print("device=cuda requested but not available — falling back to cpu",
                  file=sys.stderr)
            picked = "cpu"
        else:
            picked = "cuda"
    elif requested == "mps":
        if not mps_ok():
            print("device=mps requested but not available — falling back to cpu",
                  file=sys.stderr)
            picked = "cpu"
        else:
            picked = "mps"
    else:
        picked = "cpu"

    if picked == "cuda":
        dtype = torch.float16
    elif picked == "mps":
        # fp32 is the safe shared default for SD + InstructBLIP on MPS.
        dtype = torch.float32
        # Enable CPU fallback for the handful of ops without MPS kernels.
        os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    else:
        dtype = torch.float32

    return picked, dtype


# Module-level singleton: the first model to call resolve_device sets the
# preference, all subsequent callers re-use it so vision + diffusion agree.
_cached: Optional[tuple[str, "object"]] = None
_cached_request: Optional[str] = None


def get_device(requested: DeviceArg = "auto") -> tuple[str, "object"]:
    global _cached, _cached_request
    if _cached is None or _cached_request != requested:
        _cached = resolve_device(requested)
        _cached_request = requested
    return _cached
