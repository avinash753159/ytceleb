# Celeb Workout Pipeline: Tool Guide

Checked 2026-11-21. Star counts, last push, and license come from `gh api repos/<owner>/<repo>`. Every repo listed here was confirmed to exist. If a name could not be found, it says so. "Last push" is the API's `pushed_at` value in UTC, so some show 2026-11-22.

**Status key**
- **CORE**: use on every film.
- **ADD NOW**: not in the pipeline today, and adding it would clearly improve quality.
- **OPTIONAL**: use only when the situation calls for it.
- **NOT RECOMMENDED**: wrong for this pipeline. The reason is given.

**What the pipeline needs**
- Runs headless on Windows from Claude Code.
- Real footage and real photos only.
- Kokoro voice.
- Verified bites.
- Licensed or claim-safe audio.

---

## 0. What is actually used today (evidence from the code)

### Used in the current playbook (celebworkout-editor-kit `reference/`)

| Tool | Evidence |
|---|---|
| yt-dlp | `jordan_v1/fetch_talk.py` (`ytsearch`, `--no-continue`, `player_client`), `aniston_v2/fetch*.py` |
| faster-whisper | 7 imports, including `src_transcribe.py` and `transcript.py`. VAD is on, which uses Silero VAD through faster-whisper. |
| kokoro-onnx | `jordan_v1/voice.py`. This is the only `kokoro_onnx` import. |
| Chatterbox Turbo/Nano | `jordan_v1_hyperframes/build_audio.py`, which uses `ChatterboxTurboTTS`. This is an experiment, and it breaks the Kokoro ruling. |
| ElevenLabs | Still coded in `aniston_v2/tts*.py`, `jordan_v1/tts6.py`, `voice.py`. These are dead paths. The ruling says Kokoro only. |
| edge-tts | `jordan_v1/voice.py`. Rejected by the owner. |
| HyperFrames | `jordan_v1_hyperframes/hyperframes.json`, `index.html`, `compositions/`. SKILL.md section 9 calls it the card engine. `hf/cards/gen_cards.py` is referenced but is not in the repo. |
| FFmpeg | Everywhere. Filters in use: `loudnorm` (26 calls), `afade` (31), `zoompan` (15), `highpass` (9), `vidstabdetect`/`vidstabtransform` (stabilise.py), `acrossfade` (3). There is no `xfade`, so no picture transitions exist today. |
| OpenCV YuNet + SFace | `jordan_v1/ident.py` (`face_detection_yunet_2023mar.onnx`, `face_recognition_sface_2021dec.onnx`), `recognise.py` |
| CLIP (HF transformers `openai/clip-vit-base-patch32`) | `semantic.py` |
| Depth-Anything-V2-Small | `depth_gen.py` (2.5D photo moves, three.js `gl/scene.js`) |
| RapidOCR | `ocr_sweep.py`, `card_qc.py`, `reels5.py` (burned-in graphics checks) |
| PIL | Thumbnails (`thumb*.py`), cards, and photo frames |
| pydub, torchaudio | `build_audio.py` |
| fal.ai (any-llm shim), Gemini | `fal_openai_shim.py` and `semantic.py`. These are paid APIs, not open source. |
| Music | `mood.py` is a hand-made word lookup (its docstring says "not sentiment analysis"). `bed.py` and `music.py` mix the bed. `score.py` makes synthetic music. Mixing is OFF under the "NO MUSIC BED" ruling, which FINAL_ASSEMBLY_PROMPT now overrides. |
| Cut detection | `aniston_v2/cuts.py` uses FFmpeg scene scoring. It does not use PySceneDetect. |
| Shorts | `docs/channel/SHORTS_PIPELINE.md` says this is **MoneyPrinterTurbo** with ElevenLabs "Brian" and Pexels stock footage. That breaks both the Kokoro rule and the real-footage rule. |

### Used in the older automated pipeline (ytceleb)

| Tool | Evidence |
|---|---|
| PySceneDetect | `pipeline/detect_shots.py` |
| open_clip + sqlite-vec | `pipeline/embed_index.py` |
| faster-whisper `small.en` word timestamps | `pipeline/align.py`. Its docstring says WhisperX is *not* used. |
| Real-ESRGAN through `realesrgan_ncnn_py` | `pipeline/fetch_stills.py`. The binding repo, Tohrusky/realesrgan-ncnn-py, is **ARCHIVED**. |
| RapidOCR | `ingest_ocr.py`, `qc.py`, `recover_crop.py` |
| youtube-transcript-api | `RUN.py` |
| Remotion | `graphics/` (v5 to v10 cards) |
| Anthropic SDK | `plan_llm_api.py`, `plan_treatments.py`, `RUN_V2.py` |
| Gemini 2.5 Flash | `AUTO_TAGS.py` |
| edge-tts | `GENERATE_FINAL_VIDEO.py` |
| sidechaincompress ducking | One use, in `pipeline/v6_assemble.py` |

### Listed in FINAL_ASSEMBLY_PROMPT.md but not used in any code today

- whisperX
- autoclip
- ffmpeg-skill
- lossless-cut
- LivePortrait
- Concat
- filmcraft
- shotcut
- moviepy
- openmotion
- palmier-pro
- OpenCreator
- rea-video
- openfilm
- FunClip
- raea
- claude-video-effects
- ai-video-editor
- Premiere MCP
- scarlet

---

## 1. Download

