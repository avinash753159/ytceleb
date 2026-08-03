# Setup — running this pipeline yourself

Everything needed to build a Celeb Workout documentary from a celebrity name.
Proven end to end on *The Disease That Built MrBeast* — 12:19, 135 shots,
**$9.40** of generation.

**No API keys are in this repo and none ever should be.** A key committed to
GitHub is a key someone else spends. Every one below is free to obtain; the
paid ones are prepaid and capped so a mistake costs cents.

---

## 1. Machine

- **Windows or Linux.** Built and tested on Windows 11.
- **Python 3.14** (3.12+ works). `ffmpeg` and `ffprobe` on `PATH`.
- ~20 GB free. Renders and downloads are large; the repo is not.
- Many cores helps. ffmpeg grabs every core by default — the pipeline pins
  `-threads 2` per process on purpose.

```bash
git clone https://github.com/avinash753159/ytceleb.git
cd ytceleb
pip install -r requirements.txt   # or the list in section 3
```

---

## 2. Keys — what to get, where, and what it costs

Create each file in the repo root. **All are gitignored.**

### `.veo_key` — image and video generation (REQUIRED)

The one that costs money. Get it at **https://aistudio.google.com/apikey**.

- Must be on a **billing-enabled** project. Veo is paid-tier only.
- Add credit under *Payments* in AI Studio. **$25 is plenty for two films.**
- Paste the key alone into `.veo_key`, no quotes, no newline.

**Costs, measured:**

| What | Price | A 12-minute film |
|---|---|---|
| Still (`gemini-3.1-flash-lite-image`) | ~$0.04 | ~100 stills ≈ $4 |
| Video (`veo-3.1-lite-generate-preview`, 720p) | $0.05/sec | ~30 clips ≈ $9 |
| **Realistic total** | | **$8–10** |

**Gotchas that cost real time:**
- The key goes in `?key=`, **never** as an OAuth bearer token. A bearer
  returns `API_KEY_SERVICE_BLOCKED`, which reads exactly like a revoked key.
- **The file beats your environment.** If your shell has a stale
  `GOOGLE_API_KEY` from another project, the pipeline still prefers `.veo_key`.
  It prints which source it used, masked.
- Veo's quota is **periodic**. A `429` is not exhausted money — wait and
  re-run. The worker is resumable.
- The Developer API **rejects** `seed`, `generate_audio`, `negative_prompt`,
  `person_generation` and `fps`. They are Vertex-only and raise client-side.

### `elevenlabs_key.txt` — narration (REQUIRED for final audio)

**https://elevenlabs.io** → Profile → API key.

- **Creator tier (~$22/mo)** gives 100k credits ≈ 20 scripts.
- Free tier works with the premade voice **Brian**
  (`nPczCjzI2devNBz1zQrb`); library voices need a paid plan.
- Model `eleven_turbo_v2_5` — 0.5 credits/char, half the cost of
  multilingual, quality fine for voiceover.
- A 10-minute script ≈ 9,500 chars ≈ **4,800 credits**.

**Build the whole video on a free `edge-tts` draft first.** Paid narration
fires **once**, on the locked script. Never spend credits before the picture
is final.

### `anthropic_key.txt` — script writing (optional)

**https://console.anthropic.com**. Unlocks automated script drafting. You can
write scripts by hand instead.

### Not needed

Pexels is built in. No Vertex AI, no Google Cloud project, no gcloud —
**Vertex bills a card and ignores AI Studio prepay**, which is backwards.

---

## 3. Python packages

```bash
pip install google-genai yt-dlp edge-tts pillow numpy opencv-python \
            mediapipe rapidocr-onnxruntime transformers torch \
            youtube-transcript-api requests pytest
```

- `torch` CPU-only is fine. Depth estimation runs ~40 s/shot on CPU.
- `mediapipe` pulls `opencv-contrib-python`; harmless.
- **`depthflow` will not install on Python 3.14** — `moderngl` has no wheels
  and needs a C++ toolchain. It is not needed; `pipeline/flow_dibr.py`
  implements the same depth warp.

