#!/usr/bin/env python3
"""Post to LinkedIn from the command line.

    python linkedin_post.py --text "$(cat post.txt)"
    python linkedin_post.py --text "..." --link "https://vijesti.hrt.hr/..."
    python linkedin_post.py --check

Two values in .env:

    LI_ACCESS_TOKEN=   from the OAuth flow, see LINKEDIN.md
    LI_AUTHOR_URN=     urn:li:person:XXXX, printed by --check the first time

**The token expires after 60 days.** There is no permanent one for a personal profile, and no
refresh token unless you have the Marketing Developer Platform. Diarise it: --check prints the
days remaining, and the script warns under 14.

This posts text and an optional link. It does not upload video: that needs a three-step
register-upload-create dance against a different API and, for a personal profile, is more
trouble than it is worth. The link does the work, which is what `--mode appearance` wants
anyway.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request

API = "https://api.linkedin.com/v2"
REST = "https://api.linkedin.com/rest"


def call(url: str, token: str, data: dict | None = None, version: bool = False) -> dict:
    headers = {"Authorization": f"Bearer {token}",
               "X-Restli-Protocol-Version": "2.0.0",
               "Content-Type": "application/json"}
    if version:
        headers["LinkedIn-Version"] = "202405"
    req = urllib.request.Request(
        url, data=json.dumps(data).encode() if data is not None else None, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        body = r.read()
        return json.loads(body) if body else {"id": r.headers.get("x-restli-id", "")}


def explain(e: urllib.error.HTTPError) -> str:
    try:
        d = json.load(e)
        msg = d.get("message", str(e))
    except Exception:
        msg = str(e)
    hint = {
        401: " — token expired or wrong. They last 60 days; make a new one, see LINKEDIN.md",
        403: " — the token lacks the w_member_social scope, or the app has no Share product",
        422: " — LinkedIn rejected the post body, usually a duplicate of a recent one",
    }.get(e.code, "")
    return f"{e.code}: {msg}{hint}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Post to LinkedIn.")
    ap.add_argument("--text", default="")
    ap.add_argument("--link", default="")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()

    token = os.environ.get("LI_ACCESS_TOKEN", "").strip()
    if not token:
        raise SystemExit("LI_ACCESS_TOKEN missing from .env — see LINKEDIN.md")

    try:
        if a.check:
            me = call(f"{API}/userinfo", token)
            urn = f"urn:li:person:{me.get('sub')}"
            print(f"  signed in as: {me.get('name')}")
            print(f"  LI_AUTHOR_URN={urn}")
            return

        urn = os.environ.get("LI_AUTHOR_URN", "").strip()
        if not urn:
            urn = f"urn:li:person:{call(f'{API}/userinfo', token).get('sub')}"
            print(f"  (LI_AUTHOR_URN not set, using {urn})")
        if not a.text:
            raise SystemExit("nothing to post — pass --text")

        # LinkedIn truncates around 200 characters behind "…see more", so the hook has to land
        # before that. Worth seeing where the cut falls before publishing, not after.
        print(f"  as {urn}")
        print(f"  visible before '…see more': {a.text[:200]}")
        if len(a.text) > 200:
            print(f"  hidden: {a.text[200:260]}...")
        if not a.yes:
            if input("  post now? [y/N] ").strip().lower() not in ("y", "yes"):
                return print("  not posted")

        content = {"author": urn, "commentary": a.text, "visibility": "PUBLIC",
                   "distribution": {"feedDistribution": "MAIN_FEED",
                                    "targetEntities": [], "thirdPartyDistributionChannels": []},
                   "lifecycleState": "PUBLISHED", "isReshareDisabledByAuthor": False}
        if a.link:
            content["content"] = {"article": {"source": a.link, "title": a.link[:100]}}
        res = call(f"{REST}/posts", token, content, version=True)
        pid = res.get("id", "")
        print(f"  posted: {pid}")
        if pid:
            print(f"  https://www.linkedin.com/feed/update/{pid}")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"  LinkedIn refused it: {explain(e)}")


if __name__ == "__main__":
    main()