### yt-dlp/yt-dlp: CORE
- **Checked:** 209,709 stars, last push 2026-11-21, Unlicense.
- **Good for:** every interview, podcast, and source clip. Format chains, player clients, search.
- **Use it when:** you are harvesting any source. Keep the playbook flags: `--no-continue`, delete `.part` files, `bv*+ba/b`.
- **Don't use it for:** re-downloading a claimed segment after the Studio trim.
- **Note:** the README now says full YouTube support needs **yt-dlp-ejs** plus a JavaScript runtime. Deno is the recommended one. yt-dlp/ejs: 487 stars, Unlicense. Install both, or extraction will degrade quietly.
- **Install:**
  ```
  winget install Gyan.FFmpeg DenoLand.Deno
  pip install -U "yt-dlp[default]"
  ```

### jdepoix/youtube-transcript-api: OPTIONAL
- **Checked:** 8,645 stars, MIT.
- **Good for:** fast pre-screening of a candidate interview's captions before downloading it.
- **Don't use it for:** bite timing. SKILL.md: auto-captions roll, so they only locate a bite.

---

## 2. Transcription and word alignment

### SYSTRAN/faster-whisper: CORE
- **Checked:** 26,929 stars, last push 2026-11-12, MIT.
- **Good for:** transcribing the whole library on CPU with int8, word timestamps, and built-in Silero VAD.
- **Use it when:** you run any transcription: sources, bite re-checks, and the narration check after TTS.
- **Don't use it for:** frame-exact caption edges on fast speech. Use whisperX alignment for that.
- **Install:**
  ```
  pip install faster-whisper
  ```

### m-bain/whisperX: ADD NOW (alignment step only)
- **Checked:** 25,576 stars, last push 2026-11-21, BSD-2-Clause.
- **Good for:** wav2vec2 forced alignment, which gives tighter word edges than Whisper's own timestamps. Also has optional pyannote diarization.
- **Use it when:** you set bite in and out points, and when you build word-synced captions. FINAL_ASSEMBLY_PROMPT requires WhisperX timings, but no code uses it yet.
- **Don't use it for:** bulk transcription of 16+ hours. faster-whisper is enough for that.

### MahmoudAshraf97/ctc-forced-aligner: OPTIONAL
- **Checked:** 577 stars, BSD-2-Clause.
- **Good for:** aligning *known* text to audio. Example: script to Kokoro output, for captions with no ASR errors.
- **Use it when:** whisperX dependencies fight with torch on Windows.

### ggml-org/whisper.cpp: OPTIONAL
- **Checked:** 55,407 stars, MIT.
- **Good for:** a single exe with no Python. Remotion's caption template uses it.
- **Use it when:** you need ASR inside a Node/Remotion step.

### openai/whisper: NOT RECOMMENDED
- **Checked:** 113,239 stars, MIT.
- **Why not:** it is slower than faster-whisper and runs the same models.

### jianfch/stable-ts: NOT RECOMMENDED
- **Checked:** 2,287 stars.
- **Why not:** the repo is **ARCHIVED**.

### linto-ai/whisper-timestamped: NOT RECOMMENDED
- **Checked:** 2,860 stars, AGPL-3.0.
- **Why not:** the AGPL licence, and whisperX already covers it.

### NVIDIA-NeMo/Speech (Parakeet and others): NOT RECOMMENDED
- **Checked:** 18,775 stars, Apache-2.0.
- **Why not:** heavy, and built for Linux/CUDA. Not worth it on Windows CPU.

### modelscope/FunASR: NOT RECOMMENDED
- **Checked:** 21,093 stars, MIT.
- **Why not:** Mandarin-first. QwenAudio/SenseVoice (9,799 stars) is the same story.

---

## 3. Speaker diarization

### pyannote/pyannote-audio: ADD NOW
- **Checked:** 10,825 stars, last push 2026-11-19, MIT.
- **Good for:** "who spoke when." The `community-1` pipeline is open. You must accept its Hugging Face conditions and use an HF token.
- **Use it when:** you run bite verification (`cut_bites.py`). SKILL.md warns that a transcript line can "belong to a different speaker in the room." Diarization turns that from an eyeball check into a gate: the bite's speaker must match the subject's or trainer's voice cluster.
- **Don't use it for:** identity. It labels clusters, not names. Pair it with SFace face ID on the same window.

---

## 4. Voice activity detection

### snakers4/silero-vad: CORE
- **Checked:** 10,736 stars, last push 2026-11-20, MIT.
- **Good for:** speech and non-speech maps.
- **Use it when:** you need it in either of two places:
  1. Inside faster-whisper, where it is already on.
  2. Standalone, to build the **speech timeline that drives music ducking**: every narration and bite interval, with padding.
- **Don't use it for:** telling narrator from subject apart. Use the edit decision list for that, since you already know which block is which.
- **Install:**
  ```
  pip install silero-vad
  ```

---

## 5. Scene and shot detection

### Breakthrough/PySceneDetect: CORE
- **Checked:** 5,613 stars, last push 2026-11-22, BSD-3-Clause.
- **Good for:** cut lists on sources and on the Studio-edited input. Its `AdaptiveDetector` handles camera motion better than a fixed threshold.
- **Use it when:** you run FINAL_ASSEMBLY step 2, or check "a clip window contains a cut" (the shot-332 bug in `cuts.py`). Put both repos on this one tool.
- **Don't use it for:** soft dissolves on archive footage. Use TransNetV2 for that.
- **Install:**
  ```
  pip install "scenedetect[opencv]"
  ```

