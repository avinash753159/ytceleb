# Session log — what was tried, what failed, and why

Companion to `HANDOFF.md`. That file says what to build. This one says what
has already been attempted so the same ground is not walked twice.

Written for whoever picks this up next. It is deliberately blunt about the
mistakes, because most of the rules in `HANDOFF.md` exist because of one.

---

## Phase 1 — Inherited state

A previous session (Codex) had produced `THE_DISEASE_THAT_BUILT_MRBEAST_V3.mp4`
plus a V11 documentary pipeline. The owner's verdict: *"this is complete
shit"*. Two problems, both real:

- the script read like a fact-checker's notice, hedging every sentence
- the picture was long podcast clips with `SOURCE:` drawtext over them

---

## Phase 2 — Effects library (kept)

Built and smoke-tested 17 effects: eased Ken Burns, multi-layer parallax,
freeze-punch, split-squeeze, kinetic captions, archive treatment, speed ramps,
whip pan, film dissolve, source labels.

**Failures worth knowing:**

- `boxblur` evaluates its radius **once at filter-config time**. There is no
  per-frame `n`. Animated blur has to be rendered frame by frame.
- A gap in a PNG sequence makes ffmpeg's image2 demuxer stop dead. A whip pan
  silently came out 0.10s instead of 0.30s because one frame near EOF failed
  to write. Every frame is now verified and the encoded length asserted.
- **Depth parallax works only on locked-off shots with a clear subject.**
  Handheld motion-blurred footage produces a mush depth map. There is an
  automatic suitability gate in `pipeline/parallax.py`; its threshold was
  calibrated on three real frames after the first guess (sharpness-based)
  rejected the two good ones. Only *edge alignment* discriminated.
- The operator rejected the standalone white `flash_cut` outright. Replaced
  with `flash_hit()`, a 2-frame bloom over the picture.

---

## Phase 3 — Audio, V3 → V6 (finished, approved)

Rewritten three times.

- **V3** — rejected. No single spine; narration echoed the clips; **the first
  music cue began at 58.2s** and the cold-open act had no cue at all.
- **V4** — one spine, scored from 0:00, echo checker added.
- **V5** — thesis sharpened after recovering new material (below).
- **V6** — added a real Crohn's explainer, removed self-repetition.
  **APPROVED. Do not rebuild.**

**The research failure that mattered most:** every earlier pass concluded
"no verified diet exists in the public record". That was wrong. Rogan #1788 at
~87–91 min contains a full first-person account — Remicade every eight weeks,
corn and spicy food as triggers, *"I'm probably one of the least energetic
people you'll ever meet"*, *"I'm dead. I just lay in bed all day."* Nobody had
transcribed it. It is now the emotional core of the film.

**The owner had to supply the single most important asset.** His 29 June 2023
post — *"Woke up and realized I was obese…"* — was flagged as REQUIRED in the
research file from V1 and never fetched. It arrived only when he pasted the
link.

**Tools built here:** `echo_check.py` (narration restating an adjacent clip),
`repetition_check.py` (narration repeating itself — found "fifteen" in six
separate blocks).

---

## Phase 4 — Picture, V6 → V7 → first-minute × 5

This is where nearly all the pain was.

### Sourcing errors

- **46% of the first full cut was other creators.** Airrack 38 shots,
  Chris Hemsworth 21. I had picked sources by *topic* ("gym footage") instead
  of by *subject*. Frame-checking twelve Airrack windows found no Jimmy-only
  window at all; Hemsworth's video is his gym, his crew, his burned-in
  graphics. **Both dropped entirely.**
- MrBeast's own produced videos are wall-to-wall stunt graphics. That is where
  `BYRON BAY, AUSTRALIA`, a pain-o-meter, `v bucks?`, a Google Earth map, a
  Bandicam watermark and a **dog** all came from. Built
  `clean_windows.py` (OCR) to reject overlay text — but tuning matters: the
  first rule rejected any lower-third text and killed every usable window,
  because product labels and studio branding tripped it. The working
  discriminator is sentence-likeness (overlays are phrases; logos are single
  words).
