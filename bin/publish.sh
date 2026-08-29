#!/usr/bin/env bash
# Crosspost Studio — one script, three modes.
#
#   publish.sh --mode video      raw.mp4 "Naslov"  [--shorts 12:40-13:35 27:10-28:05] [--lang hr] [--short-only]
#   publish.sh --mode appearance "https://…htv…" "Tom on HTV: …" [--host HTV] [--lang hr]
#   publish.sh --mode live       qanda.mp4 "Q&A rujan" --teaser 03:10-04:05
#
# Flags:  --dry-run   build everything, send nothing (no Postiz, no git push, no Substack)
#         --push      git commit+push the site repo (default: write the page only)
#         --now       publish immediately instead of the weekly slot
#         --video-id  YouTube ID once Postiz has published (runs captions + localizations + site embed)
#         --skip-edit keep raw.mp4 as is (no auto-editor)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT/lib"
[ -f "$ROOT/.env" ] && set -a && . "$ROOT/.env" && set +a
PY="${PYTHON:-python3}"
cfg() { "$PY" -c "import sys,yaml;c=yaml.safe_load(open('$ROOT/profiles/${PROFILE:-tom}/config.yaml'));print(eval('c'+''.join('[\"%s\"]'%k for k in sys.argv[1].split('.'))))" "$1"; }

MODE=""; INPUT=""; TITLE=""; SHORTS=(); TEASER=""; LANG_=""; HOST=""; DRY=0; PUSH=0; NOW=""; VIDEO_ID=""; SHORT_ONLY=0; SKIP_EDIT=0
while [ $# -gt 0 ]; do
  case "$1" in
    --mode) MODE="$2"; shift 2;;
    --shorts) shift; while [ $# -gt 0 ] && [[ "$1" != --* ]]; do SHORTS+=("$1"); shift; done;;
    --teaser) TEASER="$2"; shift 2;;
    --lang) LANG_="$2"; shift 2;;
    --host) HOST="$2"; shift 2;;
    --video-id) VIDEO_ID="$2"; shift 2;;
    --dry-run) DRY=1; shift;;
    --push) PUSH=1; shift;;
    --now) NOW="--now"; shift;;
    --short-only) SHORT_ONLY=1; shift;;
    --skip-edit) SKIP_EDIT=1; shift;;
    *) if [ -z "$INPUT" ]; then INPUT="$1"; elif [ -z "$TITLE" ]; then TITLE="$1"; else echo "unexpected arg $1"; exit 1; fi; shift;;
  esac
done
[ -n "$MODE" ] && [ -n "$INPUT" ] && [ -n "$TITLE" ] || { sed -n '2,16p' "$0"; exit 1; }

SLUG="$("$PY" -c "import sys;sys.path.insert(0,'$ROOT/lib');from common import slugify;print(slugify(sys.argv[1]))" "$TITLE")"
WORK="$ROOT/work/$(date +%Y%m%d)-$SLUG"; mkdir -p "$WORK"
log() { printf '\n\033[1;34m▶ %s\033[0m\n' "$*"; }
run() { if [ "$DRY" = 1 ] && [ "${ALLOW_DRY:-0}" != 1 ]; then echo "  (dry) $*"; else "$@"; fi; }
SITE_REPO="$(eval echo "$(cfg site.repo)")"

# ───────────────────────── appearance: link only, nothing downloaded ─────────────────────────
if [ "$MODE" = appearance ]; then
  log "Appearance → $SLUG"
  "$PY" "$ROOT/lib/appearance.py" "$INPUT" "$TITLE" --work "$WORK" ${HOST:+--host "$HOST"} ${LANG_:+--lang "$LANG_"}
  "$PY" "$ROOT/lib/postiz.py" --work "$WORK" --mode appearance $( [ "$DRY" = 1 ] && echo --dry-run )
  "$PY" "$ROOT/lib/site_post.py" --work "$WORK" --mode appearance
  "$PY" "$ROOT/lib/substack_draft.py" --work "$WORK" --mode appearance
  if [ "$PUSH" = 1 ] && [ "$DRY" = 0 ]; then git -C "$SITE_REPO" add -A && git -C "$SITE_REPO" commit -qm "appearance: $TITLE" && git -C "$SITE_REPO" push; fi
  echo; echo "WhatsApp: $TITLE → $(cfg site.base_url)/appearances/$SLUG/"; exit 0
fi

# ───────────────────────── video / live ─────────────────────────
[ -f "$INPUT" ] || { echo "no such file: $INPUT"; exit 1; }
LANG_="${LANG_:-$(cfg languages.spoken_default)}"

log "1/8 Cut silence"
if [ "$SKIP_EDIT" = 1 ] || [ -f "$WORK/clean.mp4" ]; then cp -n "$INPUT" "$WORK/clean.mp4" 2>/dev/null || true
else auto-editor "$INPUT" --margin 0.2s --no-open -o "$WORK/clean.mp4"; fi

log "2/8 Transcribe ($(cfg whisper.model))"
if [ ! -f "$WORK/$LANG_.srt" ]; then
  mlx_whisper "$WORK/clean.mp4" --model "$(cfg whisper.model)" --word-timestamps True \
    --output-format srt --output-dir "$WORK" --output-name "$LANG_" --language "$LANG_"
