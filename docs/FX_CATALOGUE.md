# Visual effects catalogue

Effects the owner has picked, with the reference that prompted each. Every
entry is buildable in Python + OpenCV + ffmpeg and costs **nothing per shot** —
they composite material we already have rather than generating new material.

**The contract.** Every effect is `effect(sources, frames, **params) -> Path`
returning exactly `frames` frames at 1920x1080/24fps. Frame-exact is
non-negotiable: the assembler refuses anything else.

**Assets already in place:** `graphics/public/fonts/Anton-Regular.ttf` (channel
face), `manifest/words.json` (1,396 word-level timings, so any text treatment
can be word-synced to narration), ffmpeg with `alphamerge`, `gblur`,
`chromashift`, `blend`.

---

## 1. `text_matte` — footage through the type

**Reference:** Cleo Abram, *What If You Just Keep Digging?* @ 1:07 — "THE CRUST"

Letters are a **mask**, not type laid over video. Footage plays through the
glyphs; the type overflows the frame edges; everything outside is near-black so
the letters are the only light in frame. Bloom where the footage is brightest.

**Build:** render the word to an alpha mask in PIL (Anton) -> `alphamerge` with
the clip -> bloom pass on the luminance.

**Use for:** chapter titles, the cold-open title, any single loud word.

---

## 2. `source_highlight` — a page as a physical object

**Reference:** Cleo Abram @ 2:31 — "The Russians" highlighted in a book

The most valuable effect for this channel. **Not a screenshot.** The page is
treated as an object: shallow depth of field with focus falling off above and
below, the highlighted line as the only sharp band, a marker swipe that
animates on, chromatic aberration on the letterforms, slow drift.

This is the answer to a standing problem. The last film was rejected four
separate times for showing websites — *"Again it's a website. I did not want
this."* — while rule F5 demands that when a published source is the spine, the
film shows the actual pages. This treatment satisfies both: it shows the source
without looking like a screenshot.

**Build:** page image -> depth-graded blur -> animated highlight rect ->
`chromashift` -> drift.

**Use for:** any claim that rests on a document, study, article or post.

---

## 3. `headline_over` — text in front, footage behind

**Reference:** Cleo Abram @ 10:04 — a CNN headline over her to-camera

Footage behind, slightly darkened under the text block. Headline in white with
**specific words in the accent colour**. Byline small and grey beneath. Because
`words.json` carries word-level timings, the accent lands on the exact word as
it is spoken rather than sitting there as a static graphic.

**Build:** PIL text layer, per-word colour driven by `words.json` -> overlay ->
local darken behind the block.

**Use for:** quoting a headline while narration continues over footage.

---

## 4. `annotate` — annotation that builds as the argument does

**Reference:** Johnny Harris, *Why People Think The Government Killed JFK* @ 0:21
*(awaiting screenshot to pin the exact treatment)*

Distinct from `source_highlight`. That one says *here is the source*; this one
says *look at this, and now this*. Annotations arrive in sequence as the
narration reaches each — a circle, then an arrow, then an underline — drawn on
with a hand stroke over archival grain. On declassified material: redaction
bars, stamps, typewriter faces.

**Build:** stroke paths rendered progressively (Bezier + per-frame reveal) over
the base image, composited with the existing `archive_treatment` grain.

**Use for:** making an argument visible; walking the viewer through evidence.

---

## 5. `zoom_through` — macro to micro, no cuts

**Reference:** oso95/scroll-world; *Generative Powers of Ten*

Not chained video clips. N stills where each contains the next as a sub-region,
composited into a continuous exponential zoom
([ZoomVideoComposer](https://github.com/mwydmuch/ZoomVideoComposer) does the
compositing maths). Deterministic, frame-exact, ~$0.20 for a five-scale flight
against ~$1.50 as generated video.

**Use for:** face -> skull -> brain -> neuron -> gene. Any "what is happening
inside him" beat.

---

## 6. `layer_peel` — through skin, muscle, bone

Depth map drives a masked dissolve through supplied layers; `cv2.seamlessClone`
on the boundary. Reuses the depth estimation `flow_dibr` already runs.

---

## 7. `transform_morph` — before into after

mediapipe's 468 landmarks -> `cv2.Subdiv2D` Delaunay -> per-triangle affine
warp + alpha blend. Eyes and jaw stay anchored instead of crossfading to mush.
Falls back to `DISOpticalFlow` dense warp when no face is found.

**Use for:** the channel's single most-repeated idea, which has never had a
good treatment.

---

## 8. `orbit` — camera arcs around a still

Extends the `flow_dibr` warp from one axis to a rotating path. Same subpixel
discipline: the judder fix measured 1.008px -> 0.031px, and that standard
carries over.

---

## Already built, to be brought under the contract

`pipeline/fx.py` holds 13 working effects that nothing composes because they
each take different arguments: `archive_treatment`, `speed_ramp`,
`freeze_punch`, `flash_hit`, `whip_pan`, `film_dissolve`, `punch_in`,
`letterbox_squeeze`, `source_label`. Wrapping these in the contract is cheaper
than rewriting them and makes the whole set callable from a shot manifest.

---

## Build order

1. `source_highlight` and `text_matte` — fastest to prove, highest value, no
   generation cost
2. `headline_over` — reuses the text layer from `text_matte`
3. `annotate` — once the reference screenshot lands
4. `zoom_through`
5. `orbit`, `layer_peel`, `transform_morph`
6. Wrap the existing 13
