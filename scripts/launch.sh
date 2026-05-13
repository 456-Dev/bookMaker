#!/usr/bin/env bash
# launch.sh — start an imgSequel run inside a detached tmux session.
#
# Always runs in a tmux session called "book" so the job survives SSH
# disconnects (laptop sleeping, network blips, etc). If a session named
# "book" already exists, it's reused — re-running this script is a no-op
# unless the previous job has exited.
#
# Usage:
#   bash scripts/launch.sh <args passed to qwen_critique_loop.main>
#
# Examples:
#   bash scripts/launch.sh myfile_cropped.pdf --pages 1-3
#   bash scripts/launch.sh --resume latest
#   bash scripts/launch.sh --mp4 C0046.MP4 --runset vid1.json --max-frames 8 --device auto
#
# After launch:
#   tmux attach -t book      # see live output
#   (Ctrl-B then D)          # detach without killing the job
#   tmux ls                  # list running sessions
#   tmux kill-session -t book  # stop the job

set -euo pipefail

export PATH="/usr/bin:/usr/local/bin:/opt/homebrew/bin:/snap/bin:${PATH}"

SESSION="book"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO_ROOT/.venv"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is not installed. Install it first:" >&2
  echo "  sudo apt install tmux" >&2
  exit 1
fi

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
  echo "  pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu" >&2
  echo "  pip install -r qwen_critique_loop/requirements.txt" >&2
  exit 1
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "tmux session '$SESSION' already exists. Reattach with:"
  echo "  tmux attach -t $SESSION"
  echo "Or kill it first with:"
  echo "  tmux kill-session -t $SESSION"
  exit 0
fi

# Build the inner command. We chain `; exec bash` so that when python exits
# the tmux pane stays open showing the final output and exit code instead of
# closing immediately and losing the trail.
ARGS_QUOTED=""
for a in "$@"; do
  ARGS_QUOTED+=" $(printf '%q' "$a")"
done
INNER="cd $(printf '%q' "$REPO_ROOT") && \
export PATH=/usr/bin:/usr/local/bin:/opt/homebrew/bin:/snap/bin:\$PATH && \
source .venv/bin/activate && \
python3 -m qwen_critique_loop.main$ARGS_QUOTED; \
echo; echo '[launch.sh] python exited with code '\$?'; pane will stay open'; \
exec bash"

tmux new-session -d -s "$SESSION" "bash -lc $(printf '%q' "$INNER")"

echo "Started detached tmux session '$SESSION'."
echo "Attach to watch live output:"
echo "  tmux attach -t $SESSION"
echo "Detach again from inside tmux with: Ctrl-B  then  D"
echo
echo "Or tail the progress log directly without attaching:"
echo "  tail -f $REPO_ROOT/qwen_critique_loop/runs/*/progress.txt"