### soCzech/TransNetV2: OPTIONAL
- **Checked:** 1,082 stars, last push 2023-12-04, MIT.
- **Good for:** a neural shot-boundary model that catches gradual transitions.
- **Use it when:** PySceneDetect misses dissolves in TV archive footage.
- **Note:** stale, and built on TensorFlow.

### Breakthrough/DVR-Scan: NOT RECOMMENDED
- **Checked:** 536 stars.
- **Why not:** it detects motion events for security footage, not cuts.

---

## 6. Visual tagging, search, and identity

### mlfoundations/open_clip: CORE
- **Checked:** 14,279 stars. The license field reads NOASSERTION; the repo LICENSE is MIT-style.
- **Good for:** text-to-frame search ("woman doing Pilates reformer"). It also loads SigLIP-family weights.
- **Use it when:** you match b-roll to a script line, or check that a named exercise is actually on screen.
- **Don't use it for:** identity, because CLIP will match a lookalike.
- **Install:**
  ```
  pip install open_clip_torch
  ```
- **Note:** the kit also uses HF `transformers` CLIP. Pick one and keep it.

### asg017/sqlite-vec: OPTIONAL
- **Checked:** 8,272 stars, Apache-2.0.
- **Good for:** a local vector index, as used in ytceleb `embed_index.py`.

### apple-aiml-research/ml-mobileclip: OPTIONAL
- **Checked:** 1,687 stars.
- **Good for:** faster CLIP on CPU when indexing a large library.

### OpenCV YuNet + SFace (models from opencv/opencv_zoo): CORE
- **Checked:** opencv_zoo has 1,141 stars, Apache-2.0.
- **Good for:** the identity gate (`ident.py`) and face boxes. The boxes also drive 9:16 reframing.
- **Use it when:** you check every candidate photo or clip. It is triage; eyeball the survivors.
- **Install:**
  ```
  pip install opencv-python
  ```

### deepinsight/insightface: NOT RECOMMENDED
- **Checked:** 30,282 stars.
- **Why not:** the API shows no license, and its model weights are non-commercial. SFace is enough.

### google-ai-edge/mediapipe: OPTIONAL
- **Checked:** 37,776 stars, Apache-2.0.
- **Good for:** smooth face and pose tracking for Shorts reframing.
- **Use it when:** YuNet boxes jitter.

### RapidAI/RapidOCR: CORE
- **Checked:** 8,590 stars, Apache-2.0.
- **Good for:** spotting burned-in channel logos and lower-thirds, plus card QC.
- **Install:**
  ```
  pip install rapidocr_onnxruntime
  ```

### JaidedAI/EasyOCR: NOT RECOMMENDED
- **Checked:** 30,159 stars, Apache-2.0.
- **Why not:** RapidOCR already works here.

### DepthAnything/Depth-Anything-V2: OPTIONAL
- **Checked:** 9,189 stars, Apache-2.0.
- **Good for:** 2.5D parallax on real stills, as in `depth_gen.py`.
- **Don't use it for:** anything that changes a real face.

### ultralytics/ultralytics: NOT RECOMMENDED
- **Checked:** 63,646 stars, AGPL-3.0.
- **Why not:** the AGPL licence. YuNet and MediaPipe cover the job.

---

## 7. Highlight detection and Shorts generation

> **Verdict:** the long-form pipeline already mines bites with `bites.py` and proves them. Shorts should be **cut from the finished long-form edit decision list.** Use Claude to score moments, then apply the reframe, captions, and Kokoro voice. Do not use a second stock-footage pipeline.

### AgriciDaniel/claude-shorts: ADD NOW (as the pattern, or fork it)
- **Checked:** 464 stars, last push 2026-07-11, MIT.
- **Good for:**
  1. Transcribes with faster-whisper.
  2. Claude scores candidate segments on 5 points: hook, coherence, emotion, value density, payoff.
  3. Snaps cut points to word, sentence, and silence boundaries.
  4. Renders 1080x1920 with Remotion and animated captions.
- **Why it fits:** it uses the same stack we use.
- **Use it when:** you make Shorts from a finished long-form.
- **Don't use it for:** picking long-form bites. `bites.py` and the gates do that.

### zhouxiaoka/autoclip: OPTIONAL (demote from "Core")
- **Checked:** 12,933 stars, last push 2026-11-22, MIT.
- **Good for:** a desktop app that goes from a link to clips, covers, and post copy. Has a CLI and MCP.
- **Don't use it for:** core pipeline work. It is Chinese-first and built for Douyin and Xiaohongshu. The README says cloud models are billed per use. Its highlight picks ignore our bite gates and copyright rules.

### mutonby/openshorts: OPTIONAL
- **Checked:** 9,648 stars, last push 2026-11-21, MIT.
- **Good for:** a face-tracked crop, plus stacking two people on camera with captions on the seam. Self-hosted with Docker and 8 GB RAM or more.
- **Use it when:** you want to study its reframe logic.
- **Note:** you have to bring your own Gemini, ElevenLabs, and fal keys.

### Anil-matcha/AI-Youtube-Shorts-Generator: OPTIONAL
- **Checked:** 6,436 stars, MIT.
- **Good for:** a reference for another OpusClip-style tool.

### jipraks/yt-short-clipper: OPTIONAL
- **Checked:** 1,105 stars, MIT.
- **Good for:** a Windows desktop app, for manual use only.

