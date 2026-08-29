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

Choose the single best moment in this passage to cut as a standalone vertical short video.

Give only the timestamp where each moment BEGINS. Do not give an end time; the clip is
extended automatically to the end of the thought. So pick the line where the speaker starts
saying the thing worth hearing, and make sure it is the beginning of a sentence.

Rules:
- each moment is one idea that stands on its own and needs no earlier context
- prefer a concrete claim, number or quotation over generalities
- ignore anything that reads like a transcription error, and never put such a word in a title

For each write two titles, each a short claim of at most 6 words, the thing that makes someone
stop scrolling. Not a topic label, no quotation marks, sentence case not Title Case.
  title     written in {language}, and ONLY in {language}
  title_en  the same claim written in English

Answer with JSON only:
{{"clips": [{{"start": "MM:SS", "title": "...", "title_en": "...", "why": "one sentence"}}]}}"""

LANGUAGES = {"hr": "Croatian", "en": "English", "fr": "French", "de": "German"}


def load_cues(srt: Path) -> list[tuple[float, float, str]]:
    def secs(t: str) -> float:
        hh, mm, rest = t.split(":")
        ss, ms = rest.split(",")
        return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000

    cues = []
    for block in re.split(r"\n\s*\n", srt.read_text(encoding="utf-8").strip()):
        rows = [r for r in block.splitlines() if r.strip()]
        if len(rows) >= 3 and "-->" in rows[1]:
            a, b = [x.strip() for x in rows[1].split("-->")]
            cues.append((secs(a), secs(b), " ".join(rows[2:])))
    return cues


def transcript_lines(srt: Path) -> tuple[str, float]:
    """Timestamped one-line-per-cue text, plus the end of the last cue in seconds."""
    cues = load_cues(srt)
    body = "\n".join(f"{int(s // 60):02d}:{int(s % 60):02d} {t}" for s, _, t in cues)
    return body, (cues[-1][1] if cues else 0.0)


def to_secs(stamp: str) -> float | None:
    m = re.match(r"^\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*$", stamp)
    if not m:
        return None
    a, b, c = m.groups()
    return int(a) * 3600 + int(b) * 60 + int(c) if c else int(a) * 60 + int(b)


ENDS_SENTENCE = re.compile(r"[.!?]['\"]?\s*$")
MIN_GAP = 90  # seconds between picks: a small model clusters them all in the opening minutes


def snap(cues: list[tuple[float, float, str]], anchor: float, lo: int, hi: int):
    """Turn the model's anchor into a real span.

    The model is good at spotting the moment and hopeless at timestamp arithmetic, so it only
    supplies a start. Here the start is pulled back to the beginning of its sentence, and the
    end is walked forward to the first sentence boundary past the minimum length.
    """
    i = min(range(len(cues)), key=lambda k: abs(cues[k][0] - anchor))
    while i > 0 and not ENDS_SENTENCE.search(cues[i - 1][2]):
        i -= 1
    start = cues[i][0]
    j = i
    while j + 1 < len(cues):
        if cues[j][1] - start >= lo and ENDS_SENTENCE.search(cues[j][2]):
            break
        if cues[j][1] - start >= hi:
            break
        j += 1
    return start, cues[j][1]


def validate(clips: list[dict], cues, duration: float, lo: int, hi: int) -> list[dict]:
    """Drop what the model got wrong: bad stamps, overlaps, anything past the end."""
    good: list[dict] = []
    for c in clips:
        anchor = to_secs(str(c.get("start", "")))
        title = str(c.get("title", "")).strip().strip('"').strip()
        title_en = str(c.get("title_en", "")).strip().strip('"').strip() or title
        if anchor is None or not title or anchor >= duration:
            continue
        st, en = snap(cues, anchor, lo, hi)
        if en - st < lo * 0.6:
            continue
        if any(abs(st - g["start_s"]) < MIN_GAP for g in good):
            continue
        good.append({"start": f"{int(st // 60):02d}:{int(st % 60):02d}",
                     "end": f"{int(en // 60):02d}:{int(en % 60):02d}",
                     "start_s": st, "end_s": en, "title": title, "title_en": title_en,
                     "why": str(c.get("why", "")).strip()})
    return sorted(good, key=lambda g: g["start_s"])


def main() -> None:
    ap = argparse.ArgumentParser(description="Pick and title clippable moments.")
    ap.add_argument("srt")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--lang", default="hr")
    # 45-75s is the rule of thumb in the docs, and it is right for a YouTube Short. But one
    # span feeds both renders, and WhatsApp Status refuses anything over 30s — so 30s binds,
    # and a span that respects it is never trimmed mid-sentence afterwards.
    ap.add_argument("--min", type=int, default=20)
    ap.add_argument("--max", type=int, default=28)
    a = ap.parse_args()

    srt = Path(a.srt)
    cues = load_cues(srt)
    text, duration = transcript_lines(srt)
    if not text:
        raise SystemExit(f"no cues in {srt}")

    # One call per window rather than one call for the whole interview. Asked for three from
    # thirteen minutes, a small model returns three moments from the first three minutes and
    # stops reading; asked for the best moment in one passage, it answers about that passage.
    clips = []
    window = duration / a.n
    for k in range(a.n):
        lo_t, hi_t = k * window, (k + 1) * window
        part = "\n".join(line for line in text.splitlines()
                          if lo_t <= to_secs(line[:5]) < hi_t) if text else ""
        if not part.strip():
            continue
        prompt = TEMPLATE.format(transcript=part, n=1, lo=a.min, hi=a.max,
                                 language=LANGUAGES.get(a.lang, a.lang))
        try:
            raw = ollama(prompt, system=SYSTEM, json_mode=True)
        except OSError as e:
            raise SystemExit(
                f"could not reach Ollama ({e}). Start it with `brew services start ollama` "
                f"and pull the model named in config.yaml: `ollama pull {CFG['ollama']['model']}`")
        try:
            clips += json.loads(raw).get("clips", [])[:1]
        except json.JSONDecodeError:
            print(f"  window {k + 1}: model did not return JSON, skipped")

    picks = validate(clips, cues, duration, a.min, a.max)
    if not picks:
        raise SystemExit("nothing usable came back — pick by hand from the transcript instead")

    write_json(srt.parent / "picks.json", {"clips": picks})
    for p in picks:
        print(f'--clip {p["start"]}-{p["end"]} "{p["title"]} || {p["title_en"]}"')
    print(f"\n  {len(picks)} of {a.n} kept → {srt.parent / 'picks.json'}")
    for p in picks:
        print(f'  {p["start"]}-{p["end"]}  {p["title"]} / {p["title_en"]}')


if __name__ == "__main__":
    main()
