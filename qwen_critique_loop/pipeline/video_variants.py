"""Video variant pipeline — parallel to the PDF page flow.

Input: an MP4. For each row in the runset's variant table, every frame is run
through the same img2img parameters as the PDF pipeline. Each pass uses the
previous pass's outputs as the init image (the first pass uses the prepared
frames extracted from the source video).

Requirements:
    - ffmpeg and ffprobe (see ``qwen_critique_loop.utils.ffmpeg_bins`` for
      ``IMGSEQUEL_FFMPEG`` / ``IMGSEQUEL_FFPROBE`` and search paths). Audio is
      copied from the source clip when present.

Artifacts under ``run_dir / "video"``:
    extracted/frame_%06d.png   — raw decoded frames
    prepared/frame_%06d.png  — diffusion-sized like ``prepare_for_diffusion``
    pass_{nn}_slot{mm}_{slug}/frame_%06d.png — one folder per variant, in order
    output.mp4               — muxed from the last pass (PNGs kept on disk)
"""

from __future__ import annotations

import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from .. import config
from ..models.diffusion import DiffusionModel
from ..models.vision import VisionModel
from ..runset import RunConfig, Variant
from ..utils.ffmpeg_bins import resolve_ffmpeg_ffprobe
from ..utils.io import write_manifest
from ..utils.progress import ProgressLog

from .describe import describe_image
from .prepare import prepare_for_diffusion


def _parse_fps(rate: str) -> float:
    rate = rate.strip()
    if "/" in rate:
        a, b = rate.split("/", 1)
        return float(a) / float(b)
    return float(rate)


