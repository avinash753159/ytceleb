# Celeb Workout: Final Assembly Prompt (v3, 2026-11-21)

Paste this whole file into Claude Code AFTER the YouTube copyright pass (Step 3 below).
Fill in the Project Variables first. Everything else stays as written.

---

## The 3-step workflow (do these in order)

1. **Build the first cut.** Read both repos, then make the video:
   - https://github.com/avinash753159/celebworkout-editor-kit (start with `.claude/skills/celebvid/SKILL.md`, section 0 "Standing Rulings", then `docs/channel/EDIT_RULES.md`, `docs/channel/COPYRIGHT_RULES.md`, `reference/jordan_v1/OWNER_EDITS.txt`)
   - https://github.com/avinash753159/ytceleb (older automated pipeline, Remotion graphics, research notes, this prompt)
2. **Upload the first cut to YouTube as UNLISTED.** Open YouTube Studio > Content > the video > Copyright. For every claim, use "Trim out segment" (or "Mute song" for music claims). Wait until YouTube finishes processing the edit. Write down every removed segment (start, end, what it was) in `YOUTUBE_CLAIMS.md`.
3. **Download the edited (claims removed) version** from Studio and run THIS prompt on it. The output is the final film.

Before anything goes public: **watch the full final video yourself**, start to finish, with sound. Claude's QC does not replace your eyes and ears.

---

## Project Variables (edit these per video)

- **SUBJECT_NAME:** [e.g., Miley Cyrus]
- **TRAINER_NAME:** [e.g., Tracy Anderson, or "none known"]
- **TOPIC_ANGLE:** [e.g., Real workout routine, athletic training, and diet]
- **INPUT_VIDEO_PATH:** [the Studio-edited download, e.g., C:\Users\you\Downloads\MILEY_YT_EDITED.mp4]
- **FIRST_CUT_PROJECT:** [folder of the Step 1 build: script, quotes.json, sources, images]
- **YOUTUBE_CLAIMS:** [path to YOUTUBE_CLAIMS.md from Step 2]
- **OUTPUT_VIDEO_PATH:** [e.g., C:\Users\you\Videos\MILEY_CYRUS_FINAL_1080P.mp4]
- **REFERENCE_CHANNEL:** youtube.com/channel/UCSI7B4MrQaZTS4At_T3N-ow/
- **TARGET_LENGTH:** 15 to 25 minutes (hard floor 15:00, hard ceiling 25:00)
- **MUSIC_VIBE:** High-energy motivational (driving beat, upbeat pop/electronic)
- **PACING:** Slower, cinematic storytelling (let shots breathe, 8 to 12 second average hold)

---

## Role & Objective

Act as an expert autonomous video-production coding agent. Assemble a polished, cinematic 16:9 YouTube documentary about **{{SUBJECT_NAME}}'s {{TOPIC_ANGLE}}**, styled like **{{REFERENCE_CHANNEL}}** and the Celeb Workout brand (`celebworkout-editor-kit/docs/channel/BRAND.md`, fonts in `brand/fonts/`).

The final video must feel emotionally driving, engaging, and strictly truth-seeking.

### Rule precedence (read this so nothing contradicts)

1. This prompt wins where it is explicit. **Owner override 2026-11-21: this prompt's music bed (section 4) replaces the "NO MUSIC BED" Standing Ruling in SKILL.md.** Everything else in SKILL.md section 0 still applies.
2. Then `SKILL.md` section 0 Standing Rulings.
3. Then `playbook/EDITING_CRAFT.md` (cut, music, transition and graphics rules with numbers) and `EDIT_RULES.md`.
4. Then everything else in either repo.

**Copyright:** the YouTube Studio pass (Step 2) is the copyright check. The old 10-second / one-clip-per-source limits in `COPYRIGHT_RULES.md` were withdrawn by the owner (see `SKILL.md` "YouTube copyright - WITHDRAWN"), and a 10-second cap is part of why bites felt cut off. Still spread bites across many sources for variety (EDIT_RULES R5): a film that keeps returning to one interview looks like one room.

If two rules still conflict, stop and ask the owner with A/B/C options. Do not pick silently.

---

## 1. Source Material & Output Specs

