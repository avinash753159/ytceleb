# B-roll audit — `library/broll/`

Eyes-on audit of all 44 stock clips against HANDOFF.md rule 9 (**no stand-in
people**), rule 10 (no on-screen credit for stock, so we cannot caption our way
out of an ambiguous shot) and rule 11 (no third-party watermarks or logos).

Method: `ffprobe` for duration/resolution; `cropdetect` at 15%, 50% and 85% for
active area; three frames extracted per clip at 20/50/80% and **every frame
looked at**, plus 40 extra zoom-ins and crop renders to settle the marginal
calls. Machine data is in `manifest/broll_audit.json`.

| class | count |
|---|---|
| **OBJECT** — safe to use freely | **11** |
| **FIGURE** — a person is visible; stand-in risk | **18** |
| **REJECT** — watermark, burned-in text, mismatch, bad encode or duplicate | **15** |

The headline: **11 of 44 clips are honestly usable, and rule 2 forbids reusing
a clip at all — so this library supplies about eleven shots for a twelve-minute
film, six of which are baseball.**

---

## Clips that must never be used, and why

These are ordered by how much damage they would do if they reached a cut.

| clip | why it must never be used |
|---|---|
| `teen_alone_1.mp4` | **The most dangerous clip here.** A teenage boy, ~14–16, looking straight into camera in close-up, in a room. That is a cast stand-in for Jimmy at exactly the age he was diagnosed. Also 1366×720 — neither 1080p nor 16:9 — at 1264 kbps. |
| `baseball_kid_1.mp4` / `baseball_kid_2.mp4` | A stock child, ~6–8, batting, face fully lit and central; an adult woman pitching to him. This is the literal example written into rule 9. A previous cut was rejected for it. |
| `bb_cand_0.mp4` / `bb_cand_1.mp4` | **Byte-identical duplicates** of `baseball_kid_2` / `baseball_kid_1` (matching md5). Same child actor, and a duplicate under a second filename defeats the no-reuse registry. Delete or alias them. |
| `walking_alone_2.mp4` | A casting-grade medium close-up of a young white man, ~22–28, blond, right age and colouring. Under step-count narration this reads as a deliberate re-enactment of Jimmy. |
| `bedroom_dark.mp4` | I brightened the 50/80/95% frames: there is a **figure on the bed with a bare torso and a rope or chain around the arm**. The Pexels source is *“a woman chained to a bed during a horror movie scene.”* It is keyed to the beat “fix sleep first”. Also 720p at 850 kbps over near-black, which will band and block. |
| `empty_gym2_1.mp4` | **This is the basketball court that got a cut rejected.** Filename says empty gym; the footage is a school basketball court with balls bouncing. Jimmy played baseball — a basketball court has no honest place in the film at all. Also 2048×1080. |
| `editing_desk_1.mp4` / `editing_desk_2.mp4` | The *“stock video editor where his channel belonged”* precedent, plus independent defects: `_1` plays a third-party news broadcast with a channel bug on the monitor; `_2` shows a large, fully identifiable **child** on the monitor plus a Windows taskbar and a Samsung bezel logo. |
| `hospital_1.mp4` | A female patient’s distressed face, near-full-frame at 80%, in a wheelchair. Rule 13 forbids implying clinical imagery is Jimmy; a face this size says it louder than a caption would. Cropping in exposed **three more faces** (receptionist, masked staff). |
| `bedroom_night_1.mp4` | An extreme close-up portrait of a face on a pillow. There is no part of this frame that is not face or pillow. |
| `young_gym_1.mp4` | **“GYMSHARK”** printed large and legible across the chest in every frame, an LED video light and tripod from the shoot visible in frame, and a filename mismatch (Pexels title: *“a man… working on a computer”*). |
| `gym_dumbbell.mp4` | A large, unmistakable **Nike swoosh** on the chest at 50% and 80%. Independently a high stand-in risk. |
| `young_lifting_1.mp4` | Legible slogan banners across the background — *“DON’T STOP WHEN YOU’RE TIRED, STOP WHEN YOU’RE DONE”*, *“TRAIN HARD”*. Filename mismatch: it is a garage gym with dirt bikes in it. |
| `clock_calendar_1.mp4` / `clock_calendar_2.mp4` | Payroll-explainer motion graphics with **“DECEMBER 14”** and **“PAYROLL”** burned in over stacks of dollar bills. Nothing to do with this film. Also near-identical to each other, so a dedupe hazard too. |
| `food_plain_1.mp4` / `food_plain_2.mp4` | Keyed *“plain chicken rice meal”* for the food-restriction beat; the footage is **deep-fried chicken** with dumplings and braised egg. That is roughly the opposite of a Crohn’s-safe diet. Recoverable only by re-keying and never using it over restriction narration. |
| `empty_gym2_2.mp4` | Keyed “gym at night empty”; it is a **fencing training hall**. The mildest mismatch here — the footage is clean and person-free — but with no captions allowed you cannot tell the viewer what it is, and it must never be drawn as a gym. |
| `bb_cand_9.mp4` | Looks like a harmless wide of a real amateur game. It is not: zoomed in, the central figure at 50% and 80% is a **teenage batter in an oversized #17 jersey, back to camera**. Over “a kid who played constantly,” that boy *is* young Jimmy, face or no face. |

