---
name: celebvid
description: Use when the user wants a documentary video about a celebrity for the Celeb Workout YouTube channel — "make a celeb workout video", "train like <name>", "build the <celebrity> video", /celebvid — or wants to rebuild the picture layer of one that already has approved audio.
---

# Celeb Workout video builder (V12 — generated picture)

**Repo:** `C:\Users\avina\ytceleb`. Proven end-to-end on
`THE_DISEASE_THAT_BUILT_MRBEAST_V12` (12:19, 135 shots, $9.40).

## The core reversal: generate the picture, do not hunt it

V7–V11 all failed the same way, and it was not a bug. There is only so much
real footage of any subject. The verified-window pool exhausts, stock dies on
legible branding or a stranger's face, and the allocator ends up rejecting
more than it accepts. **Five picture builds were rejected before anyone
admitted the supply was the problem.**

V12 generates the cutaway layer. That also removes, by construction, the two
defect classes that consumed the most review time: no watermark can appear in
a generated frame, and no unnamed second person wanders into shot.

**Real footage is still used where the subject speaks.** When their recorded
voice plays, the picture is them, at that timecode, from the real interview.
Everything else is generated.

**First question on any new film: does the script contain the subject's own
voice at all?** Many do not — a pure narrator VO has zero sync shots and a
100% generated picture, which is simpler and cheaper. Decide this from the
actual script before planning, and state it; do not assume the MrBeast shape
(25 bites, 17 sync-capable). Where bites do exist, a bite is sync-capable
only if a human has eyeballed a window that is clean and free of burned-in
text — derive that from the window manifest, never assert it.

## Medium: stills beat video 7.5:1, and usually look better

| Medium | Cost | Use for |
|---|---|---|
| Still + depth push-in | **~$0.04/shot** | Default. Compositions: objects, documents, landscapes, portraits of things |
| Veo video | **~$0.30/shot** | Process/change over time, scale revealed by movement, organic motion, the film's biggest beats |

A 12-minute film is ~$4 as stills, ~$30 as video. Budget the split
explicitly: ~30 video shots in a 12-minute film is a good ratio, chosen by
asking **does motion carry meaning a single frame cannot?**

Stills are also *sharper* than 720p Veo, which suits documents and objects.

- `pipeline/flow_still.py` — generate image + render the move
- `pipeline/flow_dibr.py` — depth-image-based push-in
- `pipeline/flow_gen.py` — Veo worker

**Use DIBR, not band-splitting.** Splitting an image into 3 depth bands and
scaling each produces no depth and reads as cardboard. A continuous per-pixel
warp driven by a dense depth map does. Depth-Anything-V2-Small + `cv2.remap`
with float32 maps. **Never round a coordinate** — integer rounding of the
crop box reads as judder (measured 1.008px; subpixel version 0.031px).

DepthFlow (`pip install depthflow`) does not install on Python 3.14 —
`moderngl`/`glcontext` have no wheels and need a C++ toolchain. Don't retry it.

Parallax only works where the depth map has structure. Flat or macro
compositions degrade to a plain zoom — that is automatic and correct, not a
bug to fix.

## The Gemini Developer API rejects most config fields

This cost four failed runs, discovered one at a time. **The Developer API
raises `ValueError` client-side, before any request is sent** — so these cost
$0, but they look like the API is broken.

**Rejected:** `seed`, `generate_audio`, `negative_prompt`, `person_generation`,
`fps`, `enhance_prompt`, `compression_quality`, `resize_mode`, `labels`,
`mask`, `output_gcs_uri`.

**Accepted:** `aspect_ratio`, `duration_seconds`, `resolution`,
`number_of_videos`, `last_frame`, `reference_images`, `http_options`.

Two consequences to plan around:
- **No seed = no reproducibility.** A rejected shot can only be re-rolled,
  never refined.
- **No negative_prompt.** Anti-text/logo defence lives entirely in prompt
  wording plus post-hoc QC.

**Veo attaches an AAC track that cannot be disabled.** Map video explicitly at
assembly; do not rely on `-shortest`.

