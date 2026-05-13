#!/usr/bin/env bash
# install-ffmpeg.sh — install ffmpeg + ffprobe when missing (Linux-focused).
#
# Usage:
#   bash scripts/install-ffmpeg.sh
#
# Debian/Ubuntu: apt. Fedora: dnf. Arch: pacman. Else: prints manual steps.

set -euo pipefail

export PATH="/usr/bin:/usr/local/bin:/opt/homebrew/bin:/snap/bin:${PATH}"

if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then
  echo "ffmpeg already available:"
  echo "  $(command -v ffmpeg)"
  echo "  $(command -v ffprobe)"
  exit 0
fi

if [[ -f /etc/debian_version ]] || command -v apt-get >/dev/null 2>&1; then
  echo "Installing ffmpeg via apt-get..."
  sudo apt-get update
  sudo apt-get install -y ffmpeg
  exit 0
fi

if command -v dnf >/dev/null 2>&1; then
  echo "Installing ffmpeg via dnf..."
  sudo dnf install -y ffmpeg
  exit 0
fi

if command -v pacman >/dev/null 2>&1; then
  echo "Installing ffmpeg via pacman..."
  sudo pacman -S --noconfirm ffmpeg
  exit 0
fi

if command -v zypper >/dev/null 2>&1; then
  echo "Installing ffmpeg via zypper..."
  sudo zypper install -y ffmpeg
  exit 0
fi

echo "Could not detect a supported package manager." >&2
echo "Install ffmpeg manually: https://ffmpeg.org/download.html" >&2
exit 1