### modelscope/FunClip: NOT RECOMMENDED
- **Checked:** 6,617 stars, MIT.
- **Why not:** it is built on FunASR, which is Mandarin-first. It duplicates faster-whisper plus Claude.

### harry0703/MoneyPrinterTurbo: NOT RECOMMENDED for celebrity Shorts
- **Checked:** 145,000 stars, MIT. This is the current Shorts pipeline.
- **Why not:** it generates from stock footage. Our setup also uses the ElevenLabs Brian voice, which breaks the Kokoro ruling and the real-footage rule.
- **What to do:** replace it with claude-shorts-style cutting of the long-form.

---

## 8. Vertical reframing (16:9 to 9:16)

### Own `reframe.py`: ADD NOW
- **How it works:**
  1. Get YuNet face boxes, which are already in the kit.
  2. Pick the speaker using diarization plus the face.
  3. Smooth the path with an EMA or a One-Euro filter.
  4. Apply FFmpeg `crop` and `sendcmd`.
  5. If no face is found, fall back to blurred-fill letterbox.
- **Why build it:** it needs no new dependency and keeps the identity gate.

### kamilstanuch/Autocrop-vertical: OPTIONAL, as a reference only
- **Checked:** 474 stars.
- **Why reference only:** **it has no license.** Do not copy its code.
- **Its idea:** YOLOv8 per scene decides between a tight crop and a letterbox.

### reframe-oss/reframe: NOT RECOMMENDED
- **Checked:** 178 stars, MIT.
- **Why not:** despite the name, it is a browser video editor, not an auto-reframer.

---

## 9. Captions and kinetic typography

### HyperFrames `captions-overlay` skill: ADD NOW
- **Checked:** the skill is in heygen-com/hyperframes `.claude/skills/captions-overlay/`.
- **Good for:** word-synced captions in the same engine as the glass cards.
- **Use it when:** you burn captions into Shorts, or add word-highlight treatments in the long-form.

### YouTube closed-caption track (SRT through the Data API): CORE for long-form
- **Good for:** captions on the long-form. Upload an SRT built from the narration text (exact) and the verified bite transcripts. This beats burning captions into a 20-minute documentary.

### francozanardi/pycaps: OPTIONAL
- **Checked:** 235 stars, MIT.
- **Good for:** CSS-styled animated subtitles from Python, with a CLI.
- **Use it when:** you need a quick Shorts caption style without writing a composition.

### remotion-dev/template-tiktok: OPTIONAL
- **Checked:** 308 stars.
- **Good for:** a Remotion TikTok caption template built on whisper.cpp.
- **Note:** no license is declared.

### buxuku/SmartSub: NOT RECOMMENDED
- **Checked:** 6,127 stars, MIT.
- **Why not:** it is a GUI app.

---

## 10. Motion graphics and cards

### heygen-com/hyperframes: CORE
- **Checked:** 87,897 stars, last push 2026-11-22, Apache-2.0, created 2026-03-10.
- **Good for:** HTML/GSAP to MP4 with headless Chrome. Covers glass cards, chapter cards, lower-thirds, and the transformation card. It has a registry of **transition blocks** (3d, blur, cover, dissolve, distortion, grid, light, push, and shader-dissolve) and agent skills, which are already installed locally as `/hyperframes*`.
- **Use it when:** you make any graphic. This is the house standard.
- **Don't use it for:** cutting the base footage. FFmpeg does that.
- **Install:** Node 22, then `npx hyperframes render -c compositions/<id>.html`

### remotion-dev/remotion: OPTIONAL (legacy fallback)
- **Checked:** 74,784 stars, last push 2026-11-20. The license field is NOASSERTION: the Remotion License is free for individuals and small companies, and larger companies need a company license.
- **Good for:** ytceleb's v5 to v10 cards, and claude-shorts rendering.
- **Use it when:** you reuse old cards or fork claude-shorts.
- **Don't use it for:** running new cards on two engines.

### motion-canvas/motion-canvas: NOT RECOMMENDED
- **Checked:** 20,126 stars, MIT, last push 2026-07-02.
- **Why not:** it is editor-centric, and HyperFrames already covers the job.

### ManimCommunity/manim and 3b1b/manim: NOT RECOMMENDED
- **Checked:** 42,782 and 96,780 stars, MIT.
- **Why not:** they make math explainers, which is the wrong look.

### nexu-io/openmotion: NOT RECOMMENDED
- **Checked:** 14,779 stars, Apache-2.0, created 2026-05-11.
- **Why not:** it recreates a reference video using generative providers (GPT Image, Seedance, Suno, Eleven). That is the opposite of the real-footage rule, and HyperFrames already covers the code side.

### Vibha-Ramprakash/claude-video-effects: OPTIONAL
- **Checked:** 1,123 stars. The license is NOASSERTION, so check it before you copy anything.
- **Good for:** effect ideas for talking-head clips.

---

## 11. Transitions

### FFmpeg `xfade` / `acrossfade`: CORE
- **Good for:** about 50 built-in transitions such as fade, smoothleft, circleopen, and dissolve. Runs headless and is frame-exact.
- **Use it when:** you join two pieces of real footage at chapter shifts. The house look should be restrained: fade, dissolve, or a short whip.
- **Note:** the code uses `acrossfade` today but never `xfade`.

### HyperFrames transition blocks: ADD NOW
- **Good for:** premium designed transitions (light leak, blur push, 3D) at chapter cards.