**Imagen 4 is closed to new users** (404). Use `generate_content` with
`gemini-3.1-flash-lite-image`.

Verify the whole allow-list with a test that asserts config emits *only* the
accepted keys, so re-adding a rejected field fails in the suite, not live.

## Money safety (a worker that spends unattended)

- **Charge the ledger when the API accepts the job**, not when the local
  client finishes parsing. Charging at parse-success means a wrong
  response-shape assumption leaves `spent` at $0.00 — so the cap never trips
  and the worker burns the whole backlog while printing `spent $0.00`.
  Charging *before* the call is also wrong: a client-side validation error
  books money that was never spent.
- **Circuit breaker: halt after 3 consecutive failures.** A systemic bug is
  indistinguishable from bad luck without one. Add a total-failure budget too
  — a consecutive-streak breaker is starved by alternating fail/succeed.
- **Split submit from download.** A failed download must retry the download,
  never resubmit — resubmitting buys the same video twice.
- **Record the error on every non-done state.** A ledger that says `failed`
  without saying why costs a diagnostic run to rediscover a one-line error.
- **A file on disk is not proof of a usable clip.** Quota-halted attempts
  leave partial mp4s. Trust `state == "done"`, never `path.exists()`.
- **Veo quota (429) is periodic, not spent budget.** The model stays
  reachable. Generate stills as a floor so the film is always complete, and
  let video upgrade over them when quota returns.
- **The project key file beats an ambient env var.** An operator's shell can
  carry a stale `GOOGLE_API_KEY` from another project — this one did, for
  three runs. Print which source the key came from, masked.
- The API key goes in `?key=`, never as an OAuth bearer. Bearer returns
  `API_KEY_SERVICE_BLOCKED`, which reads exactly like a revoked key.

## Timing — the rules that survived every rebuild

- **`manifest/edl_full.json` is the only source of timing.** Never a
  transcript. Whisper merges long pauses and drifts 10+ seconds.
- **Quantise boundaries, don't distribute drift.** Each EDL boundary becomes
  `round(t * FPS)`; durations derive from those integers. The totals telescope
  exactly with no reconciliation step. Allocating one global frame pool
  guarantees the *total* but pushes error onto individual cuts — and it lands
  on **sync boundaries**, where 1.35 frames is ~56ms of wrong picture under
  the subject's own voice.
- **`src_t0` comes from the EDL's bite in-point, never a scan window's `t0`.**
  `bite_windows.py` widens its search by 1.5s and nudges edges +0.25s, so a
  run's `t0` is the in-point minus 1.25s *by construction*. This put over a
  second of wrong picture under his voice on all 17 sync shots, and it passed
  every check that only asked whether the field was present and positive.
- **Integer frames, summed exactly. Never pad, never loop.** A short piece is
  an error. Rounding across 130 shots once accumulated 3.8s and the "fix"
  inserted an 18-second frozen frame.
- **Cache pieces on a content fingerprint, not the shot name.** Shot names are
  positional; swap a clip and a name-keyed cache serves the stale render.

## Prompts are the film

**A shot that needs explaining has failed.** The viewer gets one read of a
4–10 second image. Literal beats metaphorical; showing the state the sentence
describes beats showing a symbol of it.

Audit every prompt against the narration it plays under before generating.
On the MrBeast film that found 88 KEEP / 20 WEAK / 10 FAIL, and the failures
were systemic rather than isolated:

- **"Objects moved by nothing visible"** drove five separate shots. The
  operator rejected two by eye; the audit found the pattern.
- **Two shots contradicted their own line** — three chairs under "room for
  exactly one".
- **A quarter of the script was a sequence of events, not an image** —
  calendars igniting, grids filling. Those collapse to nothing as stills.

Mark shots whose meaning *is* the change over time as `needs_video` so they
stay on the expensive path deliberately, not by accident.

**Any visible human must be consistent with the subject or unreadable as
him** — hands operating a prop, a crowd, a figure at distance. A generated
person who reads as "young <subject>" and looks nothing like him is worse
than no shot, because the viewer knows who the film is about.

## Audio architecture (unchanged — 4 bugs, never regress)