- **Input video:** {{INPUT_VIDEO_PATH}}. It is the YouTube-edited first cut, so some segments were cut out by YouTube and the story may now have holes.
  - Detect scene cuts (PySceneDetect), transcribe the audio (faster-whisper or WhisperX, word timestamps, VAD on), and slice it into usable segments.
  - Compare against {{FIRST_CUT_PROJECT}} and {{YOUTUBE_CLAIMS}} to find exactly what was removed.
  - **The storyline must survive every removed segment.** For each hole: bridge it with new narration, a real photograph, an on-screen document quote (`source_highlight`), or a different source clip that YouTube did not claim. Never leave a jump cut, a half-sentence, or a fact that now has no setup.
  - Do NOT re-insert any claimed footage, even a shorter piece of it.
- **Source audio:** Keep the subject's and trainer's own recorded words wherever they strengthen the story. Every bite is a complete thought (EDIT_RULES R3).
- **Output format:** 1920x1080, 16:9, 30fps (or source fps if every source matches), H.264 High profile, CRF 18 or lower, yuv420p, AAC 48kHz stereo 320kbps, loudness -14 LUFS integrated, true peak -1.5 dBTP.
- **Output path:** {{OUTPUT_VIDEO_PATH}}

---

## 2. Tooling (full guide: `playbook/TOOLS.md`)

`playbook/TOOLS.md` says, for every tool, what it is **good for**, **when to use it**, and **when not to**. Re-checked on GitHub 2026-11-21. Before building, look for anything newer (github.com/trending has no API):

```bash
gh search repos "topic:ai-video-editing" --sort stars --limit 20
gh search repos "video editor mcp" --created ">$(date -d '-60 days' +%F)" --sort stars --limit 20
gh search repos "claude code video" --created ">$(date -d '-60 days' +%F)" --sort stars --limit 20
```

A new tool goes into `playbook/TOOLS.md` (in BOTH repos) only after you verify it exists, check its license and confirm it runs headless on Windows.

### CORE (use on every film)

| Tool | Good for / use it for |
| :--- | :--- |
| FFmpeg (`xfade`, `sidechaincompress`, `loudnorm`, `vidstab`) | Every cut, transition between footage, ducking, loudness, stabilising, final encode |
| yt-dlp (+ yt-dlp-ejs and Deno, or YouTube quality silently drops) | Downloading interviews and source clips at best quality |
| SYSTRAN/faster-whisper + snakers4/silero-vad | Transcribing every source; VAD map of where speech is, so cuts land in silence |
| Breakthrough/PySceneDetect | Finding shot changes in the input and source videos |
| mlfoundations/open_clip, OpenCV YuNet + SFace, RapidOCR | Finding the right shot by content, confirming the face is the right person, spotting burned-in text/watermarks |
| thewh1teagle/kokoro-onnx (`am_michael`, phoneme input via misaki) | Narration. Phoneme input fixes homographs and names |
| heygen-com/hyperframes | Glass cards, chapter cards, lower-thirds, caption overlay, transition blocks (house standard) |
| librosa, slhck/ffmpeg-normalize | Music analysis (tempo, energy); two-pass loudness to -14 LUFS |
| PIL + brand fonts | Thumbnails |

### ADD NOW (gaps that hurt quality today, ranked)

| Tool | Good for / use it for |
| :--- | :--- |
| LAION-AI/CLAP | Matching each licensed track to the mood of the words (`EDITING_CRAFT.md` section 4) |
| nomadkaraoke/python-audio-separator | Stripping foreign music out of interview bites so our bed sits cleanly and claims go down |
| m-bain/whisperX | Word-exact bite edges and word-synced captions |
| pyannote/pyannote-audio | Confirming a bite is spoken by the subject, not the interviewer |
| HyperFrames transition blocks + FFmpeg `xfade` | Premium transitions; today there are no picture transitions at all |
| AgriciDaniel/claude-shorts (pattern) + own YuNet `reframe.py` | Shorts cut from the final film, face-tracked 9:16 |
| CPJKU/beat_this | Snapping training-montage cuts and chapter hits to the music's beats |
| Rikorose/DeepFilterNet | Cleaning noisy interview bites |
| danielgatis/rembg | Clean cut-outs from real photos for thumbnails |
| googleapis/google-api-python-client | Unlisted upload, SRT caption track, metadata, weekly Analytics pull |

