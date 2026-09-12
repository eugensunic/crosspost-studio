#!/usr/bin/env python3
"""Which language is spoken in a recording. Prints the two-letter code (hr, fr, de, en...).

    python detect_lang.py work/<slug>/source.mp4

Whisper listens to thirty seconds from a tenth of the way in (past the intro music and the
host's welcome) and says what it hears. The spoken language decides the language of
everything downstream: captions, title card, title, description, tags. Falls back to
languages.spoken_default from config.yaml when the audio cannot be read.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from common import CFG


def duration(media: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                          "default=nw=1:nk=1", str(media)], capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def detect(media: Path) -> str:
    import mlx_whisper

    start = max(0.0, duration(media) * 0.1)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "probe.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.1f}", "-t", "30",
                        "-i", str(media), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
        result = mlx_whisper.transcribe(str(wav), path_or_hf_repo=CFG["whisper"]["model"],
                                        condition_on_previous_text=False)
    return str(result.get("language") or "").strip().lower()


def main() -> None:
    media = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if media is None or not media.exists():
        raise SystemExit("usage: detect_lang.py <media>")
    try:
        lang = detect(media)
    except Exception as e:  # noqa: BLE001 - any failure means "use the default"
        print(f"  ! language detection failed ({e}); using the default", file=sys.stderr)
        lang = ""
    print(lang or CFG["languages"]["spoken_default"])


if __name__ == "__main__":
    main()
