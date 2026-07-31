# V12 — Generated picture against locked audio

**Date:** 2026-07-31
**Film:** *The Disease That Built MrBeast* — 12:19 documentary, Celeb Workout
**Status:** design approved; implementation not started

---

## 1. Why this exists

Five picture builds have been rejected (V7, V8, V8PREVIEW, V9, V11). The
failures were not bugs. They were a supply problem:

- 83 of 85 verified Jimmy windows are already drawn. The `walk` group is at
  zero clips, `calendar` at one, `bed` at three.
- The allocator now rejects more candidates on look-alike than it accepts.
- Stock footage dies on legible third-party branding, a stranger's face, or a
  body performing an activity the narration attributes to Jimmy.

The film ran out of pictures. V12 stops searching for footage and generates it.

Generation also removes, by construction, the two defect classes that consumed
the most review time: there is no Pexels watermark in a generated frame, and no
unnamed second person wandering into shot.

## 2. What is locked and must not be rebuilt

| Thing | Path | Note |
|---|---|---|
| Audio master | `final_video/mrbeast_audio_v6/MRBEAST_V6_STORY_MASTER.wav` | approved, 12:19 |
| Authoritative timeline | `manifest/edl_full.json` | 74 segments |
| Shot prompts | Google Doc `1VoOBGxuFWpRK91JOknjxRw31gn7viSKw8Wf7jQSkzwE` | 59 Flow prompts |
| Verified Jimmy windows | `manifest/jimmy_pool2.json` | keyed `sid@t0` |
| Per-bite sync windows | `manifest/bite_windows.json` | |

**Timing comes from the EDL. Never from a transcript, never from the Doc.**
Whisper merges long pauses and drifts 10+ seconds; that mistake put baseball
footage twelve seconds early over a silent title break. The Doc's timings agree
with the EDL because the Doc was written from it, but the EDL stays
authoritative.

## 3. Composition

EDL: 40 narration + 25 bite + 8 beat + 1 card = 74 segments, 736.107s.

| Layer | Segments | Runtime | Shots | Source |
|---|---|---|---|---|
| Lead-in | 1 | 2.00s | 1 | Veo 3.1 Lite |
| Generated | 49 narr/beat/card | 459.02s | **102** | Veo 3.1 Lite |
| Generated | 8 orphan bites | 65.68s | **14** | Veo 3.1 Lite |
| Real footage | **17 sync bites** | 205.41s | 17 | `jimmy_pool2` windows |
| Silent tail | — | 2.50s | fade | — |
| | | **738.61s** | **117 generated** | |

Derived from `manifest/bite_windows.json`: a bite is sync-capable when it has
at least one run that is `verified_jimmy` and not `has_text`. Exactly 17
qualify. The 8 that do not are **6 from Airrack's video** (`7r3ORKgNUjw`),
where no Jimmy-only frame exists, and **2 from Rogan** (`cLRLEnPaJLM`, i=18 and
i=20) where the Crohn's & Colitis Foundation website sits on a studio monitor
behind him. This matches the Doc's own account of the eight exactly.

### Sync policy — reversal of the Slides note

The owner's Slides review (slide 44) cut his face to 10 bites via `KEEP_SYNC`
in `pipeline/picture_plan_v8.py`. **V12 reverses that to the Doc's policy: 17
bites keep the real man on camera.**

The Doc's argument, accepted: cutting away while his recorded voice plays is
what made the last cut feel out of sync. The original reason for cutting away
was that the alternative was bad stock footage. Generation removes that reason.

**When Jimmy talks, you see Jimmy.** A bite's picture is the real interview at
the real timecode — never generated, never a cutaway.

## 4. Shot splitting

Median generated segment is 9.95s; the longest is 18.34s. 33 of 49 exceed
Veo's 8s ceiling. Rule 4 caps a shot at ~6s, and the reference documentary the
owner admires measures a 5.15s median.

So each over-length segment is split into the 2–3 beats its sentence actually
contains, each with its own prompt. 49 segments become **~102 shots averaging
4.5s**. Each shot gets `gen_dur` of 4, 6, or 8s — Veo's only legal values —
chosen as the smallest that covers the beat.

Splitting is also cheaper than the alternatives, because 4s and 6s generations
are billed for what they are:

| Strategy (49 gen segments only) | Billed | Cost @ $0.05/s | Shots |
|---|---|---|---|
| **Split ≤6s (chosen)** | 582s | **$29.10** | 102 |
| Extend (7s chunks) | 658s | $65.80 (Fast only — Lite cannot extend) | 49 |
| One 8s + retime | 392s | $19.60 | 49 |

