# Sunic Publishing Playbook

Dated 29 Aug 2026, with Tom's decisions folded in. Strategy document; `README.md` is the operator's manual.

Everything Tom produces or appears in — his own videos, HTV and podcast appearances, a monthly live Q&A — goes out
to YouTube, X, LinkedIn, Facebook, Instagram, Telegram and tomsunic.com by itself, captioned in the other languages.
Income through Substack, Ko-fi and the books. Software cost: zero.

| | |
|---|---|
| YouTube today | 129 subscribers · 1 video · @DrTomSunic, since 2012 |
| Ads threshold | 1,000 subs / 4,000 watch-hours in 12 months (or 10M Shorts views / 90 days) |
| Memberships | 500 / 3,000 (or 3M Shorts views) — Super Thanks, Join button |
| Monthly software | €0 — only payment-processor fees on income |

## Decisions

**Books — rights.** He is the author of all eleven; authorship ≠ publishing rights. Each contract (Arktos, Fahrenheit,
Hasanbegović, Ukronija, Gnosis…) decides whether he may sell an ebook/PDF himself.
* In print with a publisher → Amazon affiliate links; ask for the author discount code.
* Out of print (e.g. *Europska nova desnica*) → one email requesting rights reversion → KDP (ebook 70% at $2.99–9.99; paperback 60% minus print cost).
* New work he owns → KDP + Payhip from day one: annual Substack essay collection, transcripts, lecture texts.

**Cadence.** Irregular production, fixed publishing: appearance mode feeds the channels without any upload; own videos
are batch-recorded and released on a weekly slot from the Postiz queue.

**Languages.** Speak in one, caption in the others. Whisper transcribes; a local model translates; YouTube gets
selectable tracks, Shorts get the spoken language burned in, the site page carries both transcripts.

**Telegram** — yes, automated, plus the phase-2 approval bot. **WhatsApp Channel** — manual line by default (Baileys
carries ban risk). **Paid Substack perk** — monthly live Q&A via Substack Live; fallback unlisted YouTube live.

## Three kinds of content, one pipeline

| mode | input | what goes out | rights |
|---|---|---|---|
| `video` | raw.mp4 | long video + 2 Shorts, Reels, X clip, LinkedIn/FB/Telegram posts, site page, Substack draft | his |
| `appearance` | a link | text + link everywhere, site entry with embed, Substack Note. **No re-upload.** | theirs — link/embed only |
| `live` | Q&A recording | paid-only Substack post; 60 s public teaser; site entry | his; stays behind paywall |

Appearances are the growth lever now. Every appearance post ends: *"Full videos and essays: tomsunic.com — newsletter: Substack."*

## Where things stand

| property | state | role |
|---|---|---|
| YouTube @DrTomSunic | dormant shell | discovery engine; keep handle, rebuild the rest |
| Substack | active, has readers | email list + paid tier; the asset no platform can take |
| tomsunic.com | MkDocs Material, GitHub Pages, EN/FR/DE, last post 2024 | owned hub; a git repo → easiest to automate |
| X, Facebook, WhatsApp | active daily | announcement channels |
| LinkedIn | profile exists | text + link per item |
| Telegram | to create | automated announcements; approval bot |
| Books, 11 titles | third-party publishers | affiliate → reversion → KDP/Payhip |
| HTV / podcasts | ongoing | appearance mode |
| Wikipedia | article exists | Knowledge Panel via Wikidata |

## How the money works (in order of expected size)

1. Substack paid tier (€5–6/mo) — live Q&A + recording, transcripts, extended cut. 10% + Stripe.
2. Ko-fi with a public goal — 0% fee. Instead of Patreon.
3. Books — affiliate (~4.5%, OneLink across .com/.fr/.it), KDP for reverted/new titles, Payhip.
4. YouTube memberships + Super Thanks at 500 / 3,000.
5. AdSense at 1,000 / 4,000 — commentary is often "limited ads"; a bonus, not the plan.

Link block, in this order, everywhere: tomsunic.com · Substack · Ko-fi · Books · PayPal / IBAN · X · LinkedIn · Facebook · Telegram.
Before the first payout: 30 min with an accountant (drugi dohodak / paušalni obrt).

## Per-platform automation

| network | automation | mechanism | auth quirk |
|---|---|---|---|
| YouTube | full | Postiz + Data API (captions, localizations) | OAuth app must be **In production**; Brand Account + Manager |
| X | full | Postiz, free tier | callback = Postiz HTTPS URL |
| Facebook Page | full | Postiz | Meta dev mode suffices for own Page |
| Instagram Reels | full | Postiz | Business account linked to Page |
| LinkedIn | text + link | Postiz personal | 60-day tokens, reconnect |
| Telegram | full | Postiz / Bot API | none |
| tomsunic.com | full | git push → Pages | none |
| Substack | draft | python-substack | unofficial; draft-only |
| WhatsApp Channel | manual | printed line | Baileys optional, ban risk |

## The tech — GitHub projects, not code

Postiz (hub, VM) · Caddy + DuckDNS (HTTPS) · auto-editor (silence) · mlx-whisper (transcribe) · Ollama + Gemma 3 /
Qwen 2.5 (translate, titles) · captacity (karaoke captions) · ffmpeg (Shorts) · mkdocs-material (site) ·
python-substack (draft) · phase 2: syncthing, n8n, optional Baileys.

Runs on: the Mac (GPU work), Oracle Always Free VM Frankfurt (Postiz stack, Caddy, later n8n), GitHub (site).

## Setup, in order

1. Day 1 with him — secure the Google account (recovery, 2FA), Brand Account, Manager access, Channel ID.
2. Day 1 with him — fill the channel (bilingual description, banner, links); create Telegram channel + bot.
3. Day 1–2 — Ko-fi goal, Substack paid tier, Amazon Associates; rights-reversion letters.
4. Day 2 — developer apps (Google, X, Meta, LinkedIn); callbacks = Postiz domain.
5. Day 2–3 — update tomsunic.com: Videos, Appearances, Books, Support, Newsletter; footer; embeds; affiliate tags.
6. Day 3 — deploy Postiz, connect accounts, API key, weekly slot.
7. Day 3–4 — Mac tools, test run unlisted, appearance test with an old HTV link, then first real video.
8. Week 1 — Wikidata + Knowledge Panel (do not edit the Wikipedia article).
9. Week 2–4 — batch-record three videos; announce first paid live Q&A a week ahead.
10. After 10 videos — phase 2: watch folder + Telegram approval bot.

## Things that bite

* Google OAuth Testing → 7-day tokens. LinkedIn 60-day tokens. X: media = OAuth 1.0a, posting = v2. Meta: Page token.
* Postiz: ~150 open issues (X link stripping, media-upload auth, 1-hour schedule shift). Pin the tag; test unlisted.
* Never re-upload HTV/podcast video. No copyrighted music. Author ≠ rights holder. Keep local copies; mirror to Rumble/Odysee.
* Translation is machine output — spot-check the English track.

## Still open

* WhatsApp Channel: automated or manual (default manual).
* Which out-of-print titles first; working title of the first KDP collection.
* Weekly slot (day + hour) → `config.yaml`.
* Substack Live vs unlisted YouTube live for the Q&A.
