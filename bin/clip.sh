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
#   bin/clip.sh <url|file> --slug <name> --auto 5 --auto-videos 2 --dest youtube --upload
#       → the whole YouTube run in one go: five Shorts and two normal 16:9 videos picked by
#         the local model, copy written beside each, then bin/yt-upload.sh. bin/yt.sh is the
#         short spelling of this line.
#
#   bin/clip.sh <url|file> --slug <name> --dest youtube
#       → only the youtube/ folder (comma list for more: --dest youtube,telegram)
#
#   bin/clip.sh <url|file> --slug <name> --video 22:43-25:41 "Naslov" [--clip ...]
#       → a normal 16:9 video (youtube/video_N_<slug>.mp4), not a Short: no length limit,
#         six-word caption lines, title along the top. Mix with --clip freely.
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

SRC=""; SLUG=""; LANG_="hr"; AUTO=0; AUTOV=0; UPLOAD=0; POSTOP=(); SPANS=(); TITLES=(); VSPANS=(); VTITLES=()
DESTS="youtube facebook telegram whatsapp substack"
while [ $# -gt 0 ]; do
  case "$1" in
    --slug)  SLUG="$2"; shift 2;;
    --lang)  LANG_="$2"; shift 2;;
    --dest)  DESTS="$(echo "$2" | tr ',' ' ')"; shift 2;;   # e.g. --dest youtube
    --clip)  SPANS+=("$2"); TITLES+=("${3:-}"); shift 3;;
    --video) VSPANS+=("$2"); VTITLES+=("${3:-}"); shift 3;;  # 16:9, not a Short
    --auto)  AUTO="$2"; shift 2;;
    --auto-videos) AUTOV="$2"; shift 2;;   # N normal 16:9 videos, picked by the local model
    --upload) UPLOAD=1; shift;;            # then bin/yt-upload.sh on the work folder
    --title-pos) POSTOP=(--title-pos "$2"); shift 2;;
    *) [ -z "$SRC" ] && SRC="$1" && shift || { echo "unexpected arg: $1"; exit 1; };;
  esac
done
[ -n "$SRC" ] || { sed -n '2,18p' "$0"; exit 1; }

# No --slug: make one from the video's title (a file: from its name). It is only the folder
# and file name on this disk, never shown anywhere.
if [ -z "$SLUG" ]; then
  if [ -f "$SRC" ]; then raw="$(basename "${SRC%.*}")"
  else raw="$(yt-dlp --skip-download --print title "$SRC" 2>/dev/null | head -1 || true)"; fi
  SLUG="$("$PY" - "$raw" <<'PY'
import re, sys, unicodedata
t = unicodedata.normalize("NFKD", sys.argv[1]).encode("ascii", "ignore").decode().lower()
t = re.sub(r"\(.*?\)|\[.*?\]|\d{1,2}\.\d{1,2}\.\d{2,4}\.?", " ", t)
t = re.sub(r"\b(dr|tomislav|tom|sunic|rendezvous|intervju|interview|gost|podcast|emisija)\b", " ", t)
words = [w for w in re.split(r"[^a-z0-9]+", t) if len(w) > 1][:5]
print("-".join(words) or "video")
PY
)"
  echo "  folder: work/$(date +%Y%m%d)-$SLUG"
fi
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
  # In ten-minute pieces, not one pass: on a 99-minute file Whisper locked onto one sentence
  # from minute 15 to the end. lib/transcribe.py cuts, transcribes each piece with the
  # previous-text prompt off, and stitches the timestamps back together.
  "$PY" "$ROOT/lib/transcribe.py" "$SOURCE" --out "$WORK/full.srt" --lang "$LANG_"
else
  echo "  cached: $WORK/full.srt"
fi

