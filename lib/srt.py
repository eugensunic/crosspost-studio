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


def from_seconds(t: float) -> str:
    h, rem = divmod(max(0.0, t), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


def resplit(cues: list[Cue], max_words: int) -> list[Cue]:
    """Break long cues into short caption lines, sharing each cue's time by word count.

    Subtitles are translated a whole sentence at a time, because a translator handed
    three-word fragments produces nonsense. Captions have to be short to be readable, so the
    sentence is cut up again afterwards.
    """
    out: list[Cue] = []
    for c in cues:
        words = c.text.split()
        if not words:
            continue
        start, end = to_seconds(c.start), to_seconds(c.end)
        span = max(end - start, 0.001)
        chunks = [words[i:i + max_words] for i in range(0, len(words), max_words)]
        used = 0
        for chunk in chunks:
            a = start + span * used / len(words)
            used += len(chunk)
            b = start + span * used / len(words)
            out.append(Cue(len(out) + 1, from_seconds(a), from_seconds(b), " ".join(chunk)))
    return out


def plain_text(cues: list[Cue]) -> str:
    return " ".join(c.text for c in cues)
