#!/usr/bin/env python3
"""Render one reel demonstrating every effect against real MrBeast assets.

The point is that effects get judged by watching them, not by reading a list.
Each segment is labelled on screen, and deliberate before/after pairs are
included so the difference is visible rather than asserted.

    py -3.12 pipeline/fx_demo.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GRAPHICS = ROOT / "graphics"
WORK = ROOT / "work" / "fx_demo"
STILLS = ROOT / "work" / "fx_stills"
OUT = ROOT / "final_video" / "FX_DEMO_REEL.mp4"

COLIN = ROOT / "dossier/mrbeast/sources/9IQ_ldV9z_A.mp4"
AIRRACK = ROOT / "dossier/mrbeast/sources/7r3ORKgNUjw.mp4"
ARCHIVE = ROOT / "dossier/mrbeast/archive/AKJfakEsgy0.mp4"

FPS = fx.FPS
ACCENT = "#E3120B"
SEG = 3.0
FONT = "graphics/public/fonts/Anton-Regular.ttf"


def render_remotion(comp, props, dest, dur_s, alpha=False):
    props = dict(props)
    props["durationInFrames"] = max(2, round(dur_s * FPS))
    props["fps"] = FPS
    props.setdefault("accent", ACCENT)
    pf = WORK / f"props_{dest.stem}.json"
    pf.write_text(json.dumps(props), encoding="utf-8")
    cmd = ["npx.cmd", "remotion", "render", "src/index.ts", comp, str(dest),
           f"--props={pf}", "--log=error"]
    if alpha:
        cmd += ["--codec=vp8", "--image-format=png",
                "--pixel-format=yuva420p"]
    else:
        cmd += ["--codec=h264", "--image-format=jpeg",
                "--pixel-format=yuv420p"]
    r = subprocess.run(cmd, cwd=GRAPHICS, capture_output=True, text=True,
                       timeout=1800)
    if r.returncode or not dest.exists():
        raise RuntimeError(f"remotion {comp} failed:\n"
                           + (r.stderr or r.stdout or "")[-2500:])
    return dest


def label(piece, dest, idx, text, note=""):
    """Burn the effect name on the piece so the reel is self-describing."""
    def esc(v):
        return (v.replace("\\", r"\\").replace(":", r"\:")
                 .replace("'", "").replace("%", r"\%"))
    vf = (f"drawbox=x=0:y=0:w=iw:h=104:color=black@0.68:t=fill,"
          f"drawbox=x=0:y=0:w=10:h=104:color={ACCENT}:t=fill,"
          f"drawtext=fontfile='{FONT}':text='{idx:02d}  {esc(text)}'"
          f":fontcolor=white:fontsize=42:x=36:y=20")
    if note:
        vf += (f",drawtext=fontfile='{FONT}':text='{esc(note)}'"
               f":fontcolor=#B9B9B9:fontsize=24:x=36:y=68")
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(piece), "-an", "-vf", vf, *fx.ENC, str(dest)])
    return dest


def plain_cut(src, t0, dur, dest):
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{t0:.3f}", "-i", str(src), "-t", f"{dur:.4f}",
            "-an", "-vf", f"{fx.FIT},fps={FPS}", *fx.ENC, str(dest)])
    return dest


def parallax_props(name):
    p = GRAPHICS / "public" / "fx"
    layers = sorted(p.glob(f"{name}_L*.png"))
    if not layers:
        raise FileNotFoundError(f"no parallax layers for '{name}' - run "
                                f"pipeline/parallax.py first")
    n = len(layers)
    return [{"src": f"fx/{q.name}", "depth": round(i / max(1, n - 1), 4)}
            for i, q in enumerate(layers)]


def stage_stills():
    """Copy the untouched source stills into graphics/public/fx.

    Comps that want a photograph must get the photograph - the *_L0.png
    plates are inpainted backgrounds with the subject removed, and using one
    as a still would put a smear on screen.
    """
    dst = GRAPHICS / "public" / "fx"
    dst.mkdir(parents=True, exist_ok=True)
    names = {"colin": "colin_interview", "teen": "teen_archive",
             "gym": "airrack_gym"}
    for short, fname in names.items():
        src = STILLS / f"{fname}.png"
        if src.exists():
            (dst / f"{short}_SRC.png").write_bytes(src.read_bytes())


def build():
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    stage_stills()
    raw, pieces = [], []

    def add(text, note, fn):
        i = len(raw) + 1
        p = WORK / f"{i:02d}_raw.mp4"
        try:
            fn(p)
        except Exception as e:  # noqa: BLE001
            print(f"  [{i:02d}] SKIP {text}: "
                  f"{type(e).__name__}: {str(e).splitlines()[-1][:160]}")
            return
        lab = WORK / f"{i:02d}_lab.mp4"
        label(p, lab, i, text, note)
        raw.append(p)
        pieces.append(lab)
        print(f"  [{i:02d}] ok   {text}")

    print("Building effect demo reel...")

    # ---- before/after: the Ken Burns fix -------------------------------
    add("KEN BURNS - OLD (LINEAR)", "existing comp: no easing, stops dead",
        lambda p: render_remotion(
            "KenBurns", {"src": "fx/colin_SRC.png", "zoomFrom": 1.04,
                         "zoomTo": 1.18}, p, SEG))
    add("KEN BURNS - NEW (EASED + SETTLE)",
        "eases out, rotation drift, handheld, grain",
        lambda p: render_remotion(
            "KenBurns2", {"src": "fx/colin_SRC.png", "zoomFrom": 1.04,
                          "zoomTo": 1.18, "panFrom": [0.42, 0.46],
                          "panTo": [0.57, 0.53], "rotTo": 0.5,
                          "drift": 2.5, "grain": 0.05, "vignette": 0.4},
            p, SEG))

    # ---- parallax ------------------------------------------------------
    add("PARALLAX - DEPTH LAYERS (INTERVIEW)",
        "3 depth-separated planes, one virtual camera",
        lambda p: render_remotion(
            "ParallaxPhoto", {"layers": parallax_props("colin"),
                              "zoomFrom": 1.02, "zoomTo": 1.12,
                              "panFrom": [0.40, 0.5], "panTo": [0.60, 0.5],
                              "strength": 1.15, "grain": 0.04,
                              "vignette": 0.35}, p, SEG))
    add("PARALLAX - DEPTH LAYERS (2013 ARCHIVE)",
        "same rig on the teen webcam footage",
        lambda p: render_remotion(
            "ParallaxPhoto", {"layers": parallax_props("teen"),
                              "zoomFrom": 1.02, "zoomTo": 1.14,
                              "panFrom": [0.58, 0.5], "panTo": [0.42, 0.52],
                              "strength": 1.25, "grain": 0.07,
                              "vignette": 0.45}, p, SEG))
    add("PARALLAX STAGE - CARD DEPTH",
        "bg, accent rings and type on separate planes",
        lambda p: render_remotion(
            "ParallaxStage", {"title": "DAY 310", "bgSrc": "fx/gym_SRC.png",
                              "sub": "FOLLOWING THE PACT / PROGRAMMED REST",
                              "amount": 1.4}, p, SEG))

    # ---- documentary beats --------------------------------------------
    add("FREEZE FRAME + PUNCH IN", "locks, pushes, desaturates, type snaps on",
        lambda p: render_remotion(
            "FreezePunch", {"src": "fx/colin_SRC.png", "title": "THE CONTRACT",
                            "sub": "JUNE 2023", "punch": 1.26}, p, SEG))
    add("SPLIT SQUEEZE - DATED COMPARE", "both sides keep their own date",
        lambda p: render_remotion(
            "SplitSqueeze", {"leftSrc": "fx/teen_SRC.png",
                             "rightSrc": "fx/gym_SRC.png",
                             "leftLabel": "2013", "rightLabel": "2024"},
            p, SEG))

    # ---- kinetic captions over real footage ----------------------------
    def captions(p):
        base = WORK / "cap_base.mp4"
        plain_cut(COLIN, 731.0, SEG, base)
        ov = WORK / "cap_ov.webm"
        words = [{"text": w, "atMs": 260 * i} for i, w in enumerate(
            ["TODAY", "WAS", "DAY", "310", "ME", "AND", "ERIC",
             "SIGNED", "A", "CONTRACT"])]
        render_remotion("KineticCaptions", {"words": words, "perLine": 4,
                                            "fontSize": 72}, ov, SEG,
                        alpha=True)
        fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(base), "-c:v", "libvpx", "-i", str(ov),
                "-filter_complex", "[0:v][1:v]overlay=0:0:eof_action=pass",
                "-an", *fx.ENC, str(p)])
    add("KINETIC CAPTIONS", "word-synced, burned in, accent on active word",
        captions)

    # ---- ffmpeg treatment layer ---------------------------------------
    add("ARCHIVE - UNTREATED (COMPARE)", "raw 2015 upload, reads as modern",
        lambda p: plain_cut(ARCHIVE, 49.0, SEG, p))
    add("ARCHIVE TREATMENT - TEEN ERA",
        "grade, gate weave, grain, vignette - dates the footage",
        lambda p: fx.archive_treatment(ARCHIVE, 49.0, SEG, p, era="teen"))
    add("PUNCH IN - EASED, MOVING FOOTAGE", "cubic ease on live video",
        lambda p: fx.punch_in(AIRRACK, 430.0, SEG, p, zoom_to=1.22))
    add("SPEED RAMP - DECELERATE IN", "12 eased slices, no frame interp",
        lambda p: fx.speed_ramp(AIRRACK, 430.0, 2.0, p, ramp="in"))
    add("LETTERBOX SQUEEZE", "scope bars ease in on the beat",
        lambda p: fx.letterbox_squeeze(COLIN, 731.0, SEG, p))
    add("FREEZE PUNCH (FFMPEG)", "same beat, source-side",
        lambda p: fx.freeze_punch(AIRRACK, 1083.0, SEG, p))
    add("SOURCE CREDIT - NO LOGO", "attribution bottom-left, zero watermark",
        lambda p: fx.source_label(
            plain_cut(COLIN, 731.0, SEG, WORK / "cred_base.mp4"), p,
            "COLIN AND SAMIR", "YOUTUBE / JUNE 2023"))

    # ---- transitions (need two finished pieces) ------------------------
    if len(raw) >= 2:
        add("WHIP PAN TRANSITION", "per-frame blur ramp + slide",
            lambda p: fx.whip_pan(raw[-1], raw[0], p, dur=0.5))
        add("FILM DISSOLVE", "xfade, timed",
            lambda p: fx.film_dissolve(raw[2], raw[3], p, dur=0.8))
    # flash_cut() was rejected in review - a standalone white card read as a
    # glitch. flash_hit() blooms over the incoming picture instead.
    add("FLASH HIT - 2 FRAMES OVER PICTURE",
        "act-turn punctuation; picture never disappears",
        lambda p: fx.flash_hit(AIRRACK, 430.0, SEG, p, at=0.55, frames=2))

    if not pieces:
        raise RuntimeError("no demo segments rendered")

    lst = WORK / "concat.txt"
    lst.write_text("\n".join(f"file '{p.absolute().as_posix()}'"
                             for p in pieces), encoding="utf-8")
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(lst),
            "-an", "-vf", f"fps={FPS}", *fx.ENC,
            "-movflags", "+faststart", str(OUT)], timeout=3600)

    print(f"\n[OK] {OUT}")
    print(f"[OK] {len(pieces)} segments, {fx.probe_dur(OUT):.1f}s")
    return OUT


if __name__ == "__main__":
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    raise SystemExit(0 if build() else 1)

