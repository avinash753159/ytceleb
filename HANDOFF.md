# MrBeast documentary — handoff spec

Repo: `C:\Users\avina\ytceleb`
Channel: Celeb Workout (YouTube)

---

## 1. What we are making

A ~12-minute documentary, **"The Disease That Built MrBeast"**.

**Thesis (approved by the owner, do not change):**
> The most energetic man on the internet has almost no energy. Everything
> Jimmy Donaldson built, he built while his own immune system was attacking
> him — and the workout was never vanity. It was a man taking something back
> from a body that had been taking things from him since he was fifteen.

---

## 2. THE AUDIO IS FINISHED. DO NOT REBUILD IT.

`final_video/mrbeast_audio_v6/MRBEAST_V6_STORY_MASTER.wav` — 12:19, approved.

Narration is ElevenLabs "Brian" (`nPczCjzI2devNBz1zQrb`); every regeneration
costs credits, and the owner has signed off on this cut. Only the **picture**
layer is outstanding.

Build script if it ever must be regenerated: `pipeline/mrbeast_audio_v4.py`
(`MRBEAST_SCRIPT_VERSION=V6`).

---

## 3. Get timings from the EDIT, never from a transcript

This caused the worst failure in the project. Whisper merges long pauses into
one segment, so its timestamps drift by 10+ seconds. Baseball footage landed
twelve seconds before the baseball narration, on top of a silent break.

**Authoritative timings:** run `work/_edl_times.py`. Current opening:

```
 0.00- 2.00  music lead-in
 2.00-11.89  "most productive person ... 300 million subscribers"
11.89-13.99  BITE  "least energetic people you'll ever meet"
13.99-22.01  "since he was fifteen ... attacking him from the inside"
22.01-30.80  "not a story about a workout ... take some of it back"
30.80-34.00  beat
34.00-44.50  "he was an athlete, a kid who played constantly"
44.50-54.10  BITE  "I got Crohn's when I was 15 ... lost like 50 pounds"
54.10-58.10  TITLE BREAK — 4s, music only, before the diagnosis
58.10-69.43  "The diagnosis had a name. Crohn's disease."
```

---

## 4. HARD RULES — every one comes from a rejected cut

1. **ONLY JIMMY.** No other creator on screen, ever. Airrack and Chris
   Hemsworth were dropped entirely after frame-checking proved there is no
   Jimmy-only window in either. Joe Rogan and Steven Bartlett must never
   appear — they did, because long windows crossed the podcast's own edits.
2. **NEVER REUSE A CLIP OR A WINDOW.** Not once. Enforce with a registry that
   throws on a second draw.
3. **NO LOOPING.** `-stream_loop` is banned. If a clip is shorter than the
   shot, fail the build; do not play the same 5 seconds twice.
4. **NO SHOT OVER ~6 SECONDS.**
5. **WINDOWS MUST NOT CROSS A CAMERA CUT.** Use scene detection and place the
   shot inside a single uninterrupted run (`uncut_window()` in
   `pipeline/mrbeast_picture_v7.py`).
6. **PERCEPTUAL DEDUPE.** Different timecodes can look identical. Compare
   dHashes and reject near-matches. This is necessary but NOT sufficient —
   it cannot tell who is in frame.
7. **EYES-ON IDENTITY PASS IS MANDATORY.** Machine dedupe passed two pure
   green frames, five Joe Rogan singles and four Steven Bartlett singles.
8. **PICTURE MUST ILLUSTRATE THE SENTENCE BEING SPOKEN.** Not "next clip in
   the rota".
9. **NO STAND-IN PEOPLE.** No stock child playing baseball as young Jimmy.
   Use equipment, fields, objects. Nothing cast as him.
10. **NO ON-SCREEN CREDIT FOR STOCK.** Only the interview sources get a
    lower-third. Stock attribution belongs in the description.
11. **NO CELEBWORKOUT LOGO OR WATERMARK ANYWHERE.**
12. **NARRATION MUST NOT ECHO THE CLIP** beside it (`pipeline/echo_check.py`).
13. **CLINICAL IMAGERY: short, ~2s, faded, never implied to be Jimmy.**

---

## 5. Immediate task the owner asked for

### 5a. Use REAL screenshots of his posts, not reconstructions

`pipeline/post_card.py` builds a hand-drawn card in Anton font. It looks like
a graphic, not like a post. **Replace it** with a real screenshot of the
actual tweet.

Approach: headless Chrome (already used in `pipeline/storyboard.py`) against
the X embed/syndication render, or `publish.twitter.com/oembed`. Chrome is at
`C:\Program Files\Google\Chrome\Application\chrome.exe`.

