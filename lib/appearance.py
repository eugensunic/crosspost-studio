#!/usr/bin/env python3
"""Turn a link (HTV, podcast, someone's YouTube upload) into appearance.json — never downloads the video.

    python appearance.py "https://…" "Tom on HTV: …" --work work/<slug> [--host "HTV"] [--lang hr]
"""
from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

from common import ollama, slugify, write_json


def oembed(url: str) -> dict:
    """Try YouTube / generic oEmbed for title + embed html. Fail soft."""
    try:
        if "youtu" in url:
            q = urllib.parse.urlencode({"url": url, "format": "json"})
            with urllib.request.urlopen(f"https://www.youtube.com/oembed?{q}", timeout=20) as r:
                return json.load(r)
    except Exception:
        pass
    return {}


def page_title(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=20).read(200_000).decode("utf-8", "ignore")
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
    except Exception:
        return ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("title")
    ap.add_argument("--work", required=True)
    ap.add_argument("--host", default="")
    ap.add_argument("--lang", default="hr")
    ap.add_argument("--no-llm", action="store_true")
    a = ap.parse_args()

    oe = oembed(a.url)
    host = a.host or oe.get("provider_name") or urllib.parse.urlparse(a.url).netloc.replace("www.", "")
    src_title = oe.get("title") or page_title(a.url)
    embed = oe.get("html", "")

    summary = summary_en = ""
    if not a.no_llm:
        out = ollama(
            f'Guest appearance by Dr. Tom Sunic. Host: {host}. Headline: "{a.title}". Source title: "{src_title}".\n'
            f'Write a 2-sentence announcement in {"Croatian" if a.lang == "hr" else "English"} (key "summary") '
            f'and the same in English (key "summary_en"). Sober tone, no emojis. JSON only.',
            system="Return only valid JSON.", json_mode=True)
        try:
            d = json.loads(out)
            summary, summary_en = d.get("summary", ""), d.get("summary_en", "")
        except json.JSONDecodeError:
            pass

    data = {"title": a.title, "url": a.url, "host": host, "lang": a.lang, "slug": slugify(a.title),
            "source_title": src_title, "embed": embed, "summary": summary, "summary_en": summary_en}
    Path(a.work).mkdir(parents=True, exist_ok=True)
    write_json(Path(a.work) / "appearance.json", data)
    print(f"  appearance.json → {data['slug']} ({host})")


if __name__ == "__main__":
    main()