- **8.3 hours of Jimmy existed and about 11 windows were being recycled.**
  Fixed by `jimmy_pool.py` → `verify_pool.py`: 41 candidates scanned,
  **26 verified by eye**, 15 rejected including two pure green frames.

### Sync disaster

Picture was timed from **Whisper transcript timestamps**. Whisper merges long
pauses, so it reported the athlete line starting at 30s when the edit says 46s.
Baseball played over a silent title break. Always read timings from the EDL.

### Loops

`-stream_loop` was added as a "safety net" for clips shorter than their beat.
It played the same five seconds two or three times. The owner spotted it
immediately. **Deleted. Banned.**

### Duration and cache bugs

- Windows seeking past EOF produce zero-frame pieces (killed a render at shot
  015). Archive files are short — `AKJfakEsgy0` is 127s.
- Frame rounding across 130 shots accumulated ~3.8s; the first fix padded with
  a **frozen frame**, giving an 18s stall. Now the final shot is re-rendered
  longer from live footage — to its **own path**, because overwriting the
  cached piece made the next run fail its own duration check.
- Killing a render leaves truncated pieces; 30 corrupt cached shots were found
  and re-rendered on one pass.

### Performance — three wrong calls in a row

Each time I claimed a speedup without measuring one.

1. Thread pool for OCR — **slower** (8s/window vs 4.6s). RapidOCR does not
   release the GIL.
2. Process pool — still slow. onnxruntime defaults to all-core intra-op, so
   8 processes × 20 threads thrashed 20 cores. Fixed with
   `OMP_NUM_THREADS=1`.
3. 14 ffmpeg workers × ~20 x264 threads each — starved the machine so badly
   PowerShell could not start a thread. Fixed with `-threads 2` and
   `workers = cores ÷ threads`.

**Measured result: 2.2 → 18.5 shots/min (8.4×).** Benchmark first, always.

### False alarms worth not chasing

`freezedetect` at −60dB flags a slow Ken Burns on a photograph. Measuring
actual pixel delta separated three false alarms (39–71) from one genuine
frozen slate (0.23). A rendered card on flat dark ground needs a ~34% push to
register at all; a photograph needs 12%.

---

## Phase 5 — First minute, five revisions

| Rev | Rejected because |
|---|---|
| 1 | looping artefact; same photo three times; a basketball court captioned "empty gym" |
| 2 | Pexels credits on screen; a guitar clip; a stock child cast as young Jimmy; a stock video editor where his channel belonged |
| 3 | before/after composite reused both photos that were also shown alone |
| 4 | picture timed off the transcript — baseball 12s early over silence |
| 5 | current. Post cards are **hand-drawn reconstructions, not real screenshots** — the outstanding item |

---

## Phase 6 — Picture V8: the rebuild

### The two things that were asked for, and what they turned out to be

**Real post screenshots.** `platform.twitter.com/embed/Tweet.html?id=<ID>&theme=dark`
renders X's own markup with no auth and no key, and headless Chrome pulls the
real photos from `pbs.twimg.com`. A browser User-Agent is mandatory
everywhere. One geometric limit worth knowing before anyone "fixes" it: the
embed hard-clamps the card to `max-width:550px`, and X crops a portrait photo
to 1:1, so the card's aspect approaches `w/(w+198)` and can never exceed 1.0.
`post_gains` therefore occupies 39% of frame width, not the 60% asked for;
forcing it wider shrinks the timestamp to ~9px. `post_obese` is 62% because
its photo pair is landscape.

**The unscanned 115-minute Colin & Samir.** Now scanned. **It contains zero
illness content** — no Crohn's, gut, immune, Remicade, flare, bathroom,
weight, fatigue, energy, gym or workout, across all 115 minutes. It is a
machine-and-origin source only. That is a real answer, not a failure to look.
It did yield 28 verified Jimmy windows in a white warehouse with a cream
Street Fighter II jacket — a set the film did not previously have.

