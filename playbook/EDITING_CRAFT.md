# EDITING_CRAFT — Celeb Workout edit playbook (v1, 2026-11-21)

Scope: 15-25 min celebrity workout/diet docs. Celebrity + trainer bites carry the film, Kokoro narrator bridges, real photos, full-frame glass cards (HyperFrames/Remotion), FFmpeg assembly, licensed bed.
Targets the owner's three complaints: (1) cuts too abrupt, (2) music doesn't fit the moment, (3) basic transitions and graphics.

> **CONFLICT TO RESOLVE FIRST.** `~/.claude/skills/celebvid/SKILL.md` (V16) says **"NO MUSIC BED AT ALL"**, quoting the owner: *"Remove the complete background audio track… don't put sound over their voice."* This brief asks for a licensed bed with ducking. Section 4 is written so both can hold: **no music under any bite**, a bed only under narration, stingers and breathers. The owner must pick: A) the bed as in §4, B) no bed but stingers and transition SFX allowed, C) keep V16 with no music at all.

---

## 1. Nate Herk: observed vs claimed

Sources: transcripts and 480p frame sheets of `7jHXoPGnA4c` ("Opus 5.5 Just Changed Video Editing Forever", 325k views) and `DByAR5Su1Yw` ("Make it better 100 times", 874k, his top recent video). I also read the transcript of `o3IEkKXXXvo` ("GPT-6 Astra Finally Solves AI Video Editing"). Notes and frames are in `research/nate/`. I found no interview with Nate or his editor about his process. Everything below comes from his videos.

**What he says he does** (the 16:12 segment of 7jHX, which is his process):
1. **Transcribe first** (Whisper or ElevenLabs) so "beats come in at the exact right time".
2. **Cut** mistakes and dead space.
3. **Plan the beats.** Name the exact line where each graphic lands ("when I say *best outputs ever*, put those three words at the bottom and highlight them"). Specify the **emotion** you want the viewer to feel, not only the visuals.
4. **Build skills from references.** He downloads a video he likes, has the model work out "why this is so good", saves that as a skill, then after every run edits the skill with "liked this / didn't like this".
5. **Verification loop** ("most important"). The agent renders, screenshots, watches its own output and iterates five or six times before a human sees it.
- Every overlay gets a **liquid-glass card or scrim behind it** "otherwise it will be hard to see".
- He admits the AI cut still had "an awkward cut of the speech". That is the same defect our owner raises.

**What the frames show:**
- **Cold open (0-27s) is a separately designed piece.** It has 18 scene changes in 27s (about 1.5s per shot), a red/black YouTube showreel, kinetic type ("BROADCAST YOURSELF" ticker, "500+" stat, "+10s" full-bleed red card) and a 3D play-button render. Then it **drops straight to calm talking head** at 0:28. The contrast is the hook.
- **Graphics are anchored to the spoken word.** Glass pills with logos ("Fable 5.1", "GPT-6 Astra") slide in **on the side he points to**, at the moment he names them. A lower-third phrase gets word highlighting. Small labelled glass cards ("Screen recording", "Generated image", "Verification") come in **left and right of the face, never over it**.
- **There is a constant subtle push-in** on the A-roll, which he says the AI added unprompted.
- **The body of the video holds shots for a long time.** After the intro, scene changes drop to roughly one every 9-90s. The screen-share sections stay on one layout (face cam at bottom left, content at right) for 40s or more. Novelty comes from what changes on screen, not from cuts.
- **The hook formula (DBy, 0-40s):** "I did [extreme experiment], here's what happened". The premise and the exact prompt are on screen by 0:20, the stakes ("it used to stop at 20-25") come next, and there is **no channel intro**.
- **Audio:** the cold open is wall-to-wall music and SFX, with one gap of 0.34s or more in 50s. The body is voice only.
- **Outro** is a fixed formula ("if you enjoyed… like… see you in the next one", plus a playlist pointer) and takes about 10s.

**What to take from him:** (a) a designed, music-driven cold open that hands off to a calmer body; (b) every graphic keyed to a word timestamp and placed away from faces on a glass backing; (c) slow, constant camera motion so nothing is static; (d) a reference-to-skill loop plus a self-verifying render loop. His body pacing is a talking-head tutorial, so it is not a model for a documentary. Take his **graphics and verification method**, not his A-roll rhythm.

