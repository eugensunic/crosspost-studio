# How this is intended to work

Third document in the set. `PLAYBOOK.md` is the strategy (why, and what the money does), `README.md` is the
operator's manual (which command, which flag). This one is the mental model: **what happens to a piece of footage
from the moment you find it to the moment it is live in six places**, and how to decide which path it takes.

Read this one first if you are new to the repo. Read `README.md` when you are about to run something.

---

## The one idea

One input, one command, every destination.

```
        ┌─ YouTube long ──────┐
raw ───▶│  Shorts ×2          │
clip    │  X · LinkedIn · FB  ├──▶ scheduled to the weekly slot
        │  Instagram Reels    │
        │  Telegram           │
        └─ tomsunic.com ──────┘
             + Substack draft (he clicks Publish)
             + WhatsApp line (printed, pasted by hand)
```

Everything between raw footage and those destinations — silence removal, transcription, translation into three
languages, title and description writing, vertical crops, caption burn-in, scheduling — is one pass of
`bin/publish.sh`. Nothing is a separate manual step. That is the entire point of the repo.

The unit of work is a **work folder**: `work/<date>-<slug>/`. It holds every intermediate artefact. It is cached,
so re-running the same input does not redo the expensive steps, and it is the local archive — never delete it.

---

## Step 0: whose footage is it?

**This is the first decision and it determines everything downstream.** Get it wrong and the channel takes a
copyright strike, which at 1 subscriber is survivable and at 5,000 is not.

The rule that trips people up: **Tom being the person in the clip does not make the clip his.** Copyright belongs to
whoever recorded and published it. If HTV filmed an interview, HTV owns that footage. If a podcast recorded him as a
guest, the podcast owns the recording. Appearing in something confers no rights to redistribute it.

So, three cases:

| The footage is | Mode | What goes out |
|---|---|---|
| **His own recording** — he filmed it, he owns it | `video` | Full pipeline. Long video, Shorts, everything. |
| **Someone else's, no permission** | `appearance` | Text + link + embed. **The video is never downloaded or re-uploaded.** |
| **Someone else's, permission granted in writing** | `video --short-only` | Clips only, credited. No full re-upload. |

The middle row is the default for podcasts and broadcast. It is not a limitation — `appearance` mode is described
in the playbook as *the growth lever right now*, because it feeds all six networks without any upload, editing, or
rendering at all. A link and a title is the whole input.

### Getting to the third row

`README.md` says "got a clip with permission?" but not how to get it. Most podcasts and independent shows say yes
immediately — guest clips promote them for free, and many have a standing policy allowing it. Broadcasters (HTV)
are slower and often say no. Ask like this, and keep the reply:

> Hi — thanks again for having me on. I'd like to cut two or three short clips (under 90 seconds each) from our
> conversation to post on my own channels, crediting the show by name with a link to the full episode in every
> caption. Is that alright with you? Happy to send them over before they go out.

What makes this workable: **short**, **credited**, **linked**, **offered for review**. Keep the yes in writing —
an email or a DM screenshot into the work folder is enough. A verbal yes at the end of a recording is worth little
six months later when someone else runs the show's account.

If the answer is no, or there is no answer: `appearance` mode. The post still goes out everywhere the same day.

---

## Step 1–8: what actually happens to an own video

This is `--mode video`. The other two modes are subsets of it.

| # | Step | Tool | Produces | Notes |
|---|---|---|---|---|
| 1 | Cut silence | auto-editor | `clean.mp4` | Typically removes 10–20% of runtime. Nothing else is edited. |
| 2 | Transcribe | mlx-whisper `large-v3-turbo` | `hr.srt`, `transcript.txt` | Runs on the Mac GPU. Croatian accuracy is the weak point — see below. |
| 3 | Translate | Ollama `gemma3:12b` | `en.srt`, `fr.srt`, `de.srt` | Local, free, timings preserved. **Machine output — spot-check the English.** |
| 4 | Write metadata | Ollama | `meta.json` | Bilingual title, descriptions, X and LinkedIn text, chapters, and **suggested Short spans**. |
| 5 | Cut Shorts | ffmpeg + captacity | `short_1.mp4`, `short_2.mp4`, `thumb.jpg` | 9:16 crop, karaoke captions burned in, spoken language only. |
| 6 | Publish | Postiz public API | `posts.json` → six networks | Scheduled to the weekly slot, not posted immediately. |
| 7 | Captions | YouTube Data API | Subtitle tracks + localizations | **Needs `--video-id`, which does not exist until step 6 actually publishes.** |
| 8 | Site + newsletter | MkDocs, python-substack | `posts/<slug>.md`, Substack draft | Draft only. He clicks Publish. |

### The step 7 gap, and why you run the command twice

Steps 1–6 happen now. Step 6 *schedules* — the video does not exist on YouTube until the weekly slot arrives, so
there is no video ID to attach captions to. Once it has gone live, run the same command again with the ID:

