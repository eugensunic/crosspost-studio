#!/usr/bin/env python3
"""Post to a Telegram channel from the command line.

    python telegram_post.py --message "text"
    python telegram_post.py --message "caption" --video work/<slug>/whatsapp/short_1.wa.mp4
    python telegram_post.py --check

Two values in .env:

    TG_BOT_TOKEN=      from @BotFather
    TG_CHAT_ID=        @yourchannel, or the numeric -100... id for a private one

Telegram is the easiest of the lot: a bot token, no OAuth, no app review, nothing expires.
See TELEGRAM-SETUP.md.

Limits worth knowing: a bot may send a file of up to 50 MB, and a caption of up to 1024
characters. Both are below what the Telegram apps allow a human, and neither can be raised.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

CAPTION_LIMIT = 1024
FILE_LIMIT_MB = 50


def api(token: str, method: str, data: dict | None = None,
        file_field: str = "", file_path: Path | None = None) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    if file_path is None:
        body = urllib.parse.urlencode(data or {}).encode()
        req = urllib.request.Request(url, data=body)
    else:
        boundary = uuid.uuid4().hex
        chunks = b""
        for k, v in (data or {}).items():
            chunks += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n"
                       f"{v}\r\n").encode()
        ctype = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        chunks += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; "
                   f"filename=\"{file_path.name}\"\r\nContent-Type: {ctype}\r\n\r\n").encode()
        chunks += file_path.read_bytes() + b"\r\n"
        chunks += f"--{boundary}--\r\n".encode()
        req = urllib.request.Request(
            url, data=chunks,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def explain(e: urllib.error.HTTPError) -> str:
    try:
        d = json.load(e)
        desc = d.get("description", str(e))
    except Exception:
        return str(e)
    hint = ""
    if "chat not found" in desc:
        hint = " — check TG_CHAT_ID, and that the bot is an administrator of the channel"
    elif "not enough rights" in desc or "CHAT_WRITE_FORBIDDEN" in desc:
        hint = " — the bot is in the channel but lacks Post Messages permission"
    elif "Unauthorized" in desc:
        hint = " — TG_BOT_TOKEN is wrong or the bot was deleted"
    return desc + hint


def main() -> None:
    ap = argparse.ArgumentParser(description="Post to a Telegram channel.")
    ap.add_argument("--message", default="")
    ap.add_argument("--video", default="")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()

    token = os.environ.get("TG_BOT_TOKEN", "").strip()
    chat = os.environ.get("TG_CHAT_ID", "").strip()
    if not (token and chat):
        raise SystemExit("TG_BOT_TOKEN / TG_CHAT_ID missing from .env — see TELEGRAM-SETUP.md")

    try:
        if a.check:
            me = api(token, "getMe").get("result", {})
            print(f"  bot: @{me.get('username')} ({me.get('first_name')})")
            info = api(token, "getChat", {"chat_id": chat}).get("result", {})
            print(f"  channel: {info.get('title')} ({info.get('type')}, id {info.get('id')})")
            return

        if not (a.message or a.video):
            raise SystemExit("nothing to post — pass --message or --video")
        if len(a.message) > CAPTION_LIMIT and a.video:
            raise SystemExit(f"caption is {len(a.message)} characters; Telegram allows "
                             f"{CAPTION_LIMIT} on a video. Shorten it, or post text separately.")

        print(f"  channel {chat} ← {'video ' + a.video if a.video else 'text'}")
        print(f"  {a.message[:200]}")
        if not a.yes:
            if input("  post now? [y/N] ").strip().lower() not in ("y", "yes"):
                return print("  not posted")

        if a.video:
            f = Path(a.video)
            if not f.exists():
                raise SystemExit(f"no such file: {f}")
            mb = f.stat().st_size / 1048576
            if mb > FILE_LIMIT_MB:
                raise SystemExit(f"{mb:.1f} MB: a bot may only send {FILE_LIMIT_MB} MB. "
                                 f"Use lib/shrink.py, or post the link instead.")
            res = api(token, "sendVideo",
                      {"chat_id": chat, "caption": a.message, "supports_streaming": "true"},
                      "video", f)
        else:
            res = api(token, "sendMessage",
                      {"chat_id": chat, "text": a.message, "disable_web_page_preview": "false"})

        msg = res.get("result", {})
        print(f"  posted: message {msg.get('message_id')}")
        if str(chat).startswith("@"):
            print(f"  https://t.me/{str(chat).lstrip('@')}/{msg.get('message_id')}")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"  Telegram refused it: {explain(e)}")


if __name__ == "__main__":
    main()
