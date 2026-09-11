#!/usr/bin/env python3
"""Write the YouTube copy file beside a clip: title, description, tags, thumbnail.

    python yt_copy.py work/<slug>/youtube/short_1_<slug>.mp4 \
        --title "Naslov" --srt work/<slug>/clip_1_sent.srt --source work/<slug>/source.json

Produces short_1_<slug>.txt in the shape bin/yt-upload.sh reads, and a thumbnail JPEG from the
clip's opening seconds, while the title card is on screen. Runs only when the txt does not
exist yet, so a hand-edited description is never overwritten by a re-render.

The description is written by the local Ollama model from the clip's sentence-level
transcript: two or three first-person sentences naming the concrete claims, then the source
link and credit. Without Ollama it falls back to the clip's own opening sentences. Read it
before uploading when you can; Whisper's Croatian needs checking.
"""
from __future__ import annotations

import argparse
import re
import subprocess
from datetime import datetime
from pathlib import Path

from common import CFG, ollama, read_json

DESCRIBE = (
    "You write YouTube descriptions for clips of a TV interview with {who}. Answer only with "
    "JSON. Write in {language} and only in {language}. Never use an em dash or en dash, and "
    "never use quotation marks around a whole sentence."
)
DESCRIBE_TEMPLATE = """Title of the clip: {title}

What {who} says in the clip (a machine transcript, so ignore anything that looks like a
transcription error):

{body}

Write, in {language}:
  description  two or three sentences in the first person, as {who} speaking. Name the
               concrete claims, figures, names and places from the clip. No preamble like
               "in this clip". No hashtags, no links.
  tags         six to ten search tags for this clip's actual topics: people, places, events,
               concepts named in it. Specific, not generic words like "interview" or "video".

Answer with JSON only: {{"description": "...", "tags": ["...", "..."]}}"""

LANGUAGES = {"hr": "Croatian", "en": "English", "fr": "French", "de": "German"}


def describe(title: str, body: str, who: str, lang: str) -> tuple[str, list[str]]:
    """Description and tags from the local model; ("", []) when it is not running."""
    import json
    try:
        raw = ollama(DESCRIBE_TEMPLATE.format(title=title, body=body, who=who,
                                              language=LANGUAGES.get(lang, lang)),
                     system=DESCRIBE.format(who=who, language=LANGUAGES.get(lang, lang)),
                     json_mode=True)
        data = json.loads(raw)
    except (OSError, ValueError):
        return "", []
    desc = re.sub(r"\s*[—–]\s*", ", ", str(data.get("description", ""))).strip()
    desc = re.sub(r"\s+", " ", desc)
    # The model is told "two or three sentences, no preamble" and does not always listen.
    parts = [x for x in re.split(r"(?<=[.!?])\s+", desc) if x]
    parts = [x for x in parts if not re.match(r"^(U ovom|U ovoj|In this)\b", x)] or parts
    desc = " ".join(parts[:3])
    tags = [str(t).strip() for t in data.get("tags", []) if str(t).strip()][:10]
    return desc, tags

STOP = set("""i u a o s je su se da na za od do ne li kao što ali ili pa te iz po pri uz još samo
sam smo ste si bi bih bio bila bili biti će ću ćemo ćete ovo to ono ovaj taj onaj ova ta ona ovi ti oni
koji koja koje kojih koje kad kada gdje kako zašto jer već vrlo sve svi sva svoj svoje svoju mi vi
ja ti on ona ono nas vas ih im mu joj ga je jedan jedna jedno dva tri ima nema može mogu treba tako
ovdje tamo sada onda evo eto možemo možete znate mislim kažem recimo dakle međutim naravno nego""".split())

CHANNEL_TAGS = ["Tomislav Sunić", "Tom Sunić"]


def sentences(srt: Path, limit: int = 3) -> str:
    text = " ".join(rows[2] for b in re.split(r"\n\s*\n", srt.read_text(encoding="utf-8").strip())
                    if len(rows := [r for r in b.splitlines() if r.strip()]) >= 3)
    parts = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(parts[:limit]).strip()


