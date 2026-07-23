# ytceleb — Celeb Workout automated video builder

Turns a celebrity name (or a transcript) into a finished "Train Like ___"
documentary for the [Celeb Workout](https://www.youtube.com/@CelebWorkout)
channel: narration → auto-sourced B-roll → content-matched edit → rendered MP4.

Fork of the original documentary builder, upgraded to be **portable,
non-interactive, and self-classifying**.

## What's new in this fork

| Upgrade | Detail |
|---|---|
| **Portable** | `ROOT` is the project folder (was a hardcoded `D:\...` path). Override with `CELEB_ROOT`. |
| **Auto B-roll classification** | `AUTO_TAGS.py` sends the contact sheets to **Gemini vision** and writes `vision_tags.json` automatically — replacing the old manual `GEN_TAGS2.py` review. Shots are chosen on what's *in* the footage. Degrades to the filename heuristic if no key. |
| **ElevenLabs "Titan" voice** | `make_voiceover()` uses ElevenLabs (deep/bold/powerful Titan) when `config.json` `"tts":"elevenlabs"` and a key is present; chunks long scripts under the API limit; falls back to free edge-tts. |
| **One-command runner** | `RUN.py` drives the whole pipeline non-interactively (for automation / the `/celebvid` skill). |
| **Reuse existing audio** | `--audio <file|YouTube id>` drops in a narration and skips TTS (used for the Ryan Reynolds trial). |

## Requirements

- Python 3.10+, `ffmpeg`/`ffprobe` on PATH
- `pip install yt-dlp edge-tts pillow requests google-genai youtube-transcript-api`
- Keys (optional, unlock upgrades):
  - `gemini_key.txt` or `GEMINI_API_KEY` — auto B-roll tagging ([get one](https://aistudio.google.com/apikey))
  - `elevenlabs_key.txt` or `ELEVENLABS_API_KEY` — Titan voice
  - `anthropic_key.txt` or `ANTHROPIC_API_KEY` — Claude-written scripts
  - Pexels key is built in (generic B-roll)

## Quick start

```bash
# New video, Claude-written script, Titan voice, generic Pexels B-roll
python RUN.py --name "Jason Statham" --gen-transcript --minutes 8 \
    --tts elevenlabs --pexels

# Reuse an existing narration (file or YouTube id) and just re-edit the B-roll
python RUN.py --name "Ryan Reynolds" --coach "Don Saladino" \
    --transcript iJyAcSuuuq8 --audio iJyAcSuuuq8 --pexels
```

Output: `final_video/<SLUG>_FINAL.mp4`.

See **[CELEBVID_CHARTER.md](CELEBVID_CHARTER.md)** for the full operating guide
(the `/celebvid` skill and the `/goal` charter both reference it).

## Pipeline

```
config.json → footage (yt-dlp + Pexels) → INDEX_NEW (scene-detect + contact
sheets) → AUTO_TAGS (Gemini) → GENERATE_FINAL_VIDEO (timeline + text + render)
```

Individual stages (`DOWNLOAD_VIDEOS.py`, `VISION_INDEX.py`, `INDEX_NEW.py`,
`GENERATE_FINAL_VIDEO.py`) still run standalone; `RUN.py` just orchestrates them.
