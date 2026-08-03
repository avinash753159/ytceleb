# New sources — acquisition and eyes-on assessment

Task: mine the two sources named in `HANDOFF.md` §5b that had never been touched.
Date: 2026-07-29. No pipeline file was modified. No video was rendered.

---

## Headline

| Source | Verdict |
|---|---|
| `fl0xOUzINHg` (brockashby) | **NOTHING USABLE. Zero windows.** Downloaded, fully scanned, every frame looked at. |
| Reddit `14mzyb6` | **Useful, but not as B-roll.** One genuinely valuable primary asset recovered plus 77 real comments. |

---

## 1. `fl0xOUzINHg` — "Mr. Beast Insane Body Transformation", brockashby

### Downloaded

`dossier/mrbeast/sources/fl0xOUzINHg.mp4` + `fl0xOUzINHg.info.json`

- 1280x720, 30 fps, h264 + opus, 562.214 s, 76.9 MB
- yt-dlp `-f "bv*[height<=720]+ba/b[height<=720]" --merge-output-format mp4 --write-info-json`
  with a Chrome User-Agent, run locally, no proxy. Matches the 720p mp4 convention of
  the other eight files in that directory (they resolved to av1 `398+251`; this video
  offers no av1, so it resolved to `136+251` — same 720p, h264 instead).
- Channel `brockashby` (UCN5Zx41Q3YBVjhq9RgqmTGQ), uploaded **2023-07-13**, 3,170 views,
  51 likes. Own tag list includes `colin and samir mr beast interview`.

### What was done

- Shot detection: `ffmpeg -vf "scale=320:-2,select='gt(scene,0.3)',metadata=print"`
  → 61 cuts / 57 shots. Written to `work/fl0x_scan/shots.json`.
- Uniform coverage pass: a frame every 3.0 s across the whole 562 s (**188 frames**),
  built into **16 labelled contact sheets** (`work/fl0x_scan/sheet_00..15.jpg`, tile
  index + m:ss + t= burned onto every tile, 4x3 at 480x270).
- Dense pass over every region containing Jimmy: a frame every 0.5 s across
  64–76 s, 156–162 s, 233–241 s, 336–352 s, 464–498 s (**152 frames**) → 13 sheets
  (`work/fl0x_scan/dense_00..12.jpg`).
- **All 29 sheets were read and looked at frame by frame.** Nothing was judged by
  machine dedupe.

### Table of usable windows

| start | end | what is happening |
|---|---|---|
| — | — | **none** |

Zero. Not one window survives.

### Why — measured, not guessed

The structure is the failure. This is a fitness coach reacting to camera, and it is
almost entirely *him*:

- **~85% of the runtime is brockashby's own face**, a static talking head against a
  white wave-panel wall, wearing his own branded tee. Two of the "shots" the detector
  found are 44.8 s and 64.1 s long — that is one unbroken take of the presenter.
  Every such frame violates hard rule 1 on its own.
- **Every frame containing Jimmy is Colin & Samir footage we already own.** See §1a.
- **Every Jimmy frame in four of the five Jimmy regions carries brockashby's burned-in
  subtitle** — large white caption text across the lower third, e.g. "I was really fat.",
  "I do 15,000 steps a day...", "we signed a contract workout every day,",
  "Airrack is looking yoked." Rule: no burned-in overlay text. Rejected.
- **Only three Jimmy frames in the entire film are subtitle-free**, at t≈66.0 s,
  t≈74.5 s and t≈159.5 s. Each sits inside a shot fragment of **1.03 s, 0.63 s and
  ~0.5 s** respectively. The pool's own floor is `MIN_RUN = 3.2 s`
  (`pipeline/jimmy_pool2.py`). Nothing close. And all three are frames of footage we
  already hold uncut and unsubtitled, so even a 4-second version would be worthless.
- **Other creators appear repeatedly.** Colin (green jacket) and Samir (yellow jacket)
  are full-frame at t≈67, 72.5–74, 158–158.5, 341–341.5, 344–345, 438, 441, 476.5.
  A three-shot wide of the whole studio at t≈441. **Airrack** shirtless and flexing at
  t≈486.5–489.
- **Composites that put Jimmy and the presenter in the same frame**, which no crop
  fixes: a cut-out of shirtless Jimmy standing beside the presenter at t≈24, and the
  Instagram before-photo split-screened with the presenter at t≈519–522.
- **Graphics and third-party UI** over the presenter throughout: the MrBeast YouTube
  subscribe card (t≈12), an Instagram like-bar reading "Liked by cheatmeats and
  5,142,255 others" (t≈18), the full Instagram caption block (t≈33–48), five blue
  chapter title cards, a PubMed paper citation card (t≈135–141), animated
  BMR/NEAT/TEF/EAT bar charts (t≈171–207), a Feastables product still (t≈288), and a
  YouTube-comment screenshot stack (t≈516).
