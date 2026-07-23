#!/usr/bin/env python3
"""
RUN - non-interactive pipeline runner for the Celeb Workout builder.

One command drives the whole flow so it can run under automation / the
/celebvid skill (the original CELEB_VIDEO.py is interactive-only):

  config.json  ->  footage download  ->  scene detect + contact sheets
  ->  Gemini auto-tag (AUTO_TAGS)  ->  render (GENERATE_FINAL_VIDEO)

Voice:  --tts elevenlabs uses the Titan voice (needs an ElevenLabs key);
        default edge-tts is free. --audio reuses an existing narration
        (a file OR a YouTube URL/id) and skips TTS entirely.
Script: --transcript takes a local file OR a YouTube URL/id (captions are
        pulled) OR, with --gen-transcript, Claude writes one (needs
        ANTHROPIC_API_KEY).

Examples:
  # Trial: rebuild Ryan reusing the published audio + its captions
  python RUN.py --name "Ryan Reynolds" --coach "Don Saladino" \
      --transcript iJyAcSuuuq8 --audio iJyAcSuuuq8

  # New video, Titan voice, Claude-written script
  python RUN.py --name "Jason Statham" --gen-transcript --minutes 8 \
      --tts elevenlabs
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def is_yt(s):
    return bool(re.search(r"(youtu\.be/|youtube\.com/|watch\?v=)", s)) \
        or bool(re.fullmatch(r"[\w-]{11}", s))


def yt_id(s):
    m = re.search(r"(?:youtu\.be/|watch\?v=|/embed/)([\w-]{11})", s)
    return m.group(1) if m else s


def _captions_via_ytdlp(vid):
    """Pull auto/manual subs with yt-dlp and flatten the VTT to prose.
    Robust to youtube_transcript_api IP bans."""
    import tempfile
    d = Path(tempfile.mkdtemp())
    base = d / vid
    subprocess.run(["yt-dlp", "--skip-download", "--write-subs",
                    "--write-auto-subs", "--sub-langs", "en.*",
                    "--sub-format", "vtt", "-o", str(base),
                    f"https://youtu.be/{vid}"],
                   capture_output=True, timeout=120)
    vtts = list(d.glob("*.vtt"))
    if not vtts:
        return ""
    seen, out = set(), []
    for line in vtts[0].read_text(encoding="utf-8", errors="ignore").splitlines():
        if "-->" in line or line.strip().startswith(("WEBVTT", "Kind:",
                                                     "Language:")) or not line.strip():
            continue
        t = re.sub(r"<[^>]+>", "", line).strip()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return " ".join(out)


def fetch_captions(src, dest):
    """Pull YouTube captions as the narration transcript (matches reused
    audio timing). Tries youtube_transcript_api, then yt-dlp."""
    vid = yt_id(src)
    text = ""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        try:
            snips = [s.text for s in YouTubeTranscriptApi().fetch(vid)]
        except AttributeError:
            snips = [s["text"] for s in YouTubeTranscriptApi.get_transcript(vid)]
        text = " ".join(snips)
    except Exception:
        text = _captions_via_ytdlp(vid)
    if not text.strip():
        raise SystemExit(f"[!] could not fetch captions for {vid} "
                         "(try passing a local --transcript file instead)")
    dest.write_text(f"# {dest.stem}\n\n{text}\n", encoding="utf-8")
    print(f"[OK] transcript from captions: {dest.name} "
          f"({len(text.split())} words)")


def pull_audio(src, dest):
    """Download an mp3 to reuse as the voiceover (skips TTS)."""
    vid = yt_id(src)
    subprocess.run(["yt-dlp", "-x", "--audio-format", "mp3",
                    "--audio-quality", "0", "-o", str(dest.with_suffix("")),
                    f"https://youtu.be/{vid}"], check=True)
    # yt-dlp appends .mp3
    out = dest.with_suffix(".mp3")
    if out.exists() and out != dest:
        out.replace(dest)
    print(f"[OK] reused audio -> {dest.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="celebrity/subject name")
    ap.add_argument("--coach", default="", help="trainer/coach name")
    ap.add_argument("--transcript", default="",
                    help="local file, YouTube URL/id (captions), or blank")
    ap.add_argument("--gen-transcript", action="store_true",
                    help="write the script with Claude (needs ANTHROPIC_API_KEY)")
    ap.add_argument("--minutes", type=int, default=8)
    ap.add_argument("--audio", default="",
                    help="existing narration to reuse: file OR YouTube URL/id")
    ap.add_argument("--tts", default="edge",
                    choices=["edge", "elevenlabs"])
    ap.add_argument("--el-voice", default="Titan", help="ElevenLabs voice name")
    ap.add_argument("--voice", default="en-US-ChristopherNeural",
                    help="edge-tts voice")
    ap.add_argument("--pexels", action="store_true",
                    help="also pull generic Pexels B-roll")
    ap.add_argument("--skip-download", action="store_true")
    args = ap.parse_args()

    slug = slugify(args.name)
    os.environ["CELEB_ROOT"] = str(ROOT)
    os.environ["CELEB_SUBJECT"] = args.name

    # ---- transcript --------------------------------------------------
    transcript = ROOT / f"transcript_{slug}.md"
    if args.gen_transcript:
        sys.path.insert(0, str(ROOT))
        from CELEB_VIDEO import generate_transcript
        transcript, detected = generate_transcript(args.name, args.minutes)
        args.coach = args.coach or detected
    elif args.transcript and is_yt(args.transcript):
        if transcript.exists() and len(transcript.read_text(
                encoding="utf-8").split()) > 50:
            print(f"[=] transcript exists: {transcript.name}")
        else:
            fetch_captions(args.transcript, transcript)
    elif args.transcript:
        transcript = Path(args.transcript)
        if not transcript.exists():
            raise SystemExit(f"[!] transcript not found: {transcript}")
    else:
        raise SystemExit("[!] need --transcript or --gen-transcript")

    # ---- config ------------------------------------------------------
    cfg = {
        "subject": args.name, "coach": args.coach, "slug": slug,
        "voice": args.voice, "transcript": str(transcript),
        "output": f"{slug.upper()}_FINAL.mp4",
        "tts": args.tts, "el_voice_name": args.el_voice,
    }
    (ROOT / "config.json").write_text(json.dumps(cfg, indent=2))
    print(f"[OK] config.json (subject={args.name}, coach={args.coach or 'none'}"
          f", tts={args.tts})")

    # ---- reuse audio (skips TTS) -------------------------------------
    voiceover = ROOT / f"voiceover_{slug}.mp3"
    if args.audio and voiceover.exists() and voiceover.stat().st_size > 100_000:
        print(f"[=] voiceover exists: {voiceover.name}")
    elif args.audio:
        if is_yt(args.audio):
            pull_audio(args.audio, voiceover)
        else:
            import shutil
            shutil.copy(args.audio, voiceover)
            print(f"[OK] reused audio -> {voiceover.name}")

    # ---- footage -----------------------------------------------------
    if not args.skip_download:
        sys.path.insert(0, str(ROOT))
        from CELEB_VIDEO import build_queries, download
        print("\n[1/4] Downloading subject footage...")
        download(build_queries(args.name, args.coach, slug))
        if args.pexels:
            print("\n[1b] Generic Pexels B-roll...")
            from DOWNLOAD_VIDEOS import download_pexels_videos
            os.chdir(ROOT)
            download_pexels_videos()

    # ---- detect + sheets --------------------------------------------
    print("\n[2/4] Scene detection + contact sheets...")
    subprocess.run([PY, str(ROOT / "INDEX_NEW.py")], check=True,
                   env={**os.environ, "CELEB_ROOT": str(ROOT)})

    # ---- auto-tag ----------------------------------------------------
    print("\n[3/4] Auto-classifying scenes (Gemini)...")
    subprocess.run([PY, str(ROOT / "AUTO_TAGS.py")],
                   env={**os.environ, "CELEB_ROOT": str(ROOT)})

    # ---- render ------------------------------------------------------
    print("\n[4/4] Rendering final video...")
    r = subprocess.run([PY, str(ROOT / "GENERATE_FINAL_VIDEO.py")],
                       env={**os.environ, "CELEB_ROOT": str(ROOT)})
    ok = r.returncode == 0
    out = ROOT / "final_video" / cfg["output"]
    print(f"\n{'[OK]' if ok else '[FAILED]'} "
          f"{out if out.exists() else 'no output produced'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