Posts confirmed and already downloaded to `dossier/mrbeast/primary/`:

| Date | Text | Image |
|---|---|---|
| 2023-06-29 | "Woke up and realized I was obese so I started lifting and walking 12,500 steps a day. Still got a long way to being yoked but I'm happy with my progress so far" (656,553 likes) | `mrbeast_transformation_2023-06-29.jpg` |
| 2025-04-21 | "Go get gains boyz" | `mrbeast_after_2025-04-21_1.jpg` |

Status IDs: `1674429048095916032`, `1914347042089877638`.
Metadata without auth: `https://cdn.syndication.twimg.com/tweet-result?id=<ID>&lang=en&token=a`
(a browser User-Agent header is REQUIRED — without one Cloudflare returns 403
error 1010, which looks exactly like a dead API key).

### 5b. Widen the source pool

Only four videos were ever downloaded. The owner has pointed at more:

- `https://www.youtube.com/watch?v=fl0xOUzINHg`
- `https://www.reddit.com/r/GettingShredded/comments/14mzyb6/thoughts_about_mr_beast_progress/`
  (contains the post image and community reaction)
- `c8VcUnz3nVc` (Colin & Samir, *The Full Story of MrBeast*, 115 min) is
  already downloaded and **has never been scanned**.

Any new source must pass the identity pass before use.

---

## 6. What already exists and works

**The V8 picture chain is the current one.** V7 and `first_minute*.py` are
superseded and kept only for reference; V7 uses `-stream_loop`, reuses windows,
and draws from `library/broll`, all of which are now banned.

| Thing | Path |
|---|---|
| Locked audio | `final_video/mrbeast_audio_v6/MRBEAST_V6_STORY_MASTER.wav` |
| **Authoritative full timeline (74 segments)** | `manifest/edl_full.json`, built by `work/_edl_full.py` |
| **The shot plan — read this first** | `pipeline/picture_plan_v8.py` |
| **Picture build** | `pipeline/mrbeast_picture_v8.py` |
| **Pre-delivery gate** | `pipeline/qc_v8.py` → `dossier/mrbeast/QC_V8.md` |
| Verified Jimmy windows (95 drawable) | `manifest/jimmy_pool2.json` |
| Pool builder | `pipeline/jimmy_pool2.py` (keyed `sid@t0`, NOT sheet index) |
| Per-bite sync windows | `pipeline/bite_windows.py` → `manifest/bite_windows.json` |
| Burned-in-text screen | `pipeline/screen_text.py` (6 frames/window) |
| Identity verdicts | `manifest/verdicts_*.json` → `pipeline/apply_verdicts.py` |
| Real X post screenshots | `pipeline/post_card.py` (Playwright + Chrome) |
| Documents captured for the film | `pipeline/prep_docs_v8.py` → `work/docs_v8/` |
| 18 rendered cards | `work/cards/` (`pipeline/render_cards_v8.py`, `reground_cards.py`) |
| OBJECT-class stock allow-list | `manifest/broll_allow.json` — the ONLY source of stock |
| Stock clips | `library/broll3/`, `library/broll4/` (`fetch_broll3/4.py`) |
| Description + credits | `pipeline/credits_v8.py` → `DESCRIPTION_V8.md` |
| Effects library | `pipeline/fx.py`, `graphics/src/fxcards.tsx` |
| Medical stills, licensed | `dossier/mrbeast/medical/` + `CREDITS*.json` |

**`library/broll` (the original 44 clips) must not be drawn from.** Audited:
11 OBJECT, 18 FIGURE, 15 REJECT. It contains a horror-film clip of a woman
chained to a bed (`bedroom_dark.mp4`, which V7 used for "fix sleep first"), a
teenage boy looking into camera, and two byte-identical duplicate files of the
same child actor. See `dossier/mrbeast/BROLL_AUDIT.md`.

**Performance:** ffmpeg and onnxruntime each grab every core by default. Run
~10 workers × `-threads 2` on this 20-core machine. Getting this wrong made
renders 8× slower and once starved the OS so badly PowerShell could not start
a thread.

---

## 7. Known defects still open

Picture V8 is built and machine-clean (`dossier/mrbeast/QC_V8.md`): 172 shots,
none reused, nothing over 6s, no static shots, no black stretches, frame-exact
against the locked audio, 56% of screen time is Jimmy. The five defects listed
in the original spec are closed:

1. ~~Post cards are reconstructions~~ — CLOSED. `pipeline/post_card.py` now
   captures the real X embed through headless Chrome.
2. ~~`c8VcUnz3nVc` unscanned~~ — CLOSED. Scanned; 28 verified windows. It also
   settled a question: **it contains no illness content at all.**
