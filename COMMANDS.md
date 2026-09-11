# Commands

The short list. `README.md` is the full operator's manual, `POLISHING.md` the rules a clip has
to meet, `CLAUDE.md` the working conventions.

## YouTube in one command

```
bin/yt.sh "https://www.youtube.com/watch?v=YQoug8JTIGo" --slug tito-diktator
```

Downloads, transcribes, lets the local model pick five Shorts (45 to 75 s) and two longer
passages (3 to 5 min, normal 16:9), cuts and captions them, writes title, description, tags
and thumbnail beside each, and uploads them unlisted. `--shorts 3 --videos 1` changes the
count, `--no-upload` stops before the upload so the copy can be read first, and anything else
(`--lang`, `--clip`, `--video`) is passed through to `bin/clip.sh`.

It is the same as the two commands below with `--auto 5 --auto-videos 2 --dest youtube
--upload`, so everything said there about the work folder, the ledger and the quota holds.
What it does not do is judge: the local model is a mediocre picker and its Croatian is rough,
so the description is a draft written by it, not a transcript dump, and a wrong word in
`clip_N.srt` goes out burned in. Reading the `.txt` files and the captions before the upload
is still the difference between good and passable; use `--no-upload`, fix, then
`bin/yt-upload.sh work/<folder>`. Better picks and copy come from a larger model:
`ollama pull gemma3:12b` and set `ollama.model` in `profiles/tom/config.yaml`.

## YouTube in two commands

One command makes the clips, one command posts them. Worked example, with the Informer
interview from 10 September 2026:

```
# 1. Clips into the work folder. Downloads, transcribes, cuts, captions, and writes the
#    YouTube title, description, tags and thumbnail beside every clip.
bin/clip.sh "https://www.youtube.com/watch?v=SZIK-StxUzk" --slug tajne-svetog-pisma --auto 4

# 2. Post them. Reads the .txt beside each clip; nothing else to type.
bin/yt-upload.sh work/20260910-tajne-svetog-pisma
```

Step 1 leaves this behind:

```
work/20260910-tajne-svetog-pisma/
  full.srt                              transcript of the whole recording, with timecodes
  youtube/
    short_1_tajne-svetog-pisma.mp4      the clip, 1080x1920, Croatian captions, title card
    short_1_tajne-svetog-pisma.txt      TITLE / DESCRIPTION / TAGS / THUMBNAIL for that clip
    short_1_tajne-svetog-pisma.jpg      thumbnail, a frame with the title card on it
    short_2_...                         and so on
```

Between the two commands, open the `.txt` files. The title comes from the pick, the
description is a draft made of the clip's own words, so make it two or three punchy
sentences. Fix Croatian mistakes in `clip_N.srt` and re-run step 1; the download and the
transcript are cached, only the render repeats. A clip whose `.txt` lacks a title,
description, tags or thumbnail is refused by step 2, so nothing goes out half-filled.

Normal 16:9 videos, not Shorts, for the longer passages. Add `--video` spans; they land as
`youtube/video_N_<slug>.mp4` with their own `.txt` and `.jpg`, and step 2 posts them the same
way (without the #Shorts tag):

```
bin/clip.sh "https://www.youtube.com/watch?v=SZIK-StxUzk" --slug tajne-svetog-pisma --dest youtube \
  --video 22:43-25:41 "Više komunista u Kaliforniji nego u Jugoslaviji" \
  --video 01:15:58-01:20:27 "Hrvatska je danas karikatura one iz 1991."
```

Picking the moments yourself instead of `--auto`:

```
bin/clip.sh "https://www.youtube.com/watch?v=SZIK-StxUzk" --slug tajne-svetog-pisma \
  --clip 03:12-04:05 "Što bi Hrvati bez Srba? || What would Croats do without Serbs?" \
  --clip 09:43-10:25 "Identitet na broju žrtava || An identity built on a body count"
```

Step 2 remembers what it uploaded in `youtube/uploaded.json`, so running it again only sends
new clips. It also checks each clip before anything is sent: title under 100 characters,
description and tags present, thumbnail file present, and the signed-in channel is the one in
`config.yaml`. Step 1 checks the clip edges (opens on a sentence, closes on a full stop, no
repeated Whisper lines) and prints a warning per clip when something is off.

**Thumbnails need a one-time step in YouTube Studio.** The API refuses a custom thumbnail
(403) until the channel has verified a phone number: Studio → Settings → Channel → Feature
eligibility → Intermediate features → Verify phone number. Until then the upload succeeds and
the thumbnail has to be set by hand from the `.jpg` beside the clip. Uploads are unlisted by default (`config.yaml`): check the Copyright tab in Studio,
then `bin/yt-upload.sh work/<folder> --privacy public` next time, or flip them in Studio.
Quota is about six uploads a day; when it runs out the command stops and tells you, and the
next run picks up where it left off.

## The one you will use

```
bin/clip.sh "<article url>"  --slug sunic-kanada  --auto 3
bin/clip.sh "<youtube url>"  --slug sunic-desnica --auto 3
```

An article page, a YouTube link, or a local file. Broadcaster pages have the media URL in their
HTML and are scraped; YouTube, Vimeo, Rumble and the rest build the stream in JavaScript, so
those go through yt-dlp. Either way it downloads the video, transcribes it, picks the moments,
titles each in Croatian and English, then renders every one twice:

```
work/<date>-<slug>/
  youtube/   short_N_<slug>.mp4   Croatian subtitles and title, full quality
  facebook/  short_N_<slug>.mp4   same file
  telegram/  short_N_<slug>.mp4   same file (a bot may not send over 50MB)
  whatsapp/  short_N_<slug>.mp4   same cut, under 30s and under 10MB
  substack/  short_N_<slug>.mp4   English subtitles and title
```

One folder per destination, so uploading is "open the folder for the place you are posting to".
The first three are hard links to one file, so five folders cost one copy on disk.

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
