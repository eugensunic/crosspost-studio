#!/usr/bin/env python3
"""Upload every finished clip in a work folder to YouTube, copy and all.

    python yt_publish.py work/<date>-<slug>            # everything in youtube/ not yet uploaded
    python yt_publish.py work/<date>-<slug> --dry-run  # show what would go, send nothing
    python yt_publish.py work/<date>-<slug> --privacy public

For each youtube/<name>.mp4 the copy is read from youtube/<name>.txt, the file bin/clip.sh
writes next to the clip:

    TITLE
    one line, under 100 characters

    DESCRIPTION
    two or three sentences, the source link, the hashtags

    TAGS
    comma, separated, tags

    THUMBNAIL
    <name>.jpg           relative to the txt, optional but expected

A clip with no txt, an empty title, an empty description or no tags is refused, not uploaded
with defaults: every video that goes out has all four. Finished uploads are recorded in
youtube/uploaded.json so re-running the command only sends what is new.

RIGHTS: uploading is publishing. Broadcaster footage needs their written yes, see step 0 of
HOW-THIS-IS-INTENDED-TO-WORK.md. Privacy defaults to config.yaml (unlisted): check the
Copyright tab in Studio, then flip to public.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from common import CFG, read_json, write_json
from youtube_upload import service, set_thumbnail, upload, whoami

SECTIONS = ("TITLE", "DESCRIPTION", "TAGS", "THUMBNAIL")


def parse_copy(txt: Path) -> dict:
    parts: dict[str, list[str]] = {}
    cur = None
    for line in txt.read_text(encoding="utf-8").splitlines():
        if line.strip() in SECTIONS:
            cur = line.strip()
            parts[cur] = []
        elif cur:
            parts[cur].append(line)
    out = {k: "\n".join(v).strip() for k, v in parts.items()}
    out["TAGS"] = [t.strip() for t in re.split(r"[,\n]", out.get("TAGS", "")) if t.strip()]
    return out


def check(name: str, c: dict, txt: Path) -> list[str]:
    problems = []
    if not c.get("TITLE"):
        problems.append("no TITLE")
    elif len(c["TITLE"]) > 100:
        problems.append(f"TITLE is {len(c['TITLE'])} characters, YouTube's limit is 100")
    if not c.get("DESCRIPTION"):
        problems.append("no DESCRIPTION")
    elif len(c["DESCRIPTION"]) > 5000:
        problems.append("DESCRIPTION over 5000 characters")
    if not c.get("TAGS"):
        problems.append("no TAGS")
    thumb = c.get("THUMBNAIL", "")
    if not thumb:
        problems.append("no THUMBNAIL")
    elif not (txt.parent / thumb).exists():
        problems.append(f"THUMBNAIL {thumb} does not exist")
    return problems


def main() -> None:
    ap = argparse.ArgumentParser(description="Upload a work folder's clips to YouTube.")
    ap.add_argument("work", help="work/<date>-<slug>, or its youtube/ folder")
    ap.add_argument("--privacy", choices=["private", "unlisted", "public"],
                    default=CFG["youtube"]["default_privacy"])
    ap.add_argument("--channel-id", default=CFG["youtube"].get("channel_id", ""))
    ap.add_argument("--only", nargs="*", default=[], help="basenames to upload, default all")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    folder = Path(a.work)
    if folder.name != "youtube":
        folder = folder / "youtube"
    if not folder.is_dir():
        raise SystemExit(f"no such folder: {folder}")
    ledger = folder / "uploaded.json"
    done = read_json(ledger) if ledger.exists() else {}

    clips = sorted(p for p in folder.glob("*.mp4") if not a.only or p.stem in a.only)
    if not clips:
        raise SystemExit(f"no .mp4 in {folder}")

    todo, refused = [], []
    for mp4 in clips:
        if mp4.name in done:
            print(f"  skip {mp4.name}: already at {done[mp4.name]['url']}")
            continue
        txt = mp4.with_suffix(".txt")
        if not txt.exists():
            refused.append((mp4.name, ["no .txt beside the clip"]))
            continue
        c = parse_copy(txt)
        if problems := check(mp4.name, c, txt):
            refused.append((mp4.name, problems))
            continue
        todo.append((mp4, c, txt))

    for name, problems in refused:
        print(f"  ✗ {name}: {'; '.join(problems)}")
    if refused:
        print("  fix the .txt files above, then re-run. Nothing goes out half-filled.")
    if not todo:
        return

    print(f"\n  {len(todo)} to upload as {a.privacy}:")
    for mp4, c, _ in todo:
        print(f"    {mp4.name}  {mp4.stat().st_size / 1048576:.0f} MB  “{c['TITLE']}” "
              f"({len(c['TITLE'])} chars, {len(c['TAGS'])} tags)")
    if a.dry_run:
        return print("  (dry run, nothing sent)")

    yt = service()
    ch = whoami(yt)
    print(f"\n  signed in as: {ch['snippet']['title']} ({ch['id']})")
    if a.channel_id and a.channel_id != ch["id"]:
        raise SystemExit(f"signed in as {ch['id']}, but the channel should be {a.channel_id}. "
                         f"Delete .yt_token.json and re-run to sign in as the other account.")

    for mp4, c, txt in todo:
        print(f"\n  ▶ {mp4.name}")
        try:
            vid = upload(yt, mp4, c["TITLE"], c["DESCRIPTION"], c["TAGS"], a.privacy)
        except Exception as e:  # quota, network: keep the ledger for what did go out
            msg = str(e)
            if "quotaExceeded" in msg:
                print("  ! YouTube quota for today is used up (resets 09:00 Zagreb). "
                      "Re-run tomorrow; finished uploads are remembered.")
                break
            print(f"  ! failed: {msg[:300]}")
            continue
        # Record the upload before anything else touches it. Whatever goes wrong with the
        # thumbnail, the video is already on YouTube and must never be uploaded twice.
        done[mp4.name] = {"id": vid, "url": f"https://www.youtube.com/watch?v={vid}",
                          "privacy": a.privacy, "title": c["TITLE"],
                          "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        write_json(ledger, done)
        set_thumbnail(yt, vid, txt.parent / c["THUMBNAIL"])

    print(f"\n  ledger: {ledger}")
    if a.privacy != "public":
        print(f"  uploads are {a.privacy}. Check Copyright in Studio, then make them public.")


if __name__ == "__main__":
    main()
