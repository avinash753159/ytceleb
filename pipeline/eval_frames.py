#!/usr/bin/env python3
"""eval_frames.py - cheap keyframe sampling + contact sheets for the eval.

Watching a 30-minute MP4 with a vision model is expensive and slow, so the
Incredible eval never sends raw video. It samples keyframes (dense over the
first ~90s where the hook lives, sparse elsewhere), tiles them into labeled
contact sheets - the same trick VISION_INDEX.py uses - and sends one image per
~20 frames to the vision judge.

Also exposes probe_settings(): the ffprobe read that backs the E_settings
technical gate (>=1080p, 24-30fps, h264/aac).

Everything degrades gracefully: no ffmpeg/ffprobe or no Pillow -> returns
empty/None rather than crashing, matching the pipeline's convention.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent

CELL_W, CELL_H = 320, 180
COLS = 4
HOOK_WINDOW = 90.0      # seconds of dense sampling at the top
HOOK_STEP = 6.0         # a frame every 6s inside the hook window
BODY_STEP = 60.0        # a frame a minute after that
MAX_FRAMES = 24


def _have(cmd):
    from shutil import which
    return which(cmd) is not None


def probe(video):
    """Return the raw ffprobe json for a video, or {} if unavailable."""
    if not _have("ffprobe"):
        return {}
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", str(video)],
        capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}


def probe_settings(video):
    """Delivery settings for the E_settings gate. Returns a dict with
    width/height/fps/vcodec/acodec/duration and a `pass` bool, or
    {'available': False} if ffprobe is missing."""
    p = probe(video)
    if not p:
        return {"available": False}
    v = next((s for s in p.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in p.get("streams", []) if s.get("codec_type") == "audio"), {})
    h = int(v.get("height") or 0)
    w = int(v.get("width") or 0)
    fr = v.get("avg_frame_rate") or v.get("r_frame_rate") or "0/1"
    try:
        n, d = fr.split("/")
        fps = float(n) / float(d) if float(d) else 0.0
    except Exception:
        fps = 0.0
    vcodec = v.get("codec_name", "")
    acodec = a.get("codec_name", "")
    dur = float(p.get("format", {}).get("duration") or 0.0)
    ok = (h >= 1080 and 23.5 <= fps <= 30.5
          and vcodec in ("h264", "hevc", "avc1")
          and acodec in ("aac", "mp4a"))
    return {"available": True, "width": w, "height": h, "fps": round(fps, 2),
            "vcodec": vcodec, "acodec": acodec, "duration": round(dur, 2),
            "pass": ok}


def sample_times(duration):
    """Dense in the hook window, sparse after; capped at MAX_FRAMES."""
    times = []
    t = 0.5
    while t < min(HOOK_WINDOW, duration):
        times.append(round(t, 2))
        t += HOOK_STEP
    t = HOOK_WINDOW + BODY_STEP
    while t < duration and len(times) < MAX_FRAMES:
        times.append(round(t, 2))
        t += BODY_STEP
    return times[:MAX_FRAMES]


def _extract(video, t, out):
    subprocess.run(["ffmpeg", "-ss", f"{t:.2f}", "-i", str(video),
                    "-frames:v", "1", "-q:v", "3", "-y", str(out)],
                   capture_output=True, timeout=60)
    return out if out.exists() else None


def _pil():
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "pillow", "-q"],
                       check=False)
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            return None
    return (Image, ImageDraw)


def build_sheets(video, workdir):
    """Extract keyframes and tile them into labeled contact-sheet JPGs.
    Returns a list of sheet paths (possibly empty). Never raises."""
    video = Path(video)
    if not video.exists() or not _have("ffmpeg"):
        return []
    settings = probe_settings(video)
    duration = settings.get("duration") or 0.0
    if not duration:
        return []
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    times = sample_times(duration)

    frames = []
    for i, t in enumerate(times):
        f = _extract(video, t, workdir / f"f_{i:03d}.jpg")
        if f:
            frames.append((t, f))
    if not frames:
        return []

    pil = _pil()
    if pil is None:
        # can't tile; hand back individual frames so a caller can still use them
        return [f for _, f in frames]
    Image, ImageDraw = pil

    rows = (len(frames) + COLS - 1) // COLS
    per_sheet = COLS * 5
    sheets = []
    for s0 in range(0, len(frames), per_sheet):
        chunk = frames[s0:s0 + per_sheet]
        srows = (len(chunk) + COLS - 1) // COLS
        sheet = Image.new("RGB", (COLS * CELL_W, srows * CELL_H), (12, 12, 12))
        draw = ImageDraw.Draw(sheet)
        for j, (t, f) in enumerate(chunk):
            try:
                im = Image.open(f).convert("RGB").resize((CELL_W, CELL_H))
            except Exception:
                continue
            x, y = (j % COLS) * CELL_W, (j // COLS) * CELL_H
            sheet.paste(im, (x, y))
            label = f"{int(t // 60):02d}:{int(t % 60):02d}"
            draw.rectangle([x, y + CELL_H - 16, x + 52, y + CELL_H], fill=(0, 0, 0))
            draw.text((x + 3, y + CELL_H - 14), label, fill=(255, 255, 255))
        out = workdir / f"sheet_{s0 // per_sheet:02d}.jpg"
        sheet.save(out, quality=85)
        sheets.append(out)
    return sheets


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python eval_frames.py <video.mp4>")
        raise SystemExit(2)
    v = sys.argv[1]
    print("settings:", json.dumps(probe_settings(v), indent=1))
    ss = build_sheets(v, ROOT / "eval" / "_frames_tmp")
    print(f"built {len(ss)} sheet(s):", *[str(s) for s in ss], sep="\n  ")
