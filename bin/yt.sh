#!/usr/bin/env bash
# One command, link in, YouTube videos out. Downloads, transcribes, lets the local model pick
# five Shorts and two longer passages, cuts and captions them, writes title, description,
# tags and thumbnail beside each, and uploads them (unlisted by default, see config.yaml).
#
#   bin/yt.sh "https://www.youtube.com/watch?v=..." --slug tito-diktator
#   bin/yt.sh "<url>" --slug <name> --shorts 3 --videos 1
#   bin/yt.sh "<url>" --slug <name> --no-upload        make everything, upload later by hand
#
# Everything lands in work/<date>-<slug>/. The captions and the copy are machine-made: when
# a clip needs a fix, edit clip_N.srt or youtube/short_N_<slug>.txt and run the same line
# again; the download, transcript and cuts are cached, so only the render repeats.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ $# -gt 0 ] || { sed -n '2,12p' "$0"; exit 1; }
SRC="$1"; shift
SHORTS=5; VIDEOS=2; UPLOAD=(--upload); REST=()
while [ $# -gt 0 ]; do
  case "$1" in
    --shorts) SHORTS="$2"; shift 2;;
    --videos) VIDEOS="$2"; shift 2;;
    --no-upload) UPLOAD=(); shift;;
    *) REST+=("$1"); shift;;
  esac
done
exec "$ROOT/bin/clip.sh" "$SRC" --dest youtube --auto "$SHORTS" --auto-videos "$VIDEOS" \
  ${UPLOAD[@]+"${UPLOAD[@]}"} ${REST[@]+"${REST[@]}"}
