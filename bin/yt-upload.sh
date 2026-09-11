#!/usr/bin/env bash
# Finished clips in, YouTube videos out. Title, description, tags and thumbnail come from the
# .txt beside each clip, which bin/clip.sh writes. Nothing else to type.
#
#   bin/yt-upload.sh work/<date>-<slug>              upload what is not yet uploaded
#   bin/yt-upload.sh work/<date>-<slug> --dry-run    list what would go, send nothing
#   bin/yt-upload.sh work/<date>-<slug> --privacy public
#
# Uploads are remembered in youtube/uploaded.json, so re-running sends only the new ones.
# A clip whose .txt is missing a title, description, tags or thumbnail is refused.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-$ROOT/.venv/bin/python}"
[ -x "$PY" ] || PY="python3"
[ -f "$ROOT/.env" ] && set -a && . "$ROOT/.env" && set +a
export PYTHONPATH="$ROOT/lib"
[ $# -gt 0 ] || { sed -n '2,10p' "$0"; exit 1; }
exec "$PY" "$ROOT/lib/yt_publish.py" "$@"
