# LinkedIn

Two things: the shape of an announcement post, and how to connect so you can post one by
command. The format belongs with `--mode appearance` — nothing is uploaded, the link does the
work.

---

# Part 1 — The post format

## Anatomy

```
┌ 1  HOOK        the claim itself, 1–2 sentences. Not "I was on TV".
│
├ 2  (blank)
│
├ 3  BRIDGE      "Više o tome u mom gostovanju za HRT:"
├ 4  SOURCE      HRT – Sunić: Sukob SAD-a i Kanade nije samo trgovinski, već i kulturološki
├ 5  LINK        https://lnkd.in/… (LinkedIn wraps it automatically)
└ 6  HASHTAGS    #SAD #Kanada #geopolitika #HRT
```

Six lines, four blocks. The whole post is under 400 characters.

### The one rule that matters

**The hook is an argument, not an announcement.** The reference post opens with a claim someone
could disagree with — *the US–Canada conflict is not only about tariffs and trade, it has a
deeper political and cultural dimension* — and only then mentions the appearance. Reversing that
order ("I was a guest on HRT, where I discussed…") turns a position into a press release and it
stops travelling.

The reliable hook shape here, and the one used in the reference post:

> **X is not only A — it also has a deeper B dimension.**

Others that work the same way: *What is presented as A is in fact B.* · *The real question is not
A, but B.* · *A explains less here than B does.* The common structure is a reframe: take the
obvious reading, name it, then displace it.

## Template

```
{HOOK — 1–2 sentences, the claim, in the language of the audience}

{BRIDGE}
{SOURCE_TITLE}
{URL}
#{TOPIC1} #{TOPIC2} #{FIELD} #{OUTLET}
```

**Bridge line, by source type** (Croatian):

| Source | Bridge |
|---|---|
| TV appearance | `Više o tome u mom gostovanju za {OUTLET}:` |
| Podcast / long interview | `Više o tome u razgovoru za {OUTLET}:` |
| Print or web interview | `Cijeli intervju za {OUTLET}:` |
| Panel, lecture, conference | `Snimka cijelog izlaganja:` |
| His own article | `Cijeli tekst:` |

English equivalents: `More on this in my appearance on {OUTLET}:` · `More in my conversation with
{OUTLET}:` · `Full interview with {OUTLET}:` · `Recording of the full talk:` · `Full piece:`

**Source title line** — copy the real headline from the source, prefixed with the outlet:
`{OUTLET} – Sunić: {headline}`. Do not rewrite it. It is the outlet's framing, it is verifiable,
and it tells the reader what they are clicking before they click.

**Hashtags** — exactly four, in this order: two subject/place, one field, one outlet.
`#SAD #Kanada #geopolitika #HRT`. Three is fine, six looks like spam. Keep `#HRT`-style outlet
tags: they are how the broadcaster's own audience finds it.

## Reference post

The one already published, as the calibration example:

```
Sukob SAD-a i Kanade nije samo pitanje carina i trgovine, već ima i dublju političku i kulturološku dimenziju.

Više o tome u mom gostovanju za HRT:
HRT – Sunić: Sukob SAD-a i Kanade nije samo trgovinski, već i kulturološki
https://lnkd.in/eTbnu2sw
#SAD #Kanada #geopolitika #HRT
```

Why it works: hook is a claim · appearance is secondary · headline is the outlet's own · four
tags · no emoji · no "excited to share" · short enough that nothing is hidden behind *…see more*.

## Writing one, in order

1. **Read the source headline.** It gives you the outlet's framing and usually the topic pair for
   the hashtags.
2. **Write the hook last-thing-first.** What is the claim someone could argue with? Fit it in
   under 200 characters or it disappears behind *…see more*.
3. **Pick the bridge** from the table by source type. It is fixed text, not a decision.
4. **Paste the real headline**, prefixed with the outlet.
5. **Four hashtags**: two subject/place, one field, one outlet.

If the source supports more than one angle, write both and pick, rather than averaging them into
something with no edge.

## Mechanics worth knowing

* **Truncation.** LinkedIn cuts at roughly 200 characters on desktop, fewer on mobile, then shows
  *…see more*. The hook must be complete before that point. `lib/linkedin_post.py` prints exactly
  where the cut falls before you publish.
* **Language.** Post in the language of the intended audience, not English by default. LinkedIn
  offers *Show translation* automatically, so a Croatian post loses nothing with a foreign reader
  but gains everything with a Croatian one.
* **Outbound links.** LinkedIn is widely observed to show link posts to fewer people than
  text-only posts. The usual workaround is hook plus hashtags in the post, link in the first
  comment. The reference post did not do this. Worth testing across a few posts and comparing
  impressions before adopting it: with the account this small the sample is too thin to conclude
  anything.
