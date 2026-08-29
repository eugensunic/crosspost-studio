# Connecting to YouTube

One-time setup so this machine can upload to the channel. Fifteen minutes, done once. No server,
no domain, no Postiz: Google's desktop OAuth uses a loopback redirect, so everything happens
locally.

After this, uploading is one command and never asks again.

---

## Before you start

You need to be signed into the Google account that **owns the channel**, not one that merely has
access to it. Check by opening the channel in YouTube Studio and looking at the account picture
top right. That is the account you must use in step 5.

Channel: `UCI8I-1QsJIVQ1vralwI-IYw`

---

## 1. Make a Google Cloud project

Go to [console.cloud.google.com](https://console.cloud.google.com).

Top bar → project dropdown → **New Project**. Name it anything, `crosspost` is fine. Create, then
make sure the project dropdown now shows it.

## 2. Turn on the YouTube API

**APIs & Services → Library**, search **YouTube Data API v3**, open it, press **Enable**.

Nothing works without this and the error it produces if you forget is unhelpful.

## 3. Set up the consent screen, and set it to production

**APIs & Services → OAuth consent screen**.

* User type: **External**. Create.
* App name: anything. User support email and developer email: your own.
* Scopes: skip, the script asks for what it needs at sign-in.
* Test users: skip.
* Save.

Then, back on the OAuth consent screen page, find **Publishing status** and press
**PUBLISH APP**. Confirm.

> **This is the step everyone gets wrong.** Left in *Testing*, Google issues refresh tokens that
> expire after **7 days**. Uploads work all week, then quietly stop, and the failure looks like a
> broken script rather than an expired token. Publishing status must read **In production**.
>
> Google may say the app is unverified. That is fine here. Verification is for apps used by
> other people; you are the only user of your own project.

## 4. Create the credentials

**APIs & Services → Credentials → Create Credentials → OAuth client ID**.

* Application type: **Desktop app**. This matters. A "Web application" client needs an HTTPS
  redirect URL and a server; a Desktop client redirects to localhost, which is why no server is
  needed.
* Name: anything. Create.
* Press **Download JSON**.

Save that file as **`client_secret.json` in the repo root**:

```
/Users/eugen.sunic/Desktop/crosspost-studio/client_secret.json
```

It is already in `.gitignore`, so it will never be committed. Treat it like a password.

## 5. Sign in, once

```
cd ~/Desktop/crosspost-studio
PYTHONPATH=lib .venv/bin/python lib/youtube_upload.py --check
```

A browser opens. **Pick the account that owns the channel.** Google will warn that the app is
unverified: **Advanced → Go to (your app name)**. Approve.

The terminal then prints:

```
  signed in as: <channel name> (UCI8I-1QsJIVQ1vralwI-IYw, N subscribers)
```

Check that the id matches. If it shows a different channel, you signed in with the wrong Google
account: delete `.yt_token.json` and run `--check` again.

The refresh token is now saved in `.yt_token.json` (gitignored, chmod 600). You will not be asked
again.

---

## Uploading

```
PYTHONPATH=lib .venv/bin/python lib/youtube_upload.py \
  work/<slug>/substack/short_1_<slug>.mp4 \
  --title "Title, under 100 characters" \
  --description "..." \
  --channel-id UCI8I-1QsJIVQ1vralwI-IYw
```

It asks for confirmation, shows progress, and prints the video and Studio links.

* `--channel-id` makes it refuse if the saved token belongs to a different account. Uploading to
  the wrong channel is not something you can quietly undo.
* `--privacy` defaults to `unlisted`, from `config.yaml`. Leave it there. Upload unlisted, check
  the **Copyright** tab in Studio, and only then switch to public.
* `--yes` skips the confirmation once you trust it.

**For a Short:** the file must be vertical and under 3 minutes. Everything `bin/clip.sh` produces
is 1080x1920 and well under. Putting `#Shorts` in the title or description helps YouTube classify
it.

---

## Quota

The project gets **10,000 units a day**. An upload costs **1,600**, so about **six uploads a day**,
shared with anything else using the same project. `--check` costs 1. The quota resets at midnight
Pacific time. Exceeding it gives a `quotaExceeded` error and nothing else breaks.

---

## When it stops working

| Symptom | Cause |
|---|---|
| Uploads worked for a week, then stopped | Consent screen is back in *Testing*. Set it to **In production**, delete `.yt_token.json`, run `--check` again. |
| `client_secret.json missing` | Step 4 not done, or the file is not in the repo root. |
| Signed in as the wrong channel | Delete `.yt_token.json`, run `--check`, pick the other account. |
| `quotaExceeded` | More than ~6 uploads today. Wait for midnight Pacific. |
| `accessNotConfigured` | Step 2 skipped: the YouTube Data API is not enabled on this project. |

---

## Before you upload someone else's footage

This is publishing. If the video came from a broadcaster, uploading it is the step that draws a
copyright strike, and Content ID matches the broadcast audio whatever you do to the picture.
Without written permission the clip goes out as `--mode appearance`: your text and a link to
their page, no upload. See step 0 of `HOW-THIS-IS-INTENDED-TO-WORK.md`.