**Whole-film cost**, including the lead-in and the 14 orphan-bite shots the
table above omits:

| | Shots | Billed | Cost |
|---|---|---|---|
| Lead-in | 1 | 4s | $0.20 |
| 49 gen segments | 102 | 582s | $29.10 |
| 8 orphan bites | 14 | 78s | $3.90 |
| **Full pass** | **117** | **664s** | **$33.20** |

Extension was ruled out twice over: Veo 3.1 Lite does not support it, and it
bills in 7s chunks regardless of what is used.

## 5. Backend

**Veo 3.1 Lite (`veo-3.1-lite-generate-preview`), 720p, 16:9, via the Gemini
API** — `generativelanguage.googleapis.com`, project
`gen-lang-client-0088838569`, authenticated with an `AQ.`-format API key.

Vertex AI was investigated and rejected: it bills the card and leaves the
prepay untouched. The Gemini API spends the **$21.08 Gemini API prepay**, which
is the money already committed to this.

The API key is passed as `?key=`, not as an OAuth bearer token. Passing it as a
bearer returns `API_KEY_SERVICE_BLOCKED`, which looks exactly like a dead key.

### Budget

$21.08 buys **421 billed seconds** at $0.05/s. A full 117-shot pass needs
**664s ($33.20)**, so the prepay covers **63%** of one pass. A top-up is needed
to finish a complete pass, but not before the proof has been reviewed.

### Frame budget, 24fps

| | Seconds | Frames |
|---|---|---|
| Picture, 0 → EDL end | 736.107 | **17,667** |
| Silent tail (fade to black) | 2.499 | 60 |
| **Total** | 738.606 | **17,727** |

Per-shot frame counts are integers that sum to exactly 17,667 for the picture
body. Rounding across 130 shots previously accumulated ~3.8s of drift, and the
first fix padded with a frozen frame, producing an 18-second stall.

`flow_gen.py` carries a **hard spend cap that stops submission**, not a warning.

## 6. Components

```
manifest/flow_shots.json    ~102-entry shot list — single source of truth
  ↑ built by
pipeline/flow_plan.py       Doc prompts × EDL timings → split into ≤6s beats
pipeline/flow_gen.py        background worker: submit → poll → download → mark
pipeline/flow_qc.py         gates each clip before it reaches the timeline
pipeline/flow_assemble.py   conform, frame-exact cut, join bites, mux audio
```

**`flow_plan.py`** joins the Doc's 59 prompts to the EDL's 74 segments by
order, splits over-length segments, and writes each shot with: `shot_id`,
`seg_id`, `start`, `end`, `frames`, `kind`, `prompt`, `gen_dur`, `refs`,
`status`.

**`flow_gen.py`** is the background worker. Submits any shot not `done`, polls
the long-running operation, downloads to `library/veo/<shot_id>.mp4`, writes
status atomically. Idempotent and resumable — kill it and restart it.

**`flow_assemble.py`** conforms each clip, allocates an integer frame count per
shot, makes the counts sum to exactly the audio's frame count, and copy-trims
with `-frames:v N -c copy`. This is V8's solution kept verbatim; it is the one
part of the picture chain that never failed.

## 7. Rules

Inherited from `HANDOFF.md`, still binding:

1. **Only Jimmy.** No other identifiable creator on screen, ever.
2. **Never reuse a clip or a window.** Enforced by a registry that throws.
3. **No looping.** `-stream_loop` is banned. A short clip is an error, never a
   freeze and never a repeat.
4. **No cutaway over ~6s.** Amended: sync bites may run longer, because sync is
   sync. The cap governs generated cutaways.
5. Windows must not cross a camera cut (`scdet=threshold=6`).
6. Perceptual dedupe at 17×16 (256-bit). The 64-bit dHash has no usable
   separation on this material.
7. **Eyes-on identity pass is mandatory.** Machine gates have passed Joe Rogan
   singles, Steven Bartlett singles and two pure green frames.
8. Picture must illustrate the sentence being spoken.
9. **(rewritten below)**
10. On-screen credit for interview and archive sources; medical stills carry
    Wikimedia credits where the licence requires attribution.
11. No CelebWorkout logo or watermark anywhere.
12. Narration must not echo the clip beside it (`pipeline/echo_check.py`).
13. Clinical imagery: short, faded, never implied to be Jimmy.

### Rule 9, rewritten for generation

