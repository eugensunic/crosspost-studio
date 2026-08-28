"""Minimal SRT parse/write."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_TS = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)")


@dataclass
class Cue:
    index: int
    start: str
    end: str
    text: str


def parse(path: Path | str) -> list[Cue]:
    blocks = re.split(r"\n\s*\n", Path(path).read_text(encoding="utf-8").strip())
    cues = []
    for b in blocks:
        lines = b.strip().splitlines()
        if len(lines) < 2:
            continue
        idx = int(lines[0]) if lines[0].strip().isdigit() else len(cues) + 1
        timing = lines[1] if lines[0].strip().isdigit() else lines[0]
        text_lines = lines[2:] if lines[0].strip().isdigit() else lines[1:]
        start, end = [t.strip() for t in timing.split("-->")]
        cues.append(Cue(idx, start, end, " ".join(l.strip() for l in text_lines)))
    return cues


def write(cues: list[Cue], path: Path | str) -> None:
    out = []
    for i, c in enumerate(cues, 1):
        out.append(f"{i}\n{c.start} --> {c.end}\n{c.text}\n")
    Path(path).write_text("\n".join(out), encoding="utf-8")


def to_seconds(ts: str) -> float:
    h, m, s, ms = _TS.match(ts).groups()
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def plain_text(cues: list[Cue]) -> str:
    return " ".join(c.text for c in cues)