### OPTIONAL (only when the situation calls for it)

zhouxiaoka/autoclip (owner request 2026-11-21: use it to surface highlight candidates in long interviews; still run every pick through our bite gates. It is Chinese-platform-first and bills cloud models), mutonby/openshorts, Anil-matcha/AI-Youtube-Shorts-Generator, kajisho5/ffmpeg-skill, JuneYaooo/rea-video (reverse-engineer a top reference video into a VIDEO.md), hetpatel-11/Adobe_Premiere_Pro_MCP and samuelgursky/davinci-resolve-mcp (drive the editor packages), remotion-dev/remotion (legacy graphics in `ytceleb/graphics/`), Vibha-Ramprakash/claude-video-effects, Real-ESRGAN / video2x (only for a must-use clip; never as a substitute for a better source), mifi/lossless-cut (manual trims), MTG/essentia (WSL only).

### NOT RECOMMENDED for this pipeline (and why)

| Tool | Why not |
| :--- | :--- |
| KlingAIResearch/LivePortrait, GFPGAN, CodeFormer | They invent faces or motion of real people. Breaks the real-photos rule |
| jub0t/Concat, storytold/filmcraft, mltframework/shotcut, Forward-Future/scarlet, MartinDelophy/ai-video-editor | Desktop editors; fine for a human touch-up, not for the agent pipeline |
| palmier-io/palmier-pro | macOS only |
| krillinai/OpenCreator, modelscope/FunClip | Translation/dubbing suite; Mandarin-first ASR |
| nexu-io/openmotion, openfilm/openfilm, shinyobjectz/raea | Generative video; we use real footage |
| Chatterbox, edge-tts, ElevenLabs, MoneyPrinterTurbo | Archived or rejected by the owner; MoneyPrinterTurbo uses stock footage and a rejected voice |

**Deliverable before rendering:** list the exact tools you chose (and any new ones you found) and write a `VIDEO.md` storyboard mapping every timestamp in {{INPUT_VIDEO_PATH}} and every new asset to the script line it sits under.

---

## 3. Truth-Seeking Research & Script

Research {{SUBJECT_NAME}} (and {{TRAINER_NAME}}) before writing or rewriting narration.

**Find the real sources first:**
- Every book, memoir, trainer book, and long-form interview by or about the subject on fitness, diet, and looks. Confirm each one is legit: real publisher or ISBN, real outlet, real date, real author. Log each in `SOURCES.md` with title, author, date, URL or ISBN, and what it proves.
- Search the trainer by name as its own sweep. Trainer interviews are usually the richest source.

**Truth rules:**
- **Primary sources only.** Verified interviews, trainer breakdowns, books, documented training logs. Not SEO fitness blogs, not "I tried X's workout" YouTubers.
- **No cliches.** Fact-check dietary restrictions (vegetarian, vegan, allergies, sobriety, real eating habits) and actual training style (dance, Pilates, sport, calisthenics, weights). Never default to "chicken, rice, and broccoli".
- **Every quote is verified against its source audio or page.** If you cannot prove it, cut it.
- **Attribute claims** ("she told Vogue in 2019", "her trainer has said"). Never invent private facts.
- **Real photographs only for real people.** Never AI-generated images of the subject, family, or anyone real. Photos are pinned to the name and era being spoken (Standing Ruling).

**Narrative arc:**
1. **The Hook:** the most surprising or counterintuitive true thing about {{SUBJECT_NAME}}'s approach to fitness.
2. **The Workout Breakdown:** training philosophy, role or tour prep, everyday routine. Show the actual movement when an exercise is named.
3. **The Diet Breakdown:** real, documented nutrition habits and mindset around food.
4. **The Takeaway:** an emotionally resonant, actionable lesson for the viewer.

**Script rules (from EDIT_RULES):** the narrator sets up, frames, or moves on. It never repeats what the bite beside it says. A block that only describes the picture gets cut.

---

## 4. Voice, Audio & Music

**Narration voice:** Kokoro `am_michael` (local, free). Not edge-tts, not ElevenLabs.

