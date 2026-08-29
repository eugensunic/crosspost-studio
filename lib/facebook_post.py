#!/usr/bin/env python3
"""Post to a Facebook Page from the command line. No server, no Postiz.

    python facebook_post.py --message "text" --link "https://…"
    python facebook_post.py --message "text" --video work/<slug>/short_1.mp4 --title "Naslov"
    python facebook_post.py --check          # who am I, which Page, when does the token expire

Needs two values in .env, both of which you generate yourself:

    FB_PAGE_ID=            the Page's numeric id
    FB_PAGE_TOKEN=         a Page access token, ideally the never-expiring kind

How to get them, once, no server and no App Review for your own Page:

  1. developers.facebook.com → My Apps → Create App → type "Business".
  2. Tools → Graph API Explorer. Pick your app. Add permissions:
     pages_show_list, pages_manage_posts, pages_read_engagement.
     (pages_manage_posts is what actually lets you publish.)
  3. Generate Access Token, accept the dialog. That is a short-lived USER token.
  4. In the Explorer, call  GET /me/accounts  → find your Page, copy its `id`
     and its `access_token`. That second one is a PAGE token.
  5. Make it long-lived. Call, with the short-lived USER token:
       GET /oauth/access_token?grant_type=fb_exchange_token
           &client_id=<APP_ID>&client_secret=<APP_SECRET>&fb_exchange_token=<USER_TOKEN>
     then call GET /me/accounts again using the long-lived user token. The Page token
     you get back does not expire, as long as you stay a Page admin.
  6. Put the Page id and that Page token in .env. Run --check to confirm.

A Page token is a password. It lives in .env, which is gitignored, and nowhere else.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

GRAPH = "https://graph.facebook.com/v21.0"


def _get(path: str, **params) -> dict:
    url = f"{GRAPH}/{path}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def _post(path: str, data: dict) -> dict:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(f"{GRAPH}/{path}", data=body)
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def _post_file(path: str, fields: dict, file_field: str, file_path: Path) -> dict:
    """Multipart upload, hand-rolled to keep the repo dependency-free."""
    boundary = uuid.uuid4().hex
    body = b""
    for k, v in fields.items():
        body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n"
                 f"{v}\r\n").encode()
    ctype = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; "
             f"filename=\"{file_path.name}\"\r\nContent-Type: {ctype}\r\n\r\n").encode()
    body += file_path.read_bytes() + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"{GRAPH}/{path}", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r)


def explain(e: urllib.error.HTTPError) -> str:
    """Graph errors are informative but buried; surface the message and the common causes."""
    try:
        err = json.load(e).get("error", {})
    except Exception:
        return str(e)
    msg = err.get("message", str(e))
    code = err.get("code")
    hint = {
        190: "token expired or revoked — regenerate it (see the header of this file)",
        200: "missing permission — the token needs pages_manage_posts",
        100: "bad parameter — check FB_PAGE_ID is the Page id, not the app id",
        368: "the Page is temporarily blocked from posting",
    }.get(code, "")
    return f"{msg}{' — ' + hint if hint else ''}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Post to a Facebook Page.")
    ap.add_argument("--message", default="")
    ap.add_argument("--link", default="", help="shared as a link preview")
    ap.add_argument("--video", default="", help="upload a video file instead of a link")
    ap.add_argument("--title", default="", help="video title")
    ap.add_argument("--check", action="store_true", help="verify the token and print the Page")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation")
    a = ap.parse_args()

    page = os.environ.get("FB_PAGE_ID", "").strip()
    token = os.environ.get("FB_PAGE_TOKEN", "").strip()
    if not (page and token):
        raise SystemExit("FB_PAGE_ID / FB_PAGE_TOKEN missing from .env — see the header of this file")

    try:
        if a.check:
            me = _get(page, fields="name,id,fan_count", access_token=token)
            print(f"  Page: {me.get('name')} (id {me.get('id')}, {me.get('fan_count', '?')} followers)")
            info = _get("debug_token", input_token=token, access_token=token).get("data", {})
            exp = info.get("expires_at")
            print(f"  Token: {'never expires' if exp == 0 else f'expires at {exp}'}; "
                  f"scopes: {', '.join(info.get('scopes', [])) or 'unknown'}")
            return

        if not (a.message or a.link or a.video):
            raise SystemExit("nothing to post — pass --message, --link or --video")

        what = f"video {a.video}" if a.video else (a.link or "text only")
        print(f"  Page {page} ← {what}")
        print(f"  {a.message[:200]}")
        if not a.yes:
            if input("  post this publicly now? [y/N] ").strip().lower() not in ("y", "yes"):
                return print("  not posted")

        if a.video:
            f = Path(a.video)
            if not f.exists():
                raise SystemExit(f"no such file: {f}")
            res = _post_file(f"{page}/videos",
                             {"access_token": token, "description": a.message,
                              "title": a.title or ""}, "source", f)
        else:
            data = {"access_token": token, "message": a.message}
            if a.link:
                data["link"] = a.link
            res = _post(f"{page}/feed", data)

        pid = res.get("id") or res.get("post_id")
        print(f"  posted: {pid}")
        if pid and "_" in str(pid):
            print(f"  https://www.facebook.com/{str(pid).replace('_', '/posts/')}")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"  Facebook refused it: {explain(e)}")


if __name__ == "__main__":
    main()
