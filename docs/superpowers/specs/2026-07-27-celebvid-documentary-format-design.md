# Celeb Workout — Documentary Format (V11)

**Date:** 2026-07-27
**Status:** Approved design, pending implementation plan
**Supersedes:** the ~10-minute explainer format (V9/V10). The old path stays in
the repo as dead code; it is not maintained.

---

## 1. Why this exists

The channel's current films are accurate, well-researched, information-dense —
and they do not move anyone. The Statham V5 narration is an excellent magazine
article read aloud: thesis in sentence three, chronology, the diary, the diet,
five copyable rules. Nothing is withheld, nothing is at stake, nothing changes.

The reference channel is **Fight Films by Patrick Gavia** — MMA character
documentaries, 23–47 min, 550k subs, a 25-minute film at 8.5M views. His subject
matter is irrelevant to us; his grammar is the entire point.

### What Gavia does that V9/V10 does not

Derived from his catalog (yt-dlp) and a full caption analysis of *The Girl Who
Broke Khamzat Chimaev* (`1T8ZRx5FR4I`, 8.5M views, 25:24):

1. **Story, not briefing.** His spine is scenes. Ours is information.
2. **The cold open withholds.** He opens on an orphan girl whispering to Khamzat
   and says outright *"I'll reveal later what she whispered."* Paid off at
   24:13 — the film's last beat. Ours states the conclusion immediately.
3. **Chapters are hooks.** `The Girl / Welcome to Hell / The Answer / At Death's
   Door / Smash Bros For Life / Arrested / The Fall / Vanished`. Ours are a
   table of contents.
4. **Real voices carry the film.** Roughly half his runtime is archival audio —
   subject, coaches, teammates, commentators, journalists — cut as a chorus that
   argues with itself. Narration is the connective tissue *between* soundbites.
   We run one synthetic voice for ten unbroken minutes with 6–8 interludes
   bolted on afterward. **This is the single largest perceptual gap.**
5. **A named antagonist, always.** "The UFC broke him." Ours: "he was always in
   shape" — a premise with no opposition.
6. **Length.** 23–47 min (median ~26) vs our 8–10.
7. **No infographic cards at all.** Every frame is footage; on-screen text is
   sparse chapter titles.
8. **Process order is inverted.** ~3 weeks/video: two weeks *story* research →
   a beat sheet naming every scene → *then* video research per scene → edit. We
   generate a script from facts and hunt footage matching sentences.
9. **It is a universe.** Characters recur; outros hand you the next film inside
   the same world.
10. **Breathing room.** He lets moments sit with music and no speech. We have
    zero.

### Operator decisions taken during design

| Question | Decision |
|---|---|
| Fitness-utility channel or story channel? | **Both.** The workout stays the product; the story is what makes it land. |
| Emotional engine | **The Wound** — something broke them, the body became the answer. |
| Infographic cards | **Kept**, but confined (see §2, Protocol Act). |
| Runtime | **~30 min** (longer runtime, more mid-rolls). |
| Titles | **Stay searchable** — Gavia hook in front, search terms behind. |
| Universe / cross-linking | **Yes.** Superman → Batman → Spider-Man. |
| Real archival voices | **Yes — primary track.** |
| Antagonist | **Yes.** |
| Music | **Royalty-free**, Content-ID-verified. |
| Prototype subject | **Jimmy Donaldson / MrBeast.** |
| Old 10-min format | Retired. One product. |

---

## 2. The format

**A Celeb Workout film is a 30-minute Wound story with a Protocol Act at its
center.**

Five rules replacing the old format rules:

1. **Real voices are the primary track.** Target **≥40% of runtime** carrying
   real archival audio. Narration narrates a documentary; it does not present an
   essay. Side benefit: roughly halves the TTS bill on a 30-minute film.
2. **The cold open withholds; the final chapter pays it off.** Non-negotiable.
   Every film owes the viewer an answer it does not give for ~27 minutes.
