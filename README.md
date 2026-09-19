# Crosspost Studio

Everything Tom produces or appears in — own videos, HTV/podcast appearances, the monthly live Q&A — goes out to
YouTube, X, LinkedIn, Facebook, Instagram, Telegram and tomsunic.com from **one command**, captioned in the other
languages. Software cost: €0. See `PLAYBOOK.md` for the strategy; this README is the operator's manual.

```
bin/publish.sh --mode video      raw.mp4 "Naslov" --shorts 12:40-13:35 27:10-28:05
bin/publish.sh --mode appearance "https://…htv…" "Tom on HTV: …" --host HTV
bin/publish.sh --mode live       qanda.mp4 "Q&A rujan" --teaser 03:10-04:05
```

## Layout

```
bin/publish.sh          the glue — 3 modes, 8 steps
bin/setup-mac.sh        one-time install of the prep tools (ffmpeg, ollama, mlx-whisper, auto-editor, captacity)
lib/
  common.py             config, link block, UTM tags, slug, Ollama client
  srt.py                SRT parse/write
  translate_srt.py      hr.srt → en/fr/de.srt via local Ollama, timing preserved
  titles.py             transcript → meta.json (bilingual title, descriptions, X/LinkedIn texts, chapters, Short spans)
  grab.py               article URL → local video + source.json (title, date, page) — provenance, not permission
  polish.py             raw clip → finished 1080x1920 short: removes cursor/player chrome, black 9:16 pad,
                        burned-in subtitles, opening title card — one ffmpeg pass (see POLISHING.md)
  appearance.py         link → appearance.json (oEmbed title/embed, LLM announcement) — never downloads video
  postiz.py             uploads media, builds one posts.json for every network, POSTs to Postiz (weekly slot)
  yt_captions.py        subtitle tracks + per-language title/description on YouTube (Data API)
  site_post.py          MkDocs page into ~/tomsunic.com (posts/ or appearances/)
  substack_draft.py     Substack draft (paid-only for live) — never publishes; falls back to substack.md
templates/              post.md, appearance.md
profiles/tom/config.yaml  links, languages, weekly slot, Postiz integration IDs — the only file per person
deploy/postiz/          docker-compose (pinned), Caddyfile, .env.example, Oracle VM bootstrap
work/<date>-<slug>/     every intermediate: clean.mp4, *.srt, meta.json, shorts, posts.json, substack.md
tests/test_dry_run.sh   offline smoke test
```

## Setup (order matters)

1. **Mac** — `bin/setup-mac.sh`, then `cp .env.example .env`.
2. **VM** — Oracle Always Free (Frankfurt; fall back to Amsterdam/Zurich on "out of capacity"):
   `deploy/postiz/vm-setup.sh`, copy `deploy/postiz/*` there, fill `.env`, `docker compose up -d`.
3. **Developer apps** — Google (consent screen **In production** or refresh tokens die in 7 days), X (Read+Write),
   Meta (Page + Instagram Business), LinkedIn ("Share on LinkedIn"), Telegram (@BotFather).
   All callbacks → `https://<DOMAIN>/integrations/social/<provider>`.
4. **Postiz** — connect the six networks, Settings → Public API → key into `.env`,
   `GET /public/v1/integrations` → IDs into `config.yaml`. Set the weekly slot in `config.yaml`.
5. **YouTube captions** — download the OAuth desktop client as `client_secret.json` into the repo root.
6. **tomsunic.com** — `config.yaml → site.repo` must point at the MkDocs checkout; add `posts/` and `appearances/` to nav.
7. `tests/test_dry_run.sh`, then `bin/publish.sh --mode video test.mp4 "Test" --dry-run`, then the same without
   `--dry-run` with `youtube.default_privacy: unlisted`. Flip to `public` after checking the Croatian transcript,
   English track, Shorts crop and site page.

## Flow per own video

| step | tool | output |
|---|---|---|
| 1 cut silence | auto-editor | clean.mp4 |
| 2 transcribe | mlx-whisper large-v3-turbo | hr.srt, transcript.txt |
| 3 translate | Ollama gemma3:12b | en.srt fr.srt de.srt |
| 4 titles | Ollama | meta.json (bilingual title, descriptions, X/LinkedIn text, chapters, Short spans) |
| 5 shorts | lib/polish.py — clean, black 9:16 pad, burned-in subtitles, title card | short_1.mp4 short_2.mp4 thumb.jpg |
| 6 publish | Postiz public API | posts.json → YouTube (long + Shorts), X, LinkedIn, Facebook, Instagram, Telegram, scheduled to the weekly slot |
| 7 captions | YouTube Data API | subtitle tracks HR/EN/FR/DE + HR/EN localizations (needs `--video-id`) |
| 8 site + newsletter | MkDocs, python-substack | posts/<slug>.md, Substack draft (he clicks Publish), WhatsApp line printed |

Step 7 needs the YouTube video ID, which exists only after Postiz publishes at the slot. Rerun
`bin/publish.sh --mode video raw.mp4 "Naslov" --video-id <ID> --push` — the work folder is cached, so only
captions, the site embed and the Substack draft run. (Phase 2: a Postiz webhook / n8n does this automatically.)

Nothing is committed to the site repo unless `--push` is given. Nothing is sent anywhere with `--dry-run`.

## Modes

* **video** — his recording. Full pipeline. Rights: his.
* **appearance** — a link. Text + link on every network, immediately (not the weekly slot), site entry under
  Appearances with the embed, Substack Note text. **Never re-uploads the broadcaster's video.** Got a clip with
  permission? `--mode video --short-only`.
* **live** — the Q&A recording. Substack draft is paid-only; only a public 60 s teaser goes to YouTube/Reels/X.

## Things that bite

* Google OAuth "Testing" → 7-day tokens. LinkedIn → 60-day tokens, reconnect in Postiz (script warns, does not fail).
* Postiz: pin the image tag, `compose down` before env changes, keep the domain forever (every callback points at it).
* Translation is machine output — spot-check `en.srt` on the first few videos.
* Whisper `large-v3-turbo` is weaker on Croatian than `whisper-large-v3-mlx`; switch in `config.yaml` if needed.
* mlx-whisper needs Python ≤ 3.12 — hence the uv venv in `setup-mac.sh`. captacity is unused: it imports `moviepy.editor`,
  removed in moviepy 2.x, so it cannot run. `lib/polish.py` replaced it.
* Keep `work/` — it is the local archive; mirror long.mp4 to Rumble/Odysee as backup.

## Another person

`profiles/<name>/config.yaml` + `PROFILE=<name>` in `.env`; a new Postiz organization. Walls appear around
5–10 active creators (Google verification, shared 10k YouTube quota, Meta App Review, X Basic tier).
