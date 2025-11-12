#!/usr/bin/env bash
set -euo pipefail
VIDEO="$1"        # e.g. data/input/Tanzania-2.mp4
AUDIO="$2"        # e.g. data/work/de_mix.wav
OUT_MP4="$3"      # e.g. data/output/Tanzania-2.de.mp4

# Re-mux with new audio (AAC), keep original video, faststart for web players.
ffmpeg -y -i "$VIDEO" -i "$AUDIO" \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k \
  -shortest -movflags +faststart "$OUT_MP4"

echo "OK: muxed $OUT_MP4"