### gl-transitions/gl-transitions: NOT RECOMMENDED on Windows
- **Checked:** 2,265 stars.
- **Why not:** to use it in FFmpeg you need transitive-bullshit/ffmpeg-gl-transition (722 stars, no license, last push 2024-07-23) and a custom FFmpeg build. Use HyperFrames instead.

### mifi/editly: NOT RECOMMENDED
- **Checked:** 5,638 stars, MIT, last push 2025-05-12.
- **Why not:** stale, and it overlaps FFmpeg plus HyperFrames.

---

## 12. Music: mood matching, beats, ducking, stems

### Music source (not GitHub)
- **Library:** YouTube Audio Library, Pixabay Music, FreePD, CC0, or CC-BY, per FINAL_ASSEMBLY section 4.
- **Logging:** log every track in CREDITS.txt.

### Mood of the script: keep `mood.py`, add an LLM pass. CORE (exists)
- **What it is today:** a hand-made word lookup.
- **Upgrade:** have Claude label each block (tense, grind, triumph, reflective, method) from the words at that timecode. Keep the lookup as a cross-check.

### LAION-AI/CLAP: ADD NOW
- **Checked:** 2,353 stars, CC0-1.0, last push 2025-05-15.
- **Good for:** zero-shot matching between text and audio. Score every library track against prompts like "high-energy motivational workout electronic" or "quiet reflective piano." This gives a mood vector per track with no training, and it runs on Windows.
- **Use it when:** you pick the cue for each mood segment.

### MTG/essentia (plus its TensorFlow mood/genre classifiers): OPTIONAL, WSL only
- **Checked:** 3,813 stars, AGPL-3.0.
- **Good for:** classifiers trained on mood, genre, and danceability.
- **Why only optional:** the README says pip install is Linux only, so it needs WSL on this laptop. It is also AGPL.

### AMAAI-Lab/Music2Emotion: OPTIONAL
- **Checked:** 65 stars, MIT.
- **Good for:** valence and arousal regression on tracks.
- **Note:** the repo is small.
- **Name check:** "music2emo" under amaai-lab was **not found**. The real repo is `AMAAI-Lab/Music2Emotion`.

### librosa/librosa: CORE
- **Checked:** 9,090 stars, ISC.
- **Good for:** tempo, onsets, RMS energy curves, and spectral checks (the 58%-below-500 Hz problem in `bed.py`).
- **Install:**
  ```
  pip install librosa
  ```

### CPJKU/beat_this: ADD NOW
- **Checked:** 491 stars, MIT, last push 2026-05-28.
- **Good for:** an accurate beat and downbeat tracker. Install with `pip install beat-this`.
- **Use it when:** you snap montage cuts in training sections and chapter hits to the downbeat.

### CPJKU/madmom: NOT RECOMMENDED
- **Checked:** 1,741 stars, last push 2026-03-20, license NOASSERTION.
- **Why not:** packaging lags behind, and beat_this replaces it.

### FFmpeg `sidechaincompress` plus volume keyframes: CORE
- **How to set it up:**
  1. Duck the bed to about -20 dB under speech and bring it up to about -11 dB in gaps.
  2. Use 150 to 300 ms ramps.
  3. Drive it from the Silero speech map or the edit decision list.
  4. Apply `highpass=f=120` on the bed (`bed.py` used 220 Hz).
  5. Use `amix=normalize=0`.
- **Note:** the code uses this only once (ytceleb `v6_assemble.py`).

### nomadkaraoke/python-audio-separator: ADD NOW
- **Checked:** 1,505 stars, MIT, last push 2026-10-29.
- **Good for:** a CLI and Python package for UVR, MDX, and Roformer vocal/instrumental models.
- **Use it when:** you **strip background music out of interview bites** before you lay our bed under them. This avoids two songs clashing, and lowers the chance of Content ID claims on music inside the bites.
- **Don't use it for:** clean studio bites. It always adds some artifacts, so listen afterwards.

### adefossez/demucs: OPTIONAL
- **Checked:** 3,587 stars, MIT, last push 2026-10-26.
- **Good for:** Demucs v4 htdemucs for vocal stems.
- **Note:** facebookresearch/demucs (10,419 stars) is **ARCHIVED**. Use this maintained fork, or audio-separator, which can run Demucs models.

### Anjok07/ultimatevocalremovergui: OPTIONAL (manual)
- **Checked:** 27,303 stars, MIT.
- **Good for:** a GUI for one-off listening tests.

### deezer/spleeter: NOT RECOMMENDED
- **Checked:** 28,540 stars.
- **Why not:** older models, with lower quality than Roformer or Demucs.

### ace-step/ACE-Step-1.5: OPTIONAL, owner decision
- **Checked:** 15,060 stars, MIT.
- **Good for:** local music generation, a claim-proof bed in the spirit of `score.py`.
- **Why it needs the owner:** FINAL_ASSEMBLY section 4 allows only library-licensed tracks. Generated music needs the owner's OK.

### facebookresearch/audiocraft (MusicGen): NOT RECOMMENDED
- **Checked:** 23,942 stars.
- **Why not:** the MusicGen weights are non-commercial.

---

## 13. Audio cleanup and loudness