- **Not-Jimmy filler**: a spinning casino/mall plate (t≈282), two unidentified men in
  a casino (t≈285), a bodybuilder torso with the presenter's face pasted on (t≈546).
- One frame at t≈297 is Jimmy on a beach **with a woman kissing his cheek** — a still
  photo, two people, rejected.
- The **first 25.8 s and the last 14.7 s are single presenter takes** (intro and
  outro), exactly the pattern the brief warned about.

### 1a. Recycling — confirmed, and it is total

Every Jimmy frame in this video is lifted from **Colin and Samir, "A Brutally Honest
Conversation with MrBeast", 2023-06-27** — which is already on disk as
`dossier/mrbeast/sources/9IQ_ldV9z_A.mp4` (7,574 s, 720p, no burned-in text).

Two independent proofs:

1. **Visual.** Identical maroon tee, grey Nike cap, plywood-framed studio, Shure mic
   and Feastables bottle; and Colin and Samir themselves appear in the reverse shots.
2. **Perceptual.** Extracted all 7,574 one-second frames of `9IQ_ldV9z_A` and dHash-
   matched 12 probe frames from the fl0x Jimmy regions against them. Every probe
   matched at Hamming distance **2–9**, against the project's own near-duplicate
   threshold of `HAMMING = 14`. In other words the pipeline's dedupe would already
   reject all of it as a picture we have used.

So there is no scenario in which this file adds anything. It is a lower-generation,
subtitle-burned copy of a source we hold in full. **Recommend: do not add
`fl0xOUzINHg` to `SOURCES` in `pipeline/jimmy_pool2.py`. Exclude it by construction,
alongside Airrack and Hemsworth, with the reason "reaction video; 100% of Jimmy footage
is recycled 9IQ_ldV9z_A under burned-in captions".**

The one genuinely new thing the file gave us is a pointer, not a picture: the real
yield from that Colin & Samir interview is `9IQ_ldV9z_A` itself, and brockashby's
caption track hands us a rough index of where the fitness answers sit in it
("15,000 steps a day", "an hour and a half every day", "the last 310 days",
"we signed a contract workout every day", "get a tattoo of each other").

---

## 2. Reddit r/GettingShredded — `14mzyb6`

### Access

reddit.com returns **HTTP 403 to this machine on every route attempted**: `www`,
`old`, `api`, `oauth`, the `.json` endpoint, a descriptive-UA request, and headless
Chrome. Redlib/Libreddit mirrors were 403, 503, SFW-blocked, or gated behind Anubis
proof-of-work. The `WebFetch` tool is blocked from reddit.com outright.

Recovered instead from the **Internet Archive** (raw `id_` captures): the thread page
snapshot from 2023-06-30T13:07:57Z, the post image, and 77 archived comment permalinks
spanning 2023-06-30 to 2023-07-06.

### (a) Confirmation and dating

| Field | Value |
|---|---|
| Title | **"Thoughts about Mr. Beast progress?"** |
| Author | **u/b4l1f3** (`t2_2pkwkrf`) |
| Post id | `t3_14mzyb6` |
| Created | **2023-06-30 13:07:24 UTC** |
| Type | image post, `i.redd.it/tc1j53pim59b1.png` |
| Score | **not obtainable** — see below |
| Comment count | **not obtainable**; 77 recovered |

The date is corroborated independently of the page's own timestamp: the first reply
carries ts 2023-06-30T13:13:38 UTC (6 minutes later) and comment IDs rise monotonically
with their capture times. So the Reddit post is a **next-day repost** of the
2023-06-29 tweet, not a separate event.

Score and true comment count **cannot be had**. The only Wayback capture of the thread
page was taken 33 seconds after the post went up, before any votes accrued, and live
Reddit is 403. Do not let a number get invented here.

### (b) Additional primary images — one, and it matters

`dossier/mrbeast/primary/reddit_14mzyb6_tweet_screenshot.png`
(1080x1080 PNG, sha256 `6ce53bd2…8472a`, provenance in `reddit_14mzyb6.json`)

This is **not** a new photo of Jimmy. It is something more useful: a **genuine
screenshot of the actual @MrBeast tweet**, X interface chrome intact, captured
contemporaneously and archived. That is precisely the asset **HANDOFF §5a** demands
("Use REAL screenshots of his posts, not reconstructions") and it removes the need to
scrape the syndication API or drive headless Chrome for this post.

Read off the screenshot itself: `7:46 AM · Jun 29, 2023 · 35.5M Views`,
`13.3K Retweets`, `5,091 Quotes`, `434.1K Likes`, `7,275 Bookmarks`.

**Two flags before anyone cuts with it:**

