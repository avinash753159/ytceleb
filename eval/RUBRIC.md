# The Incredible Rubric — what makes a Celeb-Workout video *incredible*

> **Source of truth.** The machine-readable copy of every weight and anchor lives in
> `pipeline/eval_rubric.py` (the harness reads *that*, never this file). The two MUST
> match — `pipeline/eval.py --calibrate` fails if the scoring drifts. Edit weights
> here and there together.

## What this is

`qc.py` already answers *"is the render broken?"* (gates G1–G8: stray text, reuse,
shot length, black/freeze, loudness, duration sync). This rubric answers a different
question: **"is the video incredible?"** — will people click it, watch to the end, and
subscribe.

**North star = audience outcome.** Every dimension below is a *predictor* of one hard
metric: click-through rate (CTR), 30-second retention, average view duration, or
subscriber conversion. Craft is not scored for its own sake — it is scored because it
is the controllable lever that moves those numbers *before* a video is published.

**The 10 is Patrick Gavia's *The Girl Who Broke Khamzat Chimaev*** (`1T8ZRx5FR4I`,
8.5M views, 25:24) — the channel's declared reference (see the V11 documentary spec).
The channel's own current drafts (Statham V5, Bruce Lee V1, Reynolds) should land
**≈4–6**. If everything scores high, the rubric is broken — the gap is the point.

## Two modes, one 0–10 scale

- **PREDICTIVE** (pre-publish): categories A–D are judged; E is a technical multiplier.
  This is a *forecast* of the outcome metrics.
- **MEASURED** (post-publish): once real analytics exist (category F), F *becomes* the
  score and A–D are kept only as a diagnostic delta — the report emits the
  prediction-vs-actual error so the judge's calibration is tracked over time.

## Composite

```
CraftScore  = 0.25·A(Hook) + 0.25·B(Story) + 0.20·C(Pacing) + 0.30·D(Packaging)
TechFactor  = 1.0 − Σ(failing qc gates) ; hard A/V-drift or black/duration fail clamps ≤0.5
INCREDIBLE  = round(CraftScore × TechFactor, 1)            # PREDICTIVE
INCREDIBLE  = OutcomeScore(F)                              # MEASURED (CraftScore kept as diagnostic)
```

Technical is a **multiplier, not a slice**: a 9/10 craft film with audio drift is not a
9. A broken render kills retention regardless of how good the story is — same "fail
loudly" ethos as `qc.py`.

**Weights are retention-first.** Hook + Packaging = 55% of the craft score because CTR
gates whether the video is watched at all, and 30-second retention is the single biggest
ranking signal YouTube exposes.

---

## Category A — Hook / Cold Open — 25% — *predicts 30-second retention*

The first 30–90 seconds decide the whole video. Judged on the script **and** the opening
frames of the render.

| # | Dimension | Wt | 0 (channel drafts) | 10 (Gavia) | Why it predicts retention |
|---|---|---|---|---|
| A1 | **Withheld promise** | .35 | States the thesis in sentence 3 ("he was always in shape"). | Opens on a concrete unanswered question ("I'll reveal what she whispered") paid off at the very end. | An open loop is the strongest reason a viewer stays; a stated conclusion gives them permission to leave. |
| A2 | **First line opens a loop** | .25 | Generic scene-set / date-and-place. | A sentence you cannot walk away from. | The first line is where 30–40% of the drop-off happens. |
| A3 | **Arresting first frame** | .20 | Logo bug / title card / talking head. | A charged, legible image on frame 1. | Viewers judge production value in <2s; a card reads as "skippable." |
| A4 | **Time-to-hook** | .20 | Branding/intro before any hook. | Zero throat-clearing — hook is beat 0. | Every second before the hook is a second of pure drop-off. |

## Category B — Story & Stakes — 25% — *predicts average view duration*

Is this a story (scenes, stakes, change) or a briefing (facts in a row)? Briefings get
skipped; stories hold the curve. Judged on the script / beat sheet.

| # | Dimension | Wt | 0 | 10 | Why |
|---|---|---|---|---|
| B1 | **Story, not briefing** | .30 | Magazine article read aloud; nothing at stake. | Scene spine; something breaks them and the body is the answer ("the Wound"). | Narrative tension is what carries a viewer across the mid-video sag. |
| B2 | **Named, escalating antagonist** | .25 | No opposition ("he just trained hard"). | Act-1 antagonist replaced by a worse one in Act 2, resolved in Act 3. | Conflict is the engine of attention; without it there is nothing to resolve. |
| B3 | **Payoff resolves the open loop** | .25 | Cold-open question never answered / no cold-open question. | Final chapter explicitly pays off the cold-open promise. | The promise-of-payoff is what viewers stay *for*; breaking it trains them not to finish. |
| B4 | **Chapters are hooks** | .10 | Table-of-contents labels ("Diet", "Training"). | Every chapter title is itself a hook ("At Death's Door"). | Chapter cards are re-hook points that reset attention mid-video. |
| B5 | **Real voices carry it** | .10 | One synthetic VO for 10 unbroken minutes. | ≥40% of runtime is real archival audio, cut as a chorus. | Synthetic monotone bleeds retention; real voices feel like evidence, not narration. |

