# Working rules for this repo

Read `HOW-THIS-IS-INTENDED-TO-WORK.md` for the mental model, `README.md` for the commands,
`POLISHING.md` for what has to be true of a clip before it goes out. This file is the shorter
thing: how to work here.

## Git

**Commit straight to `main`.** No feature branch, no merge. One person, no remote, no reviewers,
so a branch and a fast-forward merge produce the same history with three more steps. Still only
commit when asked.

## Language, per destination

Every clip is rendered **twice** and filed into one folder per destination under
`work/<date>-<slug>/`:

| Folder | Subtitles and title card | Sized for |
|---|---|---|
| `youtube/` `facebook/` `telegram/` | the spoken language, normally Croatian | full quality |
| `whatsapp/` | the spoken language | under 30 s and under 10 MB |
| `substack/` | **always English** | full quality |

The spoken-language folders are hard links to one file, so the copies are free.

**The spoken language decides the language of everything.** Tom speaks Croatian, French,
German and English on YouTube. `bin/clip.sh` detects the language from the audio
(`lib/detect_lang.py`, remembered in `work/<folder>/lang`) and the captions, title card,
title, description and tags all follow it. A French talk gets French copy, never Croatian.
`--lang` overrides the detection when it is wrong. [2026-09-12]

Substack is English throughout: burned-in subtitles, the title card on the video, and the post.
Never substitute the Croatian cut, and never ship only one of the two. `bin/clip.sh` does both.

## Writing copy

Applies to anything published under Tom's name: Substack posts, social copy, titles, captions.

* **No em dashes.** Full stops, commas, or "and". They read as machine-written and the whole
  point is that a person wrote it.
* **Short.** Two or three sentences for a summary. Write it short first rather than trimming a
  long draft down.
* **Use `templates/substack-clip.md`.** It holds the approved post shape, the intro wording, and
  a worked example. Fill it in rather than starting from scratch.
* The intro names the **real topics with their specifics** (figures, place names), never a
  generic "I spoke about migration", and never a meta line like "this is the part where I said
  X".
* **One copy file per clip, next to the video.** Every `short_N_<slug>.mp4` in every
  destination folder gets a `short_N_<slug>.txt` beside it with the copy for that destination:
  title, description and tags for `youtube/`, post text for `facebook/` and `telegram/`, the
  status line for `whatsapp/`, English title and summary for `substack/`. A combined `POSTS.md`
  is fine as an overview but is not a substitute; the copy has to travel with the file. [2026-09-06]
* **LinkedIn gets one post per source, not one per clip.** One hook for the whole interview,
  the HRT title and link, hashtags, saved as `linkedin.txt` in the work folder root. Never
  three LinkedIn texts for three clips. [2026-09-06]

## Rights, before anything is published

Step 0 of `HOW-THIS-IS-INTENDED-TO-WORK.md` decides everything downstream. Tom appearing in a
recording does not make it his. HRT footage is HRT's, edited or not: cropping, captioning and
retitling produces a derivative work, which still needs their permission.

* Without written permission → `--mode appearance`. Text and link on every network, no upload.
* With written permission → `--mode video --short-only`. Keep the email in the work folder next
  to `source.json`.
* `lib/grab.py` downloads for local transcription and quoting. Downloading is not permission.

## Machine output is a draft, not a result

* **Croatian subtitles are wrong often enough to matter.** Every clip made so far had errors:
  `suštavu` for `sustav`, `dosudce` for `doslovce`, `razumijem` for `razumijete`. `bin/clip.sh`
  prints a warning per clip. Act on it, then re-run; the cut and transcribe stages are cached.
* `lib/pick.py` shortlists clippable moments, it does not decide. Check what it chose against the
  rules of thumb: one idea per clip, 45 to 75 seconds, start on the sentence, two or three per
  source.

## Things that are not what they look like

* **captacity is dead.** It imports `moviepy.editor`, removed in moviepy 2.x. Its failure used to
  be swallowed by `2>/dev/null ||`, shipping Shorts with no captions at all. `lib/polish.py`
  replaced it.
* **Homebrew's ffmpeg has no libass or freetype**, so `subtitles`, `ass` and `drawtext` do not
  exist in that build. Captions are Pillow-rendered PNGs composited with `overlay`.
* **Whisper cannot translate here.** `whisper-large-v3-turbo` is a transcription-only
  distillation; `--task translate` returns Croatian in a single cue. English subtitles come from
  `lib/translate_srt.py`, which needs Ollama and a pulled model.
* **python-substack cannot upload video.** `Post.youtube()` embeds by id and `get_image()` does
  images, and that is all. The video goes to YouTube first and the post embeds it.
* **Never centre-crop to 9:16, and never a blurred pad.** On a wide two-shot the centre strip
  contains neither speaker, so the whole frame is letterboxed over plain black. The blurred copy
  of the picture above and below was rejected on 2026-09-19; a Short looks like a normal Short.
* **Default counts are 3 Shorts and 3 normal videos per source.** `bin/yt.sh` does that without
  flags; `--shorts N --videos N` change it. [2026-09-19]

## Credentials

Never ask for them in chat and never put them on a command line. They live in `.env`, which is
gitignored. `.env.example` holds the placeholders.
