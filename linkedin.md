# LinkedIn post format — appearances

The shape of a LinkedIn announcement post, reverse-engineered from the HRT / SAD–Kanada post. Give me a source
link and I write one of these. Belongs with `--mode appearance`; nothing is uploaded, the link does the work.

---

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

**The hook is an argument, not an announcement.** The reference post opens with a claim someone could disagree
with — *the US–Canada conflict is not only about tariffs and trade, it has a deeper political and cultural
dimension* — and only then mentions the appearance. Reversing that order ("I was a guest on HRT, where I
discussed…") turns a position into a press release and it stops travelling.

The reliable hook shape here, and the one used in the reference post:

> **X is not only A — it also has a deeper B dimension.**

Others that work the same way: *What is presented as A is in fact B.* · *The real question is not A, but B.* ·
*A explains less here than B does.* The common structure is a reframe: take the obvious reading, name it, then
displace it.

---

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

English equivalents: `More on this in my appearance on {OUTLET}:` · `More in my conversation with {OUTLET}:` ·
`Full interview with {OUTLET}:` · `Recording of the full talk:` · `Full piece:`

**Source title line** — copy the real headline from the source, prefixed with the outlet:
`{OUTLET} – Sunić: {headline}`. Do not rewrite it. It is the outlet's framing, it is verifiable, and it tells the
reader what they are clicking before they click.

**Hashtags** — exactly four, in this order: two subject/place, one field, one outlet.
`#SAD #Kanada #geopolitika #HRT`. Three is fine, six looks like spam. Keep `#HRT`-style outlet tags — they are how
the broadcaster's own audience finds it.

---

## Reference post

The one already published, as the calibration example:

```
Sukob SAD-a i Kanade nije samo pitanje carina i trgovine, već ima i dublju političku i kulturološku dimenziju.

Više o tome u mom gostovanju za HRT:
HRT – Sunić: Sukob SAD-a i Kanade nije samo trgovinski, već i kulturološki
https://lnkd.in/eTbnu2sw
#SAD #Kanada #geopolitika #HRT
```

Why it works: hook is a claim · appearance is secondary · headline is the outlet's own · four tags · no emoji ·
no "excited to share" · short enough that nothing is hidden behind *…see more*.

---

## What to send me

Minimum:

```
LINK: <url>
```

That is enough — I read the headline and outlet from the page. Add any of these when you want control:

```
ANGLE:   the specific point to lead on, if the headline buries it
LANG:    hr (default) | en | de | fr
OUTLET:  if the page title does not name it cleanly
```

You get back the post as a single block, ready to paste, plus the four hashtags. If the source supports more than
one angle I will send two versions rather than guess.

---

## Mechanics worth knowing

* **Truncation.** LinkedIn cuts at roughly 200 characters on desktop, fewer on mobile, then shows *…see more*.
  The hook must be complete before that point. In the reference post it is — that is not an accident.
* **Language.** Post in the language of the intended audience, not English by default. LinkedIn offers *Show
  translation* automatically, so a Croatian post loses nothing with a foreign reader but gains everything with a
  Croatian one.
* **Outbound links.** LinkedIn is widely observed to show link posts to fewer people than text-only posts. The
  usual workaround is hook + hashtags in the post, link in the first comment. The reference post did not do this.
  Worth testing across a few posts and comparing impressions before adopting it — with the account this small, the
  sample is too thin to conclude anything yet.
* **No emoji, no "thrilled to share".** The account's register is *Author · Lecturer · Political TV Commentator*.
  The posts should read the same way.
* **Editing.** Editing a post shortly after publishing is fine — the reference post shows *Edited* and was still
  circulating. Do not edit after it gains traction.
* **Timing.** Weekday mornings CET. `appearance` mode posts immediately rather than at the weekly slot, because
  an appearance is news and decays fast.

---

## Wiring it into the pipeline

`lib/appearance.py` already fetches `source_title`, `host` and `url`, and asks Ollama for a summary. But the
current prompt asks only for *"a 2-sentence announcement"*, which produces a description, not the hook above.
To make the generated text match this format, the prompt needs to specify the shape:

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

The remaining lines are deterministic and need no model at all — bridge comes from the table above keyed on source
type, source title and URL are already in `appearance.json`. Only the hook is worth spending a model on.

Machine output still needs a human read before it goes out. The hook is the one line people judge him on.