### Rikorose/DeepFilterNet: ADD NOW
- **Checked:** 5,073 stars, last push 2026-11-06. The license field is NOASSERTION; the repo carries MIT and Apache files.
- **Good for:** fast, real-time-class speech denoising on CPU. Handles red-carpet crowd noise, room hum, and podcast hiss.
- **Use it when:** a verified bite is noisy. Run it before loudness.
- **Don't use it for:** narration, which is already clean.

### resemble-ai/resemble-enhance: OPTIONAL, with caution
- **Checked:** 2,504 stars, MIT, last push 2024-12-03.
- **Good for:** denoising plus bandwidth "enhancement."
- **Caution:** the enhancer *regenerates* speech. Never use it on a bite that has to stay forensically the subject's own audio. Re-verify after any use.

### slhck/ffmpeg-normalize: CORE
- **Checked:** 1,544 stars, last push 2026-11-17.
- **Good for:** two-pass EBU R128 to exactly -14 LUFS / -1.5 dBTP. Today the code uses single-pass `loudnorm`, which drifts.
- **Install:**
  ```
  pip install ffmpeg-normalize
  ```

### sergree/matchering: NOT RECOMMENDED
- **Checked:** 2,727 stars, GPL-3.0.
- **Why not:** music mastering is not needed here.

---

## 14. Text to speech (narration)

**Ruling:** Kokoro `am_michael` (SKILL.md section 0).

### thewh1teagle/kokoro-onnx: CORE, and keep it
- **Checked:** 2,918 stars, MIT, last push 2026-09-01.
- **Good for:** CPU, no key, deterministic output, 158 wpm, a channel match.
- **Pronunciation control:** this fixes the "live" read as "lyve" problem. The repo ships `examples/with_phonemes.py` and recommends **misaki G2P**. Pass phonemes for homographs and names instead of respelling. Keep the Whisper diff gate after TTS.
- **Install:**
  ```
  pip install kokoro-onnx soundfile misaki[en]
  ```
  Model files come from the repo's releases.

### hexgrad/kokoro: OPTIONAL
- **Checked:** 10,292 stars, Apache-2.0, last push 2025-08-06.
- **Good for:** the upstream PyTorch package. It supports inline `[word](/phonemes/)` markup.
- **Note:** SKILL.md says it needs spacy. Use it only if onnx phonemes fall short.

### remsky/Kokoro-FastAPI: OPTIONAL
- **Checked:** 5,715 stars, Apache-2.0.
- **Good for:** an OpenAI-compatible Kokoro server, so MoneyPrinterTurbo-style tools can call Kokoro.

### Comparison of newer open TTS

None of these replaces Kokoro for this channel.

| Repo | Stars, last push, license | Strength | Why it is not the default |
|---|---|---|---|
| resemble-ai/chatterbox | 28,025, 2026-11-04, MIT | Expressive, voice cloning, Multilingual V3 | The README now says it is kept **as an archive, with no support or updates**. Used in `build_audio.py`, which breaks the ruling. **NOT RECOMMENDED** |
| SWivid/F5-TTS | 15,634, 2026-11-03, MIT code | Strong zero-shot cloning | Needs a GPU. Check the HF model-weight license before commercial use. Cloning a real person's voice is off-limits anyway. OPTIONAL |
| canopyai/Orpheus-TTS | 6,412, 2025-12-05, Apache-2.0 | Emotive LLM-based TTS | 3B and GPU-first, with a llama.cpp CPU path. Stale. NOT RECOMMENDED |
| nari-labs/dia | 19,417, 2025-11-19, Apache-2.0 | Two-speaker dialogue | README: "tested on only GPUs." Stale. NOT RECOMMENDED |
| microsoft/VibeVoice | 57,474, 2026-10-08, MIT | Long-form, multi-speaker | The README table shows VibeVoice-TTS-1.5B as "**Disabled**" after misuse. NOT RECOMMENDED |
| KittenML/KittenTTS | 17,037, 2026-11-19, Apache-2.0 | Tiny and CPU-fast | Worth a blind A/B against am_michael only if speed matters. OPTIONAL |
| QwenLM/Qwen3-TTS | 14,569, 2026-03-17, Apache-2.0 | Multilingual, controllable | GPU. OPTIONAL |
| OpenBMB/VoxCPM | 42,862, 2026-11-09, Apache-2.0 | Voice design | GPU. OPTIONAL |
| index-tts/index-tts | 25,226, NOASSERTION | Controllable duration, useful for dubbing | License unclear, GPU. NOT RECOMMENDED |
| fishaudio/fish-speech | 33,825, Fish Audio Community/Research License | Quality | Not an OSI license. NOT RECOMMENDED |
| abus-aikorea/voice-pro | 13,463, GPL-3.0 | Gradio front end | GUI only, ~20 GB, per SKILL.md. NOT RECOMMENDED |
| debpalash/VoiceStudio | 116,015, AGPL-3.0, created 2026-04-09 | Local ElevenLabs alternative | AGPL, GUI, and an unusual star count for its age. NOT RECOMMENDED |
| coqui-ai/TTS | 46,265, last push 2024-08-16 | Toolkit | Abandoned. The fork idiap/coqui-ai-TTS (2,356 stars) is alive but older-generation. NOT RECOMMENDED |

---

## 15. Upscaling and restoration

**Rule:** FINAL_ASSEMBLY section 5 bans sources under 640 px and bans upscaling tiny clips. These tools are for modest fixes only.