3. ~~Only the first 70s rebuilt~~ — CLOSED. All 12:19 is built to the rules.
4. ~~Three graphics never built~~ — CLOSED. 12 new cards, and the 6 V7 cards
   re-grounded to match. Two were then CUT on factual grounds (see below).
5. **The title still over-promises.** Unchanged and still true: the title says
   "His Real Workout & Diet", no training split was ever published, and the
   "40% body fat" figure is Airrack's. The film says so; the title does not.

### What a five-way eyes-on pass found, and what is still open

A verification fleet reviewed all 29 contact sheets against the narration.
Identity discipline held everywhere - across 172 shots not one frame contained
Rogan, Bartlett, Colin, Samir, or the MrBeast executive who fooled a thumbnail
pass; the Rogan screen-share panel never appears; credits are on every
interview/archive shot and on no stock shot. What it caught instead:

FIXED since that pass (all verified by eye in the current render):
- `severe_colitis.jpg` is **ulcerative colitis**, and CREDITS2.json says
  "Only usable if captioned as related IBD, never as Crohn's." It was
  full-frame and uncaptioned under his own Crohn's bite. Withdrawn.
- `card_rest` drew a **MON-FRI training split** seventeen seconds before the
  narration promises the film invents nothing. Cut.
- `card_time` printed a broken **"2-2h ... every night"** with a sleep emoji
  and no source. Cut.
- `card_steps` said 12,500 starting 0.01s after a bite in which he says
  15,000. Cut - the figure's real source, his June 2023 post, is already on
  screen as a document at 26s.
- **20 stock clips withdrawn**: hands, forearms, legs and a thigh performing
  the activity the narration attributes to Jimmy (rule 9), and legible ROGUE,
  BODYTONE, SVENSSON, CarFitness and SD FITNESS branding (rule 3). Every
  `walk` clip went - walking footage is legs by nature, and on the steps beat
  legs read as a stand-in for him.
- A **camera cut inside a shot** at 246.47s. The fine gate used
  `scene > 0.30`; the angle change scored 0.09. It now uses `scdet` at
  threshold 6, calibrated against that cut (8.9) and the noisiest archive
  window (4.9).
- NIDDK pages showed the **NIH logo, site nav and a search box**; cropped to
  the article. The intestine plate was pillarboxed to 44% of frame; now fills.
  The villi micrograph was classed `still` so skipped rule 13's grade; now
  clinical. The credit plate was a fixed 680px slab hanging past short text;
  now sized to it.

STILL OPEN - these need the next session:
1. **A fresh eyes-on pass is owed on the current render.** The fleet reviewed
   earlier builds; roughly twenty fixes have landed since, and three of the
   five reviewers were looking at a file that was being rewritten underneath
   them. Freeze the render, re-cut the sheets, review again.
2. **The 2025 post photo contains a second person** - the phone-holder's arm,
   watch and hair at the right edge of his own gym mirror shot.
   `work/post_cards/post_gains_cropped.png` is prepared but NOT yet wired into
   the plan; `DOCS["post_gains"]` still points at the uncropped card.
3. **Two Colin & Samir sync shots are butted together** at 317.8 and 436.2
   with a punch delta too small to read as a new shot and too large to be
   invisible. One reviewer called it an editing mistake rather than monotony.
4. **The attribution question at 599s**: a 2025 Diary of a CEO quote plays
   over Colin & Samir picture carrying a "JUNE 2023" lower-third. The credit
   describes the picture, but a viewer reads it as the source of the words.
5. **Rule 10 contradicts the code.** Medical stills carry Wikimedia credits
   because CC BY requires attribution, but rule 10 says only interview
   sources get a lower-third. Write the exception into the rule.
6. **`calendar` is down to one clip and `bed` to three** (one window-limited
   to 3.46s). Any further rejection breaks the build. `walk` is at zero.
7. **The pool is at its variety limit**: 83 of 85 verified windows are drawn,
   and the allocator now rejects more on look-alike than it accepts.
   `jimmy_pool2.py` is set to 200 candidates per source for a wider re-scan;
   it has NOT been re-run, and a wider scan needs a fresh identity pass.

## 8. Description must credit

- Score: Scott Buckley, CC BY 4.0 (attribution strings in the audio cue sheet)
- Medical stills: Wikimedia Commons — CC0 / CC BY 2.0 / CC BY 3.0 / CC BY 4.0,
  plus one CC BY-SA 4.0 (resected tissue) which is flagged in `CREDITS2.json`
- Stock: Pexels, photographers listed in `library/broll/CREDITS.json`
- Interview sources: PowerfulJRE, The Diary of a CEO, Colin and Samir
