# WhatsApp

Short version: **WhatsApp Status cannot be posted by any API.** There is no setup guide here
because there is nothing to connect. This page explains why, so the question does not keep
coming back, and gives you the fastest manual route.

---

## What the WhatsApp APIs actually do

| | What it is for | Can it post a Status? |
|---|---|---|
| **Cloud API** (Meta's official) | Businesses replying to customers who messaged first, and template messages to people who opted in | **No** |
| **Business App** | The phone app for small businesses. Status is a manual tap | **No** |
| **Channels** | Broadcast feed, like Telegram channels | **No public API at all** |
| **Baileys** and similar | Unofficial libraries reverse-engineering WhatsApp Web | Technically yes. See below |

The Cloud API is a messaging API. It sends a message to a phone number that has opted in, inside
a 24-hour window or via an approved template. Status is not a message to anyone: it is a
broadcast to your contacts, and Meta exposes no endpoint for it. Same for Channels.

## Why not the unofficial route

`HOW-THIS-IS-INTENDED-TO-WORK.md` already rules this out and it is right to. Baileys drives a
real WhatsApp Web session pretending to be a browser. It works until it does not, and the
failure mode is the **phone number being banned**, not an error message. That is Tom's actual
number, the one his contacts have. No amount of automation is worth that.

---

## So: the manual route, made as short as possible

`bin/clip.sh` already produces the file in exactly the shape WhatsApp accepts:

```
work/<date>-<slug>/whatsapp/short_N_<slug>.wa.mp4
```

Croatian subtitles, Croatian title card, **under 30 seconds and under 10 MB**, which are the two
limits Status enforces. If a file was ever refused as *"larger than the 10 MB limit"*, that is
the file that fixes it.

To post: AirDrop the `.wa.mp4` to the phone, open WhatsApp → Status → pick it from the gallery.
Roughly twenty seconds per clip.

If you want to resize something that did not come from `clip.sh`:

```
.venv/bin/python lib/shrink.py <file> --preset whatsapp
```

---

## The two limits, since they are not documented anywhere obvious

* **30 seconds.** Longer videos are trimmed or refused. `lib/pick.py` now chooses 20 to 28 second
  spans specifically so nothing is ever cut mid-sentence to fit.
* **10 MB.** Not the 16 MB quoted for ordinary media sharing. Observed from the app's own error
  message. `lib/shrink.py` targets 9 MB to leave room for container overhead.

---

## If this ever changes

Meta would have to publish a Status or Channels endpoint in the Cloud API. If that happens the
work is small: a `lib/whatsapp_post.py` in the shape of `lib/telegram_post.py`, plus a token in
`.env`. Until then this stays a manual step, deliberately, and the pipeline's job is to hand you
a file that uploads first time.