### xinntao/Real-ESRGAN: OPTIONAL
- **Checked:** 37,602 stars, BSD-3-Clause, last push 2024-08-06.
- **Good for:** 2x on a real *still* that sits between 720 and 1000 px, for a Ken Burns move.
- **Use it with:** the ncnn-vulkan exe from xinntao/Real-ESRGAN-ncnn-vulkan (2,306 stars).
- **Replace:** the archived `realesrgan_ncnn_py` binding.

### k4yt3x/video2x: OPTIONAL
- **Checked:** 22,842 stars, AGPL-3.0, last push 2026-03-07.
- **Good for:** upscaling video and frame interpolation on Windows.
- **Use it when:** an irreplaceable 720p archive clip needs a mild 1.5x.

### upscayl/upscayl: OPTIONAL (manual)
- **Checked:** 53,036 stars, AGPL-3.0.
- **Good for:** a GUI for one-off stills.

### TNTwise/REAL-Video-Enhancer: OPTIONAL
- **Checked:** 2,430 stars, AGPL-3.0.
- **Good for:** a Windows GUI that combines upscaling, interpolation, and denoising.

### hzwer/Practical-RIFE: OPTIONAL, with caution
- **Checked:** 1,050 stars, MIT.
- **Good for:** smooth slow motion of a real movement clip.
- **Caution:** it invents in-between frames, so never use it on faces in close-up.

### TencentARC/GFPGAN: NOT RECOMMENDED
- **Checked:** 37,724 stars, license NOASSERTION.
- **Why not:** face restoration **invents facial detail**. A "restored" celebrity face is an AI image of a real person, which the Standing Ruling bans.

### sczhou/CodeFormer: NOT RECOMMENDED
- **Checked:** 18,256 stars, license NOASSERTION.
- **Why not:** the same as GFPGAN. Face restoration invents facial detail, which the Standing Ruling bans.

### KlingAIResearch/LivePortrait: NOT RECOMMENDED
- **Checked:** 19,544 stars, license NOASSERTION.
- **Why not:** animating a real person's photo is fabricated motion of a real person. FINAL_ASSEMBLY allows it "labelled," but that conflicts with the no-AI-images ruling. Drop it.

---

## 16. Stabilisation

### FFmpeg `vidstabdetect` / `vidstabtransform`: CORE
- **Good for:** shaky red-carpet and handheld footage. Already used in `stabilise.py`.

---

## 17. Thumbnails

### PIL plus brand fonts (`thumb4.py`): CORE
- **Good for:** the fixed reference layout: subject on the right, a stacked headline on the left.

### danielgatis/rembg: ADD NOW
- **Checked:** 25,615 stars, MIT, last push 2026-11-06.
- **Good for:** a clean cut-out of the subject from a *real* photo for the thumbnail. Install with `pip install "rembg[cpu]"`.
- **Don't use it for:** altering the face.

### ZhengPeng7/BiRefNet: OPTIONAL
- **Checked:** 4,437 stars, MIT.
- **Good for:** higher-quality matting around hair edges. rembg can load it.

No thumbnail-generator repo found on GitHub was worth using. The top result had 83 stars and was stale.

---

## 18. Editors, MCP bridges, and agent skills

### kajisho5/ffmpeg-skill: OPTIONAL
- **Checked:** 9,333 stars, MIT, standard library only, created 2026-09-03.
- **Good for:** an agent-facing FFmpeg toolset that measures its own output.
- **Use it when:** you want a fast probe or measure check.
- **Don't use it for:** replacing the proven `build5.py` edit decision list renderer. It is too new to be "Core."

### JuneYaooo/rea-video: OPTIONAL
- **Checked:** 11,867 stars, Apache-2.0.
- **Good for:** breaking a top reference-channel video into a shot-by-shot VIDEO.md, so you can copy its pacing.
- **Use it when:** you plan the edit, once per format change.

### hetpatel-11/Adobe_Premiere_Pro_MCP: OPTIONAL
- **Checked:** 915 stars, MIT.
- **Use it when:** the owner finishes in Premiere. It requires Premiere.

### samuelgursky/davinci-resolve-mcp: OPTIONAL
- **Checked:** 4,275 stars, MIT. Its description says it is for DaVinci Resolve **Studio**, the paid version.
- **Use it when:** a manual colour or finish pass happens in Resolve.

### AgriciDaniel/claude-youtube: OPTIONAL
- **Checked:** 839 stars, MIT.
- **Good for:** a Claude Code skill for channel audits, SEO, and thumbnail review.
- **Use it when:** you draft metadata.

### mifi/lossless-cut: OPTIONAL (manual)
- **Checked:** 46,302 stars, GPL-2.0.
- **Good for:** a quick lossless trim of a downloaded file by hand.

### Not recommended: desktop editors and translation suites

None of these fits a headless Windows agent pipeline.

| Repo | Checked | Why not |
|---|---|---|
| jub0t/Concat | 19,461 stars, AGPL-3.0, created 2026-08-25 | Beta |
| storytold/filmcraft | 18,784 stars, created 2026-09-30 | Desktop editor |
| mltframework/shotcut | 15,756 stars | Desktop editor |
| palmier-io/palmier-pro | 14,800 stars | **macOS only**, so useless on this laptop |
| Forward-Future/scarlet | 501 stars | Desktop editor |
| MartinDelophy/ai-video-editor | 1,002 stars | Desktop editor |
| openfilm/openfilm | 8,891 stars | Generative video agent |
| shinyobjectz/raea | 3,328 stars | Generative render engine |
| krillinai/OpenCreator | 14,459 stars | **Translation and dubbing into 120 languages.** Not our job. |
| OpenMontageInc/OpenMontage | 82,157 stars, AGPL-3.0, created 2026-03-29 | Generative production system |
| Vincentwei1021/video-shotcraft | 21,986 stars | Product-promo videos |
| Zulko/moviepy | 15,188 stars, MIT | FFmpeg already does everything moviepy would do, faster. OPTIONAL at most. |