---

## The safest clips in the library

Ranked. These are the ones I would build on.

1. **`bb_cand_2.mp4`** (19.8s, 1080p, 5305 kbps) — two bats, a batting helmet, a
   glove and a pile of scuffed baseballs against a chain-link fence, golden
   hour. Verified sharp at 1:1 pixels. This is the correct answer to “young
   Jimmy played baseball” and the best single clip here.
2. **`hospital_2.mp4`** (21.0s, 1080p) — an empty hospital corridor, gurney and
   folded wheelchair at the far end. The **only** honest clinical image in the
   library. Its low 1577 kbps flagged, so I checked it at 1:1: clean, no
   macroblocking, low only because the shot is static.
3. **`walking_treadmill.mp4`** (9.8s, 1080p, 6209 kbps) — feet and lower legs
   only, no face, no torso: a true anonymous-body-part shot and exactly what
   rule 9 permits. The only honest movement clip here.
4. **`baseball_field_2.mp4`** (8.4s, 7740 kbps) — aerial of an empty field at
   sunset. Cleanest encode in the library. Clears the 8-second bar by 0.4s.
5. **`bb_cand_3.mp4`** (23.0s) — macro of baseballs, glove and bat handles in
   grass. The tight insert that pairs with bb_cand_2’s wide.
6. **`bb_cand_8.mp4`** (27.2s, 5269 kbps) — high aerial of a diamond; distant
   figures are unidentifiable texture.
7. **`gym_empty.mp4`** (13.0s) — the real empty gym: bench, loaded rack,
   dumbbells. Carries in-scene “SO FITNESS” branding (see below) and a heavy
   purple grade to neutralise.

---

## OBJECT — 11 clips, safe to use

