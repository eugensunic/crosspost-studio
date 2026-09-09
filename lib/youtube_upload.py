#!/usr/bin/env python3
"""Upload a video to YouTube from this machine. No server needed.

    python youtube_upload.py work/<slug>/substack/short_1.mp4 \
        --title "Naslov" --description "..." --privacy unlisted

    python youtube_upload.py --check        # which channel am I signed in as

Google's desktop OAuth uses a loopback redirect, so this works entirely locally: no public
HTTPS callback, no VM, no Postiz. The first run opens a browser once and caches the refresh
token in .yt_token.json (gitignored). After that it is silent.

SETUP, once:
  1. console.cloud.google.com → new project → APIs & Services → Enable "YouTube Data API v3".
  2. OAuth consent screen. Set it to **In production**, not Testing: a Testing consent screen
     issues refresh tokens that die after 7 days, and YouTube then stops working with no error
     you would notice.
  3. Credentials → Create credentials → OAuth client ID → type **Desktop app**.
  4. Download the JSON, save it as client_secret.json in the repo root. It is gitignored.
  5. Run with --check. A browser opens once; approve, and it prints your channel name.

QUOTA: an upload costs 1600 units of a 10,000/day allowance, so roughly six uploads a day
across everything using the same Google project. --check costs 1.

RIGHTS: uploading is publishing. If the footage is a broadcaster's, this is the step that draws
a copyright strike. See step 0 of HOW-THIS-IS-INTENDED-TO-WORK.md. Default privacy comes from
config.yaml and is "unlisted" for a reason: upload unlisted, confirm Content ID has not claimed
it, then switch to public in YouTube Studio.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import CFG, ROOT

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]
CLIENT_SECRET = ROOT / "client_secret.json"
TOKEN = ROOT / ".yt_token.json"


def service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET.exists():
                raise SystemExit(
                    f"{CLIENT_SECRET.name} missing. Download an OAuth **Desktop app** client "
                    f"from console.cloud.google.com and save it there. See this file's header.")
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            print("  a browser will open once, to authorise this machine")
            # select_account forces the chooser even when the browser is already signed in:
            # without it Google binds whichever account happens to be active, and a token for
            # the wrong channel looks identical to a working one until the first upload.
            creds = flow.run_local_server(port=0, prompt="select_account consent")
        TOKEN.write_text(creds.to_json(), encoding="utf-8")
        TOKEN.chmod(0o600)
    return build("youtube", "v3", credentials=creds)


def whoami(yt) -> dict:
    r = yt.channels().list(part="snippet,statistics", mine=True).execute()
    items = r.get("items", [])
    if not items:
        raise SystemExit("that Google account has no YouTube channel")
    return items[0]


def main() -> None:
    ap = argparse.ArgumentParser(description="Upload a video to YouTube.")
    ap.add_argument("video", nargs="?", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--description", default="")
    ap.add_argument("--tags", nargs="*", default=[])
    ap.add_argument("--privacy", choices=["private", "unlisted", "public"],
                    default=CFG["youtube"]["default_privacy"])
    ap.add_argument("--channel-id", default="", help="refuse to upload unless this channel matches")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()

    yt = service()
    ch = whoami(yt)
    name = ch["snippet"]["title"]
    cid = ch["id"]
    subs = ch.get("statistics", {}).get("subscriberCount", "?")
    print(f"  signed in as: {name} ({cid}, {subs} subscribers)")

    if a.check:
        return
    if not a.video:
        raise SystemExit("nothing to upload — pass a video file, or --check")
    # A wrong Google account uploading to the wrong channel is not something you can quietly
    # undo, so make the intended channel checkable up front.
    if a.channel_id and a.channel_id != cid:
        raise SystemExit(f"signed in as {cid}, but --channel-id says {a.channel_id}. "
                         f"Delete .yt_token.json and re-run to sign in as the other account.")

    f = Path(a.video)
    if not f.exists():
        raise SystemExit(f"no such file: {f}")
    title = a.title or f.stem
    print(f"  upload: {f.name} ({f.stat().st_size / 1048576:.1f} MB) as {a.privacy}")
    print(f"  title:  {title}")
    if not a.yes:
        if input(f"  upload to {name} now? [y/N] ").strip().lower() not in ("y", "yes"):
            return print("  not uploaded")

    from googleapiclient.http import MediaFileUpload

    body = {"snippet": {"title": title[:100], "description": a.description,
                        "tags": a.tags, "categoryId": "25"},
            "status": {"privacyStatus": a.privacy, "selfDeclaredMadeForKids": False}}
    media = MediaFileUpload(str(f), chunksize=8 * 1024 * 1024, resumable=True,
                            mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    res = None
    while res is None:
        status, res = req.next_chunk()
        if status:
            print(f"\r  {int(status.progress() * 100)}%", end="", file=sys.stderr, flush=True)
    print()
    vid = res["id"]
    print(f"  uploaded: https://www.youtube.com/watch?v={vid}")
    print(f"  studio:   https://studio.youtube.com/video/{vid}/edit")
    if a.privacy != "public":
        print(f"  it is {a.privacy}. Check the Copyright tab for a Content ID claim before "
              f"making it public.")


if __name__ == "__main__":
    main()
