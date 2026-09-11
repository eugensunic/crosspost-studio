#!/usr/bin/env python3
"""Transcribe a recording to SRT in chunks, so a long file cannot derail Whisper.

    python transcribe.py work/<slug>/source.mp4 --out work/<slug>/full.srt --lang hr

Whisper carries the previous window's text into the next one as a prompt. On a long
recording that feedback loop sometimes locks: one 99-minute interview came back with the same
sentence repeated 986 times from minute 15 to the end. Two things stop it, and both are done
here: the audio is cut into ten-minute pieces, and condition_on_previous_text is off, so no
window can poison the next. Cue timestamps are shifted back to the full recording afterwards.

Pieces are cached under <work>/.chunks/, so a re-run after a crash finishes the missing ones.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from common import CFG, ROOT

SEGMENT_S = 600


def to_secs(t: str) -> float:
    hh, mm, rest = t.strip().split(":")
    ss, ms = rest.split(",")
    return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000


def to_stamp(s: float) -> str:
    h, r = divmod(s, 3600)
    m, r = divmod(r, 60)
    sec, frac = divmod(r, 1)
    return f"{int(h):02d}:{int(m):02d}:{int(sec):02d},{int(round(frac * 1000)):03d}"


def cues(srt: Path) -> list[tuple[float, float, str]]:
    out = []
    for block in re.split(r"\n\s*\n", srt.read_text(encoding="utf-8").strip()):
        rows = [r for r in block.splitlines() if r.strip()]
        if len(rows) >= 3 and "-->" in rows[1]:
            a, b = rows[1].split("-->")
            out.append((to_secs(a), to_secs(b), " ".join(rows[2:])))
    return out


def looped(c: list[tuple[float, float, str]], run: int = 8) -> str | None:
    """The signature of a stuck decoder: the same text on many consecutive cues."""
    streak, last = 0, None
    for _, _, text in c:
        streak = streak + 1 if text == last else 1
        last = text
        if streak >= run:
            return text
    return None


def whisper(wav: Path, out_dir: Path, name: str, lang: str, model: str, words: bool,
            per_line: int = 0) -> None:
    py = ROOT / ".venv" / "bin" / "python"
    cmd = [str(py if py.exists() else sys.executable), "-m", "mlx_whisper.cli", str(wav),
           "--model", model, "--language", lang, "--condition-on-previous-text", "False",
           "--word-timestamps", str(words), "--output-format", "srt",
           "--output-dir", str(out_dir), "--output-name", name]
    if per_line:
        cmd += ["--max-words-per-line", str(per_line)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> None:
    ap = argparse.ArgumentParser(description="Chunked Whisper transcription to SRT.")
    ap.add_argument("media")
    ap.add_argument("--out", required=True)
    ap.add_argument("--lang", default=CFG["languages"]["spoken_default"])
    ap.add_argument("--model", default=CFG["whisper"]["model"])
    ap.add_argument("--segment", type=int, default=SEGMENT_S, help="seconds per piece")
    ap.add_argument("--no-word-timestamps", action="store_true")
    ap.add_argument("--words", type=int, default=0,
                    help="max words per caption line (3 for a Short, 6 for landscape); 0 = sentences")
    a = ap.parse_args()

    media, out = Path(a.media), Path(a.out)
    # One scratch folder per output, so two transcriptions in one work folder never share pieces.
    chunks = out.parent / f".chunks-{out.stem}"
    chunks.mkdir(parents=True, exist_ok=True)
    if not list(chunks.glob("part_*.wav")):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(media), "-vn", "-ac", "1",
                        "-ar", "16000", "-f", "segment", "-segment_time", str(a.segment),
                        "-reset_timestamps", "1", str(chunks / "part_%03d.wav")], check=True)
    parts = sorted(chunks.glob("part_*.wav"))
    for i, wav in enumerate(parts):
        srt = wav.with_suffix(".srt")
        if srt.exists():
            continue
        print(f"  transcribing {i + 1}/{len(parts)}", file=sys.stderr)
        whisper(wav, chunks, wav.stem, a.lang, a.model, not a.no_word_timestamps or bool(a.words),
                a.words)

    n, lines, warned = 1, [], False
    for i, wav in enumerate(parts):
        off = i * a.segment
        part = cues(wav.with_suffix(".srt"))
        if (bad := looped(part)) and not warned:
            print(f"  ⚠ piece {i + 1} still repeats a line ({bad[:50]}…); check that stretch",
                  file=sys.stderr)
            warned = True
        for s, e, text in part:
            lines += [str(n), f"{to_stamp(s + off)} --> {to_stamp(e + off)}", text, ""]
            n += 1
    out.write_text("\n".join(lines), encoding="utf-8")
    for p in chunks.iterdir():
        p.unlink()
    chunks.rmdir()
    print(f"  {out} ({n - 1} cues)")


if __name__ == "__main__":
    main()
