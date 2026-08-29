#!/usr/bin/env python3
"""Find and download the video behind a news article URL.

    python grab.py "https://vijesti.hrt.hr/…" --work work/<slug>

Prints the local path on success. Writes source.json beside it with the article title, date and
the page it came from — keep that: it is the provenance record you need if anyone asks where a
clip came from, and it is what `--mode appearance` should be crediting.

RIGHTS. Downloading is not permission. A broadcaster's clip stays theirs; see step 0 of
HOW-THIS-IS-INTENDED-TO-WORK.md. This exists so you can watch, transcribe and quote a segment
locally — publishing a cut of it needs the broadcaster's written yes, or it goes out as
`--mode appearance`: text, credit and a link to their page, with no re-upload.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"
MEDIA_RE = re.compile(r'https?://[^\s"\'<>\\]+?\.(?:mp4|m3u8|mpd)(?:\?[^\s"\'<>\\]*)?', re.I)
JUNK = re.compile(r"(promo|teaser|trailer|preroll|advert|bumper|logo)", re.I)


def curl(url: str, referer: str = "", out: Path | None = None, head: bool = False) -> bytes:
    cmd = ["curl", "-sSL", "--max-time", "900", "-A", UA]
    if referer:
        cmd += ["-e", referer]
    if head:
        cmd += ["-I"]
    cmd += ["-o", str(out)] if out else []
    cmd.append(url)
    return subprocess.run(cmd, capture_output=True, check=True).stdout


def meta(html: str) -> dict:
    def og(prop: str) -> str:
        m = re.search(rf'<meta[^>]+property=["\']og:{prop}["\'][^>]+content=["\']([^"\']+)', html, re.I)
        if not m:
            m = re.search(rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:{prop}["\']', html, re.I)
        return m.group(1).strip() if m else ""

    date = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html)
    return {"title": og("title"), "description": og("description"),
            "date": date.group(1) if date else ""}


def find_media(html: str, page: str) -> list[str]:
    """Media URLs on the page, best first. Longest path wins as a rough proxy for the main
    asset — promo and bumper files tend to sit at shorter, tidier paths."""
    urls = []
    for u in MEDIA_RE.findall(html):
        u = u.replace("\\/", "/")
        if JUNK.search(u) or u in urls:
            continue
        urls.append(urllib.parse.urljoin(page, u))
    return sorted(urls, key=lambda u: (u.lower().endswith(".mp4"), len(u)), reverse=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Download the video behind an article URL.")
    ap.add_argument("url")
    ap.add_argument("--work", required=True)
    ap.add_argument("--name", default="source", help="basename for the downloaded file")
    ap.add_argument("--list", action="store_true", help="only list the media URLs found")
    a = ap.parse_args()

    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    html = curl(a.url).decode("utf-8", "replace")
    urls = find_media(html, a.url)
    if not urls:
        sys.exit("no media URL found on that page — the player may build it in JavaScript")
    for u in urls:
        print(f"  found {u}")
    if a.list:
        return

    info = meta(html)
    dest = work / f"{a.name}{Path(urllib.parse.urlparse(urls[0]).path).suffix or '.mp4'}"
    # Referer matters: CDNs in front of broadcaster media commonly 403 a bare request and
    # return 200 for the same URL when it looks like it came from the article page.
    curl(urls[0], referer=a.url, out=dest)
    if dest.stat().st_size < 100_000:
        sys.exit(f"download failed — {dest} is {dest.stat().st_size} bytes (blocked?)")

    (work / "source.json").write_text(json.dumps(
        {**info, "page": a.url, "media": urls[0], "file": dest.name,
         "rights": "Third-party footage unless stated otherwise. Do not re-upload without "
                   "written permission — see HOW-THIS-IS-INTENDED-TO-WORK.md step 0."},
        indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  {dest} ({dest.stat().st_size / 1e6:.0f} MB)")
    print(f"  {work / 'source.json'}")


if __name__ == "__main__":
    main()