---

## 2. Current best practice (2025-2026), condensed

- **YouTube (primary source):** "Intro" means the % still watching at 30s. A high figure means the open "matched the viewer's expectation of the thumbnail and title". Dips are where viewers skip or abandon. If top moments sit late in the video, move strong content earlier. ([YT Help 9314415](https://support.google.com/youtube/answer/9314415))
- **Mario Joos (former MrBeast retention strategist):** *"It's not the cutting speed, it's the speed at which you introduce progressive novel information."* Don't stack non-progressive beats. Fast cuts without a reason don't help. The 70% retention target is a "myth". Compare against your own similar videos. ([Vidpros](https://vidpros.com/retention-editing-what-you-can-learn-from-mario-joos/))
- **AIR audit of 100 long-form channels:** stakes inside 15s and a pattern interrupt at 25-35s. A re-hook every ~2 min. A static talking head past 40s flattens retention. About 2s of dead air reads as the video ending. For ages 25+ (our audience), visual change every 20-40s and only on topic or tone shifts. The "Contrast" pattern (calm sections plus 5-10-cut bursts every 2-3 min) and the "Anchor" pattern (cuts on emotional beats) suit documentaries. Music sits 20-25 dB under the voice in calm sections and 8-12 dB under in energetic ones. ([AIR](https://air.io/en/youtube-hacks/advanced-retention-editing-cutting-patterns-that-keep-viewers-past-minute-8)) Treat these as secondary-source numbers.
- **Documentary editors:** linger on a reaction a beat longer, then let music carry into the next scene. Start the track late or drop the music to land an emotional delivery. Silence lets the audience "gather themselves before the next chapter" ([LBB](https://lbbonline.com/news/the-responsibility-of-making-someone-cry-editors-spill-their-secrets), [Vimeo/Brian Hall](https://vimeo.com/blog/post/when-silence-is-better-than-a-soundtrack)). Scenes should flow into each other ("they don't just stop and a new one starts"), and the picture gets finessed *after* the music ([Frame.io](https://blog.frame.io/2017/06/19/a-musical-approach-to-cutting-documentaries/)). Don't cut audio and video at the same time (J/L cuts), which is standard in interview docs ([CreativeLive/Griffin Hammond](https://site.creativelive.com/class/street-filmmaking-creating-content-from-real-world-events-griffin-hammond/lessons/editing-j-and-l-cuts)). Sync cuts to the beat work, but skip beats so the pattern doesn't become predictable ([Adorama](https://www.adorama.com/alc/editing-cuts-in-video/)).
- **Motion design systems:** entrances decelerate, exits accelerate and run 50-100ms shorter. Productive entrances take ~200ms and expressive ones ~500ms ([Microsoft Fluent](https://learn.microsoft.com/en-us/windows/apps/design/motion/timing-and-easing), [Atlassian](https://atlassian.design/foundations/motion), [Cognite Aura](https://docs.cognite.com/aura-design-system/foundations/motion)).
- **HyperFrames' own transition guide** (local skill `hyperframes-animation/transitions/overview.md`): one primary transition for 60-70% of scene changes plus 1-2 accents. Calm takes 0.5-0.8s (`sine.inOut`), medium 0.3-0.5s (`power2/3`), high 0.15-0.3s (`power4/expo`). **The transition is the exit**: outgoing and incoming elements animate at the same time T.
- **Chapters** ([YT Help 9884579](https://support.google.com/youtube/answer/9884579)): first at 00:00, at least 3, each at least 10s.
- **Loudness:** YouTube normalises to about -14 LUFS integrated.

---

## 3. CUT RULES (complaint 1: "cuts off too quick")

All times come from **word-level timestamps** (WhisperX or ElevenLabs) **plus VAD** (silero-vad, 30ms frames). Never use sentence-level SRT.

| ID | Rule | Number |
|---|---|---|
| C1 | **Bite in-point** sits inside the silence before the first word | at least **200ms** before word-1 onset (VAD), 350ms target; never inside a breath that begins a word |
| C2 | **Bite out-point** comes after the thought ends | at least **500ms** after the last word's end; **800-1200ms** if `emotion ∈ {vulnerable, triumph, funny}` (lets a laugh or exhale land) |
| C3 | **Snap every edit point to silence** | the cut frame must fall in a VAD-silent run of **≥120ms**; move up to ±400ms to find one, otherwise reject the bite |
| C4 | **A bite ends on a complete thought** | the last token ends in `. ! ?` **and** is not in `{and, but, so, because, which, that, or, um, uh, like, you know}`; reject a bite if the next word starts within 250ms with lowercase continuation |
| C5 | **A bite starts clean** | the first token is not a mid-sentence continuation (lowercase after no punctuation, or a conjunction); no interviewer voice inside the bite (diarization) |
| C6 | **Audio edge fades** on every bite | 40ms fade-in and **150ms fade-out** (a tail fade, not a chop); room tone continues under the next shot (C9) |
| C7 | **Breathing room after a bite** | gap from bite end (last word) to next narrator word: **≥0.7s**, 1.2-2.0s after emotional bites; **≤2.0s** of true silence, or music/picture must carry it |
| C8 | **J-cut into a bite** (on ~50% of bites) | the bite's audio starts **300-600ms** before its picture; the old shot is still on screen as the voice enters |
| C9 | **L-cut out of a bite** | the speaker's picture holds **500-1000ms** past the last word, *or* the bite's room tone runs **400ms** under the next picture with a 200ms fade |
| C10 | **Narrator paragraphs breathe** | **350-600ms** between Kokoro sentences in a paragraph, **700-1000ms** between paragraphs (Kokoro chunks join with no gap by default, which is the "exhausting" defect V16 measured) |
| C11 | **Shot holds** | stills with motion **5-10s** (V16 rule 8-12s still stands for b-roll); **minimum 2.5s** for any shot except deliberate montage bursts; nothing static over **12s** without new motion, overlay or reframe |
| C12 | **Montage bursts** (Contrast pattern) | 5-10 cuts of 0.8-1.5s, snapped to the beat, **at most one burst every 2-3 min**, never over a bite |
| C13 | **Cards hold for reading time** | `hold = max(4.0s, 1.2s + 0.28s × words_on_card)` after the entrance completes |

**Implementation (Python plus FFmpeg):**
```python
# snap a proposed cut to the nearest silent run (VAD frames: list of (t0,t1,is_speech))
def snap(t, vad, min_sil=0.12, search=0.4):
    sil = [(a,b) for a,b,s in vad if not s and b-a >= min_sil]
    cands = [min(max(t,a+0.04),b-0.04) for a,b in sil if a-search <= t <= b+search]
    return min(cands, key=lambda x: abs(x-t)) if cands else None  # None => reject bite
in_pt  = snap(words[0].start - 0.35, vad)
out_pt = snap(words[-1].end + (1.0 if emo in EMO_LONG else 0.6), vad)
```
```bash
# cut a bite with a clean tail (no chop), keep source tc
ffmpeg -ss $IN -to $OUT -i src.mp4 -af "afade=t=in:d=0.04,afade=t=out:st=$FADE_ST:d=0.15"   # FADE_ST = (OUT-IN)-0.15, computed in Python -c:v libx264 -crf 16 bite.mp4
# J-cut: delay the bite's picture by 0.45s against its audio when overlaying onto the outgoing shot
ffmpeg -i prev.mp4 -i bite.mp4 -filter_complex "[1:v]tpad=start_duration=0.45:start_mode=clone[v1];..." 
```
In practice, J/L cuts are far easier in the HyperFrames/Remotion timeline: put the bite `<audio>` at `start = picture_start - 0.45`.

---

## 4. MUSIC RULES (complaint 2: "music and tone don't match")

**The cue sheet is driven by words, not chapters** (the V16 lesson). Each narration sentence and bite gets an `emotion` tag from an LLM pass over the transcript, chosen from 8 tags. Each tag maps to a music family:

| Tag | When | Music | Bed level vs voice |
|---|---|---|---|
| `hook` | cold open | pulsing, rising tension, 90-110 BPM | -10 dB (music-forward), full level when no voice |
| `origin` | childhood, early career | soft piano, ambient, 60-80 BPM | -22 dB |
| `struggle` | injury, rejection, body image | sparse, minor, low strings, or **nothing** | -24 dB, or out |
| `grind` | training method, routine | driving percussion, 110-125 BPM | -16 dB |
| `science` | trainer explains why | light pulse, curious, plucked | -20 dB |
| `diet` | meals, macros | warm, lifestyle, mid-tempo | -20 dB |
| `triumph` | transformation, results | swell, major, builds | -14 dB, swell +6 dB in the gap after |
| `outro` | takeaway, CTA | resolve of the main theme | -18 dB, then full for the last 8s |

| ID | Rule | Number |
|---|---|---|
| M1 | **Change cue when the tag changes**, not when the chapter does; merge runs shorter than **25s** into the neighbour (no jitter) | cue length 25s to 3 min; over 3 min, switch to a variation or stem drop |
| M2 | **No music under any bite** (V16 owner rule): duck to **-inf** (or -30 dB) across the bite, using the bite's C1/C2 handles | duck attack **250ms** before bite audio, release **600ms** after |
| M3 | **Ducking under narration** if the bed is kept | bed sits **18-24 dB** under the voice (calm), **10-14 dB** under (energy); sidechain attack 80-120ms, release 400-700ms |
| M4 | **Cue changes happen in a gap**, never under a word | change in a C7/C10 pause; reflective → reflective uses a **2-3s** equal-power crossfade; energy shift uses a **hard switch on the incoming track's downbeat**, with a 1-beat pre-fade on the outgoing track |
| M5 | **Music stop for impact**: before the 2-4 biggest reveals (the weight, the transformation, the trainer's key line) | music out **0.6-1.2s** before the line (fade 300ms), true silence or room tone; re-enter on a downbeat after the payoff, or don't |
| M6 | **"Music-up" breathers** at chapter turns | 2-4s with no voice, bed up to full (-14 LUFS short-term) under the chapter card; **one per chapter**, beat-aligned |
| M7 | **Cut on the beat** only for montage bursts, chapter cards and the cold open | cut frame within **±60ms** (2 frames) of a detected beat; skip beats so cut intervals vary |
| M8 | **Bed EQ** | high-pass at **200-220Hz** (existing V16 finding), -3 dB bell at 2.5 kHz under narration (voice carve) |
| M9 | **Final loudness** | `loudnorm=I=-14:TP=-1.5:LRA=11`, two-pass |
| M10 | **SFX palette** (subtle) | whoosh on full-frame card entrances, riser into chapter cards, soft "tick" on number count-ups, impact on title slam; SFX at **-18 to -22 dB** under voice, never over a bite |

**Implementation:**
- Beats: `librosa.beat.beat_track(y, sr, units='time')` per track. Store `beats[]` and `downbeats[]` (use `madmom` or a 4-beat phase guess).
- Duck envelope: generate a per-sample gain curve in numpy from the bite and narration intervals (cheaper and more exact than sidechain), then apply with FFmpeg `volume` expression or by multiplying arrays:
```bash
# sidechain alternative (bed ducked by the voice stem) + loudnorm
ffmpeg -i bed.wav -i voice.wav -filter_complex \
 "[0:a]highpass=f=210,equalizer=f=2500:t=q:w=1.2:g=-3[b];[1:a]asplit[v][sc];\
  [b][sc]sidechaincompress=threshold=0.02:ratio=12:attack=90:release=550:makeup=1[bd];\
  [bd][v]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11" mix.wav
```
- Crossfade between cues: `acrossfade=d=2.5:c1=qsin:c2=qsin`.
- HyperFrames: `<audio data-start data-duration data-volume>`. Use the `hyperframes-audio` skill's duck parameters (`duckDb`) and its "Voiceover carve" job. Remotion: `<Audio volume={(f)=>duckCurve[f]} />`.
- Write `qc/CUE_SHEET.md`: one row per cue with `t_in, t_out, tag, track, why (quote of the words)`.

---

## 5. TRANSITIONS AND GRAPHICS (complaint 3: "incredible, not basic")

**Transition palette.** Pick one primary and two accents per film. Never vary for its own sake.

| Situation | Transition | Duration | Ease |
|---|---|---|---|
| Within a chapter, photo → photo (same thought) | **straight cut on a pause** or a **0.4s blur-dissolve** with a continuous push-in carried across | 0-0.4s | sine.inOut |
| Narrator b-roll → bite (speaker appears) | **cut** (made smooth by the J-cut in C8) | 0 | none |
| Bite → b-roll | **cut** plus L-cut (C9), or **0.5s blur crossfade** after emotional bites | 0.5s | power1.inOut |
| Into a full-frame glass card | **frosted push**: the background blurs from 0 to 30px and darkens 30% while the card scales 0.94→1 | 0.5-0.6s | power3.out / `cubic-bezier(.16,1,.3,1)` |
| Card → back to picture | **card lifts away** (y -40px, opacity → 0, blur) as the photo de-blurs underneath | 0.35-0.45s | power2.in |
| **Chapter change** (never a hard cut) | **light-leak / flash-through-white** or **whip-pan with motion blur**, into a chapter title card on a music-up (M6) | 0.6-0.9s | expo.inOut |
| Era jump (then → now) | **film-burn / match-cut on the face** (align eyes to within 10% of frame position) | 0.6s | sine.inOut |
| Montage burst | hard cuts on the beat plus a 2-frame white flash on the downbeat accent | 0.07s | none |
| Cold open → title | **impact slam**: the title scales 1.15→1 with a 1-frame white flash, SFX impact | 0.25s | power4.out |

**Banned:** star wipes, spins, page-curls, cube-3D, default "slide" on every cut, a different transition on every cut, and dissolves longer than 1s inside a chapter.

**Graphic animation specs (HyperFrames GSAP / Remotion spring):**
- **Entrance:** 450-600ms, `power3.out` (`cubic-bezier(0.16,1,0.3,1)`). Translate y 24-40px plus opacity 0→1 plus blur 8→0px. Children stagger **60-90ms**.
- **Exit:** none. The transition is the exit (HyperFrames rule). If it is forced: 250-350ms `power2.in`.
- **Numbers:** count up over 0.9-1.3s on `expo.out`. The final value lands with a 1.04→1 scale pop plus a "tick" SFX.
- **Never static:** every card and still drifts continuously (scale 1.00→1.04 over its hold, or parallax layers at 0.5x/1x/1.5x). This is the depth push-in V16 already uses.
- **Glass card style:** `backdrop-filter: blur(28px) saturate(140%)`, fill `rgba(18,18,22,.55)`, 1px border `rgba(255,255,255,.16)`, radius 28px, shadow `0 30px 80px rgba(0,0,0,.45)`, one accent colour (brand red), and a large numeral or ring as the hero element. **Every card is a different format** (ring, gauge, counter, bar, split, timeline, real article screenshot), per V16.
- **Word-anchored timing (Nate):** a graphic's entrance completes **at or 100ms before** the spoken word it illustrates (from word timestamps). It is never later than **+150ms**.
- **Placement:** overlays avoid faces (face box from a detector, 10% padding). Lower-thirds sit in the bottom 18% of frame.
- **Name lower-third** on each speaker's first bite: 500ms in, hold 3.5s, out by the time the bite reaches 50%.
- **Kinetic type** only for the cold open, chapter cards and at most 3 "big line" pull-quotes per film. Highlight words with a colour sweep (`gradient-text-sweep`, 400ms) timed to the spoken word.
- **Captions:** burned-in, word-by-word highlight, 2 lines max, 42 characters per line max, bottom-centre at 12% safe margin. Inter/Montserrat semibold at about 54px for 1080p, white with a 60% black pill, active word in the accent colour. Shown **only on bites** (accents, crosstalk). Narration is clear TTS, so upload an SRT for CC instead of burning it in. Remotion: `@remotion/captions` `createTikTokStyleCaptions` with `combineTokensWithinMilliseconds: 1200`.

---

## 6. STRUCTURE

**Hook template (0:00-0:60):**
| t | Beat |
|---|---|
| 0-3s | **Celebrity's own most striking bite** (cold, no logo), or a then/now photo split with a number |
| 3-12s | **Promise and stakes** in one narrator line: "how [name] went from X to Y at [age], and what their trainer says actually did it" (must match title and thumbnail) |
| 12-25s | **Proof burst**: 5-8 beat-cut shots and 2 flash cards (the number, the meal, the move), music-driven, the Nate-style cold open |
| 25-35s | **Pattern interrupt**: music stop (M5) and the trainer's surprising line ("He didn't do cardio") |
| 35-50s | **Open loop**: "But the thing that changed everything came in [year], and it wasn't the workout." |
| 50-60s | Title slam and chapter 1 card on a music-up |

**Chapters (18-22 min film):** 6-8 chapters of 2-4 min, for example: Hook → Origin → The Turn (role or injury) → The Training → The Diet → The Science (trainer) → The Hard Part → The Result & Takeaways. Each chapter opens on a re-hook or open-loop line within its first 15s and closes a loop opened earlier. Plant one forward-reference every ~2 min ("we'll get to the cheat meal"). Description chapters: first at 00:00, each at least 10s.

**End:** the takeaway card (a 3-item glass list), then one narrator CTA line naming a specific next celebrity video. **End screen for the last 15s** (YT allows 5-20s): the bed resolves at full level, the background is a slow-drift hero photo, the left 60% of the frame is left clear for the 2 end-screen elements, and there is no new information.

---

## 7. AUTOMATABLE EDIT-QUALITY EVAL (`qc/edit_eval.py`, blocking)

Inputs: EDL JSON, word timestamps (re-transcribed from the **rendered** audio), VAD on the final mix and on the voice stem, cue sheet, beats, and a scene-cut list (`ffmpeg select='gt(scene,0.3)'`).

| # | Check | Pass |
|---|---|---|
| E1 | No cut within **250ms after** any word end or **150ms before** any word onset (voice stem) | 0 violations |
| E2 | Every bite's last token ends in `.!?`, is not a conjunction or filler, and is not followed by a same-speaker word within 250ms in the source | 100% |
| E3 | Bite pre-roll ≥200ms and post-roll ≥500ms (≥800ms for emotional tags) | 100% |
| E4 | Gap after a bite before the narrator ≥0.7s; gap between narrator paragraphs ≥0.7s; **no silence >2.0s** without music or SFX in the mix | 100% |
| E5 | Pause density: **≥1 pause of 0.35s or more per 30s** of runtime (V16 baseline: the reference had 11 in total; zero = fail) | ≥ target |
| E6 | Bite audio re-transcribed from the render matches `quotes.json` word for word (WER ≤ 3%) | pass |
| E7 | Music RMS during bites is ≤ -30 dB relative to voice (or absent); during narration it is in the tag's band ±3 dB | 100% |
| E8 | Every cue change falls in a voice-silent gap; cue tag equals the dominant emotion tag of the words in its span (LLM judge on `CUE_SHEET.md`) | ≥90% agree |
| E9 | At least 2 music stops (M5) and at least 1 music-up per chapter (M6) | present |
| E10 | Chapter boundaries use an approved non-hard transition of 0.6-0.9s (EDL `transition != "cut"`) | 100% |
| E11 | No shot shorter than 2.5s outside montage bursts; no static frame (SSIM >0.995 for consecutive frames) over 4s; no visual change gap over 40s | 0 violations |
| E12 | Montage cuts within ±60ms of a beat | ≥90% |
| E13 | Graphic entrance completion is within [-300, +150]ms of its anchor word | ≥95% |
| E14 | No transition type is used for more than 70% of non-cut transitions, and no banned types | pass |
| E15 | No overlay intersects a detected face box | 0 |
| E16 | Card hold ≥ reading-time formula (C13) | 100% |
| E17 | Hook: first bite or striking visual ≤3s; promise line ≤15s; scene-change count in 0-30s ≥8; a music stop or interrupt between 25-40s | pass |
| E18 | Chapters: at least 3, first at 0:00, each at least 10s; description timestamps generated from the EDL | pass |
| E19 | Final loudness -14 ±1 LUFS, TP ≤ -1.5 dBTP (`ffmpeg -af ebur128`) | pass |
| E20 | **Visual verification loop (Nate's step 5):** render a contact sheet at 1 frame per 2s for 0-60s, every chapter boundary ±3s, and every card. A vision-model judge scores readability, face occlusion, brand consistency and "does this look premium" against the reference build; anything under threshold goes back into the build loop, **max 3 iterations**, before the owner sees it | ≥ threshold |

Plus the existing V16 gates (echo_check, one clip per source, branded-frame check, A/V sync gate).

**Process change from Nate:** keep `refs/` with 2-3 reference videos the owner likes. Run "why is this good" analysis once and save it as `celebvid/STYLE.md`. After every owner review, append liked and disliked items to that file. Every build reads it.