| clip | dur | size | watermark / logo | honest use | notes |
|---|---|---|---|---|---|
| `bb_cand_2` | 19.8s | 1920×1080 | none | **Origin** — the equipment: bats, helmet, glove, balls on a fence | Best clip in the library |
| `bb_cand_3` | 23.0s | 1920×1080 | none | **Origin** — macro insert of balls and glove | Clean |
| `bb_cand_8` | 27.2s | 1920×1080 | none | **Origin** — aerial diamond, chapter establisher | Distant figures read as texture |
| `bb_cand_4` | 18.7s | 1280×720 | none | **Origin** — top-down over a ball complex | 720p, 2107 kbps, soft when zoomed. Never under narration about a single boy — the specks would then be read as him |
| `baseball_field_1` | 12.6s | 1920×1080 | **yes, in-scene** — outfield ad boards legibly read “Taco Time”; scoreboard reads “Home of the LUMBERJACKS”; a “355” marker | **Origin** — the field he played on | Use from ~6s on, or crop (0.30,0.35,1.00,1.00) to drop the sponsor wall |
| `baseball_field_2` | 8.4s | 1920×1080 | none | **Origin** — empty field at sunset; also the origin chapter’s out | Cleanest encode here |
| `gym_empty` | 13.0s | 1920×1080 | **yes, in-scene** — “SO FITNESS” embossed on the bench pad, “SO FIT…” on two rack uprights, a “TRAIN HARD / NO … GAIN” banner | **Training** — the empty gym; also the chapter’s close | Frame on bench and floor, e.g. (0.15,0.40,0.70,1.00), to avoid the branding. Heavy purple grade |
| `walking_treadmill` | 9.8s | 1920×1080 | belt logo, motion-blurred and illegible | **Training** — walking, steps, daily movement | Legs read as a woman’s and the footwear is a flat sandal, which an attentive viewer will clock |
| `hospital_2` | 21.0s | 1920×1080 | small ceiling “EXIT” sign, benign | **Illness** — the corridor, diagnosis, treatment | The only honest clinical image here. Flat, needs a grade |
| `clock_time` | 9.5s | **1920×1440 (4:3)** | none | **The machine** — protected time, a clock running | **Not 16:9.** Must be centre-cropped to 1920×1080; pillarboxing leaves 75% active, under the 85% bar. The hands run **backwards** (reversed time-lapse). Pastel-pink lifestyle styling, tonally wrong |
| `calendar_pages` | 10.3s | 1280×720 | the word **“october”** is printed large and legible on the calendar in shot | **The machine** — day count, a calendar | Pins the film to October. 720p, 1408 kbps, autumn food-blog styling. Weakest of the usable set |

---

## FIGURE — 18 clips, stand-in risk

“Reads as Jimmy?” is the operative question, and **it does not require a face.**
Rule 9 forbids anything *cast as him*: a lone man walking, framed as the
subject, over step-count narration is a stand-in even shot from behind.

The **crop-resolution rule** used below: to fill a 1920×1080 frame without an
obvious upscale, a crop needs to be roughly ≥1280×720 (≤1.5× blow-up). Almost
every face-free crop in this library is a thin horizontal strip, so it passes
geometrically and fails on resolution. Every crop below was actually rendered
and looked at.

