#!/usr/bin/env python3
"""
assemble.py - Phase 4: render the video as a pure function of the manifest.

Per beat (from plan.json + assets.json), produce piece_<beat>.mp4 at
1920x1080/30fps, EXACTLY beat-duration long, silent:

  clip   -> trim + scale/crop (motion_broll / exercise_demo)
  still  -> Remotion <KenBurns> render (no ffmpeg zoompan jitter)
  split  -> Remotion <SplitCompare> (opaque)
  generated (list/stat) -> darkened under-clip + Remotion alpha overlay
  person_card -> darkened under-clip + <PersonCard> alpha overlay
  monogram    -> same, PersonCard renders a monogram when imageSrc=""

Overlays are alpha WebM (vp8 + png + yuva420p) composited per piece with
  ffmpeg -i base -c:v libvpx -i overlay.webm -filter_complex overlay
(libvpx decoder REQUIRED - the native decoder silently drops alpha).

Then: concat all pieces (fast concat demuxer path kept) + mux narration.
Every stage writes artifacts to disk under final_video/v2_work/.

Run:  py -3.12 pipeline/assemble.py [--only b_004]   (--only for debugging)
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest"
GRAPHICS = ROOT / "graphics"
WORK = ROOT / "final_video" / "v2_work"
OUT = ROOT / "final_video"
FPS = 30
W, H = 1920, 1080
ACCENT = "#E63946"          # per-celebrity accent (profiles later)

KB_PANS = [((0.5, 0.5), (0.5, 0.5)), ((0.35, 0.5), (0.65, 0.5)),
           ((0.65, 0.5), (0.35, 0.5)), ((0.5, 0.35), (0.5, 0.65)),
           ((0.5, 0.65), (0.5, 0.35)), ((0.35, 0.35), (0.65, 0.65)),
           ((0.65, 0.35), (0.35, 0.65))]


def run(cmd, timeout=600):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"cmd failed: {' '.join(map(str, cmd))[:200]}\n"
                           f"{(r.stderr or '')[-400:]}")
    return r


def data_url(path):
    """Chrome blocks file:// URIs inside Remotion's served bundle
    ('Not allowed to load local resource') - embed images as data URLs."""
    import base64
    ext = Path(path).suffix.lower().lstrip(".") or "jpeg"
    if ext == "jpg":
        ext = "jpeg"
    b = Path(path).read_bytes()
    return f"data:image/{ext};base64," + base64.b64encode(b).decode()


_BUNDLE = None


def remotion_bundle():
    """Bundle once; every render reuses it (CLI re-bundling is ~15s/call)."""
    global _BUNDLE
    if _BUNDLE:
        return _BUNDLE
    b = WORK / "remotion_bundle"
    if not (b / "index.html").exists():
        run(["npx.cmd", "remotion", "bundle", "src/index.ts",
             "--out-dir", str(b)], timeout=900)
    _BUNDLE = b
    return b


def render_remotion(comp, props, dest, dur_s, alpha):
    """Render a composition; alpha -> vp8 webm, else h264 mp4."""
    props = dict(props)
    props["durationInFrames"] = max(2, round(dur_s * FPS))
    props["fps"] = FPS
    props["accent"] = ACCENT
    pf = WORK / f"props_{dest.stem}.json"
    pf.write_text(json.dumps(props), encoding="utf-8")
    cmd = ["npx.cmd", "remotion", "render", str(remotion_bundle()), comp,
           str(dest), f"--props={pf}", "--log=error"]
    if alpha:
        cmd += ["--codec=vp8", "--image-format=png",
                "--pixel-format=yuva420p"]
    else:
        # config.ts defaults to yuva420p (for overlays) - h264 must override
        cmd += ["--codec=h264", "--image-format=jpeg",
                "--pixel-format=yuv420p"]
    old = os.getcwd()
    os.chdir(GRAPHICS)
    try:
        run(cmd, timeout=900)
    finally:
        os.chdir(old)
    return dest


def _video_start(src):
    """TRUE video start = first packet PTS. yt-dlp --download-sections keeps
    original timestamps, so video packets can begin many seconds after t=0
    while stream/container metadata claims start_time=0; seeking before the
    first packet encodes zero frames."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "packet=pts_time",
                        "-read_intervals", "%+#1", "-of", "csv=p=0",
                        str(src)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip().split("\n")[0].strip(","))
    except Exception:
        return 0.0