`fl0xOUzINHg` (brockashby) is **worthless and should stay excluded by
construction**: ~85% is the presenter's own face, and every Jimmy frame is a
caption-burned, lower-generation copy of `9IQ_ldV9z_A` footage we already
hold — proved by dHash-matching 12 probes against all 7,574 seconds of it at
Hamming 2-9. Its only value is that its caption track indexes where the
fitness answers sit inside the original.

### Thresholds guessed vs thresholds calibrated

Three times in one session a threshold picked by intuition silently destroyed
real data. Each was found only by testing against labelled frames.

1. A flat-frame filter set at luma std < 14 and max-channel > 0.42 rejected
   **every usable frame in the film**: the Rogan studio is a red curtain, so a
   genuine Jimmy single measures max-channel 0.505-0.532, and a dark single
   measures std 13.7. Real frames occupy std 13.7-62 / 0.34-0.53. Correct
   values are std < 6 and max-channel > 0.72 — far outside the real range, not
   beside it. Verified against a synthetic green frame (std 0.0, G 0.99).
2. The screen-share panel detector was set at a luma ratio of 1.9 and reported
   the contaminated region as clean. Measured at timestamps labelled by eye:
   panel absent reads 0.70-0.73, present reads 1.67-1.73. Threshold 1.2.
3. Candidate dedupe at Hamming 14 threw out 125 of 140 windows per interview.
   Inside one interview almost every frame is the same set, so a strict bar at
   the *candidate* stage starves a film that needs ~175 shots. It belongs at
   the allocator, where it can be proximity-weighted; candidate stage is now 9.

### The Rogan studio has a monitor in shot

Rogan pulled the Crohn's & Colitis Foundation website up on a studio monitor
while they discussed the illness, and it sits in the lower right of frame. It
**comes and goes mid-window**: the midpoint frame of the "it's just life"
window is clean and the panel arrives 2.3s later. A one-frame verdict ships
it. `work/_panel_map.py` maps it; contaminated spans are 5349.5-5360.5,
5363.5-5365.25 and 5417.5-5420.5.