| clip | who is in it | reads as Jimmy? | crop rescue |
|---|---|---|---|
| `man_tired` | Male ~28–35, dark beard, asleep face-down on an office desk; face in profile at 50/80% | **Yes.** Right age, collapsed at a desk, under “the least energetic person you’ll ever meet.” Also a corporate-office cliché — desk phone, business shirt — wrong for MrBeast | **Geometrically yes, resolution no.** `(0.00,0.62,1.00,1.00)` is head-free at 20%, 50% *and* 80% — verified — showing a desk phone, coiled cord, keyboard and chair. But it is 1920×410 → 2.6× blow-up. A 16:9 sub-box `(0.00,0.55,0.60,1.00)` = 1152×486 still needs 1.9× |
| `baseball_kid_1` | Boy ~6–8, face lit and central; adult woman pitching | **Yes — the literal example in rule 9** | **No.** Both faces are large and central at every point; the only face-free region is ~350×240px |
| `baseball_kid_2` | The same boy, tighter | **Yes** | **No.** He fills the frame throughout |
| `bb_cand_5` | One adult male ballplayer, full body, face not resolvable | **Yes.** A lone ballplayer under origin narration is him even without a face | **Geometrically yes, resolution no.** `(0.62,0.00,1.00,0.85)` at t≈4.5–9s is clean empty bleachers and backstop (verified clean at 5.3s; **not** clean at 2.1s — a shoulder at the right edge). 730×918 → the 16:9 slice inside is 730×411 → 2.6× |
| `bb_cand_6` | Adult male ~25–35, **face fully visible and sharp**, adjusting batting gloves | **Yes** | **No.** Centre-frame throughout; the only person-free region is 672×432 and sits beside a “Cubs”-style jersey wordmark |
| `bb_cand_7` | The same actor, full body, face visible | **Yes** | **No.** Tested `(0.28,0.72,0.70,1.00)` hoping for a bat on the dirt — rendered and looked: his legs and shoes dominate and the bat is a sliver at the far left |
| `bb_cand_9` | Real amateur game. Foreground catcher, back turned. **Mid-ground: a teenage batter, oversized #17 jersey, back to camera** | **Yes — high.** I first read this as a harmless crowd wide, then zoomed the 50/80% frames. That boy is young Jimmy to the viewer | **No.** Tested `(0.00,0.35,0.45,1.00)` for bare home plate — rendered and looked: the batter is inside that box at 50%, and has moved to x≈0.75 by 80%. No fixed box excludes him for a whole shot |
| `teen_alone_2` | Boy ~11–14, red hair, freckles, ukulele on a bed; face visible throughout | **Yes** | **Yes but pointless.** `(0.28,0.55,0.95,1.00)` at 13.1s is hands on a ukulele, face-free — verified — but 1286×486 (2.2×), and a teenager’s hands on a ukulele illustrates nothing in this film |
| `young_gym_2` | Male ~25–30, long hair, tying it up in a locker room; face partly readable | **Yes.** A man of Jimmy’s age getting ready in a locker room, over training narration, is a re-enactment | **Geometrically yes, resolution no.** `(0.00,0.42,1.00,1.00)` at 8.9s and 14.2s is head-free — lockers, bench, backpack, a genuinely usable object shot — verified twice. But the source is 720p, so the region is 1280×418 → 2.6× |
| `young_lifting_2` | Male ~25–30, **face in close-up looking up at the bar**, bench pressing | **Yes — high.** Right age, build, activity, face to camera. A body double | **Geometrically yes, resolution no.** `(0.00,0.00,1.00,0.40)` at 8.6s is the textbook rescue — two hands gripping a barbell, no face — verified. But 1920×432 → 2.5×. Keeping 720 lines `(0.00,0.00,1.00,0.667)` puts his face back in the box; verified |
| `gym_lifting` | Man ~60–70, grey hair, bench pressing, face visible. A second person, defocused, enters at 80% | Not as Jimmy — forty years too old — but a random elderly man bench pressing under narration about a 27-year-old is its own credibility problem, and it is still a face | **The best of a bad lot.** `(0.35,0.00,1.00,0.40)` at t≈5.5s gives hands on the bar and a green “22LB” plate, no face — verified (at 0.30 the top of his head clips the corner). Window ≈4.5–7s only; a bystander enters the box at 80%. 1248×432 → 2.5×, so it will look soft |
| `gym_barbell` | Adult **woman**, barbell back squats. Face turned away at 20/50%; at 80% the camera is on her hips and buttocks | No — plainly a woman. But the 80% framing is fitness-glamour and would be embarrassing in this film | **Partial, not worth it.** `(0.00,0.00,1.00,0.45)` at ≈3.9s gives bar-on-traps and hands, no face — verified across all three points, only the 3.5–4.5s window works. 1920×486 → 2.2×. Also **7.85s, under the 8-second bar** |
| `walking_street` | Male from behind, walking away, backpack. No face | **Yes.** Framed as the subject, over step-count narration | **Geometrically yes, content irrelevant.** `(0.00,0.00,0.30,1.00)` at 5.0s is a clean brownstone facade, autumn foliage, iron railing, no person — verified. A 16:9-ish box `(0.00,0.28,0.42,1.00)` = 806×778 needs only ≈1.4×, the **only crop here that nearly passes** — but the film has no beat that needs a New York brownstone |
| `walking_alone_1` | Male from close behind, backpack. No face | **Yes** | **No — tested and failed.** `(0.00,0.00,0.28,1.00)` rendered and looked: the background is entirely out-of-focus bokeh mush. There is nothing to crop *to* |
| `walking_alone_2` | **Young white male ~22–28, blond, face in prominent close-up** | **Yes — the worst risk after `teen_alone_1`** | **No.** He is the frame |
| `bedroom_night_1` | Extreme close-up portrait, face on a pillow, ~25 | **Yes** | **No.** No region of this frame is not face or pillow. Also 2048×1080 |
| `bedroom_night_2` | Bearded male in bed, overhead; face visible at 20/80%. At 50% only duvet and one hand | Only in the face windows | **No crop needed — a *time* window rescues it.** Use **9.5–12.5s only**: duvet and a hand, no face, verified at 10.6s. A hand on a duvet is an anonymous body part and clears rule 9. Do not extend past ≈13s. The closest thing the library has to a “fall” image, and still a compromise: it is a stranger’s bed |
| `hospital_1` | Female patient’s face near-full-frame at 80%, wheelchair, masked nurse — **plus three more faces** revealed by cropping | **Yes**, and rule 13 forbids it outright | **No — tested and failed.** `(0.00,0.00,0.32,1.00)` at 50% and 80%, rendered and looked: the patient is still in frame at the right edge in both, and the crop exposes the receptionist and masked staff |