# ── 3. let the local model pick and title the moments ────────────────────────
# Shorts run 45-75s for YouTube; when the WhatsApp cut is wanted too, one span feeds both and
# WhatsApp Status stops at 30s, so 20-28s binds instead.
# Videos first, so the Shorts are picked from what is left: a Short cut out of the middle of
# a video is the same minute uploaded twice.
AVOID=(); for span in ${VSPANS[@]+"${VSPANS[@]}"}; do AVOID+=(--avoid "$span"); done
if [ "$AUTOV" -gt 0 ] && [ ${#VSPANS[@]} -eq 0 ]; then
  log "Choosing $AUTOV longer passages for 16:9 videos (local model)"
  while IFS= read -r line; do
    [ "${line:0:7}" = "--video" ] || continue
    span="$(echo "$line" | awk '{print $2}')"
    title="$(echo "$line" | sed 's/^--video [^ ]* //; s/^"//; s/"$//')"
    VSPANS+=("$span"); VTITLES+=("$title"); AVOID+=(--avoid "$span")
  done < <("$PY" "$ROOT/lib/pick.py" "$WORK/full.srt" --n "$AUTOV" --lang "$LANG_" --kind video | tee /dev/stderr)
  [ ${#VSPANS[@]} -gt 0 ] || echo "  ! model found no usable long passage — add --video spans by hand"
fi

if [ "$AUTO" -gt 0 ] && [ ${#SPANS[@]} -eq 0 ]; then
  log "Choosing $AUTO moments (local model)"
  LEN=(); case " $DESTS " in *" whatsapp "*) LEN=(--min 20 --max 28);; esac
  while IFS= read -r line; do
    [ "${line:0:6}" = "--clip" ] || continue
    span="$(echo "$line" | awk '{print $2}')"
    title="$(echo "$line" | sed 's/^--clip [^ ]* //; s/^"//; s/"$//')"
    SPANS+=("$span"); TITLES+=("$title")
  done < <("$PY" "$ROOT/lib/pick.py" "$WORK/full.srt" --n "$AUTO" --lang "$LANG_" ${LEN[@]+"${LEN[@]}"} \
             ${AVOID[@]+"${AVOID[@]}"} | tee /dev/stderr)
  [ ${#SPANS[@]} -gt 0 ] || { echo "model picked nothing usable — pick by hand"; exit 1; }
fi
# ── 4. no spans yet? print the transcript and stop ───────────────────────────
if [ ${#SPANS[@]} -eq 0 ] && [ ${#VSPANS[@]} -eq 0 ]; then
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
#
# --dest youtube (or a comma list) renders only those folders. youtube/ is always made: it is
# the master the others link to.
case " $DESTS " in *" youtube "*) ;; *) DESTS="youtube $DESTS";; esac
for d in $DESTS; do mkdir -p "$WORK/$d"; done
want() { case " $DESTS " in *" $1 "*) return 0;; *) return 1;; esac; }

link_or_copy() { ln -f "$1" "$2" 2>/dev/null || cp -f "$1" "$2"; }

# Edge check. A span picked from cue timestamps is often off by a second at either end:
# it opens on the tail of the previous sentence or cuts the last word. Show both edges
# so that is visible before the render, and flag the two tell-tale signs.
edges() { "$PY" - "$1" <<'PY'
import re, sys
from pathlib import Path
cues = [[r for r in b.splitlines() if r.strip()] for b in
        re.split(r"\n\s*\n", Path(sys.argv[1]).read_text(encoding="utf-8").strip())]
cues = [c for c in cues if len(c) >= 3 and "-->" in c[1]]
if not cues:
    sys.exit("  ! no captions transcribed for this clip")
first, last = " ".join(cues[0][2:]), " ".join(cues[-1][2:])
end = cues[-1][1].split("-->")[1].strip()
print(f"  opens: “{first}”   closes: “{last}” at {end}")
if first[:1].islower():
    print("  ⚠ opens mid-sentence: move the start later (or earlier to the sentence start)")
if not re.search(r"[.!?…]['\"]?\s*$", last):
    print("  ⚠ closes mid-sentence: move the end to the end of the last word")
seen = {}
for c in cues:
    seen[c[2]] = seen.get(c[2], 0) + 1
if any(v >= 3 for v in seen.values()):
    print("  ⚠ a line repeats three or more times: Whisper hallucinated, delete those cues")
PY
}

# cut_and_transcribe <base> <start-s> <end-s> <words-per-caption-line>
# Cached on the file names: delete <base>_src.mp4 to re-cut, <base>.srt to re-transcribe.
# <base>.span remembers the span behind the name; a different span (new picks, moved edge)
# throws the cut, its transcripts and its copy file away rather than reusing the old moment.
cut_and_transcribe() {
  local base="$1" start="$2" end="$3" words="$4" stem; stem="$(basename "$base")"
  if [ -f "${base}.span" ] && [ "$(cat "${base}.span")" != "$start-$end" ]; then
    echo "  span changed since last run: re-cutting"
    rm -f "${base}_src.mp4" "${base}.srt" "${base}_sent.srt" "${base}.en.srt" \
          "$WORK/youtube/${stem/clip_/short_}_${SLUG}.txt" "$WORK/youtube/${stem/clip_/short_}_${SLUG}.jpg"
  fi
  echo "$start-$end" > "${base}.span"
  [ -f "${base}_src.mp4" ] || ffmpeg -y -loglevel error -ss "$start" -to "$end" -i "$SOURCE" \
      -c:v libx264 -crf 18 -preset medium -c:a aac -b:a 192k "${base}_src.mp4"
  if [ ! -f "${base}.srt" ]; then
    # Through lib/transcribe.py, not mlx_whisper directly: it turns the previous-text prompt
    # off, which is what stopped Whisper repeating one line for a whole minute on a
    # four-minute cut. Two passes: short caption lines, then whole sentences for the
    # translator, which needs grammar to work from.
    "$PY" "$ROOT/lib/transcribe.py" "${base}_src.mp4" --out "${base}.srt" --lang "$LANG_" \
      --words "$words" >/dev/null
    "$PY" "$ROOT/lib/transcribe.py" "${base}_src.mp4" --out "${base}_sent.srt" --lang "$LANG_" \
      --no-word-timestamps >/dev/null
    echo "  ⚠ check ${base}.srt before this goes anywhere"
  fi
  edges "${base}.srt"
}

# ── 5a. the 16:9 videos: youtube only, landscape render, six-word caption lines ──
# Not a Short: no length limit, title along the top edge, so these carry the longer passages.
i=1
for span in ${VSPANS[@]+"${VSPANS[@]}"}; do
  raw="${VTITLES[$((i-1))]}"
  title="${raw%%||*}"; title="${title% }"
  start="$(secs "${span%-*}")"; end="$(secs "${span#*-}")"
  base="$WORK/video_${i}"
  name="video_${i}_${SLUG}.mp4"
  log "Video $i: $span — $title"
  cut_and_transcribe "$base" "$start" "$end" 6
  "$PY" "$ROOT/lib/polish.py" "${base}_src.mp4" --work "$WORK" --srt "${base}.srt" \
    --title "$title" --format landscape --out "$WORK/youtube/$name"
  "$PY" "$ROOT/lib/yt_copy.py" "$WORK/youtube/$name" --title "$title" \
    --srt "${base}_sent.srt" --source "$WORK/source.json" --lang "$LANG_"
  i=$((i+1))
done

# ── 5b. the Shorts ───────────────────────────────────────────────────────────
i=1
for span in ${SPANS[@]+"${SPANS[@]}"}; do
  raw="${TITLES[$((i-1))]}"
  title="${raw%%||*}"; title="${title% }"
  title_en="${raw#*||}"; title_en="${title_en# }"
  [ "$title_en" = "$raw" ] && title_en="$title"
  start="$(secs "${span%-*}")"; end="$(secs "${span#*-}")"
  base="$WORK/clip_${i}"
  name="short_${i}_${SLUG}.mp4"
  log "Clip $i: $span — $title"
  cut_and_transcribe "$base" "$start" "$end" 3

  # English subtitles for the Substack cut. Whisper cannot do this: the turbo model is
  # transcription-only, and its translate task returns the source language unchanged.
  if want substack && [ ! -f "${base}.en.srt" ] && [ "$LANG_" != "en" ]; then
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
  # Title, description draft, tags and thumbnail beside the clip, for bin/yt-upload.sh.
  # Written once; a hand-edited .txt survives a re-render.
  "$PY" "$ROOT/lib/yt_copy.py" "$WORK/youtube/$name" --title "$title" \
    --srt "${base}_sent.srt" --source "$WORK/source.json" --lang "$LANG_"
  want facebook && link_or_copy "$WORK/youtube/$name" "$WORK/facebook/$name"
  want telegram && link_or_copy "$WORK/youtube/$name" "$WORK/telegram/$name"
  want whatsapp && "$PY" "$ROOT/lib/shrink.py" "$WORK/youtube/$name" --preset whatsapp --out "$WORK/whatsapp/$name"

  if want substack && [ -f "${base}.en.srt" ]; then
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
if [ "$UPLOAD" = 1 ]; then
  log "Uploading to YouTube"
  "$ROOT/bin/yt-upload.sh" "$WORK"
  echo
  echo "Captions and copy were machine-made. If a Short needs a fix: edit clip_N.srt or"
  echo "youtube/short_N_*.txt, re-run the same command (cut and transcript are cached), and"
  echo "replace the video in Studio, or delete it there and remove its line from uploaded.json."
else
  echo "Next: read youtube/*.txt (title, description, tags), fix the Croatian in clip_N.srt if needed,"
  echo "then  bin/yt-upload.sh $WORK"
fi
echo "Rights: if this is a broadcaster's footage it stays theirs — publish as --mode appearance"
echo "(text + link, no re-upload) unless you have written permission. See step 0 of the docs."
