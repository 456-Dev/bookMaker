#!/usr/bin/env bash
# run_local.sh — run the pipeline in the foreground for local testing.
#
# Counterpart to launch.sh. Use this for quick iteration on your own machine
# (e.g. M1 Mac) where you want live output in your terminal and don't need
# the SSH-survivable tmux wrapper.
#
# Usage:
#   bash scripts/run_local.sh <args passed to qwen_critique_loop.main>
#
# Examples:
#   bash scripts/run_local.sh myfile_cropped.pdf --pages 1-1 --device mps
#   bash scripts/run_local.sh myfile.pdf --runset myrun.runset.json --device auto
#   bash scripts/run_local.sh --resume latest --device mps
#   bash scripts/run_local.sh --mp4 C0046.MP4 --runset vid1.json --max-frames 8 --device auto
#
# For long runs on a remote box, use scripts/launch.sh instead — it wraps the
# same command in a detached tmux session.

set -euo pipefail

export PATH="/usr/bin:/usr/local/bin:/opt/homebrew/bin:/snap/bin:${PATH}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO_ROOT/.venv"

_uses_mp4=0
for _a in "$@"; do
  if [[ "$_a" == "--mp4" ]]; then _uses_mp4=1; break; fi
done
if [[ "$_uses_mp4" -eq 1 ]]; then
  if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
    echo "ffmpeg / ffprobe not found (required for --mp4)." >&2
    echo "Install with:" >&2
    echo "  bash scripts/install-ffmpeg.sh" >&2
    echo "Or: sudo apt update && sudo apt install -y ffmpeg" >&2
    echo "Or set IMGSEQUEL_FFMPEG and IMGSEQUEL_FFPROBE to full paths." >&2
    exit 1
  fi
fi
unset _a _uses_mp4

if [[ ! -d "$VENV" ]]; then
  echo "venv not found at $VENV" >&2
  echo "Create it first:" >&2
  echo "  python3 -m venv $VENV" >&2
  echo "  source $VENV/bin/activate" >&2
  echo "  pip install --upgrade pip" >&2
  # CPU/Linux installs from the cpu wheel index; on Mac the default index has
  # native arm64 wheels that include MPS support.
  if [[ "$(uname -s)" == "Darwin" ]]; then
    echo "  pip install torch torchvision" >&2
  else
    echo "  pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu" >&2
  fi
  echo "  pip install -r qwen_critique_loop/requirements.txt" >&2
  exit 1
fi

cd "$REPO_ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate
exec python3 -m qwen_critique_loop.main "$@"