---

## Technical flags

**Under 8 seconds:** `gym_barbell` (7.85s) only. `baseball_field_2` (8.42s) and
`hospital_1` (8.27s) are the next closest — with rule 4 capping shots at ~6s
and rule 3 banning loops, these leave almost no window latitude.

**Not 16:9:**

| clip | size | ratio | consequence |
|---|---|---|---|
| `clock_time` | 1920×1440 | 4:3 | Must be centre-cropped; pillarboxed it is 75% active, under the 85% bar |
| `teen_alone_1` | 1366×720 | 1.897 | Already rejected |
| `bedroom_night_1` | 2048×1080 | 1.896 | Needs a 6.7% horizontal crop |
| `empty_gym2_1` | 2048×1080 | 1.896 | Already rejected |

**Vertical video:** none.

**Letterboxing / pillarboxing:** none. `cropdetect` flagged only
`editing_desk_1` at 48.1% active, and that is a false positive — I brightened
the frame and the picture genuinely reaches all four edges; it is an unlit
room, not bars. Every other clip measures 100%.

**Sub-1080p sources:** `baseball_kid_2`, `bb_cand_0`, `bb_cand_4`,
`bedroom_dark`, `calendar_pages`, `young_gym_2` (1280×720) and `teen_alone_1`
(1366×720). No clip shows evidence of being an upscale.

**Worst encodes** (bits per pixel per second): `clock_calendar_2` 0.34,
`clock_calendar_1` 0.38 (flat graphics, expected), `bedroom_dark` 0.92 at 720p
over near-black — will visibly band, `young_gym_2` 1.15, `teen_alone_1` 1.29.
`hospital_2` measured a low 0.76 but was checked at 1:1 and is clean.

**Exact duplicates** (matching md5 — a hazard for the no-reuse registry):
`bb_cand_0` = `baseball_kid_2`, `bb_cand_1` = `baseball_kid_1`.
Visually near-identical pairs: `clock_calendar_1`/`_2`,
`food_plain_1`/`_2`, `bb_cand_6`/`bb_cand_7` (same actor and location).

**In-scene third-party marks on otherwise-clean clips:** `baseball_field_1`
(“Taco Time” ad board, “Home of the LUMBERJACKS” scoreboard) and `gym_empty`
(“SO FITNESS” on the bench and racks, a “TRAIN HARD” banner). Neither is an
overlay, but both are legible on a large screen. Reframe or crop.

---

## Where the library has a gap