> **Generated picture must not contradict the real subject.** Jimmy Donaldson
> is a white man in his late twenties. Any human visible in a generated shot
> must either be consistent with that, or be unreadable as him — hands
> operating a prop, a crowd, a figure at distance.
>
> No shot is cast as Jimmy: no stand-in body, no silhouette training, no child
> playing baseball. A generated person who reads as "young Jimmy" and looks
> nothing like him is worse than no shot at all, because the viewer knows who
> the film is about.

## 8. Look consistency

Two mechanisms, both applied to every generation:

1. **The Doc's shared style tail** — *cinematic, anamorphic, shallow depth of
   field, near-black shadows, muted desaturated palette with deep red as the
   only warm accent, slow deliberate camera move, volumetric haze, no text, no
   logos, no recognisable faces, 24fps.*
2. **1–3 fixed reference stills**, generated once and approved by the owner,
   passed to all ~102 shots.

Without this, 102 independently sampled generations drift on colour and grain
and the film reads as a stitched-together stock reel.

## 9. QC gates

Machine, on every downloaded clip:

- **OCR** — Veo invents signage and gibberish text despite "no text, no logos".
  Reuse `clean_windows.py`'s sentence-likeness discriminator (overlays are
  phrases; logos are single words).
- **Person detection** → routes to the rewritten rule 9. Any visible human is
  flagged for the owner, never passed straight to the timeline.
- **Perceptual dedupe** at 17×16, proximity-weighted at the allocator. Sync
  windows are exempt: two windows of one interview always hash alike.
- **Black-frame, static-frame, exact duration.** `freezedetect` at −60dB
  false-fires on a slow Ken Burns; measure actual pixel delta.

Then **contact sheets for the owner's eyes-on pass, cut from a frozen render.**
Reviewing a file being rewritten underneath the reviewer wasted an entire
five-person pass once already. Freeze, cut sheets, then review.

## 10. Error handling

- Spend cap stops submission at a hard ceiling.
- Shot status is written atomically; a killed run resumes without regenerating.
- A generation that fails after N retries is marked `failed`, not silently
  skipped. `take_broll` once did `if not p.exists(): continue`, which silently
  dropped 14 allow-list entries and still reported success.
- A clip shorter than its allocated frame count is a build error.
- Pieces are cached on an **asset fingerprint**, never on positional shot name.

## 11. Test plan

Before spending past $2: generate **three shots** — a 4s beat, a 6s beat, and
one split out of the 18.34s segment — conform them, and assemble against the
real audio at their real timecodes. **Cost: $0.80.** The owner watches before
anything else is generated.

The prompt list is reviewed by the owner **before any generation at all**. The
prompts are the film now; if they are wrong, no amount of clean pipeline saves
it.

## 12. Delivery format

All four interview sources are **1280×720**, at four different frame rates:

| Source | Frame rate | Resolution |
|---|---|---|
| `7r3ORKgNUjw` | 30 | 1280×720 |
| `9IQ_ldV9z_A` | 23.976 | 1280×720 |
| `FjrJ2DJN_pA` | 25 | 1280×720 |
| `cLRLEnPaJLM` | 29.97 | 1280×720 |

**1. Frame rate: deliver at 24fps.** V8/V9/V11 were 30fps; V12 changes this
deliberately. Generated shots are 69% of the runtime and Veo outputs 24fps
natively, so 24fps delivery leaves the majority pass-through and converts only
the talking heads — where motion is least and judder shows least. Delivering
30fps would frame-duplicate every slow deliberate camera move, which is the
worst case for judder. 24fps also matches the Doc's prompts and the cinematic
reference. Source rates differ anyway; conversion is unavoidable for some
material either way.

**2. Resolution: generate 720p, upscale to 1080p for delivery.** The film is
capped at 720p by its own interview footage, so native 1080p generation
(**$65.28**, forced to 8s clips) would buy nothing and would make generated
shots visibly sharper than the bites they cut against. Upscaling to 1080p for
upload is what the film already does, and YouTube allocates more bitrate to a
1080p upload. **Cost stays $29.10/pass.**

**3. The 2.5s tail is silence.** Measured at mean −69.9 dB / max −57.8 dB,
against −17.8 dB for a genuine music-only beat. It is dead air, not an
unaccounted music cue. The frame budget derives from the EDL's **736.107s**;
the silent tail carries a fade to black.

## 13. Explicitly out of scope

- Rebuilding the audio. It is approved.
- Re-scanning sources for more Jimmy windows. The pool is at its variety limit
  and that is what V12 exists to route around.
- The headless-Chrome Flow route. Retained as a fallback only if the Gemini API
  path fails.
