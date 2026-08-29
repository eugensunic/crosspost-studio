#!/usr/bin/env bash
# Link (or file) in, finished vertical shorts out.
#
#   bin/clip.sh <url|file> --slug <name>
#       → downloads, transcribes, prints the transcript with timecodes so you can pick moments
#
#   bin/clip.sh <url|file> --slug <name> --auto 3
#       → the local model picks three moments and titles them, then cuts all three.
#         Needs a model: `ollama pull gemma3:4b`. Check what it chose — it is a mediocre judge.
#
#   bin/clip.sh <url|file> --slug <name> \
#       --clip 00:54-01:29 "Carinski naslov || English title" \
#       --clip 05:55-06:31 "Drugi naslov || Second English title"
#       → one folder per destination under work/<date>-<slug>/:
#           youtube/ facebook/ telegram/  spoken language, full quality
#           whatsapp/                     same cut, under 30s and under 10MB
#           substack/                     English subtitles and title
#         Titles are "spoken || English"; with no ||, the same title is used for both.
#
# Everything is cached in work/<date>-<slug>/: re-running does not re-download or re-transcribe.
#
# Two steps are deliberately yours, not the script's:
#   * which moments are worth clipping — see the rules of thumb in HOW-THIS-IS-INTENDED-TO-WORK.md
#   * checking the Croatian, which Whisper gets wrong often enough to matter. Edit the per-clip
#     .srt in the work folder and re-run; the cut and transcribe stages are cached, so it is quick.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-$ROOT/.venv/bin/python}"
[ -x "$PY" ] || PY="python3"
export PYTHONPATH="$ROOT/lib"

SRC=""; SLUG=""; LANG_="hr"; AUTO=0; POSTOP=(); SPANS=(); TITLES=()
while [ $# -gt 0 ]; do
  case "$1" in
    --slug)  SLUG="$2"; shift 2;;
    --lang)  LANG_="$2"; shift 2;;
    --clip)  SPANS+=("$2"); TITLES+=("${3:-}"); shift 3;;
    --auto)  AUTO="$2"; shift 2;;
    --title-pos) POSTOP=(--title-pos "$2"); shift 2;;
    *) [ -z "$SRC" ] && SRC="$1" && shift || { echo "unexpected arg: $1"; exit 1; };;
  esac
done
[ -n "$SRC" ] && [ -n "$SLUG" ] || { sed -n '2,18p' "$0"; exit 1; }

WORK="$ROOT/work/$(date +%Y%m%d)-$SLUG"; mkdir -p "$WORK"
log() { printf '\n\033[1;34m▶ %s\033[0m\n' "$*"; }
secs() { "$PY" -c "import sys;p=sys.argv[1].split(':');print(sum(float(x)*60**i for i,x in enumerate(reversed(p))))" "$1"; }
model() { "$PY" -c "import yaml;print(yaml.safe_load(open('$ROOT/profiles/${PROFILE:-tom}/config.yaml'))['whisper']['model'])"; }

# ── 1. get the video ─────────────────────────────────────────────────────────
if [ -f "$SRC" ]; then
  SOURCE="$SRC"
else
  log "Fetching $SRC"
  SOURCE="$(ls "$WORK"/source.* 2>/dev/null | grep -v json | head -1 || true)"
  if [ -z "$SOURCE" ]; then
    "$PY" "$ROOT/lib/grab.py" "$SRC" --work "$WORK"
    SOURCE="$(ls "$WORK"/source.* | grep -v json | head -1)"
  else
    echo "  cached: $SOURCE"
  fi
fi

# ── 2. transcribe the whole thing ────────────────────────────────────────────
log "Transcribing ($LANG_)"
if [ ! -f "$WORK/full.srt" ]; then
  ffmpeg -y -loglevel error -i "$SOURCE" -vn -ac 1 -ar 16000 "$WORK/full.wav"
  "$PY" -m mlx_whisper.cli "$WORK/full.wav" --model "$(model)" --language "$LANG_" \
    --word-timestamps True --output-format srt --output-dir "$WORK" --output-name full >/dev/null 2>&1 \
    || "$ROOT/.venv/bin/mlx_whisper" "$WORK/full.wav" --model "$(model)" --language "$LANG_" \
       --word-timestamps True --output-format srt --output-dir "$WORK" --output-name full >/dev/null 2>&1
  rm -f "$WORK/full.wav"
else
  echo "  cached: $WORK/full.srt"
fi