def probe_video_fps(video_path: Path) -> float:
    _, ffprobe = resolve_ffmpeg_ffprobe()
    cmd = [
        str(ffprobe), "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate", "-of",
        "default=noprint_wrappers=1:nokey=1", str(video_path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    if not out:
        return 24.0
    return _parse_fps(out)


def _sanitize_slug(label: str, max_len: int = 48) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", label.strip())
    s = s.strip("_") or "variant"
    return s[:max_len]


def _resolve_negative(v: Variant, llm_description: str) -> tuple[str, str]:
    if v.negative_prompt is None:
        return llm_description, "llm"
    return v.negative_prompt, "manual"


def _frame_seed(seed_base: Optional[int], frame_idx: int) -> int:
    """1-based frame index, same recipe as PDF per-page seeds."""
    if seed_base is None:
        return frame_idx * 1009
    return seed_base + frame_idx * 1009


def _resolve_variant_seed(v: Variant, seed_base: Optional[int], frame_idx: int) -> int:
    ref = _frame_seed(seed_base, frame_idx)
    return ref if v.seed_override is None else v.seed_override


def _run_ffmpeg(args: list[str]) -> None:
    r = subprocess.run(
        args, check=False, stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE, text=True,
    )
    if r.returncode != 0:
        msg = r.stderr.strip() if r.stderr else "ffmpeg failed"
        raise RuntimeError(msg)


def extract_frames(
    mp4_path: Path,
    out_dir: Path,
    max_frames: Optional[int] = None,
) -> int:
    """Decode video to PNG sequence. Returns frame count."""
    ffmpeg, _ = resolve_ffmpeg_ffprobe()
    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(out_dir / "frame_%06d.png")
    cmd = [str(ffmpeg), "-y", "-i", str(mp4_path)]
    if max_frames is not None:
        cmd.extend(["-vframes", str(max_frames)])
    cmd.extend(["-vsync", "0", pattern])
    _run_ffmpeg(cmd)
    return len(sorted(out_dir.glob("frame_*.png")))


def probe_has_audio(video_path: Path) -> bool:
    _, ffprobe = resolve_ffmpeg_ffprobe()
    cmd = [
        str(ffprobe), "-v", "error", "-select_streams", "a",
        "-show_entries", "stream=codec_type", "-of", "csv=p=0",
        str(video_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return bool(r.stdout.strip())


def encode_mp4_from_frames(
    frames_dir: Path,
    fps: float,
    source_mp4: Path,
    output_mp4: Path,
) -> None:
    """H.264 from numbered PNGs; copy audio from source when available."""
    ffmpeg, _ = resolve_ffmpeg_ffprobe()
    pattern = str(frames_dir / "frame_%06d.png")
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(ffmpeg), "-y",
        "-framerate", str(fps),
        "-i", pattern,
        "-i", str(source_mp4),
        "-map", "0:v:0",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        "-shortest",
    ]
    if probe_has_audio(source_mp4):
        cmd.extend(["-map", "1:a:0", "-c:a", "copy"])
    cmd.append(str(output_mp4))
    _run_ffmpeg(cmd)


def _list_sorted_frames(folder: Path) -> list[Path]:
    return sorted(folder.glob("frame_*.png"))


def run_video_variant_pipeline(
    mp4_path: Path,
    run_dir: Path,
    cfg: RunConfig,
    seed_base: Optional[int],
    device_request: str = "auto",
    max_frames: Optional[int] = None,
    progress: Optional[ProgressLog] = None,
) -> dict:
    """Chain img2img across variants; every frame is saved as PNG before mux."""
    if progress is None:
        progress = ProgressLog(run_dir / config.PROGRESS_FILE)
    if not cfg.variants:
        raise ValueError("runset has no variants — nothing to apply")

    resolve_ffmpeg_ffprobe()
    mp4_path = mp4_path.expanduser().resolve()
    if not mp4_path.exists():
        raise FileNotFoundError(mp4_path)

    work = run_dir / "video"
    extracted = work / "extracted"
    prepared_dir = work / "prepared"
    desc_path = work / "description.txt"
    out_mp4 = work / "output.mp4"

    progress.banner(f"imgSequel video run: {run_dir.name}")
    progress.event(f"MP4: {mp4_path}")
    progress.event(f"variants: {len(cfg.variants)} chained passes")
    fps = probe_video_fps(mp4_path)
    progress.event(f"source fps ≈ {fps:.4f}")

    cfg.save(run_dir / "runset.json")

    # --- extract ---
    cached = sorted(extracted.glob("frame_*.png"))
    if max_frames is not None:
        if len(cached) >= max_frames:
            frames = cached[:max_frames]
            progress.event(
                f"extract: skip (cached {len(frames)} frame PNGs, --max-frames)"
            )
        else:
            if extracted.exists():
                shutil.rmtree(extracted)
            progress.stage_start("ffmpeg extract frames")
            n = extract_frames(mp4_path, extracted, max_frames=max_frames)
            progress.stage_done(detail=f"{n} frames")
            frames = _list_sorted_frames(extracted)
    elif cached:
        frames = cached
        progress.event(f"extract: skip (cached {len(frames)} frame PNGs)")
    else:
        progress.stage_start("ffmpeg extract frames")
        n = extract_frames(mp4_path, extracted, max_frames=None)
        progress.stage_done(detail=f"{n} frames")
        frames = _list_sorted_frames(extracted)

    if not frames:
        raise RuntimeError("no frames extracted — check the input video")

    # --- prepare (diffusion sizing) ---
    progress.stage_start("prepare frames for diffusion")
    for fp in frames:
        dest = prepared_dir / fp.name
        prepare_for_diffusion(
            fp, dest,
            scale_percent=cfg.diffusion.scale_percent,
            long_side_max=cfg.diffusion.long_side_max,
        )
    progress.stage_done(detail=f"{len(frames)} prepared")

    # --- optional VLM description ---
    needs_llm = any(v.negative_prompt is None for v in cfg.variants)
    llm_description = ""
    if needs_llm:
        if not cfg.describe.questions:
            raise ValueError(
                "runset uses LLM negative (variant.negative_prompt null) but "
                "describe.questions is empty"
            )
        progress.stage_start(
            f"describe first frame ({len(cfg.describe.questions)} questions)"
        )
        first_prepared = prepared_dir / frames[0].name
        vlm = VisionModel(device_request=device_request)

        def on_q(slot: int, total_q: int, key: str, answer: str, cached: bool) -> None:
            tag = "skip" if cached else "done"
            preview = answer.replace("\n", " ")
            preview = preview[:100] + ("..." if len(preview) > 100 else "")
            progress.event(f"    [{slot}/{total_q}] q={key:<10}  {tag}  -> {preview}")

        llm_description = describe_image(
            vlm, first_prepared, desc_path,
            questions=cfg.describe.questions,
            max_tokens=cfg.describe.max_tokens,
            on_question=on_q,
        )
        progress.stage_done(detail=f"({len(llm_description.split())} words)")
    else:
        progress.event("describe: skip (no variant uses LLM negative)")

    diffusion = DiffusionModel(device_request=device_request)
    diffusion._ensure_loaded()
    progress.event(
        f"diffusion: {config.DIFFUSION_MODEL} on {diffusion.device} "
        f"(dtype={str(diffusion.dtype).rsplit('.', 1)[-1]})"
    )

    prev_dir = prepared_dir
    pass_records: list[dict] = []

    total_ops = len(frames) * len(cfg.variants)
    done_ops = 0

    def tick() -> None:
        nonlocal done_ops
        done_ops += 1
        if done_ops % max(1, total_ops // 20) == 0 or done_ops == total_ops:
            pct = 100.0 * done_ops / total_ops
            progress.event(f"img2img progress: {done_ops}/{total_ops} ({pct:.1f}%)")

    for pass_i, variant in enumerate(cfg.variants, start=1):
        slug = _sanitize_slug(variant.label)
        pass_dir = work / f"pass_{pass_i:02d}_slot{variant.slot:02d}_{slug}"
        pass_dir.mkdir(parents=True, exist_ok=True)
        neg_text, neg_source = _resolve_negative(variant, llm_description)

        frame_indices: list[dict] = []
        for fp in frames:
            frame_idx = int(fp.stem.split("_")[1])  # frame_000042 -> 42
            init_p = prev_dir / fp.name
            out_p = pass_dir / fp.name
            rec = {
                "frame": frame_idx,
                "path": str(out_p),
                "skipped": out_p.exists(),
            }
            if not out_p.exists():
                diffusion.img2img(
                    init_image_path=init_p,
                    output_path=out_p,
                    positive_prompt=variant.positive_prompt,
                    negative_prompt=neg_text,
                    strength=variant.strength,
                    steps=variant.steps,
                    guidance=variant.guidance,
                    seed=_resolve_variant_seed(variant, seed_base, frame_idx),
                )
            frame_indices.append(rec)
            tick()

        pass_records.append(
            {
                "pass": pass_i,
                "slot": variant.slot,
                "label": variant.label,
                "negative_prompt_source": neg_source,
                "negative_prompt_text": neg_text,
                "output_dir": str(pass_dir),
                "frames": frame_indices,
            }
        )
        prev_dir = pass_dir

    if out_mp4.exists():
        progress.event("encode: skip (output.mp4 exists)")
    else:
        progress.stage_start("ffmpeg encode output.mp4 (PNGs retained)")
        encode_mp4_from_frames(prev_dir, fps, mp4_path, out_mp4)
        progress.stage_done()

    manifest = {
        "mode": "video",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mp4_path": str(mp4_path),
        "run_dir": str(run_dir),
        "fps": fps,
        "frame_count": len(frames),
        "device_request": device_request,
        "device_used": diffusion.device,
        "dtype_used": str(diffusion.dtype).rsplit(".", 1)[-1],
        "runset_name": cfg.name,
        "runset_file": str(run_dir / "runset.json"),
        "runset": cfg.to_dict(),
        "vlm_model": config.VLM_MODEL if needs_llm else None,
        "diffusion_model": config.DIFFUSION_MODEL,
        "seed_base": seed_base,
        "max_frames": max_frames,
        "description_path": str(desc_path) if needs_llm else None,
        "passes": pass_records,
        "output_mp4": str(out_mp4),
    }
    write_manifest(run_dir, manifest)
    progress.banner("DONE — video run complete")
    progress.event(f"MP4: {out_mp4}")
    return manifest