Mapped against the five chapters. Rule 2 means a clip can be drawn **once**, so
the count of usable clips is the count of available shots.

### 1. The illness — fatigue, hospital, treatment, food restriction
**Honest OBJECT footage: one clip.** `hospital_2`, an empty corridor.

- **Treatment / infusion: nothing. Zero clips.** No IV line, no drip, no pills,
  no blister pack, no infusion chair, no wristband. The film’s thesis turns on
  “his own immune system was attacking him”, and there is no image of the
  treatment anywhere in this library.
- **Food restriction: nothing honest.** Both `food_plain` clips are deep-fried
  chicken — the opposite of the beat.
- **Fatigue: nothing OBJECT-class.** `man_tired` is a face. There is no unmade
  bed, no untouched plate going cold, no 3am desk.

### 2. The origin — baseball, equipment and fields only
**Well covered: six OBJECT clips** (`bb_cand_2`, `bb_cand_3`, `bb_cand_4`,
`bb_cand_8`, `baseball_field_1`, `baseball_field_2`). The only chapter that is
actually resourced. Caveat: `baseball_field_1` carries sponsor signage.

### 3. The machine — editing desks, clocks, calendars, uploading late at night
**Nearly empty, and the two clips that exist are both compromised.**

- **Editing desk / the work itself: zero honest clips.** Both `editing_desk_*`
  are rejects, and were the cause of a prior rejection anyway. There is no
  keyboard, no monitor glow, no timeline, no render bar, no upload progress.
- **Clocks: one**, `clock_time` — 4:3, pastel pink, hands running backwards.
- **Calendars: one**, `calendar_pages` — with the word “october” burned into
  the scene. The other two calendar clips are payroll graphics.
- **Uploading late at night: zero.** No screen glowing in a dark room.

### 4. The training — gyms, barbells, walking, steps
**Two OBJECT clips**, `gym_empty` and `walking_treadmill`.

- **No person-free barbell, plate or rack insert exists.** Every barbell in
  this library has a person attached to it. The nearest thing is a 2.5×
  blow-up of a crop of `gym_lifting`.
- **No person-free outdoor walking.** All three walking clips are FIGURE. No
  shoes on a sidewalk, no step counter, no watch face.

### 5. The fall — a dark bedroom, sleep
**Zero honest OBJECT footage.** `bedroom_dark` is horror footage of a bound
woman; `bedroom_night_1` and `_2` are faces in beds. The only option is the
9.5–12.5s duvet-and-hand window of `bedroom_night_2`, which is one shot, in
a stranger’s bed. There is no empty bed, no dark room, no window at night, no
bedside lamp, no clock in the dark.

### What still needs fetching, in priority order

1. **Sleep / the fall** (currently zero): an empty unmade bed in low light; a
   dark bedroom with a window; a bedside lamp going off; a phone face-down on
   a nightstand, screen glowing.
2. **Treatment** (currently zero): an IV drip and infusion line with no
   patient; a pill organiser or blister pack; a clinical scale; a blood-draw
   tray; an empty waiting-room chair; a hospital wristband on a table.
3. **The machine / late-night work** (currently zero): hands on a keyboard —
   permitted, they are anonymous body parts; an editing timeline scrubbing with
   no branded UI; an upload or render progress bar; a wall clock reading 3:00;
   a desk lamp and monitor glow in a dark room.
4. **Food restriction** (currently zero honest): a plain grilled chicken breast
   and rice; a measured, bland meal; a full plate left untouched.
5. **Fatigue** (currently zero honest): a cold, full cup of coffee; an unmade
   bed in daylight; an untouched desk.
6. **Barbell and walking inserts** (currently zero person-free): hands chalking
   and gripping a bar; plates being loaded; a dumbbell rack; running shoes on a
   sidewalk; an unbranded treadmill console.
7. **Origin top-ups** (optional, already the strongest chapter): a batting cage;
   a glove hanging on a chain-link fence.
