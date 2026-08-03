#!/usr/bin/env python3
"""Footage treatment layer - ffmpeg effects callable from any assembler.

Every function takes source path(s) + a duration and writes one silent
1920x1080/30 H.264 piece, matching the convention in assemble.py so these
drop straight into an existing cut list.

Nothing here invents footage. Treatments change how a real, verified window
looks; they never manufacture a moment that was not filmed.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

W, H, FPS = 1920, 1080, 30

# x264 defaults to one thread per core. Run N of these concurrently and you
# get N x cores threads fighting over cores - at 14 workers on a 20-core box
# the machine was so oversubscribed that unrelated processes could not start
# a thread. Cap per-process threads so worker_count x THREADS ~= cores.
ENC_THREADS = os.environ.get("FX_ENC_THREADS", "2")
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
       "-pix_fmt", "yuv420p", "-threads", ENC_THREADS]


def run(args, timeout=1800):
    args = [str(a) for a in args]
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(
            "ffmpeg failed:\n" + " ".join(args[:20]) + "\n"
            + (r.stderr or "")[-2500:]
        )
    return r


def probe_dur(path) -> float:
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)])
    return float(r.stdout.strip())


def probe_size(path):
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "json",
             str(path)])
    s = json.loads(r.stdout)["streams"][0]
    return int(s["width"]), int(s["height"])


FIT = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"


# --------------------------------------------------------------- archive
def archive_treatment(src, t0, dur, dest, era="teen", strength=1.0):
    """Make old footage read as old, on purpose.

    This is not nostalgia decoration - it is the only thing that visually
    separates 2012 archive from 2024 gym footage in the same cut. Without
    it a viewer reasonably assumes every shot is contemporaneous.

    era: 'teen'  - 2012-2015 uploads: soft, warm, heavier grain, gate weave
         'early' - late 2010s: mild
         'sd'    - low-res source: adds scanline bloom to hide upscaling
    """
    s = float(strength)
    if era == "teen":
        grade = (f"eq=saturation={1 - 0.22 * s:.3f}:contrast={1 + 0.06 * s:.3f}"
                 f":brightness={0.012 * s:.4f},"
                 f"colorbalance=rs={0.06 * s:.3f}:gs={0.01 * s:.3f}"
                 f":bs={-0.05 * s:.3f}")
        grain = f"noise=alls={int(9 * s)}:allf=t+u"
        weave = (f"crop={W - 12}:{H - 12}:"
                 f"6+3*sin(t*2.1):6+3*cos(t*1.7),scale={W}:{H}")
        soft = f"gblur=sigma={0.6 * s:.2f}"
    elif era == "sd":
        grade = (f"eq=saturation={1 - 0.15 * s:.3f}:contrast={1 + 0.10 * s:.3f}")
        grain = f"noise=alls={int(12 * s)}:allf=t+u"
        weave = (f"crop={W - 8}:{H - 8}:4+2*sin(t*2.6):4+2*cos(t*2.2),"
                 f"scale={W}:{H}")
        soft = f"gblur=sigma={1.0 * s:.2f},unsharp=5:5:{0.8 * s:.2f}"
    else:  # early
        grade = f"eq=saturation={1 - 0.10 * s:.3f}:contrast={1 + 0.04 * s:.3f}"
        grain = f"noise=alls={int(5 * s)}:allf=t+u"
        weave = ""
        soft = ""

    vign = (f"vignette=angle=PI/{5.2 - 0.8 * s:.2f}")
    parts = [FIT, f"fps={FPS}", grade, soft, weave, vign, grain]
    vf = ",".join(p for p in parts if p)
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", f"{t0:.3f}", "-i", str(src), "-t", f"{dur:.4f}",
         "-an", "-vf", vf, *ENC, str(dest)])
    return dest


# ------------------------------------------------------------ speed ramp
def speed_ramp(src, t0, src_dur, dest, ramp="in", slowest=0.45, steps=12):
    """Retime a source window with a genuine easing ramp.

    A single setpts factor is a speed CHANGE, not a ramp. To actually ramp,
    the window is sliced into `steps` short pieces, each retimed by its own
    factor along an eased curve, then concatenated. Output duration is the
    sum of the retimed slices - the caller should measure it, not assume it.

    ramp: 'in'   full speed -> slowest   (decelerate into a moment)
          'out'  slowest -> full speed   (accelerate out of it)
          'both' fast -> slow -> fast    (slow-mo pocket in the middle)

    No frame interpolation is wired, so `slowest` below ~0.4 will judder.
    Keep ramps under ~1.5s; this is punctuation, not a slow-motion sequence.
    """
    slowest = max(0.35, min(1.0, float(slowest)))
    steps = max(2, int(steps))
    src_dur = float(src_dur)
    slice_dur = src_dur / steps
    work = Path(dest).parent / f"_ramp_{Path(dest).stem}"
    work.mkdir(parents=True, exist_ok=True)

    def speed_at(i):
        u = (i + 0.5) / steps                      # 0..1 across the window
        if ramp == "in":
            e = 1 - pow(1 - u, 3)                  # ease-out
        elif ramp == "out":
            e = 1 - pow(u, 3)                      # ease-in, reversed
        else:
            e = 1 - pow(abs(u * 2 - 1), 3)         # slow in the middle
        return 1.0 + (slowest - 1.0) * e           # 1.0 -> slowest

    pieces = []
    for i in range(steps):
        p = work / f"{i:03d}.mp4"
        sp = speed_at(i)
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-ss", f"{t0 + i * slice_dur:.4f}", "-i", str(src),
             "-t", f"{slice_dur:.4f}", "-an",
             "-vf", f"{FIT},fps={FPS},setpts={1 / sp:.5f}*PTS",
             *ENC, str(p)])
        pieces.append(p)

    lst = work / "concat.txt"
    lst.write_text("\n".join(f"file '{p.absolute().as_posix()}'"
                             for p in pieces), encoding="utf-8")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "concat", "-safe", "0", "-i", str(lst), "-an",
         "-vf", f"fps={FPS}", *ENC, str(dest)])
    for p in pieces + [lst]:
        p.unlink(missing_ok=True)
    work.rmdir()
    return dest


# ------------------------------------------------------------ freeze punch
def freeze_punch(src, t_freeze, dur, dest, punch=1.24, hold=0.30,
                 desat=0.62, vignette=True):
    """Freeze one frame and push into it. The documentary 'stop here' beat.

    hold = seconds held at 1.0x before the push begins.
    """
    still = Path(dest).with_suffix(".still.png")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", f"{t_freeze:.3f}", "-i", str(src), "-frames:v", "1",
         "-vf", FIT, str(still)])
    n = max(2, int(round(float(dur) * FPS)))
    h = max(0, int(round(float(hold) * FPS)))
    move = max(1, n - h)
    # zoompan eases with a cubic on its own normalized progress.
    p = f"max(0,(on-{h})/{move})"
    zexpr = f"1+{punch - 1:.4f}*(1-pow(1-min(1,{p}),3))"
    vf = (f"zoompan=z='{zexpr}':d={n}:x='iw/2-(iw/zoom/2)':"
          f"y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
          f"eq=saturation={desat:.3f}")
    if vignette:
        vf += ",vignette=angle=PI/4.6"
    vf += ",noise=alls=4:allf=t"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-loop", "1", "-i", str(still), "-t", f"{dur:.4f}",
         "-an", "-vf", vf, *ENC, str(dest)])
    still.unlink(missing_ok=True)
    return dest


# --------------------------------------------------------------- flash cut
def flash_hit(src, t0, dur, dest, at=0.0, frames=2, color="white",
              strength=0.75):
    """Act-turn punctuation done properly: a 2-3 frame bloom blended OVER
    the incoming shot, so the picture never disappears.

    Replaces flash_cut(), which inserted a standalone full-frame colour card
    and read as a rendering error rather than an edit. `at` is the offset in
    seconds within the piece where the hit lands.
    """
    n = max(1, int(frames))
    t_in = float(at)
    t_out = t_in + n / FPS
    vf = (f"{FIT},fps={FPS},"
          f"drawbox=x=0:y=0:w={W}:h={H}:color={color}@{strength:.3f}:t=fill:"
          f"enable='between(t,{t_in:.4f},{t_out:.4f})'")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", f"{t0:.3f}", "-i", str(src), "-t", f"{dur:.4f}",
         "-an", "-vf", vf, *ENC, str(dest)])
    return dest


def flash_cut(dest, dur=0.14, color="white", fade=True):
    """DEPRECATED - rejected in review: a standalone full-frame colour card
    reads as a glitch, not an edit. Use flash_hit(), which blooms over the
    incoming picture instead of replacing it. Kept only so existing cut
    lists do not break."""
    n = max(2, int(round(float(dur) * FPS)))
    vf = f"fps={FPS}"
    if fade:
        vf += f",fade=t=out:st={(n - 1) / FPS * 0.35:.4f}:d={(n / FPS) * 0.65:.4f}"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", f"color=c={color}:s={W}x{H}:r={FPS}",
         "-t", f"{dur:.4f}", "-an", "-vf", vf, *ENC, str(dest)])
    return dest


# ------------------------------------------------------------- whip pan
def whip_pan(a_src, b_src, dest, dur=0.30, direction="left", blur=42):
    """Directional-blur whip between two pieces. Takes the TAIL of a and the
    HEAD of b, so it is a transition, not extra runtime - the caller must
    trim `dur/2` off each neighbour."""
    n = max(2, int(round(float(dur) * FPS)))
    half = max(1, n // 2)
    tail = n - half
    da = probe_dur(a_src)
    sign = 1 if direction == "left" else -1

    # boxblur/gblur evaluate their radius ONCE at filter-config time - there
    # is no per-frame `n` or `t` available to them. So the ramp is rendered
    # frame by frame with a constant blur per frame. A whip is ~9 frames, so
    # this is a handful of tiny calls and it is exactly deterministic.
    work = Path(dest).parent / f"_whip_{Path(dest).stem}"
    work.mkdir(parents=True, exist_ok=True)
    room = int(W * 1.35)
    idx = 0

    def frame(src, at, blur_px, slide):
        """Write exactly one PNG. A gap in the numbering makes ffmpeg's
        image2 demuxer stop at that index and silently truncate the whole
        transition, so a missing frame is a hard error, never a skip."""
        nonlocal idx
        out = work / f"{idx:04d}.png"
        off = f"(iw-{W})/2+{sign * slide:.5f}*(iw-{W})/2"
        vf = f"{FIT},scale={room}:-2,crop={W}:{H}:'{off}':0"
        if blur_px >= 1:
            vf += f",boxblur={int(blur_px)}:1:{int(blur_px)}:1"
        base = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
        at = max(0.0, at)
        # Input seek is fast but lands past the final frame near EOF and
        # then exits 0 having written nothing. Fall back to output seek,
        # then to a nudged-earlier timestamp.
        for attempt in (
            base + ["-ss", f"{at:.4f}", "-i", str(src)],
            base + ["-i", str(src), "-ss", f"{at:.4f}"],
            base + ["-i", str(src), "-ss", f"{max(0.0, at - 2.0 / FPS):.4f}"],
        ):
            run(attempt + ["-frames:v", "1", "-vf", vf, str(out)])
            if out.exists() and out.stat().st_size > 0:
                idx += 1
                return
        raise RuntimeError(
            f"whip_pan: no frame decodable from {src} at {at:.3f}s")

    for i in range(half):                       # a's tail: blur/slide ramp up
        u = (i + 1) / half
        frame(a_src, da - (half - i) / FPS, blur * (u ** 1.5), u ** 2)
    for j in range(tail):                       # b's head: ramp back down
        u = 1 - (j + 1) / tail
        frame(b_src, j / FPS, blur * (u ** 1.5), -(u ** 2))

    written = sorted(work.glob("*.png"))
    if len(written) != n:
        raise RuntimeError(
            f"whip_pan: wrote {len(written)} frames, expected {n}")

    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-framerate", str(FPS), "-start_number", "0",
         "-i", str(work / "%04d.png"),
         "-an", "-vf", f"fps={FPS}", *ENC, str(dest)])

    got = round(probe_dur(dest) * FPS)
    if got != n:
        raise RuntimeError(
            f"whip_pan: encoded {got} frames, expected {n} - refusing to "
            f"return a truncated transition")
    for p in written:
        p.unlink()
    work.rmdir()
    return dest


# ---------------------------------------------------------- film dissolve
def film_dissolve(a_src, b_src, dest, dur=0.5, mode="dissolve"):
    """xfade between two pieces. mode: dissolve | fadeblack | fadewhite |
    wipeleft | smoothleft | pixelize. Total output = a + b - dur."""
    da, db = probe_dur(a_src), probe_dur(b_src)
    off = max(0.0, da - float(dur))
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(a_src), "-i", str(b_src), "-filter_complex",
         f"[0:v][1:v]xfade=transition={mode}:duration={dur:.3f}"
         f":offset={off:.3f},fps={FPS}",
         "-an", *ENC, str(dest)])
    _ = db
    return dest


# ------------------------------------------------------------ punch in/out
def punch_in(src, t0, dur, dest, zoom_from=1.0, zoom_to=1.16,
             focus=(0.5, 0.5), ease="cubic"):
    """Eased push on MOVING footage (zoompan works on stills; this uses a
    scale+crop expression so live video keeps moving under the push)."""
    n = max(2, int(round(float(dur) * FPS)))
    fx, fy = focus
    if ease == "cubic":
        p = f"(1-pow(1-min(1,t*{FPS}/{n}),3))"
    elif ease == "expo":
        p = f"(1-pow(2,-10*min(1,t*{FPS}/{n})))"
    else:
        p = f"min(1,t*{FPS}/{n})"
    z = f"({zoom_from:.4f}+{zoom_to - zoom_from:.4f}*{p})"
    # scale up by z then crop a WxH window centred on the focus point
    vf = (f"{FIT},fps={FPS},"
          f"scale=w='iw*{z}':h='ih*{z}':eval=frame,"
          f"crop={W}:{H}:'(iw-{W})*{fx:.3f}':'(ih-{H})*{fy:.3f}'")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", f"{t0:.3f}", "-i", str(src), "-t", f"{dur:.4f}",
         "-an", "-vf", vf, *ENC, str(dest)])
    return dest


# ------------------------------------------------------- letterbox squeeze
def letterbox_squeeze(src, t0, dur, dest, bars=0.14, hold=0.0):
    """Cinemascope bars slide in - marks a 'this is the moment' beat without
    any graphic. bars = fraction of height per bar at full extension."""
    n = max(2, int(round(float(dur) * FPS)))
    h = int(round(float(hold) * FPS))
    bh = int(H * float(bars))
    p = f"(1-pow(1-min(1,max(0,(t*{FPS}-{h}))/{max(1, n - h)}),3))"
    vf = (f"{FIT},fps={FPS},"
          f"drawbox=x=0:y=0:w={W}:h='{bh}*{p}':color=black@1:t=fill,"
          f"drawbox=x=0:y='{H}-{bh}*{p}':w={W}:h='{bh}*{p}'"
          f":color=black@1:t=fill")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", f"{t0:.3f}", "-i", str(src), "-t", f"{dur:.4f}",
         "-an", "-vf", vf, *ENC, str(dest)])
    return dest


# ------------------------------------------------------------- source label
def source_label(piece, dest, source, detail, accent="#E3120B"):
    """Bottom-left attribution slate. No channel logo (operator decision:
    credits yes, watermark no)."""
    def esc(v):
        return (v.replace("\\", r"\\").replace(":", r"\:")
                 .replace("'", "").replace("%", r"\%"))
    font = "graphics/public/fonts/Anton-Regular.ttf"
    vf = (f"drawbox=x=34:y=ih-128:w=620:h=84:color=black@0.72:t=fill,"
          f"drawbox=x=34:y=ih-128:w=7:h=84:color={accent}:t=fill,"
          f"drawtext=fontfile='{font}':text='SOURCE\\: {esc(source)}'"
          f":fontcolor=white:fontsize=30:x=58:y=h-116,"
          f"drawtext=fontfile='{font}':text='{esc(detail)}'"
          f":fontcolor=#CFCFCF:fontsize=21:x=58:y=h-76")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(piece), "-an", "-vf", vf, *ENC, str(dest)])
    return dest