def keywords(text: str, n: int = 8) -> list[str]:
    words = re.findall(r"[A-Za-zČĆĐŠŽčćđšž]{4,}", text)
    freq: dict[str, int] = {}
    for w in words:
        k = w.lower()
        if k in STOP:
            continue
        freq[k] = freq.get(k, 0) + 1
    ranked = sorted(freq, key=lambda k: (-freq[k], words and [w.lower() for w in words].index(k)))
    return [k for k in ranked[:n]]


def date_hr(yyyymmdd: str) -> str:
    try:
        return datetime.strptime(yyyymmdd[:8], "%Y%m%d").strftime("%d.%m.%Y.")
    except ValueError:
        return yyyymmdd


def thumbnail(mp4: Path, out: Path, at: float = 1.6) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(at), "-i", str(mp4),
                    "-frames:v", "1", "-q:v", "3", str(out)], check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="YouTube copy file beside a clip.")
    ap.add_argument("clip")
    ap.add_argument("--title", required=True)
    ap.add_argument("--srt", default="", help="sentence-level SRT of the clip")
    ap.add_argument("--source", default="", help="source.json from grab.py")
    ap.add_argument("--programme", default="", help="show name for the title suffix")
    ap.add_argument("--lang", default=CFG["languages"]["spoken_default"])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    mp4 = Path(a.clip)
    txt, jpg = mp4.with_suffix(".txt"), mp4.with_suffix(".jpg")
    if not jpg.exists() or a.force:
        thumbnail(mp4, jpg)
    if txt.exists() and not a.force:
        return print(f"  kept {txt.name} (edit it by hand, or --force)")

    src = read_json(a.source) if a.source and Path(a.source).exists() else {}
    who = CFG["youtube"].get("title_suffix") or CFG["name"].replace("Dr. ", "")
    show = a.programme or src.get("uploader", "")
    title = a.title.strip()
    suffix = f" | {who}" + (f", {show}" if show else "")
    if len(title + suffix) <= 100:
        title += suffix

    full = Path(a.srt).read_text(encoding="utf-8") if a.srt and Path(a.srt).exists() else ""
    full = " ".join(r for b in re.split(r"\n\s*\n", full.strip())
                    for r in [rr for rr in b.splitlines() if rr.strip()][2:])
    body, model_tags = describe(a.title, full, who, a.lang) if full else ("", [])
    if not body:
        body = sentences(Path(a.srt)) if a.srt and Path(a.srt).exists() else ""
    lines = [body] if body else []
    if src.get("page"):
        lines.append(f"Cijeli razgovor: {src['page']}")
    # Broadcaster, show and date. The upload's own title only when it is short; a long one
    # ("RENDEZVOUS - TOMISLAV SUNIĆ - ... (5.5.2026.)") is noise in a credit line.
    src_title = src.get("title", "") if len(src.get("title", "")) <= 60 else ""
    credit = ", ".join(x for x in (src.get("uploader", ""), a.programme or src_title,
                                   date_hr(src.get("date", ""))) if x)
    if credit:
        lines.append(f"Izvor: {credit}")
    tags = (model_tags or keywords(f"{a.title} {body}")) + ([show] if show else []) + CHANNEL_TAGS
    hashtags = " ".join("#" + re.sub(r"[^A-Za-z0-9ČĆĐŠŽčćđšž]", "", t.title()) for t in tags[:4])
    # #Shorts only on the vertical cut; a video_N_ file is a normal 16:9 upload.
    lines.append(hashtags if mp4.name.startswith("video_") else f"{hashtags} #Shorts")

    txt.write_text("TITLE\n" + title + "\n\nDESCRIPTION\n" + "\n\n".join(lines) +
                   "\n\nTAGS\n" + ", ".join(dict.fromkeys(tags)) + "\n\nTHUMBNAIL\n" + jpg.name + "\n",
                   encoding="utf-8")
    print(f"  {txt.name} ({len(title)} chars in the title) — read the description before it goes out")


if __name__ == "__main__":
    main()