```
bin/publish.sh --mode video raw.mp4 "Naslov" --video-id <ID> --push
```

The work folder is cached, so this second pass skips transcription, translation and rendering entirely. Only
captions, the site embed and the Substack draft run. Phase 2 replaces this with a Postiz webhook so it happens
by itself.

### Breaking one recording into many pieces

This is what you asked about, and it is step 4 and step 5 doing the work. The model reads the transcript and
proposes Short spans — the moments that stand on their own. You can override it when you already know the good bits:

```
bin/publish.sh --mode video raw.mp4 "Naslov" --shorts 12:40-13:35 27:10-28:05
```

Rules of thumb that matter more than the tooling:

* **One idea per clip.** A clip that needs setup is not a clip.
* **45–75 seconds.** Under 45 feels abrupt; over 90 loses retention and stops being a Short.
* **Start on the sentence, not the breath before it.** Dead air in the first second kills the view.
* **Two or three per source, not eight.** Volume without selection trains the algorithm that his content is weak.

Everything the clip needs to travel — vertical crop, burned-in captions, thumbnail — is automatic. What is not
automatic is *choosing well*, and that stays a human job.

---

## Where things land

| Destination | What arrives | Automation |
|---|---|---|
| YouTube | Long video + Shorts, four subtitle tracks, HR/EN titles | Full |
| X | Clip + text | Full |
| LinkedIn | Text + link | Full — 60-day tokens, reconnect when warned |
| Facebook Page | Post + media | Full |
| Instagram | Reels | Full — needs Business account linked to the Page |
| Telegram | Announcement | Full |
| tomsunic.com | MkDocs page under `posts/` or `appearances/` | Full — git push, but **only with `--push`** |
| Substack | Draft | Draft only, deliberately — never auto-publishes |
| WhatsApp Channel | A printed line you paste yourself | Manual by default (Baileys carries ban risk) |

Two safety valves, and they are not the same one:

* `--dry-run` — nothing leaves the machine at all. Use it whenever you change anything.
* no `--push` — everything else runs, but nothing is committed to the site repo.

---

## The three modes, side by side

| | `video` | `appearance` | `live` |
|---|---|---|---|
| Input | `raw.mp4` | a URL | Q&A recording |
| Rights | his | theirs | his |
| Downloads the source? | n/a | **never** | n/a |
| Timing | weekly slot | immediately | weekly slot |
| Substack | public draft | Note text | **paid tier only** |
| Public video | full + Shorts | none, embed only | 60 s teaser only |

`live` is the paid perk. The recording stays behind the Substack paywall; only a short teaser is public. That
asymmetry is the reason anyone subscribes, so do not let a full Q&A leak into the public queue.

---

## What this deliberately does not do

Worth stating, because each one is a decision rather than a missing feature:

* **Does not re-upload other people's video.** See step 0.
* **Does not publish to Substack.** It writes a draft. A human sends the email to the list.
* **Does not post immediately in `video` mode.** Irregular recording, regular publishing — the queue absorbs the gap.
* **Does not use copyrighted music.** Nothing in the pipeline adds audio.
* **Does not edit for meaning.** Silence removal only. It never rearranges what was said, and it should not — a
  clip that changes the sense of the original is the fastest way to lose a source's permission permanently.
* **Does not touch the Wikipedia article.** Wikidata only, per the playbook.

---

## Things that will bite you, in the order you will hit them

1. **Google OAuth in "Testing"** → refresh tokens die after 7 days and YouTube silently stops working. The consent
   screen must be **In production**.
2. **The Croatian transcript** is the quality floor for everything downstream — translations, titles and chapters
   are all built from it. If `large-v3-turbo` struggles, switch to `whisper-large-v3-mlx` in `config.yaml`.
3. **Machine translation ships unless you check it.** Spot-check `en.srt` on the first few.
4. **LinkedIn tokens expire every 60 days.** The script warns, it does not fail — so the warning is easy to miss.
5. **Postiz** has a long open-issue list (X link stripping, media-upload auth, an hour of schedule drift). Pin the
   image tag. Test unlisted before trusting it.
6. **Never change the Postiz domain.** Every OAuth callback on all five developer apps points at it.
7. **Python ≤ 3.12** for mlx-whisper and captacity — hence the uv venv in `setup-mac.sh`.

---

## Adding a second person

`profiles/<name>/config.yaml`, `PROFILE=<name>` in `.env`, and a new Postiz organization. Nothing else changes.

The ceiling is around 5–10 active creators, and it is imposed from outside rather than by this code: Google
verification, the shared 10,000-unit YouTube API quota, Meta App Review, and X's Basic tier.

---

## Phase 2, once there are ten videos

Not before — the manual loop is how you find out what the pipeline gets wrong.

* Watch folder plus syncthing: drop a file, the pipeline starts.
* Telegram approval bot: it proposes titles, Short spans and thumbnails; he taps approve.
* n8n on the same VM: the Postiz webhook fires step 7 by itself, and the second manual run disappears.
