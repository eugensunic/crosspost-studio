#!/usr/bin/env python3
"""Write the MkDocs page for a video, live session or appearance into the tomsunic.com repo.

    python site_post.py --work work/<slug> --mode video [--video-id YT_ID]
Does NOT commit — publish.sh does `git commit && git push` only when --push is given.
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import srt
from common import CFG, ROOT, closing_line, link_block, read_json


def render(template: str, **kw) -> str:
    text = (ROOT / "templates" / template).read_text(encoding="utf-8")
    for k, v in kw.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--mode", default="video")
    ap.add_argument("--video-id", default="")
    a = ap.parse_args()
    work = Path(a.work)
    repo = Path(CFG["site"]["repo"]).expanduser()
    today = dt.date.today().isoformat()

    if a.mode == "appearance":
        m = read_json(work / "appearance.json")
        out = repo / CFG["site"]["appearances_dir"] / f"{m['slug']}.md"
        page = render("appearance.md", title=m["title"], date=today, host=m.get("host", ""),
                      url=m["url"], embed=m.get("embed", ""), summary=m.get("summary", ""),
                      summary_en=m.get("summary_en", ""), closing=closing_line(m.get("lang", "hr")),
                      links=link_block("site", "appearance"))
    else:
        m = read_json(work / "meta.json")
        sp = m["spoken"]
        transcript_sp = srt.plain_text(srt.parse(work / f"{sp}.srt")) if (work / f"{sp}.srt").exists() else ""
        transcript_en = srt.plain_text(srt.parse(work / "en.srt")) if (work / "en.srt").exists() and sp != "en" else ""
        chapters = "\n".join(f"- **{c['t']}** {c['label']}" for c in m.get("chapters", []))
        embed = (f'<iframe width="100%" height="420" src="https://www.youtube.com/embed/{a.video_id}" '
                 f'frameborder="0" allowfullscreen></iframe>' if a.video_id else "_video pending_")
        out = repo / CFG["site"]["posts_dir"] / f"{m['slug']}.md"
        page = render("post.md", title=m["bilingual_title"], date=today, embed=embed, mode=a.mode,
                      summary_sp=m[sp]["summary"], summary_en=m["en"]["summary"], chapters=chapters,
                      spoken_name={"hr": "Hrvatski", "en": "English", "fr": "Français", "de": "Deutsch"}[sp],
                      transcript_sp=transcript_sp, transcript_en=transcript_en,
                      paywall_note=("_Full recording for paid Substack subscribers._" if a.mode == "live" else ""),
                      closing=closing_line(sp), links=link_block("site", a.mode))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"  wrote {out}")


if __name__ == "__main__":
    main()