---

## 19. YouTube upload, captions, metadata, analytics

### googleapis/google-api-python-client: ADD NOW
- **Checked:** 8,975 stars, Apache-2.0, last push 2026-11-17.
- **Good for:**
  - Data API v3: `videos.insert` (unlisted upload), `thumbnails.set`, `captions.insert` (SRT), and `videos.update` (title, description with CC-BY credits, tags, chapters).
  - YouTube Analytics API v2 `reports.query` for a weekly table: views, average view duration, retention, CTR, and subscribers per video, written to a Sheet.
- **Use it when:** you upload, and for the weekly analytics job. Keep weekly tracking as an on-demand run, because the fleet's token freeze bans scheduled digests until it is lifted.
- **Install:**
  ```
  pip install google-api-python-client google-auth-oauthlib
  ```
- **Reference:** youtube/api-samples (6,026 stars).

### porjo/youtubeuploader: OPTIONAL
- **Checked:** 895 stars, Apache-2.0, last push 2026-11-20.
- **Good for:** a single Go binary that uploads with metadata JSON.

### ZubeidHendricks/youtube-mcp-server: OPTIONAL
- **Checked:** 605 stars, MIT.
- **Good for:** an MCP for reading YouTube data from Claude.

### tokland/youtube-upload: NOT RECOMMENDED
- **Checked:** 2,188 stars, last push 2024-04-25.
- **Why not:** stale, with no license.

---

## Gaps: tools we should add now, ranked by impact on video quality

1. **A proper music bed chain.** The owner overrode "no music," and nothing mixes a bed today.
   - CLAP: track-to-mood matching.
   - Silero: speech map.
   - FFmpeg `sidechaincompress`: ducking, with 120 Hz high-pass and `normalize=0`.
   - ffmpeg-normalize: two-pass loudness.
2. **python-audio-separator.** Strips foreign music out of interview bites, so the bed sits cleanly and claims inside bites go down.
3. **Kokoro phoneme input (`with_phonemes.py` plus misaki).** A real fix for homographs and names, instead of respelling. Keep the Whisper diff gate.
4. **pyannote diarization in the bite gate.** Stops wrong-speaker bites, an error class named in SKILL.md.
5. **whisperX alignment.** Word-exact bite edges and captions. FINAL_ASSEMBLY requires it, but nothing uses it.
6. **Premium transitions.** HyperFrames transition blocks at chapter cards, plus FFmpeg `xfade` between footage. There are no picture transitions today.
7. **Shorts rebuilt from the long-form.** Use the claude-shorts pattern, our own YuNet reframe, the HyperFrames captions-overlay, and Kokoro. Retire MoneyPrinterTurbo with ElevenLabs and Pexels.
8. **DeepFilterNet** on noisy bites.
9. **google-api-python-client** for unlisted upload, the SRT caption track, metadata, and the on-demand weekly Analytics report.
10. **beat_this.** Downbeat-snapped cuts in training montages and chapter hits.
11. **rembg.** Cleaner thumbnail cut-outs from real photos.

## Drop or demote

- **Demote autoclip from Core to Optional.** It is Chinese-platform-first, uses paid cloud models, and bypasses our bite gates.
- **Remove from the "Approved" table:**
  - LivePortrait, which breaks the real-people rule.
  - OpenCreator, which does translation.
  - palmier-pro, which is macOS only.
  - Concat, filmcraft, shotcut, and scarlet, which are desktop editors.
  - openmotion, openfilm, and raea, which are generative.
  - FunClip, which is Mandarin ASR.
- **Retire these code paths:**
  - Chatterbox (archived upstream, and it breaks the ruling).
  - edge-tts and ElevenLabs in `tts*.py` and `voice.py`.
  - The archived `realesrgan_ncnn_py` binding.
  - MoneyPrinterTurbo for celebrity Shorts.
- **Unify:** use PySceneDetect for cut checks in both repos, and one CLIP implementation.

## Core install (Windows 11, Python 3.12)

```
winget install Gyan.FFmpeg DenoLand.Deno OpenJS.NodeJS.LTS
py -3.12 -m venv .venv && .venv\Scripts\activate
pip install -U "yt-dlp[default]" faster-whisper silero-vad "scenedetect[opencv]" opencv-python open_clip_torch rapidocr_onnxruntime librosa ffmpeg-normalize kokoro-onnx soundfile "misaki[en]"
# ADD NOW set
pip install whisperx pyannote.audio audio-separator laion-clap beat-this deepfilternet "rembg[cpu]" google-api-python-client google-auth-oauthlib
# HyperFrames (Node 22+)
npx hyperframes --help
```

Package names on PyPI were taken from each repo's README where it was checked: beat-this, kokoro-onnx, scenedetect, faster-whisper, ffmpeg-normalize, and silero-vad. These were not checked: whisperx, pyannote.audio, audio-separator, laion-clap, deepfilternet, and rembg. Their names follow standard usage, but confirm each with `pip index versions <name>` before relying on it. Torch-based packages need the CPU or CUDA torch wheel installed first.