## Category C — Pacing & Delivery — 20% — *predicts mid-video drop-off*

Does it breathe, vary, and deliver the promised product? Judged on the render + transcript.

| # | Dimension | Wt | 0 | 10 | Why |
|---|---|---|---|---|
| C1 | **Breathing room** | .30 | Zero silence; wall-to-wall VO. | Music-and-picture beats let moments land. | Relentless narration causes fatigue drop-off; pauses reset attention. |
| C2 | **No sagging middle** | .25 | Energy flatlines after the setup. | Momentum sustained across the whole arc. | The middle third is where most videos lose the plot and the viewer. |
| C3 | **The workout delivers** | .25 | Off-topic footage; the promised protocol is thin. | Protocol Act ≥90% training/physique/food; whole film ≥35%. | This channel's audience came for the workout; not delivering it kills sub-conversion. |
| C4 | **Visual variety** | .20 | Same treatment / stock footage on repeat. | Footage-first grammar, no repetition. | Repetition and generic stock feel signal "low value" and drive abandonment. |

## Category D — Packaging (click layer) — 30% — *predicts CTR*

Nothing else matters if nobody clicks. Judged on the title string + the thumbnail image.
**Highest single weight** — CTR is the gate on all downstream watch-time.

| # | Dimension | Wt | 0 | 10 | Why |
|---|---|---|---|---|
| D1 | **Thumbnail curiosity gap** | .40 | Cluttered / illegible at small size / no face-emotion. | One legible face + emotion + a transformation tease you have to click to resolve. | The thumbnail is 80% of CTR; it must read and provoke at phone size. |
| D2 | **Title: hook front, search behind** | .35 | Search terms only ("Jason Statham Workout Routine"). | Gavia hook in front, search terms behind ("The Disease That Built MrBeast \| His Real Workout & Diet"). | The hook drives the click; the search terms drive the impressions. Both, in that order. |
| D3 | **Title–thumbnail coherence** | .25 | Disconnected, or worse, contradictory. | One promise, reinforced across both. | A mismatch inflates CTR then craters retention — the algorithm punishes that pattern harder than a low CTR. |

## Category E — Technical A/V & settings — MULTIPLIER [0,1] — *retention floor*

Not a craft slice — a gate. Reuses `qc.py` verbatim (shell out, read `qc_report.json`)
plus one delivery-settings probe. This is the operator's "audio and vid syncs well and
has the right settings" requirement.

| Signal | Source | Effect on TechFactor |
|---|---|---|
| A/V duration sync | qc G8 | **hard** — fail clamps ≤0.5 (desync = instant drop) |
| Black / freeze frames | qc G6 | **hard** — fail clamps ≤0.5 |
| Loudness −14 LUFS / −1 dBTP | qc G7 | −0.06 |
| No stray text / watermark | qc G1 | −0.06 |
| Shot length 1.2–6.0s | qc G3 | −0.06 |
| No scene reuse <90s | qc G2 | −0.06 |
| Delivery settings (≥1080p, 24–30fps, h264/aac) | ffprobe (new) | −0.06 |

`TechFactor = clamp(1.0 − Σ deductions, hard-floor)`. All pass → 1.0 → craft score is
unmodified.

## Category F — Measured outcome — MEASURED mode only — *the north star itself*

When real analytics exist, prediction is replaced by truth. Each metric is normalized
0–10 against **channel median (0-anchor) and a Gavia-tier target (10-anchor)**.

| Metric | 10-anchor (Gavia-tier) | Predicts |
|---|---|---|
| Click-through rate | ≥ 6% | reach |
| 30-second retention | ≥ 70% held | the hook worked |
| Average % viewed | ≥ 45% | the story held |
| Average view duration | ≥ 10 min | watch-time / session |
| Subscriber conversion | top-quartile for the channel | the payoff landed |
| Like : view ratio | ≥ 4% | satisfaction |

In MEASURED mode the report also emits `prediction_error = |INCREDIBLE_predicted −
OutcomeScore|` per video, so the rubric can be re-tuned against reality over time.

---

## The output

`pipeline/eval.py` writes `eval_report.json` (shaped like `qc_report.json`) with the
composite `incredible_score`, `craft_score`, `tech_factor`, every dimension's
`{score, pass, note}`, and — most importantly — a ranked **`top_fixes`** list: the
single highest-leverage change, phrased as *"your score is capped by X; do Y."* That
list is the point of the whole exercise.

## Calibration

`pipeline/eval.py --calibrate` scores the fixtures in `eval/fixtures/` and asserts:
1. Gavia Khamzat composite is within tolerance of **10**, each dimension within ±1 of its
   golden scorecard.
2. The channel's own drafts land in the **4–6 discrimination band**.

(2) is the guardrail that proves the rubric *separates* channel work from the reference
rather than flattering everything. If a draft scores 9, the rubric — not the draft — is
wrong.