**Pronunciation check (this failed on the Nov 16 batch: "live" read as "lyve" instead of "liv"):**
- Before TTS, scan the script for homographs: live, lives, read, lead, tear, wind, bow, close, minute, content, record, present, object, desert, wound, row, bass. Rewrite the sentence or spell the word phonetically so only one reading is possible.
- Also check every name (subject, trainer, family, places, brands) against a real pronunciation source and respell it for Kokoro if needed.
- After TTS, re-transcribe the narration with Whisper and diff it against the script. Any word that does not match is a defect. Fix it and regenerate that block.
- Listen to every narration block once at 1x speed.
- **Pauses:** Kokoro joins sentences with no gap. Insert 350-600 ms between sentences and 700-1000 ms between paragraphs (`EDITING_CRAFT.md` section 3).

**Cuts that breathe (owner: "it cuts off too quick"):** full rules in `playbook/EDITING_CRAFT.md` section 3. The short version:
- A bite starts at least 200 ms (target 350 ms) before its first word and ends 500 ms after its last word (800-1200 ms on an emotional moment).
- Every cut lands in a silence of at least 120 ms (VAD map). A bite ends on `.` `!` or `?`, never on "and", "so" or "um".
- Fade bite audio out over 150 ms; never chop it.
- Use J-cuts (voice 300-600 ms before picture) and L-cuts (picture holds 0.5-1 s after the words).
- At least 0.7 s after a bite before the narrator comes in.

**Music (owner override 2026-11-21, replaces "NO MUSIC BED"):**
- **Vibe:** {{MUSIC_VIBE}}. Build energy during training sections; pull back during quiet interview moments.
- **Music matches the tone of the WORDS (owner: "the music and tone needs to match"):** tag every sentence with one of the 8 emotions in `EDITING_CRAFT.md` section 4, pick tracks with CLAP against those tags, and change track when the tag changes, never under a word. Drop the music out 0.6-1.2 s before the 2-4 biggest reveals. Give each chapter one 2-4 s music-up with no voice. Snap montage cuts to the beat (beat_this).
- **License:** 100% copyright-free only (YouTube Audio Library, Pixabay Music, FreePD, CC0 or CC-BY). No other source. Log every track's title, artist, license, and URL in `CREDITS.txt`. CC-BY credits also go in the YouTube description.
- **Ducking:** music sits at about -18 dB to -22 dB under any speech (narration or bite) and comes up to about -10 dB to -12 dB in B-roll gaps and chapter transitions. Use sidechain compression or volume keyframes with 150 to 300 ms fades. Speech must always be clearly on top.
- **High-pass the music around 120 Hz** so it does not muddy the voice.
- **SFX:** subtle risers or soft whooshes at chapter shifts only, from licensed free sources, logged in `CREDITS.txt`.
- **Final loudness:** -14 LUFS integrated, true peak -1.5 dBTP.
- After the YouTube pass, any music that got a claim is replaced, not re-used.

---

## 5. Visuals, Overlays & Motion Graphics

Keep {{PACING}}. No frantic 1-second cuts. Average hold 8 to 12 seconds (EDIT_RULES R2).

**Picture quality (this failed on the Nov 16 batch):**
- Use the highest-quality version of every source (yt-dlp: best video at 1080p or higher).
- Ban any source under ~640px tall after cropping. Do not upscale tiny clips to 1080p; find a better source or use a still.
- No burned-in third-party channel graphics, logos, lower-thirds, or watermarks.
- Never repeat a clip. Spread bites across many sources (EDIT_RULES R5).

**Transitions and motion (owner: "incredible"):** full table in `EDITING_CRAFT.md` section 5.
- One signature transition plus two accents for the whole film. Never a hard cut on a chapter change: 0.6-0.9 s light-leak or whip-pan (HyperFrames transition block or FFmpeg `xfade`).
- Card entrances 450-600 ms, decelerating ease, staggered children. A graphic finishes entering at, or up to 150 ms before, the word it illustrates.
- Everything keeps moving: slow push-in on footage, parallax/drift on stills and cards. No static frame over 4 s.
- Learn from Nate Herk (`EDITING_CRAFT.md` section 1): graphics land on the exact spoken word, never over the face; the agent watches its own render (frame sheets) and fixes it before a human sees it.

