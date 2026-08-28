#!/usr/bin/env python3
"""Bilingual title, description, summary and per-network post texts from a transcript.

    python titles.py work/<slug>/transcript.txt --langs hr en --title "Naslov" --mode video
Writes work/<slug>/meta.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ollama, slugify, write_json

LANG_NAMES = {"hr": "Croatian", "en": "English", "fr": "French", "de": "German"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript")
    ap.add_argument("--langs", nargs="+", default=["hr", "en"])
    ap.add_argument("--title", default="", help="working title supplied on the command line")
    ap.add_argument("--spoken", default="hr")
    ap.add_argument("--mode", default="video")
    a = ap.parse_args()

    text = Path(a.transcript).read_text(encoding="utf-8")[:24000]
    langs = ", ".join(LANG_NAMES[l] for l in a.langs)
    system = (
        "You are an editor for a political philosopher's video channel. Write in a sober, "
        "intellectual register. No clickbait, no emojis, no hashtags except where asked. "
        "Return ONLY valid JSON."
    )
    prompt = f"""Spoken language: {LANG_NAMES[a.spoken]}. Working title: "{a.title}".
Produce, for each of [{langs}] (keys = ISO codes {a.langs}):
  title        – max 70 characters
  description  – 2 paragraphs, 400–700 characters total
  summary      – 1 paragraph, 300–500 characters
  x            – post for X, max 240 characters, no links (link is appended later)
  linkedin     – 3 short paragraphs, professional tone
  hashtags     – list of 3–5 relevant hashtags
Also produce top-level:
  chapters     – list of {{ "t": "MM:SS", "label": "…" }} in the spoken language, 5–8 items, based on the transcript
  short_candidates – 2 spans {{ "start": "MM:SS", "end": "MM:SS", "why": "…" }} of 45–60 s that would work as Shorts

Transcript:
{text}"""
    meta = json.loads(ollama(prompt, system=system, json_mode=True))
    hr = meta.get("hr", {}).get("title") or a.title
    en = meta.get("en", {}).get("title") or a.title
    meta["bilingual_title"] = f"{hr} · {en}" if hr != en else hr
    meta["slug"] = slugify(en or hr or a.title)
    meta["spoken"] = a.spoken
    meta["mode"] = a.mode
    out = Path(a.transcript).with_name("meta.json")
    write_json(out, meta)
    print(f"Wrote {out}\n  {meta['bilingual_title']}")


if __name__ == "__main__":
    main()
