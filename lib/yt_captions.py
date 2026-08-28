#!/usr/bin/env python3
"""Upload subtitle tracks and per-language title/description to a YouTube video.

    python yt_captions.py VIDEO_ID work/<slug>/hr.srt work/<slug>/en.srt ... --localize hr en --meta work/<slug>/meta.json

Needs client_secret.json (Google Cloud OAuth desktop client, consent screen IN PRODUCTION) in the repo root.
Token cached in .yt_token.json. Quota: captions.insert = 400 units each; videos.update = 50.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from common import ROOT, read_json

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
LANG_NAMES = {"hr": "Hrvatski", "en": "English", "fr": "Français", "de": "Deutsch"}


def client():
    tok = ROOT / ".yt_token.json"
    creds = Credentials.from_authorized_user_file(tok, SCOPES) if tok.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = InstalledAppFlow.from_client_secrets_file(ROOT / "client_secret.json", SCOPES).run_local_server(port=0)
        tok.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video_id")
    ap.add_argument("srts", nargs="+")
    ap.add_argument("--localize", nargs="*", default=[])
    ap.add_argument("--meta")
    a = ap.parse_args()
    yt = client()

    existing = {c["snippet"]["language"]: c["id"] for c in
                yt.captions().list(part="snippet", videoId=a.video_id).execute().get("items", [])}
    for s in a.srts:
        lang = Path(s).stem
        media = MediaFileUpload(s, mimetype="application/octet-stream")
        if lang in existing:
            yt.captions().update(part="snippet", body={"id": existing[lang]}, media_body=media).execute()
        else:
            yt.captions().insert(part="snippet", body={"snippet": {
                "videoId": a.video_id, "language": lang, "name": LANG_NAMES.get(lang, lang), "isDraft": False}},
                media_body=media).execute()
        print(f"  caption {lang} ok")

    if a.localize and a.meta:
        m = read_json(a.meta)
        v = yt.videos().list(part="snippet,localizations", id=a.video_id).execute()["items"][0]
        loc = v.get("localizations", {})
        for lang in a.localize:
            if lang in m:
                loc[lang] = {"title": m[lang]["title"][:100], "description": m[lang]["description"]}
        v["snippet"]["defaultLanguage"] = m.get("spoken", "hr")
        yt.videos().update(part="snippet,localizations",
                           body={"id": a.video_id, "snippet": v["snippet"], "localizations": loc}).execute()
        print(f"  localizations {a.localize} ok")


if __name__ == "__main__":
    main()