def clip_piece(asset, dur, dest, darken=False):
    """Cut a library scene to exactly dur, 1920x1080/30, silent.
    crop_box [l,t,r,b] (from watermark recovery) trims those edges first,
    pushing corner bugs/lower-third logos out of frame."""
    src, s = asset["src"], asset["start"]
    vs = _video_start(src)
    if s < vs:                       # clamp into the actual video range
        s = vs + 0.05
    avail = asset["end"] - s
    if avail < 1.0:                  # asset window collapsed - take from vs
        avail = max(asset["end"], vs + dur + 0.2) - s
    cb = asset.get("crop_box")
    pre = ""
    if cb and any(cb):
        l, t, r, btm = cb
        pre = (f"crop=iw*{1 - l - r:.3f}:ih*{1 - t - btm:.3f}:"
               f"iw*{l:.3f}:ih*{t:.3f},")
    vf = (f"{pre}scale={W}:{H}:force_original_aspect_ratio=increase,"
          f"crop={W}:{H},fps={FPS}")
    if darken:
        # V3: graphics sit over LIVE footage - only a light dim, no blur
        vf += ",eq=brightness=-0.10:saturation=0.85"
    if avail >= dur:
        run(["ffmpeg", "-ss", f"{s + 0.05:.2f}", "-i", src,
             "-t", f"{dur:.3f}", "-vf", vf, "-an", "-c:v", "libx264",
             "-preset", "veryfast", "-crf", "20", "-y", str(dest)])
    else:  # loop the scene to cover the beat (rare: short scene, long beat)
        run(["ffmpeg", "-stream_loop", "3", "-ss", f"{s + 0.05:.2f}",
             "-i", src, "-t", f"{dur:.3f}", "-vf", vf, "-an",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
             "-y", str(dest)])
    return dest