Consequences: bite 18 ("I'm dead. I just lay in bed all day") is unrescuable —
the panel overlaps him horizontally, so no crop removes it. Bite 71 ("it's
just life", the film's closing line) survives only as a hand-trimmed 2.2s
window ending at 5417.9. Elsewhere the same monitor carried YouTube pages, a
Wikipedia page, the MrBeast Bar site and clip playback — all rejected.

### What the eyes-on identity pass actually caught

Across 268 candidates, machine dedupe had approved: **9 Joe Rogan singles, 19
Steven Bartlett singles, 2 two-shots, a Samir single, a Colin single, and nine
frames of a MrBeast company executive** (dark beard, navy tee, dark stage)
that read as clean Jimmy singles at 320x180. Plus a run of six frames with an
unnamed crew member standing beside seated Jimmy, which looked solo in
thumbnail form.

Two defect classes nobody had written down:

- **Defocused foreground body parts.** Four frames are perfect Jimmy singles
  except for another person's out-of-focus hand or shoulder in the near
  foreground — invisible at sheet scale, unmistakable at 5x. Discriminator: if
  a hand is Jimmy's own you can trace an unbroken black sleeve back to his
  torso; if you cannot, and it sits beyond his mic boom on a different focal
  plane, it is the other man's.
- **Contact-sheet padding read as a source frame.** `xstack` fills unused grid
  cells with flat green. The "two pure green frames" of the previous pass may
  well have been this, not decoded video. Sheets now pad with black.

**Verdicts are keyed by `sid@t0`, never by sheet index.** `verify_pool.py`
hard-coded tile indices, so adding a source re-sorted the thumbnails and
silently re-pointed every verdict at a different frame.

### `cWEUE8X7p-k` (Beast Games BTS) yields nothing — drop it

0 of 40 windows usable. Every frame is a crowd of contestants, a crew shot, a
set wide, an aerial, or carries MrBeast's own burned-in production furniture:
DP name cards, `$5,000,000`, `36 HOURS BEFORE PRODUCTION`, Feastables signage.
The problem is the source's nature, not the sampling. `NdjcGrpNSF4` yields 3,
all one sit-down — treat as one look, not three shots.

### The old b-roll library is mostly unusable, and one clip was alarming

Audited all 44 clips in `library/broll/`: **11 OBJECT, 18 FIGURE, 15 REJECT.**

- **`bedroom_dark.mp4` is a horror-film clip** — brightened, there is a figure
  on the bed with a bare torso and a rope or chain around the arm; the Pexels
  source is "a woman chained to a bed during a horror movie scene." V7 used it
  for "I've got to fix sleep first."
- `teen_alone_1.mp4` is a teenage boy looking straight into camera, at exactly
  the age Jimmy was diagnosed — the literal thing rule 9 forbids.
- `bb_cand_0`/`bb_cand_1` are **byte-identical duplicates** of
  `baseball_kid_2`/`baseball_kid_1`: the same child actor under a second
  filename, which defeats a no-reuse registry keyed on path.
- `young_gym_1` has GYMSHARK across the chest; `editing_desk_2` has a fully
  identifiable child on the monitor; `hospital_1` is a patient's distressed
  face.
- Crops rescue almost nothing: the face-free crops are thin horizontal strips
  needing 2.2-3.6x blow-up, which fails the no-upscale bar.

Because a clip can be drawn once, 11 OBJECT clips is 11 shots for a
12-minute film, six of them baseball. Gaps were total for sleep, treatment,
plain food, fatigue and the machine. `pipeline/fetch_broll3.py` fetches 120
object-first clips across 15 groups into `library/broll3/`, which is what V8
draws from. **`library/broll` is not drawn from at all.**

### Assets that would have shipped as evidence but are not evidence

- `dossier/mrbeast/medical/contact.jpg` was in the clinical set. It is a
  **contact sheet of the other medical images**.
- `severe_colitis.jpg` is photographed beside a ruler printed
  `(800) 383-7796`; `crohn_resected.jpg` carries a specimen label reading
  `1691 ILEON TERMINAL, CAECUM, COLON ASCENDANT`. Both croppable, neither
  usable raw.
- `mechanism.png` is a fully labelled plate. Cropping out `Normal` and
  `Crohn's Disease` matters twice over: a labelled figure reads as homework,
  and those two words are a **narration echo** — the script says exactly that
  over it.
- The two `mechanism.png` crops read as the same pink villi illustration 15
  seconds apart. `mech_right` was cut; the resected specimen shows a visibly
  thickened wall, which is better evidence for that sentence than a second
  diagram.
- Both archive videos are dated **4 October 2015** (his own title card, and a
  Windows taskbar clock reading 10/4/2015). The pool labelled them "2013
  ARCHIVE" — a false date, one step from being burned into a lower-third.
- The Crohn's & Colitis Foundation page serves a **"3X MATCH / Gifts TRIPLED /
  Donate" modal**. Removing every `position:fixed|sticky` element to kill it
  produced a blank white frame, because the page's own content wrapper is
  sticky. Anchor the crop on the measured `h1` box instead.

### Chronology worth knowing before anyone rewrites the origin chapter

In `c8VcUnz3nVc` Jimmy dates the all-in decision to **13**, describes himself
at **15** with no mention of illness, and burns the alternative at ~**18**
(the college-dropout story, never previously mined, at 6193-6311). On Rogan
and Diary of a CEO he links Crohn's at 15 → no baseball → all in on YouTube.
Both are his own accounts. The V6 audio is approved and unchanged, but if the
origin chapter is ever reworked, this source contradicts a strict
illness-caused-the-decision reading.

Two new misattribution risks found in the new sources: `NdjcGrpNSF4` 1297.6
"HE has like 50% more energy than any human I've ever met" is **not Jimmy**
(third-person, about him), and 1321.24 "Tastes cheap. I would never eat that"
is Feastables competitor product-testing, **not** Crohn's trigger foods.

### Frame drift is solved by allocating frames, not seconds

Rounding across 130 shots previously accumulated ~3.8s, and the first fix
padded with a frozen frame, giving an 18-second stall. V8 allocates an integer
**frame count** per shot, makes the counts sum to exactly the audio's frame
count, and copy-trims each rendered piece to its count with `-frames:v N -c
copy`. It never pads: a short render is an error, not a freeze.

### Things that wasted time and should not again

- Piping a long-running Python script through `head` or `tail` kills it with
  BrokenPipeError and looks exactly like a silent success. Redirect to a file.
- Editing a module while a run of it is in flight does nothing — the already
  loaded copy keeps the old thresholds. 133 Rogan candidates were discarded by
  a filter I had already fixed on disk.
- `clean_windows.scan_many`'s worker hardcodes `frames=2` and the shared cache
  key is `file|t0|dur` with **no frame count in it**, so a 2-frame verdict gets
  handed back to a caller that asked for 6. `screen_text.py` keeps its own
  cache keyed with the frame count.
- Sequential OCR ran at 26s per window — nearly two hours for the pool. It is
  a process pool with `OMP_NUM_THREADS=1`, never a thread pool: RapidOCR does
  not release the GIL.
- `ffmpeg` will not accept `#111` as a colour. Six hex digits or it errors.


### The eyes-on fleet was worth more than every machine check combined

Five reviewers took the 29 contact sheets, one chapter each, against the
narration. The machine gate was clean at that point: no reuse, no black, no
static, frame-exact. They still found, between them, three factual failures and
twenty-odd rule breaches. The most important:

- **`severe_colitis.jpg` is a photograph of ULCERATIVE COLITIS**, and
  `CREDITS2.json` states the constraint in its own `use` field: *"Only usable
  if captioned as related IBD, never as Crohn's."* It was on screen full-frame,
  full-colour and uncaptioned under his own Crohn's bite, sixty seconds after
  the film showed the viewer the NIDDK page that distinguishes the two
  diseases. Withdrawn.
- **`card_rest` drew a Monday-to-Friday training split** with weekend rest.
  No split was ever published, his own bite says rest days were *occasional*,
  and the narration seventeen seconds later says "Most videos invent this part.
  Here is only what he has said himself." Cut.
- **`card_time` printed "2-2h ... every night"** with a sleep emoji - a broken
  range, sleep copy grafted onto a training-time card, and no source for 2h at
  all when the bite 55s earlier says an hour and a half. The comment in
  `render_cards.py` shows someone knew it printed garbage and set both values
  equal rather than fixing the component. Cut.
- **`card_steps` said 12,500 starting 0.01s after a bite in which he says
  15,000.** Both figures are his, from different moments; on screen it is the
  film contradicting itself. Cut - the real source, his June 2023 post, is
  already on screen as a document at 26s.

### Rule 9 is stricter than "no faces"

The allow-list classed "anonymous body parts with no face" as OBJECT - my
brief's wording. Reviewers were right that it isn't enough. Hands with painted
nails loading a barbell, a man's legs in brogues on the 12,500-steps beat, two
people's legs in the closing minute: none has a face, all read as a stand-in
performing the activity the narration attributes to Jimmy. **Every `walk` clip
went** - walking footage is legs by definition. Twenty clips withdrawn in total,
also taking legible ROGUE, BODYTONE, SVENSSON, CarFitness and SD FITNESS.

The surviving distinction, written into the allow-list: a hand *operating a
prop* (turning a calendar page) is not a body *performing the activity*. Rule
9's own examples are a child playing baseball and a video editor - performers
standing in for him.

### A free-text note is not a constraint

`broll_allow.json` said, verbatim, *"BUILDER MUST USE THE TAIL"* on a bed clip
whose first nine seconds contain a sleeper's legs and bare foot. The builder
picks its start at 35% of the clip and duly put a stranger's legs on screen at
18s of the film. Safe spans are now a `window: [start, end]` field the builder
honours, not prose it cannot read.

### The cut gate was calibrated on the wrong scale, twice

`select='gt(scene,0.30)'` missed a real camera cut *inside* an interview take -
the angle change scored ~0.09 - and fourteen frames of a different setup
shipped. Dropping to 0.12 then fired on the 2015 webcam's sensor noise and
starved the archive pool inside one rebuild. Measured with `scdet` on both
cases: the real cut scores 8.9 and 61.9, the noisiest archive window peaks at
4.9. The gate is now `scdet=threshold=6`. Two lessons, the same lesson: pick
the metric that separates the populations, then put the threshold in the gap.

### Do not rebuild while a review is running

Three of the five reviewers were reading contact sheets cut from a file I was
overwriting underneath them. One caught it - an ffmpeg read failed with
`moov atom not found`, the mp4 grew by 9.5MB mid-review, and the shot manifest
went from 175 shots to 172 - then dHash-compared all 36 of its tiles against
the newer render to establish that 35 still matched. Freeze the render, cut the
sheets from the frozen file, then review.

### Perceptual-hash thresholds, and why there were four attempts

A 9x8 dHash (64 bits) has **no usable separation** on this material: the
closest genuinely distinct same-interview pair is 9 bits apart while
cross-interview pairs go as low as 7. At 17x16 (256 bits) they separate -
same-set from 17 (p1 26, p5 38), cross-set from 59. Measured over 877 same-set
and 600 cross-set pairs by `work/_hash_calib.py`.

Two further traps: the allocator hashes the pool *thumbnail* while QC hashes
the *rendered* piece, which has been punched in and had an identical credit bar
drawn on it - rendered pairs measure roughly 0.4-0.9x the thumbnail distance,
so the two passes need different numbers on purpose. And a bite's sync window
must be exempt from the proximity rule entirely: two windows of one interview
always hash alike, so the rule would reject the second and force a cutaway that
pretends to be sync.

### Bind order encodes priority

Binding everything in one programme-order pass let a cutaway at 8:00 consume a
DOAC look and then blocked the 10:20 bite's only sync window for resembling it.
Sync binds first, in its own pass: a bite's window is unique to that bite,
a cutaway has 85 alternatives. A cutaway can now be rejected for looking like
a bite, never the reverse.

### Five more small ones

- `ffprobe -count_frames` returns `70,` with a trailing comma for some files,
  so an `isdigit()` test reported 0 frames for good pieces and `exact_frames`
  refused to continue. Parse the first integer.
- Pieces are cached by *shot name*, which is positional. Swap a clip in the
  allow-list and the old render is served forever. Cache on an asset
  fingerprint.
- `esc()` deleted apostrophes, so a lower-third read `INSIDE MRBEASTS YOUTUBE
  MACHINE`. Use a typographic apostrophe, which needs no escaping.
- The credit plate was a fixed 680px box regardless of text; over a bright
  still, short credits left an unexplained grey slab. Size it to the text.
- `bite_windows` computes a window's usable length with a 0.2s margin while the
  builder demanded 0.25s of headroom. A 6.00s window failed a 6.00s request by
  five hundredths of a second and took the Beast Games bite out of sync.


---

## Phase 7 — the owner's review, and the direction reversal

He reviewed all 172 slides in Google Slides and left notes on 37 of them, with
the overarching direction parked in slide 44's note. Read it before doing
anything: `manifest/deck_feedback.json`.

### Two rules he reversed

1. **Rule 9 is relaxed.** Anonymous people MAY appear in stock and MAY perform
   the activity being described. He asked for "a guy eating and having issues"
   and said "use stock footage" ten times. What survives of the rule: no child
   cast as young Jimmy, no other identifiable creator. This reversed a strict
   reading that had just cost 20 clips.
2. **Third-party press imagery is in.** He linked New York Post, Men's Health,
   drvaidji.com and a Tenor GIF and chose "use them - fair use / commentary"
   over sourcing licensed equivalents. Each is credited on screen at the moment
   it appears and again in the description, and the description now says
   plainly that they are third-party and used as commentary.

### The big one: the talking head goes

"All the images where you have his face, which is pretty much all of them up
until 172, you need to change it up." Asked which of the 21 sync shots survive,
he chose: only the biggest moments.

**His face went from 56% of screen time to 8.5%.** Sync survives on ten lines:
the baseball/Crohn's origin, 190-to-139, the symptoms, day 310, the three
things, the upload cost, three months, "it's really killing me", "fix sleep
first", and "it's just life".

That is expressed as a policy at the foot of `picture_plan_v8.py` rather than
sixty hand edits, so it stays readable and reversible: `KEEP_SYNC`,
`SWEEP_FROM`, and a per-chapter palette that rotates across the chapter.
First version rotated per SEGMENT, which sent each chapter's first group 16
draws and its fourth none.

### No more website screenshots

Said four separate ways: "Again it's a website. I did not want this. I actually
want real images of the disease"; "Don't look for the page... real images of
Crohn's disease... or like a 3D rendering, not just websites". All four
document captures (NIDDK x3, Crohn's & Colitis Foundation) are out of the film.
In their place: the drvaidji 3D render he linked, the existing licensed
medical stills, and - his specific request - "five little images of real
images of people with Crohn's disease... flashes in and out for like five
seconds", built as `FLASH` in the plan from the five clinical photographs that
had previously been held back under rule 13.

### Infographics, because the cards were just type

"I want real infographics to be here", "put in images instead of just this
text", "make it as good as possible". Five built (`render_cards_ig_v1.py`):
a scale comparison where 8,726 is a 6px sliver against a full bar for 300
million, a four-tile routine carrying the "no training split was ever
published" caveat, a ten-segment dial for one problem over ten years,
"not motivation -> a second person + a written penalty" with almost no words,
and the contract as a signed document with the AIRRACK'S ACCOUNT chip.

### Bugs the audits caught in my own work

- **14 allow-list entries were stored as bare filenames** rather than
  repo-relative paths. `take_broll` does `if not p.exists(): continue`, so it
  silently skipped every one - the entire `walk` group was dead and the build
  still succeeded. `fetch_broll3.py` writes `"file": dest.name` while
  `fetch_broll4.py` writes the full path; the rule-9 restore copied the former.
- **11 durations were rounded placeholders**, 7 of them overstated, so
  `usable_window` could hand the builder a span past end-of-file.
- `render_flash`'s concat list was written with a literal newline instead of
  `
` - a heredoc escaping mistake that made the whole module unparseable.

### Branding is what kills stock clips, not people

Now that people are allowed, the rejection rate is dominated by legible
third-party marks. One audit lost 5 of 6 editing clips (SAMSUNG on a monitor
chin, a Windows taskbar with Start/Edge/Chrome and the Adobe Pr icon, "DaVinci
Resolve Stu...", "SpotiMate.io" in a media pool, an Apple logo) and 4 of 6
training clips (PANATTA SPORT cast into a plate, TSA on plates, a COVID face
mask that dates the film, graphic lettering across a shirt). Also rejected: a
sticky note reading "Call back / 510-56-2?4? / Elena!" - a stranger's name and
phone number, the same class as the legible personal calendar caught earlier.

### Still open

- **Slide 28's parallax.** He asked for a parallax treatment on a still of
  Jimmy; `pipeline/parallax.py` exists with a suitability gate and is not
  wired in.
- A fresh eyes-on pass is owed on whatever the next build produces.

---

## Things settled, do not relitigate

- **No CelebWorkout logo.** Source credit bottom-left on interviews only.
- **Verified-only claims.** No invented split, sets, reps, calories or meals.
- **The "40%+ body fat" figure is Airrack's, not Jimmy's** — frame-verified.
  Press outlets repeat it wrongly. Marked `rejected_for_jimmy_claim` in
  `manifest/mrbeast_soundbites.json`.
- **Never call it 310 or 602 consecutive workouts** — programmed rest counted.
- **Exercise is not a Crohn's treatment.** Never imply it.
- Clinical imagery: brief, licensed, credited, never implied to be Jimmy.

---

## Reference measured from the documentary the owner admires

`youtu.be/IbWl40xgw0A`, measured by `pipeline/ref_open.py`:

- audio present from 0.00s; first narrated word at 1.24s
- a **31-second music-only title break** before the story begins
- median shot **5.15s / 5.25s / 2.92s** across thirds — slow, accelerating

Copying the 31s break into a 12-minute film was a scaling error; it became a
12-second hole. It is now 4s, placed before the diagnosis.
