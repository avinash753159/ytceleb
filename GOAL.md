# /goal — Make a Celeb Workout video

Paste this whole block into Claude Code to produce one "Train Like ___"
documentary for the Celeb Workout channel.

---

GOAL: Produce a finished "Train Like <CELEBRITY>" documentary MP4 for the
Celeb Workout YouTube channel, emulating the style of youtu.be/iJyAcSuuuq8
(deep authoritative male voiceover, ~90% subject footage with exercise/coach/
food B-roll, animated title + chapter cards + lower-thirds, 6–10 min, no
on-screen presenter).

FIRST, read the full operating guide and follow it exactly:
`C:\Users\avina\ytceleb\CELEBVID_CHARTER.md`

WORKING DIR: `C:\Users\avina\ytceleb`  (GitHub: avinash753159/ytceleb)

STEPS:
1. Confirm setup: ffmpeg on PATH; `pip install -q yt-dlp edge-tts pillow
   requests google-genai youtube-transcript-api anthropic`. Check which keys
   exist (`gemini_key.txt`, `elevenlabs_key.txt`, `anthropic_key.txt`). Tell me
   which upgrades are active (Gemini auto-tagging / Titan voice / Claude script)
   and which will fall back, then continue — do NOT block on missing keys.
2. Run the pipeline (one command):
   ```
   python RUN.py --name "<CELEBRITY>" --coach "<TRAINER or blank>" \
       --gen-transcript --minutes 8 --tts elevenlabs --el-voice Titan --pexels
   ```
   - No Anthropic key? drop `--gen-transcript` and pass
     `--transcript "<path-or-YouTubeURL>"` instead.
   - Reusing an existing narration? add `--audio "<file-or-YouTubeId>"` (skips TTS).
3. If YouTube returns HTTP 429 (rate limit), back off and retry the same command
   — every stage is resumable and skips finished work. Don't give up after one try.
4. When `final_video/<SLUG>_FINAL.mp4` exists, run the Quality Checklist in
   section 2 of the charter. Report the output path, duration, which voice was
   used, whether Gemini auto-tagging ran, and any checklist item that failed.
5. Do NOT upload automatically. Leave the MP4 for my review.

CONSTRAINTS:
- Never invent private facts/quotes about the celebrity; the script must
  attribute claims ("reported", "has said").
- Keep the paid ElevenLabs voice unless I say otherwise; if it fails, fall back
  to edge-tts and TELL me it happened.
- If something genuinely blocks the render (no footage downloadable, no
  transcript obtainable), stop and tell me exactly what's blocking — don't ship
  a broken video.

Replace <CELEBRITY> and <TRAINER> before running. Everything else is in the
charter file above.