def composite(base, overlay_webm, dest):
    run(["ffmpeg", "-i", str(base), "-c:v", "libvpx", "-i",
         str(overlay_webm), "-filter_complex",
         "[0:v][1:v]overlay=0:0:eof_action=pass",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-pix_fmt", "yuv420p", "-an", "-y", str(dest)])
    return dest


def underlay(assets_all, beat, dur, dest, bg=None):
    """LIVE footage under a graphic (V3): the beat's own resolved bg clip,
    lightly dimmed. Falls back to any resolved clip, then a dark slate."""
    if bg:
        return clip_piece(bg, dur, dest, darken=True)
    for a in assets_all.values():
        if (a.get("asset") or {}).get("kind") == "clip":
            return clip_piece(a["asset"], dur, dest, darken=True)
    run(["ffmpeg", "-f", "lavfi", "-i",
         f"color=c=0x101014:s={W}x{H}:r={FPS}", "-t", f"{dur:.3f}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-y", str(dest)])
    return dest


def face_side(base_piece):
    """Which half of the frame has faces? Graphics go on the OTHER side.
    Returns 'left' or 'right' (side to PLACE the graphic)."""
    try:
        import cv2
        cap = cv2.VideoCapture(str(base_piece))
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        centers = []
        casc = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        for fi in (n // 4, n // 2, 3 * n // 4):
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(fi, 0))
            ok, frame = cap.read()
            if not ok:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            for (x, y, w, h) in casc.detectMultiScale(gray, 1.2, 5,
                                                      minSize=(60, 60)):
                centers.append((x + w / 2) / frame.shape[1])
        cap.release()
        if not centers:
            return "left"
        avg = sum(centers) / len(centers)
        return "right" if avg < 0.5 else "left"   # graphic opposite faces
    except Exception:
        return "left"


def build_piece(p, a, beat, idx, assets_all):
    """One beat -> one exactly-timed silent mp4 piece."""
    bid = p["beat_id"]
    dur = round(beat["end"] - beat["start"], 3)
    piece = WORK / f"piece_{idx:03d}_{bid}.mp4"
    if piece.exists():
        return piece
    tr = a["treatment"]           # post-fallback treatment
    asset = a.get("asset") or {}

    if tr in ("motion_broll", "exercise_demo"):
        if asset.get("kind") == "clip":
            return clip_piece(asset, dur, piece)
        multi = None
        if asset.get("kind") == "clip2":       # >6s beat = two shots
            multi = [asset["a"], asset["b"]]
        elif asset.get("kind") == "clips":     # N shots (long/music beats)
            multi = asset["list"]
        if multi:
            n = len(multi)
            seg = dur / n
            parts = []
            for i, c in enumerate(multi):
                parts.append(clip_piece(
                    c, seg if i < n - 1 else dur - seg * (n - 1),
                    WORK / f"h{i}_{bid}.mp4"))
            l2 = WORK / f"cc_{bid}.txt"
            l2.write_text("\n".join(f"file '{p.absolute().as_posix()}'"
                                    for p in parts))
            run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(l2),
                 "-c", "copy", "-y", str(piece)])
            return piece
        raise RuntimeError(f"{bid}: {tr} without clip asset")

    if tr == "still_pushin":
        if asset.get("kind") == "still":
            pan = KB_PANS[idx % len(KB_PANS)]
            zoom = (1.0, 1.05 + (idx % 4) * 0.04)
            if idx % 2:
                zoom = (zoom[1], zoom[0])
            render_remotion("KenBurns",
                            {"src": data_url(asset["path"]),
                             "zoomFrom": zoom[0], "zoomTo": zoom[1],
                             "panFrom": list(pan[0]), "panTo": list(pan[1])},
                            piece, dur, alpha=False)
            return piece
        if asset.get("kind") == "clip":          # fallback path
            return clip_piece(asset, dur, piece)
        raise RuntimeError(f"{bid}: still_pushin without asset")

    if tr == "split_compare":
        if asset.get("kind") == "split":
            ov = p.get("overlay", {})
            render_remotion("SplitCompare",
                            {"leftSrc": data_url(asset["left"]["path"]),
                             "rightSrc": data_url(asset["right"]["path"]),
                             "leftLabel": ov.get("left", ""),
                             "rightLabel": ov.get("right", "")},
                            piece, dur, alpha=False)
            return piece
        if asset.get("kind") == "still":
            render_remotion("KenBurns",
                            {"src": data_url(asset["path"])},
                            piece, dur, alpha=False)
            return piece
        raise RuntimeError(f"{bid}: split_compare without asset")

    if tr == "person_card":
        base = underlay(assets_all, beat, dur, WORK / f"u_{bid}.mp4")
        img = (data_url(asset["path"])
               if asset.get("kind") == "still" else "")
        ov = p.get("overlay", {})
        webm = render_remotion("PersonCard",
                               {"imageSrc": img,
                                "name": ov.get("name", p.get("subject", "")),
                                "role": ov.get("role", "")},
                               WORK / f"ov_{bid}.webm", dur, alpha=True)
        return composite(base, webm, piece)

    if tr == "infographic_list":
        base = underlay(assets_all, beat, dur, WORK / f"u_{bid}.mp4",
                        bg=asset.get("bg"))
        items = [{"text": it["text"], "atMs": ms}
                 for it, ms in zip(p["items"], a.get("items_ms", []))]
        webm = render_remotion("ListReveal",
                               {"title": p.get("title", ""), "items": items,
                                "side": face_side(base)},
                               WORK / f"ov_{bid}.webm", dur, alpha=True)
        return composite(base, webm, piece)

    if tr == "stat_callout":
        base = underlay(assets_all, beat, dur, WORK / f"u_{bid}.mp4",
                        bg=asset.get("bg"))
        webm = render_remotion("StatCard",
                               {"value": p["value"], "label": p["label"],
                                "side": face_side(base)},
                               WORK / f"ov_{bid}.webm", dur, alpha=True)
        return composite(base, webm, piece)

    raise RuntimeError(f"{bid}: unhandled treatment {tr}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="render a single beat id (debug)")
    args = ap.parse_args()

    plan = {p["beat_id"]: p for p in
            json.loads((MANIFEST / "plan.json").read_text())["plan"]}
    assets = json.loads((MANIFEST / "assets.json").read_text())
    beats = {b["beat_id"]: b for b in
             json.loads((MANIFEST / "beats.json").read_text())["beats"]}
    cfg = json.loads((ROOT / "config.json").read_text()) \
        if (ROOT / "config.json").exists() else {}
    voiceover = ROOT / f"voiceover_{cfg.get('slug', 'ryan_reynolds')}.mp3"

    WORK.mkdir(parents=True, exist_ok=True)
    order = sorted(plan.keys())
    if args.only:
        order = [args.only]

    # overlay stats piggyback on stills: add after main piece (overlay_stat)
    pieces = []
    for idx, bid in enumerate(order):
        p, a, b = plan[bid], assets[bid], beats[bid]
        piece = build_piece(p, a, b, idx, assets)
        if p.get("overlay_stat") and a["treatment"] in (
                "still_pushin", "motion_broll", "exercise_demo"):
            dur = round(b["end"] - b["start"], 3)
            webm = render_remotion(
                "StatCard", {"value": p["overlay_stat"]["value"],
                             "label": p["overlay_stat"]["label"],
                             "side": face_side(piece)},
                WORK / f"ovs_{bid}.webm", min(dur, 3.0), alpha=True)
            piece2 = WORK / f"piece_{idx:03d}_{bid}_s.mp4"
            if not piece2.exists():
                composite(piece, webm, piece2)
            piece = piece2
        pieces.append(piece)
        print(f"  [{idx + 1}/{len(order)}] {bid} "
              f"{a['treatment']}{' (fb)' if a['fallback_used'] else ''}",
              flush=True)
    if args.only:
        print(f"[OK] {pieces[0]}")
        return 0

    lst = WORK / "concat.txt"
    lst.write_text("\n".join(f"file '{p.absolute().as_posix()}'"
                             for p in pieces), encoding="utf-8")
    silent = WORK / "v2_silent.mp4"
    # re-encode at concat: pieces come from two encoders (x264 + Remotion)
    # whose stream params differ - stream-copy concat would glitch
    run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
         "-pix_fmt", "yuv420p", "-r", str(FPS), "-y", str(silent)],
        timeout=3600)

    final = OUT / cfg.get("output", "RYAN_REYNOLDS_FINAL.mp4").replace(
        ".mp4", "_V2.mp4")
    run(["ffmpeg", "-i", str(silent), "-i", str(voiceover),
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-y", str(final)], timeout=1800)
    print(f"[OK] {final}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
