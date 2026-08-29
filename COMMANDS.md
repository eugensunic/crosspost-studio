# Commands

The short list. `README.md` is the full operator's manual, `POLISHING.md` the rules a clip has
to meet, `CLAUDE.md` the working conventions.

## The one you will use

```
bin/clip.sh "<article url>" --slug sunic-kanada --auto 3
```

Downloads the video, transcribes it, picks three moments, titles each in Croatian and English,
then renders every one twice:

```
work/<date>-<slug>/
  whatsapp/  short_N_<slug>.mp4      Croatian subtitles and title
             short_N_<slug>.wa.mp4   the one you actually upload: under 30s, under 10MB
  substack/  short_N_<slug>.mp4      English subtitles and title, full quality
```

**Then check the Croatian.** Edit `clip_N.srt` (and `clip_N.en.srt`) in the work folder and run
the same command again. The download, the cuts and the transcription are cached, so only the
render repeats.

## Starting a new video

```
bin/clean.sh --list          see what is in work/ and how big
bin/clean.sh --keep 2        delete everything except the two newest
bin/clean.sh                 delete everything, after asking
```

Copy out anything you still want first. The videos can be downloaded again; the subtitle
corrections you typed by hand cannot.

## Picking the moments yourself

Without `--auto` it prints the transcript with timecodes and stops:

```
bin/clip.sh "<url>" --slug sunic-kanada
```

Then pass your own spans, spoken-language title first:

```
bin/clip.sh "<url>" --slug sunic-kanada \
  --clip 00:54-01:23 "Carinski rat je i jezični rat || The tariff war is a language war" \
  --clip 06:02-06:31 "Migranti čine Englesku neprepoznatljivom || Migrants are making England unrecognisable"
```

A local file works in place of a URL.

## Publishing

```
# Facebook Page: text and link, safe for someone else's footage
.venv/bin/python lib/facebook_post.py --message "..." --link "https://vijesti.hrt.hr/..."
.venv/bin/python lib/facebook_post.py --check          # is the token still good

# Telegram channel
PYTHONPATH=lib .venv/bin/python lib/telegram_post.py --message "..." --video <file>
PYTHONPATH=lib .venv/bin/python lib/telegram_post.py --check

# YouTube
PYTHONPATH=lib .venv/bin/python lib/youtube_upload.py <file> --title "..." \
  --channel-id UCI8I-1QsJIVQ1vralwI-IYw
PYTHONPATH=lib .venv/bin/python lib/youtube_upload.py --check

# LinkedIn (text and link; token expires every 60 days)
PYTHONPATH=lib .venv/bin/python lib/linkedin_post.py --text "$(cat post.txt)" --link "..."
PYTHONPATH=lib .venv/bin/python lib/linkedin_post.py --check

# Substack: draft built around a YouTube video (it embeds, it cannot upload)
PYTHONPATH=lib .venv/bin/python lib/substack_post.py --work work/<slug> --video-url "https://youtu.be/<id>"

# Fit a file to a platform's limits by hand
.venv/bin/python lib/shrink.py <file> --preset whatsapp     # 30s, 9MB, 720x1280
.venv/bin/python lib/shrink.py <file> --preset substack     # 45MB, 1080x1920
```

Credentials live in `.env`. Never on a command line. Setup guides, one each:
`YOUTUBE-SETUP.md`, `FACEBOOK-SETUP.md`, `TELEGRAM-SETUP.md`, `LINKEDIN.md`. WhatsApp has no API at all and
`WHATSAPP.md` explains why, plus the twenty-second manual route.

## Odds and ends

```
.venv/bin/python lib/grab.py "<url>" --work work/<slug> --list   # find the video, download nothing
PYTHONPATH=lib .venv/bin/python lib/pick.py work/<slug>/full.srt --n 3 --lang hr
.venv/bin/python lib/polish.py <file> --work work/<slug> --srt <srt> --title "..." --no-clean
ollama list                                                       # is the model still there
```

## Before any of it goes public

If the footage is a broadcaster's it stays theirs, edited or not. Without written permission it
goes out as text and a link, never as an upload. See step 0 of
`HOW-THIS-IS-INTENDED-TO-WORK.md`.
