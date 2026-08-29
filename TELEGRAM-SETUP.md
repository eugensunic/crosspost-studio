# Connecting to Telegram

The easiest of the four. Five minutes, no OAuth, no app review, no expiry. A bot token and a
channel id, and it works forever.

---

## 1. Make a bot

Open Telegram and message **[@BotFather](https://t.me/BotFather)**.

```
/newbot
```

It asks for a display name (anything, e.g. `Tom Sunic`) and then a username, which must end in
`bot` (e.g. `tomsunic_bot`).

BotFather replies with a token that looks like:

```
8123456789:AAF3xQ7m-EXAMPLE-tokenstring
```

That is your **TG_BOT_TOKEN**. It is a password. Anyone with it controls the bot.

## 2. Put the bot in the channel

Open your Telegram channel → **Administrators** → **Add Admin** → search for the bot by its
username → add it.

Give it **Post Messages**. That is the only permission it needs.

A bot cannot post to a channel it does not administer, and it cannot add itself.

## 3. Find the channel id

**If the channel is public**, the id is just its @name:

```
TG_CHAT_ID=@tomsunic
```

**If the channel is private**, you need the numeric id. Post any message in the channel, then
open this URL in a browser with your token filled in:

```
https://api.telegram.org/bot<TG_BOT_TOKEN>/getUpdates
```

Look for `"chat":{"id":-1001234567890,...}`. That whole number, minus sign included, is your
**TG_CHAT_ID**. Private channel ids always start `-100`.

If `getUpdates` returns an empty list, the bot has not seen anything yet: post another message
in the channel after adding the bot, then reload.

## 4. Put them in .env

```
TG_BOT_TOKEN=8123456789:AAF3xQ7m-EXAMPLE-tokenstring
TG_CHAT_ID=@tomsunic
```

## 5. Check it

```
cd ~/Desktop/crosspost-studio
PYTHONPATH=lib .venv/bin/python lib/telegram_post.py --check
```

Prints the bot username and the channel title. If it says *chat not found*, the bot is not an
administrator of that channel, or the id is wrong.

---

## Posting

```
# text, with a link preview
PYTHONPATH=lib .venv/bin/python lib/telegram_post.py --message "..."

# video with a caption
PYTHONPATH=lib .venv/bin/python lib/telegram_post.py \
  --message "caption" --video work/<slug>/whatsapp/short_1.wa.mp4
```

It asks before posting. `--yes` skips that.

---

## Two limits that will bite

* **50 MB per file.** A bot may upload no more than 50 MB, which is lower than what the Telegram
  app allows you as a human, and it cannot be raised. The `.wa.mp4` files are around 8 MB, so
  this only matters if you post a full-length video. `lib/shrink.py` fixes it.
* **1024 characters of caption** on a video, against 4096 for a plain message. The script checks
  before uploading rather than after. If the text is longer, post the video and the text as two
  messages.

---

## When it stops working

| Symptom | Cause |
|---|---|
| `chat not found` | Bot is not an admin of the channel, or `TG_CHAT_ID` is wrong. |
| `not enough rights` | Bot is an admin but lacks **Post Messages**. |
| `Unauthorized` | Token wrong, or the bot was deleted in BotFather. |
| `getUpdates` empty | Post a message in the channel after adding the bot, then retry. |

Nothing here expires. If it worked once it keeps working, unless someone removes the bot from
the channel.

---

## Note on the video you post

Telegram does not run automated copyright matching the way YouTube and Facebook do. That makes
it technically easy to post a broadcaster's clip there, and it does not make it lawful. The rule
in step 0 of `HOW-THIS-IS-INTENDED-TO-WORK.md` is about who owns the footage, not about who is
likely to catch you.
