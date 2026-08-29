#!/usr/bin/env python3
"""Re-encode a finished short to fit somewhere that has limits.

    python shrink.py work/<slug>/short_1.mp4 --preset whatsapp
    python shrink.py work/<slug>/short_1.mp4 --max-mb 8 --max-seconds 30

Writes <name>.<preset>.mp4 next to the original and leaves the original alone.

Sizing is done by arithmetic, not by guessing a CRF: the bitrate that fits a given number of
megabytes into a given number of seconds is fixed, so it is computed and encoded two-pass,
which lands within a few percent. A CRF encode cannot promise a file size at all.

Presets are the published limits at the time of writing. Check them if an upload still bounces —
platforms move them, and WhatsApp in particular varies by app version and region.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PRESETS = {
    # WhatsApp Status: 30 s hard limit, and the uploader rejects anything over 10 MB with
    # "larger than the 10 MB limit" — observed, not the 16 MB quoted for ordinary media.
    # 9 leaves room for muxing overhead so a 10.1 MB file never comes back at you.
    "whatsapp": {"max_mb": 9, "max_seconds": 30, "height": 1280, "audio_k": 96},
    # Substack's own uploader is far more generous, but small files upload reliably; the
    # embed route (substack_post.py) avoids uploading at all.
    "substack": {"max_mb": 45, "max_seconds": None, "height": 1920, "audio_k": 128},
    # Generic "attach it to something" size.
    "small": {"max_mb": 8, "max_seconds": None, "height": 1280, "audio_k": 96},
}


def probe(path: Path) -> tuple[float, int, int]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-show_entries", "format=duration",
         "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    s = d["streams"][0]
    return float(d["format"]["duration"]), int(s["width"]), int(s["height"])


def encode(src: Path, dst: Path, seconds: float, v_k: int, a_k: int, height: int) -> None:
    """Two-pass, because only a target bitrate can hit a target file size."""
    vf = f"scale=-2:{height}"
    common = ["-y", "-loglevel", "error", "-i", str(src), "-t", f"{seconds:.3f}",
              "-vf", vf, "-c:v", "libx264", "-b:v", f"{v_k}k",
              "-maxrate", f"{int(v_k * 1.45)}k", "-bufsize", f"{v_k * 2}k",
              "-preset", "slow", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0"]
    log = dst.with_suffix(".2pass")
    subprocess.run(["ffmpeg", *common, "-pass", "1", "-passlogfile", str(log),
                    "-an", "-f", "mp4", "/dev/null"], check=True)
    subprocess.run(["ffmpeg", *common, "-pass", "2", "-passlogfile", str(log),
                    "-c:a", "aac", "-b:a", f"{a_k}k", "-movflags", "+faststart", str(dst)],
                   check=True)
    for leftover in log.parent.glob(log.name + "*"):
        leftover.unlink()


def main() -> None:
    ap = argparse.ArgumentParser(description="Fit a short inside a platform's limits.")
    ap.add_argument("input")
    ap.add_argument("--preset", choices=sorted(PRESETS), default="whatsapp")
    ap.add_argument("--max-mb", type=float, default=None)
    ap.add_argument("--max-seconds", type=float, default=None)
    ap.add_argument("--height", type=int, default=None)
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    src = Path(a.input)
    if not src.exists():
        raise SystemExit(f"no such file: {src}")
    p = PRESETS[a.preset]
    max_mb = a.max_mb if a.max_mb is not None else p["max_mb"]
    max_seconds = a.max_seconds if a.max_seconds is not None else p["max_seconds"]
    height = a.height or p["height"]
    a_k = p["audio_k"]

    dur, w, h = probe(src)
    seconds = min(dur, max_seconds) if max_seconds else dur
    if max_seconds and dur > max_seconds:
        print(f"  ! {dur:.1f}s is over the {max_seconds:g}s limit — trimming to {seconds:g}s")
        print("    a trimmed clip usually ends mid-sentence; better to re-cut the span shorter")

    # 0.94 leaves room for the container and muxing overhead the bitrate maths ignores.
    budget_k = (max_mb * 8 * 1024 * 0.94) / seconds
    v_k = int(budget_k - a_k)
    if v_k < 300:
        raise SystemExit(f"{max_mb} MB over {seconds:.0f}s leaves {v_k}k for video — unusable; "
                         f"raise --max-mb or shorten the clip")

    dst = Path(a.out) if a.out else src.with_suffix(f".{a.preset}.mp4")
    print(f"  {src.name}: {dur:.1f}s {w}x{h} → {seconds:.1f}s {height}p, video {v_k}k audio {a_k}k")
    encode(src, dst, seconds, v_k, a_k, height)

    size_mb = dst.stat().st_size / 1048576
    flag = "" if size_mb <= max_mb else "  ! still over budget"
    print(f"  wrote {dst} ({size_mb:.1f} MB of {max_mb:g} MB allowed){flag}")


if __name__ == "__main__":
    main()
