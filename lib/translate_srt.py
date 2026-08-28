#!/usr/bin/env python3
"""Translate an SRT segment by segment with a local Ollama model, keeping timing.

    python translate_srt.py work/<slug>/hr.srt --to en fr de
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import srt
from common import ollama

LANG_NAMES = {"hr": "Croatian", "en": "English", "fr": "French", "de": "German"}
BATCH = 25  # cues per LLM call — keeps context for coherent translation


def translate(cues: list[srt.Cue], src: str, dst: str) -> list[srt.Cue]:
    out: list[srt.Cue] = []
    system = (
        f"You translate subtitles from {LANG_NAMES[src]} to {LANG_NAMES[dst]}. "
        "Return ONLY a JSON object mapping each input id (string) to its translation. "
        "Keep the same number of entries. Preserve names, keep each line short, no commentary."
    )
    for i in range(0, len(cues), BATCH):
        chunk = cues[i : i + BATCH]
        payload = {str(c.index): c.text for c in chunk}
        resp = ollama(json.dumps(payload, ensure_ascii=False), system=system, json_mode=True)
        try:
            mapping = json.loads(resp)
        except json.JSONDecodeError:
            mapping = {}
        for c in chunk:
            text = mapping.get(str(c.index)) or c.text  # fall back to source rather than drop the cue
            out.append(srt.Cue(c.index, c.start, c.end, str(text).strip()))
        print(f"  {dst}: {min(i + BATCH, len(cues))}/{len(cues)}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src_srt")
    ap.add_argument("--to", nargs="+", required=True)
    ap.add_argument("--src-lang", help="defaults to the file stem, e.g. hr.srt → hr")
    a = ap.parse_args()

    src_path = Path(a.src_srt)
    src = a.src_lang or src_path.stem
    cues = srt.parse(src_path)
    for dst in a.to:
        if dst == src:
            continue
        print(f"Translating {src} → {dst} ({len(cues)} cues)")
        srt.write(translate(cues, src, dst), src_path.with_name(f"{dst}.srt"))


if __name__ == "__main__":
    main()
