#!/usr/bin/env bash
# Clear out work/ before starting a new video.
#
#   bin/clean.sh              show what is there and ask before deleting
#   bin/clean.sh --yes        delete without asking
#   bin/clean.sh --keep 2     keep the 2 most recent folders, delete the rest
#   bin/clean.sh --list       show what is there and stop
#
# READ THIS FIRST. `HOW-THIS-IS-INTENDED-TO-WORK.md` calls work/ the local archive and says
# never delete it: it holds the only copy of every cut, transcript and corrected subtitle file
# you have made, and re-running does not recreate the corrections you typed by hand. The source
# videos can be downloaded again. Your fixed Croatian cannot.
#
# So: publish or copy out what you want to keep first. `--keep` exists for that reason.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKDIR="$ROOT/work"

YES=0; KEEP=0; LIST=0
while [ $# -gt 0 ]; do
  case "$1" in
    --yes|-y) YES=1; shift;;
    --keep)   KEEP="$2"; shift 2;;
    --list)   LIST=1; shift;;
    *) echo "unknown option: $1"; sed -n '2,9p' "$0"; exit 1;;
  esac
done

# not mapfile: macOS ships bash 3.2, which does not have it
FOLDERS=()
while IFS= read -r d; do FOLDERS+=("$d"); done < <(find "$WORKDIR" -mindepth 1 -maxdepth 1 -type d | sort -r)
if [ ${#FOLDERS[@]} -eq 0 ]; then
  echo "work/ is already empty"; exit 0
fi

echo "In work/ (newest first):"
for d in "${FOLDERS[@]}"; do
  printf '  %-6s %s\n' "$(du -sh "$d" | cut -f1)" "$(basename "$d")"
done
echo "  ----"
printf '  %-6s total\n' "$(du -sh "$WORKDIR" | cut -f1)"
[ "$LIST" = 1 ] && exit 0

DOOMED=("${FOLDERS[@]:$KEEP}")
if [ ${#DOOMED[@]} -eq 0 ]; then
  echo; echo "keeping all ${#FOLDERS[@]}, nothing to delete"; exit 0
fi

echo
if [ "$KEEP" -gt 0 ]; then
  echo "Would delete ${#DOOMED[@]}, keeping the $KEEP newest."
else
  echo "Would delete all ${#DOOMED[@]} folders."
fi
if [ "$YES" != 1 ]; then
  read -r -p "Delete them? This cannot be undone [y/N] " ok
  case "$ok" in y|Y|yes|YES) ;; *) echo "nothing deleted"; exit 0;; esac
fi

for d in "${DOOMED[@]}"; do
  rm -rf "$d"
  echo "  removed $(basename "$d")"
done
touch "$WORKDIR/.gitkeep"
echo "Done."
