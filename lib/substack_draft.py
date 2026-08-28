#!/usr/bin/env python3
"""Create a Substack DRAFT (never publishes) for a video / live session, or a Note for an appearance.

    python substack_draft.py --work work/<slug> --mode video --video-id YT_ID

Needs SUBSTACK_EMAIL / SUBSTACK_PASSWORD in .env (unofficial API — python-substack).
If the library fails (endpoints change), the text is written to work/<slug>/substack.md for pasting.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from common import CFG, closing_line, link_block, read_json


def compose(work: Path, mode: str, video_id: str) -> tuple[str, str, bool]:
    if mode == "appearance":
        m = read_json(work / "appearance.json")
        body = f"{m.get('summary','')}\n\n{m.get('summary_en','')}\n\n{m['url']}\n\n{closing_line(m.get('lang','hr'))}"
        return m["title"], body, False
    m = read_json(work / "meta.json")
    sp = m["spoken"]
    page = f"{CFG['site']['base_url']}/posts/{m['slug']}/"
    yt = f"https://www.youtube.com/watch?v={video_id}" if video_id else page
    parts = []
    if sp != "en":
        parts.append(m[sp]["summary"])
    parts += [m["en"]["summary"], yt, f"Transcripts (HR/EN): {page}", closing_line("en"), link_block("substack", mode)]
    return m["bilingual_title"], "\n\n".join(parts), (mode == "live" and CFG["substack"]["paid_only_for_live"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--mode", default="video")
    ap.add_argument("--video-id", default="")
    a = ap.parse_args()
    work = Path(a.work)
    title, body, paid = compose(work, a.mode, a.video_id)
    (work / "substack.md").write_text(f"# {title}\n\n{body}\n", encoding="utf-8")

    email, pw = os.environ.get("SUBSTACK_EMAIL"), os.environ.get("SUBSTACK_PASSWORD")
    if not (email and pw):
        print("  SUBSTACK_EMAIL/PASSWORD not set — draft saved to substack.md for manual paste")
        return
    try:
        from substack import Api
        from substack.post import Post

        api = Api(email=email, password=pw, publication_url=f"https://{CFG['substack']['publication']}")
        uid = api.get_user_id()
        if a.mode == "appearance":
            print("  Notes are not supported by python-substack reliably — paste substack.md as a Note")
            return
        post = Post(title=title, subtitle="", user_id=uid, audience="only_paid" if paid else "everyone")
        for para in body.split("\n\n"):
            post.paragraph(para)
        draft = api.post_draft(post.get_draft())
        print(f"  Substack draft created: id={draft.get('id')} audience={'paid' if paid else 'everyone'} — click Publish in Substack")
    except Exception as e:  # unofficial API: degrade gracefully
        print(f"  python-substack failed ({e.__class__.__name__}: {e}); use substack.md")


if __name__ == "__main__":
    main()