---

## 4. Fonts — already included

`graphics/public/fonts/` — Anton, Archivo Black, Archivo Regular/Medium/
SemiBold, Allura. All SIL Open Font License, cleared for commercial video,
thumbnails and logos. **Keep the licence file if you pass them on.**

Read `docs/BRAND.md` before building any graphic. Four type roles, three
families, `#B22B1A` red, 70/20/10 ratio. Using one font for everything is the
main reason output looks machine-made.

---

## 5. Making a film

```bash
# 1. Research. Find the interview moment nobody has transcribed.
#    On the last film this was 87 minutes into a podcast that four
#    earlier passes had called empty. Highest-leverage hour in the job.

# 2. Sources BEFORE script. YouTube rules: one clip per source video,
#    nothing over 10 seconds, no repeats. Print quotes need no clip at
#    all - they become on-screen documents. See dossier/hemsworth/SOURCES.md.

# 3. Script, then lock the audio. Everything downstream derives from it.

# 4. Shot manifest
python pipeline/flow_plan.py

# 5. Read every prompt against the line it plays under, then generate
python pipeline/flow_still.py --cap 5.00 --fallback   # stills, ~$0.04 each
python pipeline/flow_gen.py  --cap 10.00              # video, ~$0.30 each

# 6. Assemble - frame-exact against the locked audio
python pipeline/flow_assemble.py --out final_video/FILM.mp4

# 7. Watch it. Every build here has passed every automatic check
#    and still failed review.
```

Both workers are **resumable and capped**. Kill one, re-run it, it continues.
`--cap` stops submission, not just warns.

---

## 6. Effects

- `pipeline/fx_text.py` — `text_matte` (footage through type),
  `source_highlight` (a page treated as a physical object, OCR-located
  highlight), `headline_over` (text in front of footage, words accented as
  spoken)
- `pipeline/fx_camera.py` — 15 named camera moves on a still:
  `dolly_zoom_in` (Vertigo), `crash_zoom_in`, `focus_change`, `orbit_360`,
  `head_tracking`, `handheld`, `crane_up`, `dutch_angle`, `low_shutter`…
- `pipeline/flow_dibr.py` — depth-based push-in
- `pipeline/fx.py` — 13 older ffmpeg effects

**All cost nothing per shot.** They composite material you already have. A
camera move on a generated still is $0.04; the same beat as generated video is
$0.30.

---

## 7. Read before you start

| File | Why |
|---|---|
| `docs/BRAND.md` | The visual identity. Not optional. |
| `docs/FX_CATALOGUE.md` | Every effect and the reference it came from. |
| `HANDOFF.md` | The 13 hard rules, each from a rejected cut. |
| `SESSION_LOG.md` | What was tried and failed. Saves days. |
| `dossier/hemsworth/SOURCES.md` | How to build a source map that satisfies the copyright rules. |

---

## 8. The mistakes that cost the most

Every one of these was found the expensive way.

1. **Timings come from the edit list, never a transcript.** Whisper merges
   long pauses and drifts 10+ seconds.
2. **A file on disk is not proof of a usable clip.** A quota-halted attempt
   leaves a partial mp4. Trust the ledger's `state == "done"`.
3. **Charge the budget when the API accepts a job**, not when the download
   parses. Otherwise a bad response assumption leaves spend at $0.00, the cap
   never trips, and the worker burns the backlog reporting nothing spent.
4. **Never pad or loop a short render.** It is an error. Padding once put an
   18-second frozen frame in the middle of a film.
5. **Cache renders on a content fingerprint, not the shot name.** Names are
   positional; swap a clip and a name-keyed cache serves the stale render
   forever. This is also what makes revisions cheap — change one prompt, one
   shot re-renders, nothing else moves.
6. **A shot that needs explaining has failed.** Literal beats metaphorical.