1. `amix` renormalises when a short input ends → clipping. Use `normalize=0`.
2. Mono SFX + stereo VO in `amix` → narration comes out +3dB hot. `aformat`
   both to stereo first.
3. **Never slice narration per beat** — per-beat AAC re-encode puts an audible
   glitch at every join. Narration plays continuously between interludes.
4. **Never `acrossfade` audio chunks** — each crossfade overlaps its inputs,
   shortening total audio ~0.3s per junction → cumulative A/V drift. Butt-join
   with 30ms edge fades. Keep the hard sync gate: refuse to mux if
   `|video_dur − audio_dur| > 0.25s`.

**AUDIO LAST.** Build the whole visual cut on a free edge-tts draft; paid TTS
fires once on the locked script. Check for pre-staged `voiceover_<slug>.mp3`
before spending anything.

**Profanity:** mute on a *copy* of the master, never the approved original.
Duration must stay byte-identical or the frame budget breaks. Note YouTube
auto-captions mask profanity as `[&nbsp;__&nbsp;]` — a regex for `[ __ ]`
misses it, which is how a "no profanity found" answer was wrong.

## Delivery

- Drive uploads through the gcloud OAuth client need an
  `x-goog-user-project` header and `drive.googleapis.com` enabled on a
  billable project. Without it every call is `403 Forbidden`, which reads
  like a permissions problem. Resumable session, 8 MiB chunks.
- **Background renders get killed at tool boundaries.** Do the final concat
  and mux in the foreground. Never re-encode a body that is already encoded —
  concat a matching black tail and stream-copy.
- Writing to a locked output path silently produces a corrupt file
  (`moov atom not found`). Write to a fresh filename.

## YouTube copyright — hard limits on real footage

Generated material carries no claim risk. Real interview and archive footage
does, and the owner set these limits:

1. **No clip longer than 10 seconds.**
2. **Never repeat a clip.** Already enforced by the no-reuse registry.
3. **One clip per source video.** Not one per scene — **one per source.** If a
   90-minute podcast yields a perfect moment, take that moment and nothing
   else from that video.

Rule 3 is the expensive one and it invalidates the previous film's structure:
*The Disease That Built MrBeast* draws **8 bites from a single Rogan episode**
and 6 more from one Airrack video. Under this rule that film would need 14
different sources.

Plan for it at the EDL stage, not at the picture stage: the script must be
built so each quoted moment comes from a different appearance. Widen the
source pool during research rather than mining one long interview, and where
only one source exists for a claim, use it once and carry the rest of the
point in narration over generated picture.

## Branding — the largest quality gap

Read `docs/BRAND.md` before building any graphic. It is measured off
`library/brand/channel_banner.png`, the only authoritative statement of the
identity.

The failure to avoid, in the owner's words: *"it's very easy to tell that it
was generated with AI — the fonts, animations, layouts and overall design look
like the default style Claude uses for almost every project."*

Two specifics that recur:

- **The channel red is `#C00000`, not `#E3120B`.** The brighter, more orange
  value is wrong and appears throughout the existing code.
- **The ground is `#F0F0F0` paper, not black.** The films have been built in a
  dark anamorphic world that contradicts the channel's own banner.

Identity is cumulative. It will not be fixed by restyling one video; every
film has to use the same faces, the same red, the same devices.

## Revisions — keep the unit of change small

A fix in Premiere is quick because you change one clip. An AI workflow only
matches that if the pipeline is granular, and this one is: every shot renders
to its own piece, cached on a **content fingerprint**, so changing one prompt
re-renders exactly one shot and nothing else. A re-roll costs $0.04 and the
assembler stitches around it.

Protect that property. It breaks the moment anything caches on position, or a
single render covers several beats.

## Red flags — stop

- Hunting for more footage because the pool is thin → generate it
- Trusting a file's existence instead of the ledger
- Charging the budget anywhere but on API acceptance
- Allocating frames globally instead of quantising boundaries
- `src_t0` from anything but the EDL
- A test whose expected value was copied from the output it checks
- Shipping without an eyes-on pass — every previous build was machine-clean
  and still failed review
