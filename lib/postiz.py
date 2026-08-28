#!/usr/bin/env python3
"""Build posts for every network and send them to Postiz in one call.

    python postiz.py --work work/<slug> --mode video|appearance|live [--dry-run]

Reads meta.json (from titles.py) or appearance.json; uploads media; POSTs /public/v1/posts.
Requires POSTIZ_KEY in the environment (.env).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import urllib.request
from pathlib import Path

from common import CFG, closing_line, link_block, read_json, write_json

API = CFG["postiz"]["url"].rstrip("/") + "/public/v1"
KEY = os.environ.get("POSTIZ_KEY", "")


def _req(path: str, data=None, files: dict | None = None):
    url = API + path
    if files:
        import mimetypes, uuid

        boundary = uuid.uuid4().hex
        body = b""
        for name, p in files.items():
            p = Path(p)
            ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            body += (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{p.name}\"\r\n"
                f"Content-Type: {ctype}\r\n\r\n"
            ).encode() + p.read_bytes() + b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": KEY, "Content-Type": f"multipart/form-data; boundary={boundary}"})
    else:
        req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                     headers={"Authorization": KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r)


def upload(path: Path) -> dict:
    print(f"  uploading {path.name}")
    return _req("/upload", files={"file": path})


def next_slot() -> str:
    """Next occurrence of the fixed weekly slot, ISO-8601 UTC."""
    from zoneinfo import ZoneInfo

    s = CFG["schedule"]
    tz = ZoneInfo(s["timezone"])
    now = dt.datetime.now(tz)
    hh, mm = map(int, s["hour"].split(":"))
    days = (s["weekday"] - now.isoweekday()) % 7
    cand = (now + dt.timedelta(days=days)).replace(hour=hh, minute=mm, second=0, microsecond=0)
    if cand <= now:
        cand += dt.timedelta(days=7)
    return cand.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def build_posts(work: Path, mode: str, when: str) -> dict:
    ids = CFG["postiz"]["integrations"]
    site = CFG["site"]["base_url"]
    if mode == "appearance":
        m = read_json(work / "appearance.json")
        spoken, slug = m.get("lang", "hr"), m["slug"]
        page = f"{site}/appearances/{slug}/"
        headline = m["title"]
        summary_en, summary_sp = m.get("summary_en", ""), m.get("summary", "")
        media: dict[str, list] = {}
        ext_link = m["url"]
    else:
        m = read_json(work / "meta.json")
        spoken, slug = m["spoken"], m["slug"]
        page = f"{site}/posts/{slug}/"
        headline = m["bilingual_title"]
        summary_en, summary_sp = m["en"]["summary"], m[spoken]["summary"]
        media = {k: [upload(p)] for k, p in {
            "long": work / "long.mp4", "short_1": work / "short_1.mp4",
            "short_2": work / "short_2.mp4", "teaser": work / "teaser.mp4",
            "thumb": work / "thumb.jpg"}.items() if p.exists()}
        ext_link = page

    tail = lambda net: f"\n\n{closing_line(spoken)}\n\n{link_block(net, mode, spoken)}"
    posts = []

    def add(net, content, value_media=None, settings=None):
        if not ids.get(net):
            print(f"  (skip {net}: no integration id in config)")
            return
        posts.append({"integration": {"id": ids[net]},
                      "value": [{"content": content, "image": value_media or []}],
                      "settings": settings or {}})

    if mode in ("video", "live") and "long" in media and mode == "video":
        add("youtube", m[spoken]["description"] + "\n\n" + m["en"]["description"] + tail("youtube"),
            media["long"], {"title": headline[:100], "type": CFG["youtube"]["default_privacy"],
                            "tags": m["en"].get("hashtags", [])})
    for i, key in enumerate(k for k in ("short_1", "short_2", "teaser") if k in media):
        add("youtube", f"{m[spoken]['title']} #Shorts\n{page}", media[key],
            {"title": f"{m[spoken]['title'][:85]} #Shorts", "type": CFG["youtube"]["default_privacy"]})
        add("instagram", f"{m[spoken]['title']}\n\n{summary_sp}\n\n{' '.join('#'+h.strip('#') for h in m[spoken].get('hashtags', []))}",
            media[key], {"post_type": "post"})
        if i == 0:
            add("x", (m["en"]["x"] if mode != "appearance" else headline)[:240] + f"\n{ext_link}", media[key])
    if mode == "appearance" or not any(k in media for k in ("short_1", "teaser")):
        add("x", (headline if mode == "appearance" else m["en"]["x"])[:240] + f"\n{ext_link}")
    add("linkedin", (m.get("en", {}).get("linkedin") or f"{headline}\n\n{summary_en}") + f"\n\n{ext_link}" + tail("linkedin"))
    add("facebook", f"{headline}\n\n{summary_sp}\n\n{ext_link}" + tail("facebook"),
        media.get("long") if mode == "video" else None)
    add("telegram", f"{headline}\n{ext_link}")

    return {"type": "schedule", "date": when, "shortLink": False, "tags": [], "posts": posts}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--mode", default="video")
    ap.add_argument("--now", action="store_true", help="publish immediately instead of the weekly slot")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    work = Path(a.work)

    when = dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z") if (a.now or a.mode == "appearance") else next_slot()
    if a.dry_run:
        os.environ.setdefault("POSTIZ_KEY", "dry")
        globals()["upload"] = lambda p: {"path": str(p)}  # type: ignore
    body = build_posts(work, a.mode, when)
    write_json(work / "posts.json", body)
    print(f"  {len(body['posts'])} posts scheduled for {when}")
    if a.dry_run:
        print("  dry-run: posts.json written, nothing sent")
        return
    if not KEY:
        raise SystemExit("POSTIZ_KEY missing — copy .env.example to .env")
    print(json.dumps(_req("/posts", body), indent=2)[:2000])


if __name__ == "__main__":
    main()
