#!/usr/bin/env python3
"""Find and download the video behind a news article or video-platform URL.

    python grab.py "https://vijesti.hrt.hr/…" --work work/<slug>
    python grab.py "https://www.youtube.com/watch?v=…" --work work/<slug>

Two routes in. A broadcaster's article page has the media URL sitting in its HTML, so that one
is scraped. YouTube, Vimeo, Rumble and the rest build the stream in JavaScript from a signed
manifest, so nothing is scrapable and yt-dlp does the work instead. The route is chosen by host.

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
# Hosts that never put a plain media URL in their HTML. Anything not listed is scraped first and
# only falls back to yt-dlp when the scrape comes up empty, so an unknown broadcaster still works.
PLATFORMS = ("youtube.com", "youtu.be", "vimeo.com", "rumble.com", "odysee.com",
             "dailymotion.com", "tiktok.com", "twitter.com", "x.com", "facebook.com")
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

    def site_name() -> str:
        m = re.search(r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)', html, re.I)
        return m.group(1).strip() if m else ""

    date = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html)
    return {"title": og("title"), "description": og("description"),
            "date": date.group(1) if date else "", "uploader": site_name()}


def is_platform(url: str) -> bool:
    host = (urllib.parse.urlparse(url).hostname or "").lower().removeprefix("www.")
    return any(host == h or host.endswith("." + h) for h in PLATFORMS)


def ytdlp(url: str, dest: Path | None = None) -> dict:
    """Metadata for a video-platform URL, and the file itself when `dest` is given.

    One 1080p-or-below mp4, because everything downstream is a 1080x1920 render and a 4K source
    only costs disk and decode time. yt-dlp writes to <dest> exactly, so the caller keeps naming.
    """
    probe = subprocess.run(["yt-dlp", "--no-warnings", "-J", url],
                           capture_output=True, text=True)
    if probe.returncode != 0:
        raise RuntimeError((probe.stderr or "yt-dlp failed").strip().splitlines()[-1])
    d = json.loads(probe.stdout)
    if d.get("_type") == "playlist":
        sys.exit("that URL is a playlist or channel — pass the link to one video")

    info = {"title": d.get("title", ""), "description": (d.get("description") or "")[:500],
            "date": str(d.get("upload_date") or ""), "uploader": d.get("channel") or d.get("uploader") or "",
            "duration_s": d.get("duration"), "video_id": d.get("id", "")}
    if dest is None:
        return info

    run = subprocess.run(
        ["yt-dlp", "--no-warnings", "--no-playlist", "--merge-output-format", "mp4",
         "-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]/b",
         "-o", str(dest), url],
        capture_output=True, text=True)
    if run.returncode != 0 or not dest.exists():
        raise RuntimeError((run.stderr or "yt-dlp download failed").strip().splitlines()[-1])
    return info


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

    urls: list[str] = []
    html = ""
    if not is_platform(a.url):
        html = curl(a.url).decode("utf-8", "replace")
        urls = find_media(html, a.url)
        for u in urls:
            print(f"  found {u}")

    if urls:
        info, media = meta(html), urls[0]
        dest = work / f"{a.name}{Path(urllib.parse.urlparse(media).path).suffix or '.mp4'}"
        if a.list:
            return
        # Referer matters: CDNs in front of broadcaster media commonly 403 a bare request and
        # return 200 for the same URL when it looks like it came from the article page.
        curl(media, referer=a.url, out=dest)
        if dest.stat().st_size < 100_000:
            sys.exit(f"download failed — {dest} is {dest.stat().st_size} bytes (blocked?)")
    else:
        # Either a known platform, or a page whose player is built in JavaScript. Same answer.
        dest, media = work / f"{a.name}.mp4", a.url
        try:
            if a.list:
                info = ytdlp(a.url)
                print(f"  found {info['title']} — {info['uploader']} ({info['duration_s']}s)")
                return
            print("  yt-dlp …")
            info = ytdlp(a.url, dest)
        except RuntimeError as e:
            sys.exit(f"could not fetch that URL: {e}")

    (work / "source.json").write_text(json.dumps(
        {**info, "page": a.url, "media": media, "file": dest.name,
         "rights": "Third-party footage unless stated otherwise. Do not re-upload without "
                   "written permission — see HOW-THIS-IS-INTENDED-TO-WORK.md step 0."},
        indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  {dest} ({dest.stat().st_size / 1e6:.0f} MB)")
    print(f"  {work / 'source.json'}")


if __name__ == "__main__":
    main()