# ── 3. let the local model pick and title the moments ────────────────────────
if [ "$AUTO" -gt 0 ] && [ ${#SPANS[@]} -eq 0 ]; then
  log "Choosing $AUTO moments (local model)"
  while IFS= read -r line; do
    [ "${line:0:6}" = "--clip" ] || continue
    span="$(echo "$line" | awk '{print $2}')"
    title="$(echo "$line" | sed 's/^--clip [^ ]* //; s/^"//; s/"$//')"
    SPANS+=("$span"); TITLES+=("$title")
  done < <("$PY" "$ROOT/lib/pick.py" "$WORK/full.srt" --n "$AUTO" --lang "$LANG_" | tee /dev/stderr)
  [ ${#SPANS[@]} -gt 0 ] || { echo "model picked nothing usable — pick by hand"; exit 1; }
fi

# ── 4. no spans yet? print the transcript and stop ───────────────────────────
if [ ${#SPANS[@]} -eq 0 ]; then
  log "Transcript — pick your moments, then re-run with --clip MM:SS-MM:SS \"Title\""
  "$PY" - "$WORK/full.srt" <<'PY'
import re, sys
from pathlib import Path
for b in re.split(r"\n\s*\n", Path(sys.argv[1]).read_text(encoding="utf-8").strip()):
    rows = [r for r in b.splitlines() if r.strip()]
    if len(rows) >= 3:
        print(rows[1].split("-->")[0].strip()[:8], " ".join(rows[2:]))
PY
  echo
  echo "Rules of thumb: one idea per clip · 45-75s · start on the sentence · two or three per source."
  exit 0
fi

# ── 5. cut, transcribe tight, render per destination ─────────────────────────
# One folder per place it goes. Two renders underneath: the spoken-language cut and the English
# one. The other folders are hard links to the same file, so five destinations cost one copy.
#
#   youtube/   spoken language, full quality
#   facebook/  same file
#   telegram/  same file (a bot may not send over 50MB)
#   whatsapp/  same cut, re-encoded under 30s and under 10MB
#   substack/  English subtitles and title, full quality
DESTS="youtube facebook telegram whatsapp substack"
for d in $DESTS; do mkdir -p "$WORK/$d"; done

link_or_copy() { ln -f "$1" "$2" 2>/dev/null || cp -f "$1" "$2"; }

i=1
for span in "${SPANS[@]}"; do
  raw="${TITLES[$((i-1))]}"
  title="${raw%%||*}"; title="${title% }"
  title_en="${raw#*||}"; title_en="${title_en# }"
  [ "$title_en" = "$raw" ] && title_en="$title"
  start="$(secs "${span%-*}")"; end="$(secs "${span#*-}")"
  base="$WORK/clip_${i}"
  name="short_${i}_${SLUG}.mp4"
  log "Clip $i: $span — $title"
  [ -f "${base}_src.mp4" ] || ffmpeg -y -loglevel error -ss "$start" -to "$end" -i "$SOURCE" \
      -c:v libx264 -crf 18 -preset medium -c:a aac -b:a 192k "${base}_src.mp4"

  if [ ! -f "${base}.srt" ]; then
    ffmpeg -y -loglevel error -i "${base}_src.mp4" -vn -ac 1 -ar 16000 "${base}.wav"
    "$ROOT/.venv/bin/mlx_whisper" "${base}.wav" --model "$(model)" \
      --language "$LANG_" --word-timestamps True --max-words-per-line 3 --output-format srt \
      --output-dir "$WORK" --output-name "clip_${i}" >/dev/null 2>&1
    # A second pass at sentence level. Only the caption pass wants three-word lines; the
    # translator needs whole sentences or it has no grammar to work from.
    "$ROOT/.venv/bin/mlx_whisper" "${base}.wav" --model "$(model)" \
      --language "$LANG_" --output-format srt \
      --output-dir "$WORK" --output-name "clip_${i}_sent" >/dev/null 2>&1  # no dot: mlx_whisper truncates at it
    rm -f "${base}.wav"
    echo "  ⚠ check ${base}.srt before this goes anywhere"
  fi

  # English subtitles for the Substack cut. Whisper cannot do this: the turbo model is
  # transcription-only, and its translate task returns the source language unchanged.
  if [ ! -f "${base}.en.srt" ] && [ "$LANG_" != "en" ]; then
    if "$PY" "$ROOT/lib/translate_srt.py" "${base}_sent.srt" --to en --src-lang "$LANG_" \
         --resplit 3 --out "${base}.en.srt" >/dev/null 2>&1 && [ -f "${base}.en.srt" ]; then
      echo "  ⚠ machine translation — read ${base}.en.srt before this goes anywhere"
    else
      echo "  ! no English subtitles: translate_srt.py needs Ollama and a pulled model."
      echo "    Substack cut skipped — see MEMORY: Substack is always English."
    fi
  fi

  "$PY" "$ROOT/lib/polish.py" "${base}_src.mp4" --work "$WORK" --srt "${base}.srt" \
    --title "$title" ${POSTOP[@]+"${POSTOP[@]}"} --out "$WORK/youtube/$name"
  link_or_copy "$WORK/youtube/$name" "$WORK/facebook/$name"
  link_or_copy "$WORK/youtube/$name" "$WORK/telegram/$name"
  "$PY" "$ROOT/lib/shrink.py" "$WORK/youtube/$name" --preset whatsapp --out "$WORK/whatsapp/$name"

  if [ -f "${base}.en.srt" ]; then
    "$PY" "$ROOT/lib/polish.py" "${base}_src.mp4" --work "$WORK" --srt "${base}.en.srt" \
      --title "$title_en" ${POSTOP[@]+"${POSTOP[@]}"} --out "$WORK/substack/$name"
  fi
  i=$((i+1))
done

echo
echo "Done → $WORK"
for d in $DESTS; do
  for f in "$WORK/$d"/*.mp4; do [ -f "$f" ] && printf '  %-9s %s (%s)\n' "$d" "$(basename "$f")" "$(du -h "$f" | cut -f1)"; done
done
echo
echo "Rights: if this is a broadcaster's footage it stays theirs — publish as --mode appearance"
echo "(text + link, no re-upload) unless you have written permission. See step 0 of the docs."