**Graphics (Celeb Workout brand: Anton + Archivo, house red; HyperFrames glass cards):**
1. **Chapter title cards:** minimalist, cinematic, same design every time.
2. **Workout & diet cards:** exercise names, sets and reps, diet notes, shown as they are discussed.
3. **Transformation card** where the body changed: two real photos side by side, labelled with year.
4. **Captions:** clean, readable, word-synced to speech (WhisperX timings).
5. **CTA:** a subtle "Subscribe" prompt and end screen in the last 20 seconds.

---

## 6. Execution Workflow

1. Read both repos (Step 1 list above) and `playbook/README.md`. Confirm the rule precedence.
2. Inspect {{INPUT_VIDEO_PATH}}: duration, resolution, fps, audio tracks, scene cuts, full transcript. Diff against {{FIRST_CUT_PROJECT}} and {{YOUTUBE_CLAIMS}}; list every hole.
3. Research {{SUBJECT_NAME}}; write `SOURCES.md`; verify every workout and diet fact.
4. Run the tool search (section 2); update the tables if you find something better; pick the stack.
5. Write the script and `VIDEO.md`. Show the owner the hole-bridging plan and the script for a quick sanity check, or render a fast 540p preview first.
6. Render the final 1080p MP4 to {{OUTPUT_VIDEO_PATH}}. Save `CREDITS.txt`, `SOURCES.md`, `VIDEO.md`, and `QC_REPORT.md` next to it.
7. Self-review before a human sees it: frame sheet every 2 s plus the audio, up to 3 fix rounds (`EDITING_CRAFT.md` section 7).
8. **Shorts:** cut 5-7 vertical Shorts (20-45 s, native 9:16, payoff in the first second, burned-in captions, loop ending, no licensed music) from the final film (`playbook/GROWTH_SHORTS_EVALS.md` section 3). Each Short's Related video = this film.
9. **Package:** write `METADATA.md` with the title, description, chapters, tags, hashtags and pinned comment from the template in `playbook/README.md` section 3, the SRT from the script, and 3 thumbnails for Test & Compare.
10. Run the pre-publish evals (`playbook/README.md` section 4a). Any fail blocks the upload.

---

## 7. QC Gate (every item must pass before delivery; record results in QC_REPORT.md)

- [ ] Length between 15:00 and 25:00 (measure with ffprobe on the rendered file).
- [ ] 1920x1080, H.264, AAC 48kHz, -14 LUFS (+/- 1), true peak at or below -1.5 dBTP.
- [ ] No source under 640px; no visibly soft or blocky shot (check a contact sheet, 1 frame every 10 seconds).
- [ ] No clip repeated; bites spread across sources.
- [ ] Edit-quality eval passes (`EDITING_CRAFT.md` section 7): no cut within 250 ms of speech, bites end on full sentences, a pause at least every 30 s, music quiet under bites, track changes in pauses, no hard cut on a chapter change.
- [ ] Pre-publish evals pass (`playbook/README.md` section 4a), including title, thumbnail, SEO and originality.
- [ ] 5-7 Shorts and METADATA.md ready.
- [ ] No claimed segment from Step 2 came back.
- [ ] No hole in the story: every removed segment has a bridge, no half-sentences, no orphan facts.
- [ ] Narration re-transcribed and matches the script word for word; no mispronounced names or homographs.
- [ ] Music is ducked under every line of speech; every track and SFX is in CREDITS.txt with its license.
- [ ] Every claim in the narration maps to a line in SOURCES.md.
- [ ] No AI-generated images of real people.
- [ ] Every named person and era on screen has the right photo.
- [ ] **You (the human editor) watched the whole video with sound.**

---

## 8. Delivery (this failed on the Nov 16 batch: empty folders and a duplicate link)

- Upload the FINAL file only (not a review cut, not a folder).
- Send one line per film: **Celebrity name - direct Google Drive file link** (a `/file/d/...` link, not a folder link).
- Open every link in a private window before sending. Check it plays, is the right person, and is not the same link as another film.
- Share setting: "Anyone with the link can view".
- Upload to YouTube as UNLISTED until the owner approves.
- After it goes public: add its row to `growth/video_tags.csv`; the weekly tracker scores it against the baseline.