fi
"$PY" -c "import sys;sys.path.insert(0,'$ROOT/lib');import srt;open('$WORK/transcript.txt','w').write(srt.plain_text(srt.parse('$WORK/$LANG_.srt')))"

log "3/8 Translate subtitles"
TARGETS="$("$PY" -c "import yaml;print(' '.join(yaml.safe_load(open('$ROOT/profiles/${PROFILE:-tom}/config.yaml'))['languages']['subtitle_targets']))")"
"$PY" "$ROOT/lib/translate_srt.py" "$WORK/$LANG_.srt" --to $TARGETS

log "4/8 Titles, description, summary (bilingual)"
"$PY" "$ROOT/lib/titles.py" "$WORK/transcript.txt" --langs $(cfg languages.title_langs | tr -d "[],'") --title "$TITLE" --spoken "$LANG_" --mode "$MODE"

log "5/8 Shorts / teaser"
# lib/polish.py does the cut-to-vertical, the overlay clean-up, the burned-in subtitles and
# the title card in one ffmpeg pass. See POLISHING.md. It replaces the old crop + captacity
# pair: captacity imports moviepy.editor (removed in moviepy 2.x) so it could never run, and
# its failure was swallowed by `2>/dev/null ||`, shipping Shorts with no captions at all.
secs() { "$PY" -c "import sys;p=sys.argv[1].split(':');print(sum(float(x)*60**i for i,x in enumerate(reversed(p))))" "$1"; }
polish() {  # polish <src> <out> <offset-seconds>
  "$PY" "$ROOT/lib/polish.py" "$1" --work "$WORK" --out "$2" --srt-offset "$3" \
    ${SRT_IN:+--srt "$SRT_IN"} --title "$TITLE"
}
SRT_IN="$WORK/$LANG_.srt"; [ -f "$SRT_IN" ] || SRT_IN=""

if [ "$MODE" = live ]; then
  [ -n "$TEASER" ] || { echo "--teaser MM:SS-MM:SS required for live"; exit 1; }
  ffmpeg -y -loglevel error -ss "${TEASER%-*}" -to "${TEASER#*-}" -i "$WORK/clean.mp4" -c:v libx264 -crf 18 -c:a aac "$WORK/teaser_src.mp4"
  polish "$WORK/teaser_src.mp4" "$WORK/teaser.mp4" "$(secs "${TEASER%-*}")"
else
  if [ ${#SHORTS[@]} -eq 0 ]; then
    mapfile -t SHORTS < <("$PY" -c "import json;[print(f\"{s['start']}-{s['end']}\") for s in json.load(open('$WORK/meta.json')).get('short_candidates',[])[:2]]")
    echo "  using LLM-picked spans: ${SHORTS[*]}"
  fi
  i=1; for span in "${SHORTS[@]}"; do
    ffmpeg -y -loglevel error -ss "${span%-*}" -to "${span#*-}" -i "$WORK/clean.mp4" -c:v libx264 -crf 18 -c:a aac "$WORK/short_${i}_src.mp4"
    polish "$WORK/short_${i}_src.mp4" "$WORK/short_${i}.mp4" "$(secs "${span%-*}")"
    i=$((i+1))
  done
  [ "$SHORT_ONLY" = 1 ] || cp -n "$WORK/clean.mp4" "$WORK/long.mp4"
  ffmpeg -y -loglevel error -ss 00:00:03 -i "$WORK/clean.mp4" -frames:v 1 -q:v 2 "$WORK/thumb.jpg"
fi

log "6/8 Postiz → every network"
"$PY" "$ROOT/lib/postiz.py" --work "$WORK" --mode "$MODE" $NOW $( [ "$DRY" = 1 ] && echo --dry-run )

log "7/8 YouTube subtitle tracks + localizations"
if [ -n "$VIDEO_ID" ] && [ "$DRY" = 0 ]; then
  "$PY" "$ROOT/lib/yt_captions.py" "$VIDEO_ID" "$WORK"/*.srt --localize $(cfg languages.title_langs | tr -d "[],'") --meta "$WORK/meta.json"
else echo "  skipped — rerun with --video-id <ID> after Postiz publishes (or set up the Postiz webhook, see README)"; fi

log "8/8 Site page + Substack draft"
"$PY" "$ROOT/lib/site_post.py" --work "$WORK" --mode "$MODE" ${VIDEO_ID:+--video-id "$VIDEO_ID"}
"$PY" "$ROOT/lib/substack_draft.py" --work "$WORK" --mode "$MODE" ${VIDEO_ID:+--video-id "$VIDEO_ID"}
if [ "$PUSH" = 1 ] && [ "$DRY" = 0 ]; then git -C "$SITE_REPO" add -A && git -C "$SITE_REPO" commit -qm "$MODE: $TITLE" && git -C "$SITE_REPO" push; fi

echo; echo "Done → $WORK"
echo "WhatsApp: $TITLE → $(cfg site.base_url)/posts/$SLUG/"
echo "Next: Substack → Publish. Spot-check en.srt on the first videos."