3. **A named antagonist, and it escalates.** Act 1's antagonist is *replaced* by
   a worse one in Act 2. Act 3 resolves the relationship, not necessarily the
   conflict.
4. **Chapters are hooks**, never topics.
5. **The Protocol Act is a hard, announced tonal shift** — title card plus music
   change — so it reads as the film delivering on its promise, not an ad break.
   **Cards exist only inside it.**

### Structure

```
00:00  COLD OPEN         film, no cards, withholds
  ...  ACT 1 — the wound  film, no cards
  ...  ACT 2 — the machine film, no cards
14:00  THE TURN           transition beat, primary document
15:30  ▉ PROTOCOL ACT ▉   cards, the full workout + diet, 6–8 min
23:00  ACT 3 — the price  film, no cards
27:00  PAYOFF             cold-open promise resolves
29:00  OUTRO              cinematic shot + narrated universe hook
```

Chapter markers in the description make the Protocol Act skip-to-able, which
protects search traffic from viewers who came for the workout.

### Segment types

The script is a **cut list**, not prose. Four types interleave:

- `BITE` — real archival audio, plays with its own audio, J-cut (audio leads
  picture 0.4s)
- `NARR` — our voiceover
- `CARD` — Remotion graphic; **Protocol Act only**
- `BEAT` — music and picture, nobody speaking. New. Minimum silence budget
  enforced in QC.

---

## 3. Prototype: MrBeast

**Title:** `The Disease That Built MrBeast | His Real Workout & Diet`
(Gavia hook in front, search terms behind.)

**Thesis:** *He spent his teens unable to control his own body. So he built an
empire controlling everything else. The 310 days were him finally going back for
the one thing he'd lost.*

**Why this subject is unusually strong:**

- **The wound is medically literal.** Crohn's diagnosed in ninth grade. Ten
  bathroom trips a day at fifteen. Thirty pounds lost in one summer. His words:
  pain like *"someone's stabbing you in the gut with a knife constantly."*
- **The best antagonist the channel will ever get: his own immune system.** His
  own explanation — *"your immune system in your gut thinks your gut is a
  foreign invader, so it just starts attacking itself."*
- **The answer is absurdly copyable**, which is the point for this channel:
  12,500 steps daily, a signed training contract with another creator, 310
  consecutive days, ~2 hrs/day training and meal prep, 40%+ → sub-20% body fat.
- **His own channel is the medical record.** He has uploaded his own face since
  age 13. A 2013 → 2016 → 2019 → 2023 cut physically shows the illness take him
  and the rebuild bring him back. No other subject has filmed their own
  before-and-after weekly for a decade without knowing it.
