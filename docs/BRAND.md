# Celeb Workout — brand system

Derived by sampling `library/brand/channel_banner.png`, which is the only
authoritative statement of the channel's identity that exists. Everything here
is measured off that file, not invented.

**The finding that matters:** the films do not look like the channel. The
MrBeast film's language was near-black, anamorphic, volumetric haze, deep red
as the only warm accent — a prestige-documentary look. The channel is a
**light paper ground with bold red and black**, cut-out subjects and
hand-drawn accents. A viewer arriving from the banner to the film would not
believe they came from the same place. That gap is the single biggest reason
the videos read as generic.

---

## Palette — measured, not guessed

| Token | Hex | Where it came from |
|---|---|---|
| `--paper` | **#F0F0F0** | 41.9% of the banner. The ground. Warm light grey, NOT white. |
| `--red` | **#C00000** | The circle shape and the badge box. |
| `--red-type` | **#BF0503** | Sampled off the word CELEBRITY. Slightly deeper than the shape red. |
| `--ink` | **#000000** | The subhead. True black, not a soft charcoal. |
| `--ink-soft` | **#0C0C0C** | Secondary text mass in the banner. |

**#E3120B is not the channel red.** It appears throughout the existing code
(`fx.py`'s `source_label`, the card renderers) and is brighter and more orange
than anything in the banner. Correct it to `#C00000` wherever it appears.

A pure white ground is also wrong. `#F0F0F0` carries a faint paper texture in
the banner and that texture is part of the identity.

---

## Typography — roles, not one font

The banner uses four distinct roles. Using one face for everything is a large
part of why output reads as templated.

| Role | Treatment in the banner | Asset |
|---|---|---|
| **Headline** | Heavy condensed caps, tight tracking, red — "CELEBRITY" | `Anton-Regular.ttf` is close and already on disk |
| **Subhead** | Bold grotesque, mixed case, black — "Workouts & Diet Secrets" | **MISSING** — needs a bold grotesque |
| **Accent** | A handwritten script, small, riding the baseline — the "with" in "Transform with" | **MISSING** — needs a script face |
| **Badge** | White knockout on a solid red box — "Each Week" | Any of the above, reversed |

Two of the four faces are not in the repo. `graphics/public/fonts/` holds only
Anton. Until the other two land, every card is built from a single face, which
is exactly the flattening the owner identified.

---

## Devices

These are the channel's recognisable moves, all visible in the banner:

- **Cut-out subjects** with hard edges, overlapping, no drop shadow
- **A solid red circle** behind the subject group — a shape, not a gradient
- **Hand-drawn underline swoosh** beneath a claim, slightly irregular
- **Knockout badge** — white type on a solid red rectangle, for the one number
  or phrase that matters most
- **Paper texture** over the whole ground, faint

None of these are hard to build. None of them are currently used in the films.

---

## What to avoid

The owner's note, verbatim: *"When I watch the Bruce Lee video, it's very easy
to tell that it was generated with AI. The fonts, animations, layouts, and
overall design look like the default style Claude uses for almost every
project."*

Concretely, that default look is: a warm cream ground with a serif display
face and a terracotta accent; near-black with one acid pop; hairline rules and
dense columns; Inter or Space Grotesk as the safe face; everything centred;
rounded corners everywhere; an accent bar on a rounded card.

**None of that is this channel.** This channel is loud, flat, high-contrast,
paper-grounded, and slightly hand-made.

---

## Applying it to a film

- **Ground:** cards, infographics and title treatments sit on `--paper`, not
  on black. Footage remains footage; the graphic layer is where the brand
  lives.
- **Titles:** condensed caps, red or knockout, never a serif.
- **The one number per chapter** gets the knockout badge.
- **Every claim card** gets the hand-drawn underline, not a hairline rule.
- **Logo bug** bottom-right on all footage; `library/brand/brand_lockup.png`.

---

## Open, and blocking a truly branded film

1. **Two fonts are missing** — a bold grotesque and a script. Until they are
   sourced (with a licence that permits commercial use), the type system is
   one face doing four jobs.
2. **No paper texture asset** — the banner's grain needs extracting or
   recreating.
3. **No motion language.** Fonts and colours are static identity; a channel is
   also recognised by *how things move*. Nothing in the brand assets specifies
   this, so it has to be decided: how a card enters, how a title resolves, how
   a transition behaves. Consistency there matters more than novelty.
