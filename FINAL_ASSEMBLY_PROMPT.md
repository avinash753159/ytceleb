# Celeb Workout: Final Assembly Prompt (v2, 2026-11-21)

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
3. Then `EDIT_RULES.md` and `COPYRIGHT_RULES.md`.
4. Then everything else in either repo.

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

## 2. Tooling & GitHub Ecosystem

Before building, check for new tools. github.com/trending has no API, so run these and read the top results:

```bash
gh search repos "topic:ai-video-editing" --sort stars --limit 20
gh search repos "video editor mcp" --created ">$(date -d '-60 days' +%F)" --sort stars --limit 20
gh search repos "claude code video" --created ">$(date -d '-60 days' +%F)" --sort stars --limit 20
```

Add any strong new candidate to the tables below (verify it exists, check its license, note its star count and date). Use the best-fit combination alongside FFmpeg. Prefer tools that run headless from the command line; desktop GUI editors are for manual touch-ups only.

### Core stack (use these first)

| Tool | Stars (2026-11-21) | Job in this pipeline |
| :--- | :--- | :--- |
| FFmpeg | n/a | All cuts, concat, mixing, loudness, final encode. |
| yt-dlp/yt-dlp | ~209k | Download interviews and source clips. |
| SYSTRAN/faster-whisper | ~27k | Transcribe every source (word timestamps). |
| m-bain/whisperX | ~25.6k | Word-level alignment for captions and bite edges. |
| Breakthrough/PySceneDetect | ~5.6k | Scene-cut detection on the input video. |
| thewh1teagle/kokoro-onnx | ~2.9k | Narration voice, `am_michael` (Standing Ruling). |
| heygen-com/hyperframes | ~87.9k | Glass cards, chapter cards, lower-thirds (house standard). |
| remotion-dev/remotion | ~74.8k | Alternate graphics engine (`ytceleb/graphics/`). |
| zhouxiaoka/autoclip | ~12.9k | Highlight detection to find the best moments in long interviews. Owner asked for this 2026-11-21. |
| kajisho5/ffmpeg-skill | ~9.3k | 42 FFmpeg tools for coding agents with a machine-readable contract. Good for reliable agent-driven cuts. |

### Approved, use when they fit

| Repository | Stars (2026-11-21) | Category | Purpose |
| :--- | :--- | :--- | :--- |
| mifi/lossless-cut | ~46.3k | Lossless trimmer | Fast GUI cutting and merging without re-encoding. |
| KlingAIResearch/LivePortrait | ~19.5k | AI face animation | Animate still portraits. Use only on real photos, never to invent a moment, and label it. |
| jub0t/Concat | ~19.5k | Local-first NLE | Rust editor scriptable via JSON-RPC and MCP. |
| storytold/filmcraft | ~18.8k | Desktop NLE | Non-linear editor in pure Rust. |
| mltframework/shotcut | ~15.8k | Desktop NLE | Traditional open-source editor (C++/Qt). |
| Zulko/moviepy | ~15.2k | Python scripting | Programmatic cuts, titles, compositing. |
| nexu-io/openmotion | ~14.8k | Motion graphics | Turns a reference video into editable motion graphics, 300+ agent guides. |
| palmier-io/palmier-pro | ~14.8k | AI macOS editor | Swift macOS editor with MCP and Claude integration. |
| krillinai/OpenCreator | ~14.5k | AI creator suite | Translation, dubbing (120+ languages), social edits. |
| JuneYaooo/rea-video | ~11.9k | Video reverse-engineering | Breaks a reference edit into a shot-by-shot VIDEO.md. Use it on a top {{REFERENCE_CHANNEL}} video to copy structure and pacing. |
| openfilm/openfilm | ~8.9k | AI video agent | Turns any coding agent into a video agent. |
| modelscope/FunClip | ~6.6k | Transcribe + clip | ASR-powered clipping and subtitles; LLM-assisted clip picking. |
| shinyobjectz/raea | ~3.3k | Render engine | Videos, motion graphics, 3D from a text brief. |
| Vibha-Ramprakash/claude-video-effects | ~1.1k | Effects skill | 51 free effects for Claude Code (`/effect`). |
| MartinDelophy/ai-video-editor | ~1.0k | Local-first editor | Timeline Studio, with an AI editing skill for Claude Code, Codex, Gemini CLI. |
| hetpatel-11/Adobe_Premiere_Pro_MCP | ~0.9k | Premiere MCP | Lets Claude drive Premiere Pro. Useful with the editor packages on Drive. |
| Forward-Future/scarlet | ~0.5k | AI editor | macOS/Windows editor with Claude Code / Codex MCP and timeline versioning. |

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

**Music (owner override 2026-11-21, replaces "NO MUSIC BED"):**
- **Vibe:** {{MUSIC_VIBE}}. Build energy during training sections; pull back during quiet interview moments.
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
- One clip per source, 10 seconds max, never repeated (COPYRIGHT_RULES).

**Graphics (Celeb Workout brand: Anton + Archivo, house red; HyperFrames glass cards):**
1. **Chapter title cards:** minimalist, cinematic, same design every time.
2. **Workout & diet cards:** exercise names, sets and reps, diet notes, shown as they are discussed.
3. **Transformation card** where the body changed: two real photos side by side, labelled with year.
4. **Captions:** clean, readable, word-synced to speech (WhisperX timings).
5. **CTA:** a subtle "Subscribe" prompt and end screen in the last 20 seconds.

---

## 6. Execution Workflow

1. Read both repos (Step 1 list above). Confirm the rule precedence.
2. Inspect {{INPUT_VIDEO_PATH}}: duration, resolution, fps, audio tracks, scene cuts, full transcript. Diff against {{FIRST_CUT_PROJECT}} and {{YOUTUBE_CLAIMS}}; list every hole.
3. Research {{SUBJECT_NAME}}; write `SOURCES.md`; verify every workout and diet fact.
4. Run the tool search (section 2); update the tables if you find something better; pick the stack.
5. Write the script and `VIDEO.md`. Show the owner the hole-bridging plan and the script for a quick sanity check, or render a fast 540p preview first.
6. Render the final 1080p MP4 to {{OUTPUT_VIDEO_PATH}}. Save `CREDITS.txt`, `SOURCES.md`, `VIDEO.md`, and `QC_REPORT.md` next to it.

---

## 7. QC Gate (every item must pass before delivery; record results in QC_REPORT.md)

- [ ] Length between 15:00 and 25:00 (measure with ffprobe on the rendered file).
- [ ] 1920x1080, H.264, AAC 48kHz, -14 LUFS (+/- 1), true peak at or below -1.5 dBTP.
- [ ] No source under 640px; no visibly soft or blocky shot (check a contact sheet, 1 frame every 10 seconds).
- [ ] Every clip 10 seconds or less; exactly one clip per source; no repeats.
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
