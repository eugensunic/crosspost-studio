#!/usr/bin/env python3
"""Create a Substack post built around one video.

    python substack_post.py --work work/<slug> --video-id dQw4w9WgXcQ
    python substack_post.py --work work/<slug> --video-url "https://youtu.be/dQw4w9WgXcQ" --publish

Writes a DRAFT by default. `--publish` sends it to the list — that is irreversible, so it is
never the default and it asks first unless you also pass --yes.

THE VIDEO IS NOT UPLOADED. python-substack has no media-upload call — `Post.youtube()` embeds
by video id and `Api.get_image()` handles images, and that is the whole of it. So the video has
to be on YouTube first, and this embeds it. Substack does host video natively; this unofficial
library simply cannot reach that endpoint.

Credentials come from .env, never the command line:

    SUBSTACK_COOKIES=...     preferred — paste the cookie string from a logged-in browser
    SUBSTACK_EMAIL=...       fallback; fails when Substack asks for a captcha or magic link
    SUBSTACK_PASSWORD=...

Whatever happens, the post text is written to <work>/substack.md, so a failed login costs you
nothing but a paste.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from common import CFG, closing_line, link_block, read_json

YT_ID = re.compile(r"(?:v=|youtu\.be/|/shorts/|/embed/)([A-Za-z0-9_-]{11})")


def video_id(value: str) -> str:
    """Accept a bare id or any YouTube URL shape."""
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", value):
        return value
    m = YT_ID.search(value)
    if not m:
        raise SystemExit(f"could not find a YouTube video id in {value!r}")
    return m.group(1)


def compose(work: Path, title: str, body: str, lang: str) -> tuple[str, str, list[str]]:
    """Title, subtitle and paragraphs — from meta.json when it exists, else the flags."""
    meta = work / "meta.json"
    if meta.exists() and not (title and body):
        m = read_json(meta)
        sp = m.get("spoken", lang)
        title = title or m.get("bilingual_title") or m[sp]["title"]
        paras = [m[sp]["summary"]] if sp != "en" else []
        paras.append(m["en"]["summary"])
        subtitle = m["en"].get("title", "")
    else:
        if not title:
            raise SystemExit("no meta.json in the work folder — pass --title (and --body)")
        paras = [p.strip() for p in body.split("\n\n") if p.strip()]
        subtitle = ""
    paras += [closing_line(lang), link_block("substack", "video")]
    return title, subtitle, paras


def connect():
    """Cookie string first: Substack's password login trips captchas and magic links often
    enough that email/password is the fallback, not the main route."""
    from substack import Api

    pub = f"https://{CFG['substack']['publication']}"
    cookies = os.environ.get("SUBSTACK_COOKIES", "").strip()
    if cookies:
        return Api(cookies_string=cookies, publication_url=pub)
    email, pw = os.environ.get("SUBSTACK_EMAIL"), os.environ.get("SUBSTACK_PASSWORD")
    if not (email and pw):
        return None
    return Api(email=email, password=pw, publication_url=pub)


def main() -> None:
    ap = argparse.ArgumentParser(description="Substack post built around one YouTube video.")
    ap.add_argument("--work", required=True)
    ap.add_argument("--video-id", default="", help="YouTube id, or use --video-url")
    ap.add_argument("--video-url", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--body", default="", help="paragraphs separated by blank lines")
    ap.add_argument("--lang", default=CFG["languages"]["spoken_default"])
    ap.add_argument("--paid", action="store_true", help="paid subscribers only")
    ap.add_argument("--publish", action="store_true", help="send to the list — irreversible")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation for --publish")
    a = ap.parse_args()

    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    if not (a.video_id or a.video_url):
        raise SystemExit("need --video-id or --video-url (the video must be on YouTube already)")
    vid = video_id(a.video_id or a.video_url)
    title, subtitle, paras = compose(work, a.title, a.body, a.lang)

    # Always leave something pasteable behind, whatever the API does next.
    md = f"# {title}\n\n" + "\n\n".join(paras) + f"\n\nhttps://www.youtube.com/watch?v={vid}\n"
    (work / "substack.md").write_text(md, encoding="utf-8")
    print(f"  wrote {work / 'substack.md'}")

    api = connect()
    if api is None:
        print("  no SUBSTACK_COOKIES or SUBSTACK_EMAIL/PASSWORD in .env — paste substack.md by hand")
        return

    from substack.post import Post

    try:
        uid = api.get_user_id()
    except Exception as e:
        print(f"  login failed ({e.__class__.__name__}: {e}) — paste substack.md by hand")
        return

    post = Post(title=title, subtitle=subtitle, user_id=uid,
                audience="only_paid" if a.paid else "everyone")
    for p in paras[:1]:
        post.paragraph(p)
    post.youtube(vid)               # the embed: this is what "post with a video" means here
    for p in paras[1:]:
        post.paragraph(p)

    try:
        draft = api.post_draft(post.get_draft())
    except Exception as e:
        print(f"  draft failed ({e.__class__.__name__}: {e}) — paste substack.md by hand")
        return
    did = draft.get("id")
    print(f"  draft created: id={did} audience={'paid' if a.paid else 'everyone'}")
    print(f"  https://{CFG['substack']['publication']}/publish/post/{did}")

    if not a.publish:
        print("  draft only — open it, check the embed renders, then hit Publish yourself")
        return
    if not a.yes:
        ok = input("  send this to the whole list now? this cannot be undone [y/N] ")
        if ok.strip().lower() not in ("y", "yes"):
            print("  left as a draft")
            return
    try:
        api.publish_draft(draft)
        print("  published")
    except Exception as e:
        print(f"  publish failed ({e.__class__.__name__}: {e}); the draft is still there")


if __name__ == "__main__":
    main()