- **The largest soundbite bank available:** Diary of a CEO (where he opened up
  about Crohn's), Rogan, Colin & Samir, plus Chris, Chandler, Karl and Nolan on
  record about him, plus 13 years of his own voice at every age.

### Cold open — "The Kid Who Was Disappearing"

Real 2013 footage: fifteen-year-old Jimmy doing a bit to camera, visibly gaunt,
laughing.

> *He's fifteen here. He's just lost thirty pounds in a single summer, and he's
> going to the bathroom ten times a day. Nobody watching this video knows that.
> He won't say it out loud for another eight years. But it's on camera the whole
> time — you just have to know where to look.*

### Beat sheet

| Time | Chapter | Carried by |
|---|---|---|
| 0:00 | **The Kid Who Was Disappearing** | his own 2013 archive |
| 02:00 | **Ten Times a Day** | Jimmy on Diary of a CEO — diagnosis, the knife quote |
| 06:00 | **Hard Mode** | Remicade, *"nuke your immune system"*, six COVIDs, shingles, hospitalizations |
| 10:00 | **The Machine** | Chris/Chandler/Karl on the 100-hour years; 40%+ body fat; the body he stopped noticing |
| 14:00 | **The Contract** | the turn — a literal signed agreement to train daily. Primary document on screen (F5). |
| 15:30 | **THE 310 DAYS** ▉ | **PROTOCOL ACT.** Steps, lifting, diet, the adherence system, 40% → sub-20% |
| 23:00 | **The Thing That Doesn't Go Away** | Crohn's is incurable; flare-ups continue |
| 27:00 | **What He Was Hiding** | payoff — replay the cold-open 2013 clip; same frames, now legible |
| 29:00 | outro | cinematic shot + narrated universe hook |

**Antagonist escalation:** Act 1 the disease → Act 2 *himself*, the machine he
built to outrun it → Act 3 the disease returns, permanently. The ending is not
victory. He trains anyway. Honest, and a better motivational payoff than "and
then he got shredded."

### Fact-sourcing gate

The 310 days, the training contract, and the body-fat figures currently rest on
secondary fitness-press coverage. **Every one must be sourced back to Jimmy's own
words or a primary document before a frame is cut. Anything that will not source
is dropped, not softened.** (Existing rule: never fabricate.)

### Flow / Veo budget

~$1 per film (operator budget: $20 for 20 films). **Two symbolic shots only:**
an empty school hallway under the "ten times a day" beat, and abstract
inflammation imagery under the immune-system line.

**Hard guardrail: no synthetic depiction of a real person, ever.** AI-recreating
a living person's private medical moments violates the no-fabrication rule and
reads as fake. Symbolic imagery only. Key lives in gitignored `flow_key.txt`
alongside `elevenlabs_key.txt`.

---

## 4. Production architecture

### 4.1 The core inversion

Current: Claude writes a script → we hunt footage matching sentences.
New: **research → beat sheet → soundbite bank → script written to the bank.**

The script must be written against material we actually have, so the bank is
built *before* the script exists.

### 4.2 Soundbite Bank — the major new component

`pipeline/soundbank.py` → `manifest/soundbites.json`

Download long-form sources whole; transcribe with faster-whisper (word
timestamps + diarization — YouTube VTTs are unpunctuated and unusable for this,
established in v7). Index every utterance:

```json
{"source_id": "...", "t0": 0.0, "t1": 0.0, "speaker": "...", "text": "...",
 "topic_tags": [], "emotion": "...", "on_camera": true, "audio_clean": true}
```

Target **300+ indexed candidates → ~70 in the finished film.**

Reusable across episodes: Jimmy on Crohn's is evidence in any future
creator-fitness film.

### 4.3 Audio — v10 breaks; v11 replaces it

`v10_assemble` assumes *one continuous narration river with 6–8 islands
crossfaded in*. Sixty-plus interleaved bites is not that shape.

**`pipeline/v11_assemble.py`** — a genuine audio EDL: explicit offsets, one
encode, one loudnorm. Every F7 lesson preserved:

- TTS per **narration run** (contiguous 15–45s passage), ~25–35 generations —
  never per-beat (per-beat AAC re-encodes put an audible glitch at every join)
- butt-join with 30 ms edge fades; **never** acrossfade (each crossfade overlaps
  inputs, shortening total audio ~0.3s per junction → cumulative A/V drift)
- `amix` with `normalize=0`; `aformat` everything to stereo before mixing
- **hard sync gate:** refuse to mux if `|video_dur − audio_dur| > 0.25s`

**Risk: this is the most likely source of bugs.** Build and prove v11 on a
3-minute slice before committing 30 minutes to it.

### 4.4 Music — scored, not bedded

One bed at 0.16 with ducking suits a 10-minute explainer. A 30-minute emotional
arc needs **4–6 cues entering and exiting on chapter boundaries.**

Build `library/music/` once: **20–30 royalty-free, Content-ID-verified tracks
tagged by dramatic function** — `dread / grind / the-turn / protocol / elegy /
payoff`. Scoring an episode then becomes selection, not search.

- **YouTube Audio Library** is the spine (cannot be claimed against us)
- Pixabay and Uppbeat fill gaps, **each verified before entering the library**

### 4.5 Agent fleet

Respects the existing ≤5-concurrent-during-production rule (weekly-limit
protection); fan out wide only on read-only work.

| Fleet | Width | Job |
|---|---|---|
| Research | 8–10 | one per chapter — every claim to a primary source or cut |
| Transcribe / index | 1 per source | build the soundbite bank |
| Bite selection | 1 per chapter | pick the ~70 that carry the film |
| Production | **≤5** | download, cut, render |
| Verification | wide | one agent per ledger rule F1–F12 + §4.6 |

### 4.6 New QC gates

On top of the existing F1–F12 pre-delivery checklist. All machine-measurable:

- real-voice ratio **≥40%** of runtime
- **zero** cards outside the Protocol Act
- cold-open promise resolves in the final chapter
- minimum silence/`BEAT` budget met
- no single supporting speaker exceeds 90s total
- every fact traced to a primary source in `story/facts.json`

### 4.7 Universe

`library/universe.json` — a subject graph with cluster edges (superhero actors,
transformation-for-role, creators, action stars).

Outro adopts Gavia's exact move: a cinematic shot of the subject plus a
**narrated story hook** into the next film — not a card. e.g. *"If you want to
know what happens to a body that's built for one role and then has to give it
back — that's the Hugh Jackman film."*

### 4.8 Budget

| Item | Cost |
|---|---|
| Narration | ~18 min ≈ 15k chars ≈ **7,500 ElevenLabs credits** (turbo, 0.5 cr/char) |
| | Starter 30k/mo ⇒ **4 films/month** |
| Flow / Veo | ~$1/film, 2 shots |
| Music | $0 (royalty-free) |
| Render | ephemeral DigitalOcean droplet, always destroyed |

---

## 5. Carried forward unchanged

The entire **FEEDBACK LEDGER (F1–F12)** and the pre-delivery checklist in
`.claude/skills/celebvid/SKILL.md` remain in force. Of particular relevance
under the new format:

- **F3** shot-precise cuts — no window crosses a detected shot boundary
- **F4** fitness-first footage ratio — *reinterpreted*. The old blanket "≥60% of
  footage beats show training content" does not survive contact with a story
  film: Acts 1–3 are narrative and will legitimately show a man in a hospital,
  a bedroom, a boardroom. Replaced by two separate thresholds, both measured on
  **picture**, not audio (do not confuse either with the ≥40% *real-voice audio*
  ratio in §4.6):
  - Protocol Act: **≥90%** of footage beats show training, physique, or food
  - Whole film: **≥35%** of footage beats show training, physique, or food
- **F5** primary documents on screen for central claims
- **F7** audio architecture — see §4.3
- **F9** channel branding — Anton condensed uppercase, channel red `#E3120B`,
  logo bug, brand sting
- **F10** source hygiene — reject third-party watermarks, blurred pillarbox,
  upscales
- **F11** machine-scan every cut window before ship
- **F12** loop windows must actually loop

---

## 6. Implementation phasing

This spec is larger than one plan. It decomposes into three, executed in order,
each independently verifiable:

1. **Infrastructure** — `soundbank.py`, `v11_assemble.py` (proven on a 3-minute
   slice first), `library/music/`, the §4.6 QC gates. No film shipped; the
   deliverable is a pipeline that passes its own gates on a slice.
2. **The MrBeast film** — research fleet → beat sheet → bank → script → cut →
   render → full F1–F12 + §4.6 pre-delivery pass.
3. **Universe** — `library/universe.json`, outro hook generation,
   cross-linking. Only meaningful once film #2 exists; deferrable.

## 7. Open items

- Operator to confirm whether the retired 10-min format should stay runnable
  (assumed: no).
- `library/music/` must be built and verified before the first score pass.
- MrBeast source copyright: his uploads are aggressively Content-ID'd. Fair-use
  commentary is normal for the genre; plan short windows and heavy
  transformation. Not a blocker, but needs a claims check on a test upload
  before the full render.
