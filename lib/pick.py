#!/usr/bin/env python3
"""Choose the clippable moments in a transcript, and title each one.

    python pick.py work/<slug>/full.srt --n 3 --lang hr

Writes picks.json next to the transcript and prints one `--clip MM:SS-MM:SS "Title"` line per
moment, ready to paste into (or be consumed by) bin/clip.sh.

Runs on the local Ollama model from config.yaml. No key, no API, nothing leaves the machine —
but it does need the model named in config.yaml to be pulled first.

This is the one judgement call in the pipeline, and a small local model is a mediocre judge of
it. Treat the output as a shortlist to check, not a decision — the rules it is scored against
are in HOW-THIS-IS-INTENDED-TO-WORK.md: one idea per clip, 45-75 seconds, start on the sentence
rather than the breath before it, two or three per source rather than eight.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from common import CFG, ollama, write_json

SYSTEM = (
    "You choose short vertical clips from an interview transcript. You answer only with JSON. "
    "A good clip states one idea that stands on its own, needs no setup, opens on the start of "
    "a sentence, and ends on the payoff. Prefer a concrete claim, number or quote over "
    "generalities. Never pick a moment that needs earlier context to make sense."
)

TEMPLATE = """Transcript of a TV interview, one line per cue, timestamps are MM:SS.

{transcript}

Choose the {n} best moments to cut as standalone vertical short videos.

Rules:
- each clip is one idea, complete in itself
- {lo}-{hi} seconds long
- must begin exactly at the start of a spoken sentence
- must end on the point being made, not mid-thought
- no two clips may overlap or make the same point

For each, write a title in {language}: a short claim of at most 6 words, the thing that makes
someone stop scrolling. Not a topic label. No quotation marks in the title.

Answer with JSON only:
{{"clips": [{{"start": "MM:SS", "end": "MM:SS", "title": "...", "why": "one sentence"}}]}}"""

LANGUAGES = {"hr": "Croatian", "en": "English", "fr": "French", "de": "German"}


def transcript_lines(srt: Path) -> tuple[str, float]:
    """Timestamped one-line-per-cue text, plus the end of the last cue in seconds."""
    def secs(t: str) -> float:
        hh, mm, rest = t.split(":")
        ss, ms = rest.split(",")
        return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000

    out, last = [], 0.0
    for block in re.split(r"\n\s*\n", srt.read_text(encoding="utf-8").strip()):
        rows = [r for r in block.splitlines() if r.strip()]
        if len(rows) >= 3 and "-->" in rows[1]:
            a, b = [x.strip() for x in rows[1].split("-->")]
            st, en = secs(a), secs(b)
            last = max(last, en)
            out.append(f"{int(st // 60):02d}:{int(st % 60):02d} " + " ".join(rows[2:]))
    return "\n".join(out), last


def to_secs(stamp: str) -> float | None:
    m = re.match(r"^\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*$", stamp)
    if not m:
        return None
    a, b, c = m.groups()
    return int(a) * 3600 + int(b) * 60 + int(c) if c else int(a) * 60 + int(b)


def validate(clips: list[dict], duration: float, lo: int, hi: int) -> list[dict]:
    """Drop what the model got wrong: bad stamps, zero or runaway lengths, overlaps, and
    anything past the end of the recording. A small model gets some of these wrong every run."""
    good: list[dict] = []
    for c in clips:
        st, en = to_secs(str(c.get("start", ""))), to_secs(str(c.get("end", "")))
        title = str(c.get("title", "")).strip().strip('"').strip()
        if st is None or en is None or not title:
            continue
        en = min(en, duration)
        if not (lo * 0.6 <= en - st <= hi * 1.4) or st >= duration:
            continue
        if any(st < g["end_s"] and en > g["start_s"] for g in good):
            continue
        good.append({"start": f"{int(st // 60):02d}:{int(st % 60):02d}",
                     "end": f"{int(en // 60):02d}:{int(en % 60):02d}",
                     "start_s": st, "end_s": en, "title": title,
                     "why": str(c.get("why", "")).strip()})
    return sorted(good, key=lambda g: g["start_s"])


def main() -> None:
    ap = argparse.ArgumentParser(description="Pick and title clippable moments.")
    ap.add_argument("srt")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--lang", default="hr")
    ap.add_argument("--min", type=int, default=35)
    ap.add_argument("--max", type=int, default=75)
    a = ap.parse_args()

    srt = Path(a.srt)
    text, duration = transcript_lines(srt)
    if not text:
        raise SystemExit(f"no cues in {srt}")

    prompt = TEMPLATE.format(transcript=text, n=a.n, lo=a.min, hi=a.max,
                             language=LANGUAGES.get(a.lang, a.lang))
    try:
        raw = ollama(prompt, system=SYSTEM, json_mode=True)
    except OSError as e:
        raise SystemExit(
            f"could not reach Ollama ({e}). Start it with `brew services start ollama` "
            f"and pull the model named in config.yaml: `ollama pull {CFG['ollama']['model']}`")

    try:
        clips = json.loads(raw).get("clips", [])
    except json.JSONDecodeError:
        raise SystemExit(f"model did not return JSON:\n{raw[:400]}")

    picks = validate(clips, duration, a.min, a.max)
    if not picks:
        raise SystemExit("nothing usable came back — pick by hand from the transcript instead")

    write_json(srt.parent / "picks.json", {"clips": picks})
    for p in picks:
        print(f'--clip {p["start"]}-{p["end"]} "{p["title"]}"')
    print(f"\n  {len(picks)} of {a.n} kept → {srt.parent / 'picks.json'}")
    for p in picks:
        print(f'  {p["start"]}-{p["end"]}  {p["title"]}  — {p["why"]}')


if __name__ == "__main__":
    main()
