# Polishing a video

Fourth document in the set. `PLAYBOOK.md` is the strategy, `README.md` is the operator's manual,
`HOW-THIS-IS-INTENDED-TO-WORK.md` is the mental model. This one is the finishing pass: **what has to
be true of a clip before it is allowed out**, and which code enforces it.

The rules are enforced by `lib/polish.py`, which runs as step 5 of `bin/publish.sh`. Nothing here is a
manual step. If you are polishing a single clip that did not come through the pipeline, call it directly:

```
.venv/bin/python lib/polish.py raw.mov --work work/<slug> --srt work/<slug>/hr.srt --title "Naslov"
```

---

## The three rules

### 1. Clean the clip — no cursor, no player chrome, no recording artefacts

Anything that says "this was screen-recorded off someone's website" has to go. A mouse pointer in the
corner tells every viewer the clip was ripped, and it is the first thing they notice.

`polish.py` removes, automatically:

| Artefact | How it is found | How it is removed |
|---|---|---|
| Player control bar | the instant it auto-hides — a large change confined to the bottom rows while the top of frame carries on | the bottom 24% is blurred for exactly as long as the bar is up |
| Mouse pointer | small, bright, short-lived blobs against a local median | `delogo`, which interpolates from the pixels around it |
| Scrub-preview tooltip | same | same |
| Pointer at the frame edge | same | a blurred patch — `delogo` needs neighbouring pixels on all sides and has none at an edge |

Two things that make this harder than it sounds, both handled:

* **Animated studio backdrops.** HRT's set has moving light strings, so 76–80% of pixels differ from
  any long-window median. Detection uses a *local* median a few frames wide, where the animation has
  barely moved.
* **Shot changes.** A cut differs from the median exactly as much as a control bar does. They are told
  apart by where the difference lands: a bar covers the bottom rows completely, a cut does not.

Detection is deliberately conservative — it would rather leave a faint smudge on the backdrop than
smear someone's face. If it ever gets it wrong, `--no-clean` turns the whole stage off.

### 2. Burn the subtitles in — it has to read with the sound off

Most feed playback is muted. A clip with no on-screen text is a clip nobody watches.

* Spoken-language subtitles, burned in — not a sidecar file, which no network displays in-feed.
* Three words a line, so each card is readable at a glance.
* Placed in the blurred band **below** the video, never across a face.
* White, heavy weight, thick black outline, so they survive a bright frame.

**Spot-check the Croatian before it goes out.** Whisper is the quality floor for everything downstream
and it makes real mistakes — this clip alone had `suštavu` for `sustav`, `uzržavati` for `uzdržavati`,
`inversiju` for `inverziju`. Fix the SRT, then re-run; the pass is cheap.

### 3. Hold the title for the first few seconds

The viewer decides in about two seconds. Give them the claim in text before they have heard a sentence.

* Appears at 0.3 s, holds ~3.6 s, fades out.
* `--title-pos band` (default) puts it in the blurred band **above** the picture; `--title-pos over`
  puts it **on** the picture. Band is usually better on interview footage — a title over the picture
  lands on the speaker's head, because that is exactly where a framed head sits.
* Short enough to read — if it wraps past three lines it is not a title, it is a sentence.

---

## Framing: never centre-crop a two-shot

The vertical fit is a **blurred pad**: the whole frame is placed over a scaled, blurred copy of itself.
Nothing is ever cropped out.

The tempting alternative — crop the middle 9:16 out of a 16:9 frame — throws away 58% of the width and
fails outright on interview footage. In this HRT clip the wide two-shot has Tom on the left and the host
on the right, and the centre strip a crop would keep contains **neither of them**, just an empty desk.

---

## Rights come first

Polishing does not change who owns the footage. Everything in `HOW-THIS-IS-INTENDED-TO-WORK.md` step 0
still applies: if the recording is a broadcaster's, a polished vertical cut of it is still a re-upload,
and still a copyright strike. Polish it locally all you like — publish it only in `appearance` mode, or
with written permission.

---

## Known gaps

* The masked chrome band is a fixed 24% of frame height. Detecting *that* chrome vanished is reliable;
  measuring its exact height is not, because the speaker is usually moving in the same instant.
* Overlay detection only looks inside the window where player chrome is present, on the assumption that
  a pointer only appears while the UI is up. A cursor that shows up later in a clip is not removed.
* Captions come from the SRT as written. Nothing checks the Croatian for you.
