#!/usr/bin/env python3
"""Polish a raw clip into a finished vertical short — one ffmpeg pass, no libass needed.

    python polish.py raw.mov --work work/<slug> --srt work/<slug>/hr.srt --title "Naslov"

Does, in order:
  1. finds screen-recorder junk (player control bar, mouse cursor, scrub tooltips) and removes it
  2. fits the whole frame into 1080x1920 over plain black — nothing is ever cropped off
  3. burns the subtitles in, so it reads with the sound off
  4. holds the title over the opening seconds

Captions are rendered to PNGs with Pillow and composited, because Homebrew's ffmpeg ships
without libass/freetype — `subtitles`, `ass` and `drawtext` do not exist in that build.
See POLISHING.md for the rules this implements.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
OUT_W, OUT_H = 1080, 1920

CAP_SIZE, CAP_BAND_H, CAP_Y, CAP_WRAP = 68, 240, 1330, 22
TITLE_SIZE, TITLE_BAND_H, TITLE_Y, TITLE_WRAP = 78, 400, 270, 18
TITLE_IN, TITLE_HOLD = 0.3, 3.6

# The same clip as a normal 16:9 video instead of a Short: the picture fills the canvas, the
# captions sit at the bottom of the picture and the title over its top.
FORMATS = {
    "short":     dict(out=(1080, 1920), cap=(68, 240, 1330, 22), title=(78, 400, 270, 18)),
    # Talking heads sit high in a 16:9 frame, so the title is one line hugging the top edge.
    "landscape": dict(out=(1920, 1080), cap=(52, 180, 870, 60), title=(60, 120, 14, 52)),
}


def set_format(name: str) -> None:
    global OUT_W, OUT_H, CAP_SIZE, CAP_BAND_H, CAP_Y, CAP_WRAP
    global TITLE_SIZE, TITLE_BAND_H, TITLE_Y, TITLE_WRAP
    f = FORMATS[name]
    OUT_W, OUT_H = f["out"]
    CAP_SIZE, CAP_BAND_H, CAP_Y, CAP_WRAP = f["cap"]
    TITLE_SIZE, TITLE_BAND_H, TITLE_Y, TITLE_WRAP = f["title"]

# overlay detection
SAMPLE_FPS = 5.0
SCAN_SECONDS = 14.0        # window the temporal median is built from
BLOB_THRESHOLD = 70        # cursor/tooltip are high-contrast; a moving hand is not
BLOB_MAX_FRAC = 0.22       # anything bigger than this share of the frame is content
SHOT_CUT_DELTA = 22        # mean frame-to-frame change (upper frame) that counts as a cut
CHROME_DROP_DELTA = 12     # bottom-of-frame change that marks player chrome auto-hiding
BLOB_PAD = 34              # grow each pointer box: the grid quantises, and pointers move
CHROME_BAND_FRAC = 0.24    # share of frame height masked while player chrome is up


# ───────────────────────────── probing and sampling ─────────────────────────────


def probe(path: Path) -> tuple[int, int, float]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height", "-show_entries", "format=duration",
         "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    s = d["streams"][0]
    return int(s["width"]), int(s["height"]), float(d["format"]["duration"])


def sample_gray(path: Path, w: int, h: int, upto: float) -> tuple[np.ndarray, int]:
    """Grey frames at SAMPLE_FPS, half size, as (n, h2, w2) uint8."""
    w2, h2 = (w // 2) & ~1, (h // 2) & ~1
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-t", f"{upto:.3f}", "-i", str(path),
         "-vf", f"fps={SAMPLE_FPS},scale={w2}:{h2},format=gray",
         "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    n = len(raw) // (w2 * h2)
    return np.frombuffer(raw, np.uint8)[: n * w2 * h2].reshape(n, h2, w2), 2


# ───────────────────────────── overlay detection ─────────────────────────────


def _components(mask: np.ndarray, block: int = 8) -> list[tuple[int, int, int, int]]:
    """Connected blobs, found on a coarse block grid (good enough, and dependency-free)."""
    h, w = mask.shape
    bh, bw = -(-h // block), -(-w // block)   # round up: truncating drops the frame edges,
    if bh == 0 or bw == 0:                    # which is exactly where a pointer often sits
        return []
    padded = np.zeros((bh * block, bw * block), bool)
    padded[:h, :w] = mask
    grid = padded.reshape(bh, block, bw, block).any(axis=(1, 3))
    seen = np.zeros_like(grid, bool)
    boxes = []
    for sy in range(bh):
        for sx in range(bw):
            if not grid[sy, sx] or seen[sy, sx]:
                continue
            stack, cells = [(sy, sx)], []
            seen[sy, sx] = True
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < bh and 0 <= nx < bw and grid[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            ys = [c[0] for c in cells]
            xs = [c[1] for c in cells]
            boxes.append((min(xs) * block, min(ys) * block,
                          (max(xs) + 1) * block, (max(ys) + 1) * block))
    return boxes


def _first_cut(frames: np.ndarray) -> int:
    """Index of the first shot change, or len(frames). A median spanning two shots is a blend
    of both, so everything differs from it and no overlay can be picked out of the noise.

    Measured on the upper part of the frame only: player chrome vanishing is a large change
    too, but it happens along the bottom edge, and mistaking it for a cut would truncate the
    window to exactly the stretch where the chrome is always present — and so invisible.
    """
    top = frames[:, : int(frames.shape[1] * 0.6), :].astype(np.int16)
    step = np.abs(top[1:] - top[:-1]).mean(axis=(1, 2))
    cuts = np.where(step > SHOT_CUT_DELTA)[0]
    return int(cuts[0]) + 1 if cuts.size else len(frames)


def detect_overlays(path: Path, w: int, h: int, dur: float) -> tuple[int | None, float, list[dict]]:
    """Return (bar_top_y, bar_end_time, blob masks) in full-resolution coordinates.

    Two very different things, found two different ways:

    * The control bar is a wide band that reaches the bottom edge of the frame and covers
      the same rows for as long as it is up. Frames straddling a shot change differ from the
      median everywhere, so they are excluded before looking for it.
    * Cursors and scrub tooltips only exist while that bar is up, so they are only looked for
      inside that window — and they are small and far higher contrast than a moving person,
      which is what separates them from the speaker's hands.
    """
    frames, scale = sample_gray(path, w, h, min(dur, SCAN_SECONDS))
    if len(frames) < 8:
        return None, 0.0, []
    frames = frames[:_first_cut(frames)]
    if len(frames) < 6:
        return None, 0.0, []
    h2, w2 = frames[0].shape

    # ── control bar: found by the moment it disappears ──
    # Studio backdrops are often animated, so most pixels differ from any long-window median
    # and thresholding that is hopeless. The bar's exit is unmistakable though: one sample to
    # the next, a large change confined to the bottom rows while the top of frame carries on.
    lo = int(h2 * 0.6)
    step = np.abs(frames[1:, lo:, :].astype(np.int16) - frames[:-1, lo:, :]).mean(axis=(1, 2))
    bar_top, bar_end = None, 0.0
    if step.size and step.max() > CHROME_DROP_DELTA:
        s = int(step.argmax())
        gap = np.abs(frames[s + 1].astype(np.int16) - frames[s])
        cover = (gap > 30).mean(axis=1)
        if cover[-1] > 0.5:
            # Detecting *that* the chrome went away is reliable. Measuring how tall it was is
            # not: the speaker is usually moving in the same instant, and their motion covers
            # the bottom rows as thoroughly as the bar does — there is no clean edge to find.
            # So mask a fixed share instead, sized to clear a scrub line and a button row.
            bar_top = h - int(h * CHROME_BAND_FRAC)
            bar_end = (s + 1) / SAMPLE_FPS + 0.2

    # ── cursor and tooltip, only while the bar is up ──
    # Against a local median a few frames wide the animated backdrop has barely moved, so what
    # stands out is what moved fast: the pointer, the scrub tooltip, and the speaker's hands —
    # and hands are far larger and far lower contrast than either.
    blobs = []
    last = int(bar_end * SAMPLE_FPS) if bar_top is not None else -1
    for i in range(min(last + 1, len(frames))):
        t = i / SAMPLE_FPS
        near = np.concatenate([frames[max(0, i - 3):i], frames[i + 1:i + 4]])
        if len(near) < 3:
            continue
        diff = np.abs(frames[i].astype(np.int16) - np.median(near, axis=0))
        strong = diff > BLOB_THRESHOLD
        if bar_top is not None:
            strong[bar_top // scale:, :] = False
        for x0, y0, x1, y1 in _components(strong):
            bw, bh = (x1 - x0) * scale, (y1 - y0) * scale
            if bw > 180 or bh > 110 or bw * bh > BLOB_MAX_FRAC * w * h:
                continue  # a person moving, not a cursor
            if bw < 18 or bh < 18:                        # backdrop animation, not a pointer
                continue
            patch = strong[y0:y1, x0:x1]
            fill, md = patch.mean(), diff[y0:y1, x0:x1][patch].mean()
            if md < 100:                                  # far brighter than a moving hand
                continue
            # An arrow pointer is mostly empty inside its own bounding box, so a plain
            # compactness floor throws it away. Small and bright is enough on its own.
            if fill < 0.30 and not (fill >= 0.15 and bw * bh <= 6000):
                continue
            # pad: the block grid quantises the box, and a pointer moves between samples
            blobs.append({"x": x0 * scale - BLOB_PAD, "y": y0 * scale - BLOB_PAD,
                          "w": bw + 2 * BLOB_PAD, "h": bh + 2 * BLOB_PAD,
                          "start": max(0.0, t - 0.16), "end": t + 0.32})
    return bar_top, bar_end, _merge(blobs)


def _merge(blobs: list[dict]) -> list[dict]:
    """Fold overlapping boxes from consecutive samples into single, longer-lived masks."""
    out: list[dict] = []
    for b in sorted(blobs, key=lambda d: d["start"]):
        for o in out:
            overlap = (b["x"] < o["x"] + o["w"] and b["x"] + b["w"] > o["x"]
                       and b["y"] < o["y"] + o["h"] and b["y"] + b["h"] > o["y"])
            if overlap and b["start"] <= o["end"] + 0.25:
                x0, y0 = min(o["x"], b["x"]), min(o["y"], b["y"])
                o.update(x=x0, y=y0,
                         w=max(o["x"] + o["w"], b["x"] + b["w"]) - x0,
                         h=max(o["y"] + o["h"], b["y"] + b["h"]) - y0,
                         end=max(o["end"], b["end"]))
                break
        else:
            out.append(dict(b))
    return out


# ───────────────────────────── text rendering ─────────────────────────────


def _card(text: str, size: int, band_h: int, wrap: int, dest: Path) -> None:
    font = ImageFont.truetype(FONT, size)
    lines = textwrap.wrap(text, wrap) or [text]
    img = Image.new("RGBA", (OUT_W, band_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lh = size + 18
    y = (band_h - lh * len(lines)) // 2
    for ln in lines:
        d.text((OUT_W // 2, y), ln, font=font, fill=(255, 255, 255, 255),
               stroke_width=max(6, size // 10), stroke_fill=(0, 0, 0, 240), anchor="ma")
        y += lh
    img.save(dest)


def parse_srt(path: Path, offset: float = 0.0, dur: float | None = None):
    """Cues shifted back by `offset` — a short cut from 12:40 needs the subtitles for 12:40
    rebased to zero — with anything falling outside the clip dropped."""
    def secs(t: str) -> float:
        hh, mm, rest = t.split(":")
        ss, ms = rest.split(",")
        return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000

    cues = []
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8").strip()):
        rows = [r for r in block.splitlines() if r.strip()]
        if len(rows) >= 3 and "-->" in rows[1]:
            a, b = [x.strip() for x in rows[1].split("-->")]
            st, en = secs(a) - offset, secs(b) - offset
            if en <= 0 or (dur is not None and st >= dur):
                continue
            cues.append((max(0.0, st), min(en, dur) if dur else en, " ".join(rows[2:])))
    return cues


# ───────────────────────────── the one pass ─────────────────────────────


def _even(v: float) -> int:
    """Chroma planes are half resolution, so crop and overlay geometry must be even."""
    return max(0, int(v) & ~1)


def _at_edge(b: dict, width: int, height: int, slack: int = 2) -> bool:
    return (b["x"] <= slack or b["y"] <= slack
            or b["x"] + b["w"] >= width - slack or b["y"] + b["h"] >= height - slack)


def _clamp(b: dict, width: int, height: int) -> dict | None:
    """delogo interpolates from the pixels around the box, so it needs a border on all sides."""
    x, y = max(1, int(b["x"])), max(1, int(b["y"]))
    x1, y1 = min(width - 2, int(b["x"] + b["w"])), min(height - 2, int(b["y"] + b["h"]))
    if x1 - x < 4 or y1 - y < 4:
        return None
    return {**b, "x": x, "y": y, "w": x1 - x, "h": y1 - y}


def build(src: Path, out: Path, cues, title: str, tmp: Path, bar_top: int | None,
          bar_end: float, blobs: list[dict], width: int, height: int,
          title_pos: str = "band") -> None:
    tmp.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src)]
    chain = []

    # 1. clean: interpolate small overlays away, blur the control bar band
    # A box flush against the frame edge has no surrounding pixels on that side, so delogo
    # cannot interpolate it — those get a blurred patch instead, which needs no neighbours.
    inner, edge = [], []
    for b in blobs:
        c = _clamp(b, width, height)
        if c is None:
            continue
        (edge if _at_edge(b, width, height) else inner).append(c)
    steps = [f"delogo=x={b['x']}:y={b['y']}:w={b['w']}:h={b['h']}"
             f":enable='between(t,{b['start']:.2f},{b['end']:.2f})'" for b in inner]
    chain.append("[0:v]" + (",".join(steps) if steps else "null") + "[cl]")
    prev = "[cl]"
    for i, b in enumerate(edge):
        x, y = _even(b["x"]), _even(b["y"])
        bw, bh = _even(min(b["w"], width - x)), _even(min(b["h"], height - y))
        if bw < 4 or bh < 4:
            continue
        chain.append(f"{prev}split=2[cb{i}][cp{i}]")
        chain.append(f"[cp{i}]crop={bw}:{bh}:{x}:{y},gblur=sigma=14[cg{i}]")
        chain.append(f"[cb{i}][cg{i}]overlay={x}:{y}"
                     f":enable='between(t,{b['start']:.2f},{b['end']:.2f})'[ce{i}]")
        prev = f"[ce{i}]"
    if bar_top is not None:
        band = height - bar_top
        chain.append(f"{prev}split=2[base][m]")
        # gblur, not boxblur: boxblur caps its radius at the chroma plane's size, so a short
        # band makes it fail outright.
        chain.append(f"[m]crop=iw:{band}:0:ih-{band},gblur=sigma=24[mb]")
        chain.append(f"[base][mb]overlay=0:H-{band}:enable='lte(t,{bar_end:.2f})'[cd]")
    else:
        chain.append(f"{prev}null[cd]")

    # 2. 1080x1920 over plain black — nothing is cropped out of frame, no blurred pad
    chain.append(f"[cd]scale={OUT_W}:-2,pad={OUT_W}:{OUT_H}:0:(oh-ih)/2:black,setsar=1[v0]")

    # 3. subtitles
    for i, (st, en, text) in enumerate(cues):
        png = tmp / f"cap_{i:03d}.png"
        _card(text, CAP_SIZE, CAP_BAND_H, CAP_WRAP, png)
        cmd += ["-i", str(png)]
        chain.append(f"[v{i}][{i+1}:v]overlay=0:{CAP_Y}"
                     f":enable='between(t,{st:.3f},{en:.3f})'[v{i+1}]")
    label = f"[v{len(cues)}]"

    # 4. title held over the opening
    if title:
        png = tmp / "title.png"
        _card(title, TITLE_SIZE, TITLE_BAND_H, TITLE_WRAP, png)
        idx = len(cues) + 1
        end = TITLE_IN + TITLE_HOLD
        if title_pos == "over":
            # On the picture itself: just inside the top of the video strip, whose height
            # follows from the source aspect once it is scaled to full canvas width.
            strip = int(OUT_W * height / width)
            title_y = (OUT_H - strip) // 2 + 30
        else:
            title_y = TITLE_Y
        # -loop: a still image is one frame at t=0, and fade would evaluate its alpha there
        # only — leaving a fully transparent frame that overlay then repeats for the whole clip.
        cmd += ["-loop", "1", "-framerate", "30", "-t", f"{end + 0.5:.2f}", "-i", str(png)]
        chain.append(f"[{idx}:v]format=rgba,fade=t=in:st={TITLE_IN}:d=0.4:alpha=1,"
                     f"fade=t=out:st={end - 0.5:.2f}:d=0.5:alpha=1[tt]")
        chain.append(f"{label}[tt]overlay=0:{title_y}"
                     f":enable='between(t,{TITLE_IN},{end:.2f})'[vt]")
        label = "[vt]"

    cmd += ["-filter_complex", ";".join(chain), "-map", label, "-map", "0:a?",
            "-r", "30", "-c:v", "libx264", "-crf", "20", "-preset", "medium",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Clean, pad, caption and title a clip.")
    ap.add_argument("input")
    ap.add_argument("--work", required=True)
    ap.add_argument("--srt", default="", help="subtitles to burn in (skipped if absent)")
    ap.add_argument("--title", default="", help="held over the opening seconds")
    ap.add_argument("--out", default="", help="default: <work>/short_1.mp4")
    ap.add_argument("--srt-offset", type=float, default=0.0,
                    help="seconds into the source this clip starts, for rebasing subtitles")
    ap.add_argument("--title-pos", choices=["band", "over"], default="band",
                    help="band: in the black band above the picture; over: on the picture")
    ap.add_argument("--no-clean", action="store_true", help="skip overlay removal")
    ap.add_argument("--format", choices=sorted(FORMATS), default="short",
                    help="short: 1080x1920 vertical; landscape: 1920x1080 normal video")
    a = ap.parse_args()
    set_format(a.format)

    src, work = Path(a.input), Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    out = Path(a.out) if a.out else work / "short_1.mp4"
    w, h, dur = probe(src)

    bar_top, bar_end, blobs = (None, 0.0, [])
    if not a.no_clean:
        bar_top, bar_end, blobs = detect_overlays(src, w, h, dur)
        if bar_top is not None:
            print(f"  control bar: bottom {h - bar_top}px, visible to {bar_end:.1f}s")
        for b in blobs:
            print(f"  mask {b['w']}x{b['h']} at ({b['x']},{b['y']}) "
                  f"{b['start']:.2f}-{b['end']:.2f}s")

    cues = (parse_srt(Path(a.srt), a.srt_offset, dur)
            if a.srt and Path(a.srt).exists() else [])
    print(f"  {len(cues)} subtitle cues, title={'yes' if a.title else 'no'}")
    build(src, out, cues, a.title, work / ".cards", bar_top, bar_end, blobs, w, h, a.title_pos)
    print(f"  wrote {out}")


if __name__ == "__main__":
    main()
