# Celeb Workout — brand guidelines

**Authoritative.** Supplied by the owner. Where this file and any earlier
sampling of `library/brand/channel_banner.png` disagree, **this file wins** —
the banner is a compressed JPEG and the values read off it were approximations.

## Positioning

Hollywood performance, decoded into practical workouts and diet breakdowns.

**Personality:** bold, cinematic, disciplined, aspirational. An entertainment
documentary fused with a premium fitness magazine — not a generic gym channel.

**Tagline:** TRAIN LIKE THE ICONS
**Descriptor:** Celebrity workouts, diets & transformations

Two permanent series, not a new design each upload: celebrity **Workout &
Diet** profiles, and character-led **Train Like** videos.

---

## Typography — four roles, three families

All installed in `graphics/public/fonts/`. All OFL, cleared for commercial
video, thumbnails, logos and artwork. Keep the licence file when handing fonts
to an editor.

| Role | Face | File | Use |
|---|---|---|---|
| Hero condensed | **Anton Regular** | `Anton-Regular.ttf` | Thumbnail headlines, chapter titles, major numbers |
| Bold grotesque | **Archivo Black** | `ArchivoBlack-Regular.ttf` | Logo, celebrity names, series labels |
| Utility grotesque | **Archivo** Regular/Medium/SemiBold | `Archivo-*.ttf` | Captions, facts, exercise names, body copy |
| Script accent | **Allura Regular** | `Allura-Regular.ttf` | One or two words: "with", "inside", "secrets" |

**Anton** — all caps, max two lines, tracking ≈ −2%, line height 88–94%. Never
for paragraphs. No outlines; solid white, black or red.

**Archivo Black** — all caps for names and branding. Normal or slightly tight
spacing. Red rectangular nameplates behind white text. Never artificially
stretched or condensed.

**Archivo Regular/Medium** — sentence case for explanation, all caps only for
short labels.

**Allura** — max three words, never all caps, never essential information,
35–55% of the adjacent headline height. Banners, intros and section
transitions; not standard thumbnails. It must read as editorial contrast, not
as a wedding invitation.

**Never more than two families in one frame.**

---

## Colour

| Name | Hex | Purpose |
|---|---|---|
| Celebrity Red | **#B22B1A** | Names, highlights, circles, bars |
| Training Black | **#0D0D0D** | Backgrounds and strong type |
| Warm White | **#F4F2EF** | Main text and editorial backgrounds |
| Steel Gray | **#A9A9A9** | Secondary information |
| Deep Shadow | **#252525** | Panels, gradients, image backgrounds |

**Ratio: 70% black/white/photography · 20% neutral grey and texture · 10% red.**

Red is the signature, not the ground of every frame. No oranges, blues or
neon introduced per celebrity.

**`#E3120B` is wrong and appears throughout the existing code** (`fx.py`'s
`source_label`, the card renderers). Replace with `#B22B1A`.

---

## Logo

**Primary wordmark:** CELEB / WORKOUT stacked tight — CELEB in white, WORKOUT
reversed out of a red rectangle. No bevels, chrome, flames or bodybuilding
clip art.

**Secondary:** a compact **CW** monogram in a red circle — watermark, corner
bug, shorts, social.

**Avatar:** one permanent mark. Either the CW monogram or a single
black-and-white athletic silhouette with the wordmark. It never changes per
video; it is the channel identifier, not another thumbnail.

---

## Graphic language

The signature device is the **large red circular field behind overlapping
cut-out subjects**. It is permanent brand, not decoration.

Also: red circles, half-circles and arcs · black-and-white portraits at 10–20%
opacity · subtle halftone or printed-paper texture · red rectangular labels ·
hard vertical crops · warm-white editorial space · occasional hand-drawn red
underline.

**Avoid:** glowing gym graphics, blue lightning, metallic text, lens flares,
mixed outline styles, more than one script font.

---

## Thumbnails

Three elements, always: one dominant person, one short headline, one red label.

- **A — profile:** WORKOUT & DIET PLAN + red label with the name
- **B — transformation:** TRAIN LIKE + red label with the character
- **C — investigation:** THE REAL WORKOUT + red label with the name

Headlines 3–6 words. Max two text sizes. Subject 40–55% of frame, eyes in the
upper third, chest-up or waist-up. One prop at most. Soft black shadow behind
the subject; a thin warm-white edge only where separation is needed. Test at
phone size. No script type unless a small accent.

---

## Motion

**Intro, under four seconds:** black-and-white celebrity image → red arc wipes
across → image resolves to colour → CELEB WORKOUT wordmark → script accent
writes on → hard cut into the story.

**Four repeatable chapters:** THE ROLE · THE WORKOUT · THE DIET · THE RESULTS.
Anton over black with a red number or red vertical bar.

**Exercise cards:** name in Archivo Black, sets and reps in Anton, explanation
in Archivo Regular, a red line or block as the only accent.

**Lower thirds:** black translucent rectangle, red vertical bar, name in
Archivo Black, context in Archivo Medium.

---

## Photography

Consistent across every celebrity: slightly cool shadows, natural warm skin,
strong but controlled contrast, reduced background saturation, mild grain,
sharp facial detail. No exaggerated HDR, no artificial muscles, no altered
facial anatomy.

Workout footage darker and more intense. Diet footage cleaner and brighter.

---

## Voice

Confident and specific: *"Here is how he trained for the role."* · *"The
published routine included…"* · *"This is what can realistically be adapted."*

Never: *"This secret guarantees…"* · *"Doctors don't want you to know…"* ·
*"This one exercise created his entire physique."*

Dramatic without pretending every routine is independently verified.

---

## Legibility note

A title matte over dark footage goes black-on-black and disappears — measured
on a night aerial where mean luminance inside the glyphs was under 40.
`fx_text.text_matte` now measures luminance inside the type and, when it falls
below threshold, lifts the footage toward it and adds the thin warm-white rim
the thumbnail rules already allow "only when separation is necessary".

The same rule applies anywhere type meets image: check contrast, and separate
with the warm-white edge rather than by adding a glow or a stroke in another
colour.

---

## Non-negotiable

Same red, same three families, same two thumbnail structures, every upload.
Never more than two families in one frame. Script stays decorative. One
dominant person per composition. Celebrity recognisable first, topic
understandable second, branding visible third.

Identity is cumulative. It is not fixed by restyling one video.
