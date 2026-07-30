# CELEBVID CHARTER — full operating guide

Detailed instructions for producing a **Celeb Workout** "Train Like ___"
documentary end-to-end. The `/celebvid` skill and the short `/goal` both
point here. Repo lives at `C:\Users\avina\ytceleb` (GitHub:
`avinash753159/ytceleb`).

The channel format to emulate (see the Ryan Reynolds reference,
`youtu.be/iJyAcSuuuq8`): 6–10 min, deep authoritative male voiceover, subject
footage ~90% with exercise/coach/food B-roll ~10%, animated title + chapter
cards + lower-thirds + stat callouts, no on-screen presenter.

---

## 0. One-time setup (do once)

1. `cd C:\Users\avina\ytceleb`
2. `pip install yt-dlp edge-tts pillow requests google-genai youtube-transcript-api anthropic`
3. Drop keys (each optional; each unlocks a feature):
   - `gemini_key.txt`  → a **valid AI Studio** key from https://aistudio.google.com/apikey
     (the shell's `GOOGLE_API_KEY` is a Cloud-Assist key and the public Gemini
     API rejects it — you need an AI Studio key). Unlocks auto B-roll tagging.
   - `elevenlabs_key.txt` → ElevenLabs key. Unlocks the **Titan** voice.
   - `anthropic_key.txt` → Claude key. Unlocks auto script-writing.
   - Pexels key is already built into `DOWNLOAD_VIDEOS.py`.

Verify keys before a long run:
```bash
python AUTO_TAGS.py     # prints whether the Gemini key is accepted
```

---

## 1. Produce one video

**The single command** (this is what the skill runs):
```bash
python RUN.py --name "<Celebrity>" --coach "<Trainer or blank>" \
    --gen-transcript --minutes 8 --tts elevenlabs --el-voice Titan --pexels
```
Stages, in order (all resumable — re-running skips finished work):
1. **Transcript** — Claude writes an ~8-min script (`--gen-transcript`), OR
   pass `--transcript <file|YouTubeURL>` to supply one. A YouTube URL pulls that
   video's captions (useful to reuse an existing narration's wording).
2. **Voice** — `--tts elevenlabs` → Titan (chunks long scripts, concatenates).
   Omit or `--tts edge` for the free voice. `--audio <file|YouTubeId>` reuses an
   existing narration and skips TTS entirely.
3. **Footage** — `CELEB_VIDEO.build_queries` runs ~14 targeted yt-dlp searches
   (gym, BTS, interview, diet, coach). `--pexels` adds generic exercise/food
   B-roll via the built-in Pexels key.
4. **Scene detect + contact sheets** — `INDEX_NEW.py` (ffmpeg scene detection).
5. **Auto-tag** — `AUTO_TAGS.py` classifies every scene with Gemini →
   `vision_tags.json`. No key → filename fallback (still renders).
6. **Render** — `GENERATE_FINAL_VIDEO.py` builds the timeline (subject-first,
   ≤4s/shot, no repeats), overlays animated text, validates, renders
   `final_video/<SLUG>_FINAL.mp4`.

---

## 2. Quality checklist (before publishing)

- Duration within ~5s of the narration length (the editor validates this).
- Subject-to-B-roll balance reads ~90/10; no long stretches of generic stock.
- Exercise sentences show the exercise, not just a talking head.
- No female-as-subject / graphics / reaction-cam shots survived (auto-tag
  marks these `use=0`; spot-check if you used the filename fallback).
- Titan voice is consistent; no edge-tts fallback slipped in (check the run
  log for "ElevenLabs failed" / "no key found").
- Thumbnail + title + description written (manual for now — see backlog).

**Beyond "not broken" — is it incredible?** `qc.py` only checks the render isn't
broken. To score whether a video will actually be *clicked, watched, and subscribed
to*, run the Incredible eval against the retention-first rubric in `eval/RUBRIC.md`:
```bash
py -3.12 pipeline/eval.py --slug <slug> --mp4 final_video/<SLUG>_FINAL.mp4 \
    --title "<title>" --thumb <thumb.png>       # -> eval_report.json + top_fixes
py -3.12 pipeline/eval.py --calibrate            # sanity-check the scorer (offline)
```
It reuses `qc.py` for the technical A/V dimension and anchors 10/10 to Gavia's
Khamzat film; the channel's own drafts should land ~4–6.

---

## 3. Upload (optional, semi-automated)

YouTube upload needs OAuth. Reuse the token tooling in
`C:\Users\avina\OneDrive\Desktop\Claude Projects\XL Eagle\Tools and Dashboards\Pickle creation`
(the same pickle/token generators used for other Google APIs) to mint a
YouTube Data API token, then upload with `yt-dlp`-adjacent tooling or the
YouTube API. Keep uploads **unlisted** until reviewed.

---

## 4. Troubleshooting

| Symptom | Fix |
|---|---|
| `HTTP 429 Too Many Requests` / captions fail | YouTube is rate-limiting this IP. Wait 15–60 min or use another network; `RUN.py` steps are resumable, just re-run. |
| Gemini "API key not valid" | You're using the Cloud-Assist `GOOGLE_API_KEY`. Put a real AI Studio key in `gemini_key.txt`. |
| ElevenLabs voice not found | Set `el_voice_id` in `config.json`, or confirm a voice literally named "Titan" exists on the account. |
| Few/repetitive shots | Add `--pexels`; download more (re-run downloads); ensure auto-tag ran. |
| Render fails "duration mismatch" | Transcript too short/long for the audio; regenerate script at the right `--minutes`, or trim audio. |
| No captions on a reuse source | Pass a local `--transcript` file instead. |

---

## 5. Backlog (future upgrades, not yet built)

- Burned-in captions synced to the voiceover.
- Auto thumbnail (title card: celebrity + hook).
- Branded intro/outro + licensed music bed.
- Extend Pexels/queries per muscle group for richer exercise B-roll.
- Fully automated upload with the Pickle-creation YouTube token.

---

## 6. The trial (reference run)

The Ryan Reynolds trial rebuilds `youtu.be/iJyAcSuuuq8` by **reusing its audio**
and re-editing fresh B-roll — proof the pipeline renders end-to-end:
```bash
python RUN.py --name "Ryan Reynolds" --coach "Don Saladino" \
    --transcript iJyAcSuuuq8 --audio iJyAcSuuuq8 --pexels
```
B-roll won't match the original clip-for-clip (original source footage isn't in
the repo); the narration will, because it's the same audio.