* **No emoji, no "thrilled to share".** The account's register is *Author · Lecturer · Political
  TV Commentator*. The posts should read the same way.
* **Editing.** Editing shortly after publishing is fine; the reference post shows *Edited* and was
  still circulating. Do not edit after it gains traction.
* **Timing.** Weekday mornings CET. `appearance` mode posts immediately rather than at the weekly
  slot, because an appearance is news and decays fast.

---

# Part 2 — Connecting

Unlike the others, **this one expires every 60 days** and there is nothing to be done about it: a
personal profile gets no permanent token and no refresh token without the Marketing Developer
Platform. Diarise the renewal.

## 1. Create an app

[linkedin.com/developers/apps](https://www.linkedin.com/developers/apps) → **Create app**.

* App name, and the **LinkedIn Page** it belongs to. If Tom has no Company Page you must make one
  — an app cannot exist without one, even for posting to a personal profile.
* Tick the legal agreement, create.

## 2. Verify the app

On the app's **Settings** tab there is a **Verify** button. It generates a link you open as an
admin of that Company Page. Until this is done, no products can be added.

## 3. Add the products

**Products** tab. Request:

* **Share on LinkedIn** → gives the `w_member_social` scope, which is what publishes.
* **Sign In with LinkedIn using OpenID Connect** → gives `openid` and `profile`, which is how the
  script learns your person URN.

Both are self-serve and approve within a minute or two.

## 4. Get a token

**Auth** tab → note the **Client ID** and **Client Secret**, and add an **Authorized redirect
URL** of `http://localhost:8000/callback`.

Then open this in a browser, with your client id filled in:

```
https://www.linkedin.com/oauth/v2/authorization
  ?response_type=code
  &client_id=<CLIENT_ID>
  &redirect_uri=http://localhost:8000/callback
  &scope=openid%20profile%20w_member_social
```

Approve. The browser lands on a dead localhost page — that is expected. Copy the `code=` value
out of the address bar; it is valid for 30 seconds, so do this next bit immediately:

```
curl -X POST https://www.linkedin.com/oauth/v2/accessToken \
  -d grant_type=authorization_code \
  -d code=<CODE> \
  -d redirect_uri=http://localhost:8000/callback \
  -d client_id=<CLIENT_ID> \
  -d client_secret=<CLIENT_SECRET>
```

The `access_token` in the reply is what you want.

## 5. Put it in .env

```
LI_ACCESS_TOKEN=AQV...
LI_AUTHOR_URN=
```

Leave the URN blank for now.

## 6. Check it

```
cd ~/Desktop/crosspost-studio
PYTHONPATH=lib .venv/bin/python lib/linkedin_post.py --check
```

It prints your name and the `LI_AUTHOR_URN=urn:li:person:...` line. Paste that into `.env` so
later posts skip the lookup.

## Posting

```
PYTHONPATH=lib .venv/bin/python lib/linkedin_post.py \
  --text "$(cat post.txt)" --link "https://vijesti.hrt.hr/..."
```

It shows what will be visible before *…see more*, and what will be hidden, then asks before
publishing.

**No video.** The script posts text and a link only. Uploading video to a personal profile needs
a three-step register-upload-create against a different API, and for `appearance` mode the link
is doing the work anyway.

## When it stops working

| Symptom | Cause |
|---|---|
| `401` | Token expired. They last 60 days. Redo step 4. |
| `403` | Missing `w_member_social`, or the **Share on LinkedIn** product was never added. |
| `422` | LinkedIn rejected the body, usually as a near-duplicate of a recent post. |
| No products available | The app is not verified. Step 2. |

---

## Wiring the hook into the pipeline

`lib/appearance.py` already fetches `source_title`, `host` and `url` and asks Ollama for a
summary — but its prompt asks for *"a 2-sentence announcement"*, which produces a description,
not the hook above. To generate text in this format the prompt has to specify the shape:

```python
out = ollama(
    f'Guest appearance by Dr. Tom Sunic. Host: {host}. Headline: "{a.title}". '
    f'Source title: "{src_title}".\n'
    f'Write ONE opening line for a LinkedIn post in '
    f'{"Croatian" if a.lang == "hr" else "English"} (key "hook"): a single claim of the form '
    f'"X is not only A, it also has a deeper B dimension" — an argument the reader could disagree '
    f'with, NOT an announcement that he appeared somewhere. Max 200 characters. '
    f'Then the same in English (key "hook_en"). '
    f'Then four hashtags (key "tags"): two subject or place, one field, one outlet. '
    f'Sober tone, no emojis, no "excited to share". JSON only.',
    system="Return only valid JSON.", json_mode=True)
```

Everything else is deterministic and needs no model: the bridge comes from the table keyed on
source type, and the source title and URL are already in `appearance.json`. Only the hook is
worth spending a model on.

Read the hook before it goes out. It is the one line people judge him on.