1. **Number conflict.** HANDOFF §5a records **656,553 likes**. This screenshot, taken
   ~29 hours after posting, reads **434.1K**. Both are presumably true at different
   moments, but the film cannot narrate one figure over a frame showing the other.
   Pick one and make the picture match.
2. **Framing.** The screenshot contains both panels of Jimmy's own before/after — the
   studio shot and a mirror selfie in boxer shorts. Only Jimmy is in it and there is no
   third-party watermark, so rules 1 and 11 hold; but the right panel is not obviously
   broadcast-safe for the channel. The existing `mrbeast_transformation_2023-06-29.jpg`
   is the left panel only. Cropping to the tweet header + text + left panel keeps the
   "real screenshot" quality without the selfie. Owner's call.
3. Not licensed. Screenshot of X's UI showing Jimmy's post, reposted by a third party.
   Editorial judgement, not a cleared right.

No other primary images exist in the thread. The only other `redd.it` URLs in the
archived page are preview/resize variants of the same PNG.

### (c) Community reaction

`dossier/mrbeast/primary/reddit_14mzyb6_comments.json` — 77 comments, 76 with body
text, chronological, each with author, UTC timestamp, depth and permalink. Vote counts
are absent for 74 of 77 because Reddit's permalink partials omit them; **the comments
therefore cannot be ranked by score and must not be described as "top comments".**

Per the brief this is **description context only** — nothing here goes on screen,
because no screenshot of it was obtainable. Three strands actually bear on the film:

- **The word "obese" was contested at the time, immediately.** A long sub-thread argues
  about whether the before photo qualifies. u/kac937 quotes a reply under the original
  tweet — *"showing you with an average physique and claiming it's morbidly obese
  probably isn't the best thing for your young impressionable audience"* — and
  u/sphen_lee answers *"Yeah, it's obese. Not morbid, but he didn't say that in the
  tweet"*. This is contemporaneous evidence that Jimmy's own wording was accurate and
  that the "morbidly obese" escalation came from other people. It is a real,
  independent corroboration of defect 5 in HANDOFF §7 — the pattern of the internet
  attributing numbers to Jimmy that he never said, of which the "40% body fat" figure
  (actually Airrack's) is the same error one step further on.
- **A body-fat number was already circulating and already wrong.** u/kitterkatty:
  *"Coach Greg Doucette said he thought mr beast called himself FORTY bmi but Greg
  assumed it was closer to 30."* A named third party, hedged, guessing. Worth noting
  in the description as the trail the bad figure travelled. **Not sourceable to Jimmy.**
- **The dominant reaction is "he's rich, it's easy"** (u/DasherCO, u/Disastrous-Treat0616,
  u/EntrepreneurSafe5854, u/joner888) against a counter-current of *"no matter who it is
  I love seeing someone take control of their health"* (u/CandidGuidance, u/Togodooders,
  u/hypoxiany, u/AdAstra_AI). **Nobody in 77 comments mentions Crohn's disease.** That
  silence is the film's thesis proved in public: in June 2023 the internet read a
  chronically ill man's transformation as a rich man's hobby, because it did not know
  what he was working against. That is usable narration-adjacent context, and it costs
  nothing on screen.

Names are Reddit handles. If any comment is quoted on screen or in the description,
quote it verbatim from the JSON and do not attribute a vote count to it.

---

## What could not be obtained

- Reddit post score and true comment count — reddit.com 403s this machine on all
  routes; the single Wayback capture predates any voting.
- Comment vote counts (74 of 77) — omitted by Reddit's own permalink partials.
- Whether the post's NSFW flag was applied later — a Redlib mirror refused it as NSFW
  in 2026, but the 2023 archived HTML carries no such marker. Unresolved.
- Any usable picture from `fl0xOUzINHg`. There is none, and that is a finding, not a
  gap.

## Artefacts

| Path | What |
|---|---|
| `dossier/mrbeast/sources/fl0xOUzINHg.mp4` / `.info.json` | downloaded; **do not add to the pool** |
| `dossier/mrbeast/primary/reddit_14mzyb6_tweet_screenshot.png` | real tweet screenshot, 1080x1080 |
| `dossier/mrbeast/primary/reddit_14mzyb6.json` | full provenance, conflicts flagged |
| `dossier/mrbeast/primary/reddit_14mzyb6_comments.json` | 77 comments, chronological |
| `work/fl0x_scan/shots.json` | 57 shot boundaries |
| `work/fl0x_scan/sheet_00..15.jpg` | 188-frame coverage sheets, labelled |
| `work/fl0x_scan/dense_00..12.jpg` | 152-frame 0.5 s sheets over the Jimmy regions |
| `work/fl0x_scan/c8s/` | 7,574 1 fps thumbnails of `9IQ_ldV9z_A`, used for the recycling proof |
