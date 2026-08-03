#!/usr/bin/env python3
"""Build the picture layer against the locked audio, with the rules in code.

Every one of the thirteen rules in HANDOFF.md came out of a rejected cut, so
none of them are left to the person writing the plan:

 1  ONLY JIMMY          only pool entries marked verified_jimmy by eye AND
                        cleared by the burned-in-text screen are drawable
 2  NEVER REUSE         a Registry that raises on a second draw of any window,
                        clip, still or card
 3  NO LOOPING          -stream_loop appears nowhere; a stock clip shorter
                        than its shot fails the build instead
 4  NOTHING OVER ~6s    asserted per shot, in frames
 5  NO CROSSING A CUT   every footage window is re-scanned at FULL resolution
                        over its exact span, and shifted inside its run or
                        dropped if a cut is found
 6  PERCEPTUAL DEDUPE   dHash at allocation time (cheap, so alternatives can
                        be tried) and again over the rendered pieces
 7  EYES-ON IDENTITY     enforced upstream; this file cannot draw an unjudged
                        window even by accident
 8  PICTURE FITS SPEECH  the plan is written per EDL segment against the
                        sentence, and the timings come from the EDL
 9  NO STAND-IN PEOPLE   stock is restricted to the OBJECT-class allow-list
10  NO STOCK CREDIT      only interview and archive sources get a lower-third
11  NO LOGO              nothing draws one
12  NO NARRATION ECHO    pipeline/echo_check.py, run separately
13  CLINICAL SHORT       clinical stills are capped and faded

Frame-exact by construction. Rounding across 130 shots previously accumulated
~3.8s of drift, and the first fix padded with a frozen frame - an 18-second
stall. Here every shot is allocated an integer FRAME COUNT, the counts sum to
exactly the audio's frame count, and each rendered piece is copy-trimmed to
its count. Nothing is ever padded with a still.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import fx                                                        # noqa: E402
from picture_plan_v8 import (CLIN, CLIPS, DOCS, FLASH, PARALLAX,  # noqa: E402
                             PLAN, STILLS)

W, H, FPS = fx.W, fx.H, fx.FPS
AUDIO = ROOT / "final_video/mrbeast_audio_v6/MRBEAST_V6_STORY_MASTER.wav"
SUFFIX = os.environ.get("BUILD_SUFFIX", "V8")
OUT = ROOT / f"final_video/THE_DISEASE_THAT_BUILT_MRBEAST_{SUFFIX}.mp4"
WORK = ROOT / f"work/picture_{SUFFIX.lower()}"
EDL = ROOT / "manifest/edl_full.json"
POOL = ROOT / "manifest/jimmy_pool2.json"
BITES = ROOT / "manifest/bite_windows.json"
ALLOW = ROOT / "manifest/broll_allow.json"
CARDS = ROOT / "work/cards"
SHOTLIST = ROOT / f"manifest/picture_{SUFFIX.lower()}_shots.json"

SRC_DIRS = [ROOT / "dossier/mrbeast/sources", ROOT / "dossier/mrbeast/archive"]
TEEN_SOURCES = {"AKJfakEsgy0", "F0OkwXKcPSE"}

MAX_SHOT = 6.0
MIN_SHOT = 1.15
# Spare source beyond the shot. The renderer asks ffmpeg for dur + 0.12 and
# then copy-trims to the exact frame count, so 0.18 leaves ~2 frames of slack.
# At 0.25 this disagreed with bite_windows.py, which computes a window's usable
# length with a 0.2 margin: a 6.00s window then failed a 6.00s request by five
# hundredths of a second and took the film's Beast Games bite out of sync.
HEADROOM = 0.18
# The fine cut gate uses ffmpeg's `scdet`, not `select=gt(scene,X)`.
#
# Calibrated, not guessed. `scene > 0.30` missed a genuine camera cut inside an
# interview take - the angle change scored ~0.09 - and 14 frames of a different
# setup shipped at 246.47s. Dropping the scene threshold to 0.12 then started
# firing on the 2015 webcam's sensor noise and starved the archive pool.
# Measured with scdet on both cases: the real cut scores 8.9 and 61.9, while
# the noisiest archive window peaks at 4.9. A threshold of 6 separates them.
SCDET = 6.0
# Calibrated on the 95 verified pool thumbnails by work/_hash_calib.py, over
# 877 same-interview pairs and 600 cross-interview pairs.
#
# A 9x8 hash (64 bits) has NO usable separation: the closest genuinely
# distinct same-set pair is 9 bits apart while cross-set pairs go as low as 7,
# so "same picture" and "different room" overlap. That is what rejected the
# baseball bite's only sync window.
#
# At 17x16 (256 bits) the populations separate: distinct same-set pairs start
# at 17 (p1 26, p5 38), cross-set pairs start at 59. Both thresholds now sit
# inside that gap.
HASH_W, HASH_H = 17, 16
# NOTE the allocator and the QC pass measure on DIFFERENT bases and so carry
# different numbers. The allocator hashes the pool THUMBNAIL; QC hashes the
# RENDERED piece, which has been punched in and had an identical credit bar
# drawn on it, so rendered pairs measure roughly 0.4-0.9x the thumbnail
# distance. Pairs that QC flagged at 13-32 measured >=34 as thumbnails, so the
# allocator's bar has to sit higher to catch the same repeats.
DUPE_HARD = 14           # below the observed same-set minimum of 17
# 48 was a guess aimed at "reject whatever QC would flag". Measured on
# thumbnails, same-set pairs sit at p1 26 / p5 38, so 48 rejects roughly the
# closest quarter of legitimate pairs - and once the film draws 83 of 85
# windows that starves the allocator (26 windows unspent, 27 rejected as
# look-alikes). 40 rejects about the closest 6%, and QC now reports rendered
# proximity as a warning for the eye rather than a failure, so the judgement
# lands where it belongs.
DUPE_NEAR = 40
DUPE_WINDOW = 150.0      # seconds of programme within which "close" applies
# No two ADJACENT shots from one source. Allowing two in a row put two
# near-identical red-curtain Rogan singles at 12s and 14s of the preview,
# which is exactly the defect the operator described as "five shots from the
# same set in one minute". Sync draws are exempt: a bite must come from its
# own source, and two consecutive windows of one interview under one
# continuous quote is normal grammar, not a repeat.
NO_REPEAT_SOURCE_RUN = 1

ONLY = os.environ.get("V8_ONLY")   # e.g. "0-120" to build just the opening


class Reuse(RuntimeError):
    pass


class Exhausted(RuntimeError):
    pass


# --------------------------------------------------------------- registry
class Registry:
    def __init__(self) -> None:
        self.spent: dict[str, str] = {}

    def take(self, key: str, where: str) -> None:
        if key in self.spent:
            raise Reuse(f"{key} already used at {self.spent[key]}, "
                        f"asked again for {where}")
        self.spent[key] = where


REG = Registry()


# ------------------------------------------------------------------ sources
def src_path(sid: str) -> Path:
    for d in SRC_DIRS:
        p = d / f"{sid}.mp4"
        if p.exists():
            return p
    raise FileNotFoundError(sid)


_cuts_cache: dict[tuple, list[float]] = {}


def cuts_in(src: Path, t0: float, dur: float) -> list[float]:
    """Camera cuts inside an exact span, at FULL resolution.

    The pool's cut scan is downscaled for speed and only proposes windows.
    This is the gate: a shot that would cross the podcast's own edit - and so
    start on Jimmy and end on the host - never gets rendered.
    """
    key = (str(src), round(t0, 2), round(dur, 2))
    if key in _cuts_cache:
        return _cuts_cache[key]
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{max(0, t0):.3f}",
         "-t", f"{dur:.3f}", "-i", str(src), "-an", "-vf",
         f"scdet=threshold={SCDET}", "-f", "null", "NUL"],
        capture_output=True, text=True, timeout=900)
    out = [t0 + float(m) for m in
           re.findall(r"lavfi\.scd\.time: ?([\d.]+)", r.stderr or "")]
    _cuts_cache[key] = out
    return out


def clean_span(src: Path, t0: float, dur: float, run_end: float
               ) -> float | None:
    """Return a start time whose `dur` seconds hold no cut, or None."""
    for shift in (0.0, 0.35, 0.7, 1.1, 1.6, 2.2, -0.3):
        s = t0 + shift
        if s < 0 or s + dur + HEADROOM > run_end:
            continue
        inner = [c for c in cuts_in(src, s, dur + 0.1)
                 if s + 0.12 < c < s + dur - 0.12]
        if not inner:
            return s
    return None


# --------------------------------------------------------------- perceptual
def dhash_file(p: Path) -> np.ndarray | None:
    if not p or not p.exists():
        return None
    g = np.asarray(
        Image.open(p).convert("L").resize((HASH_W, HASH_H), Image.LANCZOS),
        dtype=np.int16)
    return (g[:, 1:] > g[:, :-1]).flatten()


_placed: list[tuple[float, str, np.ndarray]] = []


def too_alike(prog_t: float, h: np.ndarray | None,
              strict: bool = True) -> str | None:
    """Reject a picture that repeats one already placed.

    `strict=False` drops the proximity rule and keeps only the hard rule -
    literally the same picture. It is used for SYNC shots and nothing else.

    A bite is Jimmy's own voice at a known timecode, and the honest picture
    over it is him saying it in that room. Two different windows of the same
    interview will always hash alike, so the proximity rule would reject the
    second one and force a cutaway that pretends to be sync. Repetition is a
    cutaway problem: cutaways still get the strict rule, and no source may run
    three shots deep whatever the hashes say.
    """
    if h is None:
        return None
    for ot, oname, oh in _placed:
        d = int(np.count_nonzero(h != oh))
        if d < DUPE_HARD:
            return f"same picture as {oname} (hamming {d})"
        if strict and d < DUPE_NEAR and abs(prog_t - ot) < DUPE_WINDOW:
            return (f"too like {oname} only {abs(prog_t-ot):.0f}s away "
                    f"(hamming {d})")
    return None


def remember(prog_t: float, name: str, h: np.ndarray | None) -> None:
    if h is not None:
        _placed.append((prog_t, name, h))


# ------------------------------------------------------------------- pools
POOL_JIMMY: list[dict] = []
POOL_TEEN: list[dict] = []
SYNC: dict[int, list[dict]] = {}
BROLL: dict[str, list[dict]] = {}


def load() -> None:
    global POOL_JIMMY, POOL_TEEN
    raw = json.loads(POOL.read_text(encoding="utf-8"))
    ok = [e for e in raw
          if e.get("verified_jimmy") is True and not e.get("has_text")]
    POOL_TEEN = [e for e in ok if e["source"] in TEEN_SOURCES]
    POOL_JIMMY = [e for e in ok if e["source"] not in TEEN_SOURCES]
    for e in POOL_TEEN + POOL_JIMMY:
        e["_thumb"] = ROOT / "work/jimmy_pool2" / e.get("thumb", "")

    for r in json.loads(BITES.read_text(encoding="utf-8")):
        good = [w for w in r["runs"]
                if w.get("verified_jimmy") and not w.get("has_text")]
        for w in good:
            w["source"] = r["source"]
            w["credit_main"], w["credit_sub"] = CREDIT.get(
                r["source"], ("SOURCE", ""))
            w["_thumb"] = (ROOT / "work/bite_windows" / w["thumb"]
                           if w.get("thumb") else None)
        SYNC[r["i"]] = good

    if ALLOW.exists():
        for grp, items in json.loads(ALLOW.read_text(encoding="utf-8")).items():
            BROLL[grp] = [dict(it) for it in items]
    else:
        raise FileNotFoundError(
            f"{ALLOW} missing - run the OBJECT-class b-roll audit first. "
            "Stock cannot be drawn without it: rule 9.")

    print(f"[pool] {len(POOL_JIMMY)} present-day Jimmy windows, "
          f"{len(POOL_TEEN)} archive windows", flush=True)
    print(f"[sync] {sum(1 for v in SYNC.values() if v)} bites with a usable "
          f"sync window, {sum(len(v) for v in SYNC.values())} windows",
          flush=True)
    print(f"[broll] {sum(len(v) for v in BROLL.values())} OBJECT clips in "
          f"{len(BROLL)} groups", flush=True)


CREDIT = {
    "cLRLEnPaJLM": ("POWERFULJRE", "JOE ROGAN EXPERIENCE #1788"),
    "FjrJ2DJN_pA": ("THE DIARY OF A CEO", "YOUTUBE"),
    "9IQ_ldV9z_A": ("COLIN AND SAMIR", "YOUTUBE / JUNE 2023"),
    "c8VcUnz3nVc": ("COLIN AND SAMIR", "THE FULL STORY OF MRBEAST"),
    "NdjcGrpNSF4": ("JON YOUSHAEI", "INSIDE MRBEAST'S YOUTUBE MACHINE"),
    "AKJfakEsgy0": ("MRBEAST", "HI ME IN 5 YEARS / 4 OCTOBER 2015"),
    "F0OkwXKcPSE": ("MRBEAST", "HI ME IN 10 YEARS / 4 OCTOBER 2015"),
}


# ------------------------------------------------------------- allocation
# Source assigned to each shot INDEX, so adjacency can be judged in programme
# order even though sync binds in an earlier pass than everything else.
_assigned: dict[int, str] = {}


def _neighbours(idx: int) -> set[str]:
    """Sources of the programme-adjacent shots, where already decided."""
    return {_assigned.get(idx - 1), _assigned.get(idx + 1)} - {None}


def _diverse_key(e: dict) -> tuple:
    """Sort key that spreads shots across sources and keeps long runs spare."""
    src = e["source"]
    near = sum(1 for i, v in _assigned.items() if v == src)
    return (near, -(e.get("run_end", 0) - e["t0"]))


def take_jimmy(prog_t: float, dur: float, opts: dict, teen: bool,
               forbid: set[str] | None = None) -> dict:
    pool = POOL_TEEN if teen else POOL_JIMMY
    prefer, avoid = opts.get("prefer"), opts.get("avoid")
    forbid = forbid or set()

    cands = [e for e in pool if e["key"] not in REG.spent]
    if avoid:
        cands = [e for e in cands if e["source"] != avoid]
    ordered = sorted(cands, key=_diverse_key)
    if prefer:
        ordered = ([e for e in ordered if e["source"] == prefer]
                   + [e for e in ordered if e["source"] != prefer])

    tried = {"alike": 0, "cut": 0, "short": 0, "adjacent": 0}
    # Two passes. The first forbids using the source of the immediately
    # preceding shot; the second allows it, so a tight spot degrades to a
    # same-set cut rather than failing the whole build. The look-alike and
    # cut-inside-span checks are never relaxed.
    for relax in (False, True):
        for e in ordered:
            if not relax and e["source"] in forbid:
                tried["adjacent"] += 1
                continue
            room = e.get("run_end", 0) - e["t0"]
            if room < dur + HEADROOM:
                tried["short"] += 1
                continue
            h = dhash_file(e.get("_thumb"))
            if too_alike(prog_t, h):
                tried["alike"] += 1
                continue
            src = src_path(e["source"])
            s = clean_span(src, e["t0"], dur, e.get("run_end", 0))
            if s is None:
                tried["cut"] += 1
                continue
            if relax:
                print(f"[warn] {prog_t:7.2f}s had to reuse the previous "
                      f"shot's source ({e['source']}) - pool is tight here",
                      flush=True)
            return {**e, "start": s, "_hash": h}
    raise Exhausted(
        f"no {'archive' if teen else 'Jimmy'} window left for {prog_t:.2f}s "
        f"({dur:.2f}s needed, {len(ordered)} unspent; rejected: "
        f"{tried['alike']} look-alike, {tried['cut']} cut inside the span, "
        f"{tried['short']} too short)")


def take_sync(segi: int, prog_t: float, dur: float) -> dict | None:
    for w in SYNC.get(segi, []):
        if w["key"] in REG.spent:
            continue
        if w["usable"] + 0.15 < dur:
            continue
        h = dhash_file(w.get("_thumb"))
        if too_alike(prog_t, h, strict=False):
            continue
        src = src_path(w["source"])
        s = clean_span(src, w["t0"], dur, w["run_end"])
        if s is None:
            continue
        return {**w, "start": s, "_hash": h}
    return None


def usable_window(it: dict) -> tuple[float, float]:
    """The span of a stock clip the builder is allowed to use.

    Some clips are only clean for part of their length - the audit found one
    bed clip with legs and a bare foot in it for the first 9 seconds and an
    empty bed for the last 3.5. That was recorded as a free-text note, which
    the builder cannot read, and it duly picked a start 3 seconds in and put a
    stranger's legs in the film. Safe spans are now data, not prose.
    """
    w = it.get("window")
    if w and len(w) == 2:
        return float(w[0]), float(w[1])
    return 0.0, float(it["duration"])


def take_broll(group: str, dur: float, prog_t: float) -> dict:
    items = BROLL.get(group) or []
    for it in items:
        p = ROOT / it["file"]
        if it["file"] in REG.spent or not p.exists():
            continue
        lo, hi = usable_window(it)
        if (hi - lo) < dur + 0.3:
            continue          # rule 3: no looping. Too short means unusable.
        return it
    raise Exhausted(
        f"OBJECT-class group '{group}' exhausted at {prog_t:.2f}s "
        f"({dur:.2f}s needed, {len(items)} clips in the group). Fetch more "
        f"or change the plan - looping is banned.")


# ------------------------------------------------------------- renderers
def _credit(main: str, sub: str) -> str:
    """Lower-third for interview and archive sources only. Rule 10 keeps
    stock attribution in the description, not on screen."""
    # A straight apostrophe has to leave the ffmpeg filter string, but deleting
    # it rendered "INSIDE MRBEASTS YOUTUBE MACHINE". Swap in a typographic
    # apostrophe, which needs no escaping and is the correct glyph anyway.
    esc = lambda v: (v.replace("\\", r"\\").replace(":", r"\:")   # noqa: E731
                      .replace("'", "’").replace("%", r"\%"))
    f = "graphics/public/fonts/Anton-Regular.ttf"
    # Size the plate to the text. A fixed 680px box left ~180px of empty
    # translucent slab hanging past short credits like "CC BY", which over a
    # bright still reads as an unexplained grey block.
    w = int(max(300, 46 + 15.5 * len(main), 46 + 11.0 * len(sub)))
    return (f"drawbox=x=34:y=ih-126:w={w}:h=84:color=black@0.70:t=fill,"
            f"drawbox=x=34:y=ih-126:w=7:h=84:color=#E3120B:t=fill,"
            f"drawtext=fontfile='{f}':text='{esc(main)}'"
            f":fontcolor=white:fontsize=29:x=58:y=h-114,"
            f"drawtext=fontfile='{f}':text='{esc(sub)}'"
            f":fontcolor=#C8C8C8:fontsize=20:x=58:y=h-74")


def _push(dur: float, amount: float, fy: float = 0.5) -> str:
    n = max(2, int(round(dur * FPS)))
    p = f"(1-pow(1-min(1,on/{n}),3))"
    return (f"scale={W*2}:-2,zoompan=z='1.02+{amount:.3f}*{p}':d={n}:"
            f"x='iw/2-(iw/zoom/2)':y='ih*{fy}-(ih/zoom/2)':s={W}x{H}:fps={FPS}")


def _crop(box) -> str:
    l, t, r, b = box
    if not any(box):
        return ""
    return (f"crop=iw*{1-l-r:.4f}:ih*{1-t-b:.4f}:iw*{l:.4f}:ih*{t:.4f},")


def _fade(dur: float, d: float = 0.28) -> str:
    return f"fade=t=in:st=0:d={d},fade=t=out:st={max(0, dur-d):.3f}:d={d}"


# Framing variants. Every window of one interview is the same wardrobe, the
# same background and - if every shot gets the same punch - the same scale, so
# four medium singles inside a minute read flat even though they are four
# different windows. Each shot from a given source cycles through these, so a
# wide is followed by a tighter push and a differently-weighted frame.
FRAMINGS = [
    (1.02, 1.11, (0.50, 0.46)),   # wide, slow push
    (1.14, 1.22, (0.50, 0.42)),   # tighter, higher on the face
    (1.07, 1.18, (0.50, 0.52)),   # medium, weighted lower
]


def render_footage(e: dict, dur: float, dest: Path, archive: bool,
                   variant: int = 0) -> None:
    src = src_path(e["source"])
    t0 = e["start"]
    zf, zt, focus = FRAMINGS[variant % len(FRAMINGS)]
    if archive:
        raw = dest.with_suffix(".raw.mp4")
        fx.archive_treatment(src, t0, dur + 0.12, raw, era="teen")
        fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(raw), "-an", "-vf",
                _credit(e["credit_main"], e["credit_sub"]),
                *fx.ENC, str(dest)])
        raw.unlink(missing_ok=True)
        return
    raw = dest.with_suffix(".raw.mp4")
    fx.punch_in(src, t0, dur + 0.12, raw, zoom_from=zf, zoom_to=zt,
                focus=focus)
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(raw), "-an", "-vf",
            _credit(e["credit_main"], e["credit_sub"]), *fx.ENC, str(dest)])
    raw.unlink(missing_ok=True)


def render_doc(key: str, dur: float, dest: Path) -> None:
    """A document. Entries may be 4-tuples (no credit - our own captures and
    his own posts) or 6-tuples carrying an on-screen credit, which is how the
    owner-supplied press images are attributed at the moment they appear."""
    e = DOCS[key]
    rel, box, push, fit = e[0], e[1], e[2], e[3]
    cmain, csub = (e[4], e[5]) if len(e) >= 6 else ("", "")
    img = ROOT / rel
    if not img.exists():
        raise FileNotFoundError(f"document {key}: {img}")
    base = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=#0B0B0D" if fit else
            f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H}")
    vf = (f"{_crop(box)}{base},{_push(dur + 0.12, push)},"
          f"{_fade(dur)},format=yuv420p")
    if cmain:
        vf += "," + _credit(cmain, csub)
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(img), "-t", f"{dur + 0.12:.4f}", "-an",
            "-vf", vf, *fx.ENC, str(dest)])


def render_still(key: str, dur: float, dest: Path, clinical: bool) -> None:
    if clinical:
        rel, box, main, sub = CLIN[key]
        push, fill = 0.10, True
    else:
        rel, box, main, sub, fill = STILLS[key]
        push = 0.12
    img = ROOT / rel
    if not img.exists():
        raise FileNotFoundError(f"still {key}: {img}")
    grade = ("eq=brightness=-0.07:saturation=0.72," if clinical else "")
    # The microscopy images are nearly square; fitting them left black bars
    # down both sides, which reads as letterboxed archive footage.
    frame = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
             f"crop={W}:{H}" if fill else
             f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
             f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=#0B0B0D")
    vf = (f"{_crop(box)}{frame},"
          f"{_push(dur + 0.12, push)},{grade}"
          f"{_fade(dur, 0.45 if clinical else 0.28)},format=yuv420p,"
          + _credit(main, sub))
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(img), "-t", f"{dur + 0.12:.4f}", "-an",
            "-vf", vf, *fx.ENC, str(dest)])


def render_broll(it: dict, dur: float, dest: Path) -> None:
    p = ROOT / it["file"]
    total = fx.probe_dur(p)
    need = dur + 0.12
    lo, hi = usable_window(it)
    hi = min(hi, total)
    if (hi - lo) < need + 0.05:
        raise RuntimeError(
            f"{it['file']} has only {hi-lo:.2f}s of usable window for a "
            f"{need:.2f}s shot - looping is banned (rule 3)")
    start = lo + min((hi - lo - need) * 0.35, max(0.0, hi - lo - need))
    crop = ""
    if it.get("crop"):
        crop = _crop(tuple(it["crop"]))
    vf = (f"{crop}scale={W}:{H}:force_original_aspect_ratio=increase,"
          f"crop={W}:{H},fps={FPS},"
          f"{_push(need, 0.07)},{_fade(dur)},format=yuv420p")
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{start:.3f}", "-i", str(p), "-t", f"{need:.4f}", "-an",
            "-vf", vf, *fx.ENC, str(dest)])


def render_clip(key: str, dur: float, dest: Path) -> None:
    """An owner-supplied third-party video, credited on screen.

    These are low-resolution web artefacts - the Tenor capture is 640x360 - so
    they are placed INSET on the film's ground at close to native size rather
    than blown up to fill 1920, which would read as a bad upscale. A soft GIF
    inside a frame reads as a GIF; a soft GIF filling the screen reads as
    broken footage.
    """
    rel, cmain, csub, scale = CLIPS[key]
    src = ROOT / rel
    if not src.exists():
        raise FileNotFoundError(f"clip {key}: {src}")
    total = fx.probe_dur(src)
    need = dur + 0.12
    start = 0.0 if total <= need + 0.1 else min(0.3, total - need - 0.05)
    loops = []
    if total < need + 0.05:
        raise RuntimeError(
            f"{rel} is {total:.2f}s for a {need:.2f}s shot - looping is banned")
    inner = int(W * scale)
    vf = (f"scale={inner}:-2:flags=lanczos,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=#0A0A0C,"
          f"fps={FPS},{_fade(dur)},format=yuv420p," + _credit(cmain, csub))
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *loops,
            "-ss", f"{start:.3f}", "-i", str(src), "-t", f"{need:.4f}", "-an",
            "-vf", vf, *fx.ENC, str(dest)])


def render_flash(key: str, dur: float, dest: Path) -> None:
    """Several real clinical photographs, each on screen for a beat.

    The owner asked for "five little images of real images of people with
    Crohn's disease and it just flashes in and out for like five seconds".
    Each is graded down and cross-faded so no single one is dwelt on, which is
    also what rule 13 asks for.
    """
    imgs = [ROOT / r for r in FLASH[key][0]]
    imgs = [i for i in imgs if i.exists()]
    if not imgs:
        raise FileNotFoundError(f"flash {key}: no images on disk")
    cmain, csub = FLASH[key][1], FLASH[key][2]
    each = dur / len(imgs)
    parts = []
    for i, im in enumerate(imgs):
        p = dest.with_suffix(f".{i}.mp4")
        n = max(2, int(round(each * FPS)))
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
              f"crop={W}:{H},{_push(each + 0.1, 0.09)},"
              f"eq=brightness=-0.06:saturation=0.75,"
              f"fade=t=in:st=0:d=0.18,"
              f"fade=t=out:st={max(0, each-0.18):.3f}:d=0.18,"
              f"format=yuv420p")
        fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-loop", "1", "-i", str(im), "-t", f"{each + 0.1:.4f}", "-an",
                "-vf", vf, "-frames:v", str(n), *fx.ENC, str(p)])
        parts.append(p)
    lst = dest.with_suffix(".txt")
    lst.write_text("\n".join(f"file '{q.absolute().as_posix()}'"
                             for q in parts), encoding="utf-8")
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f",
            "concat", "-safe", "0", "-i", str(lst), "-an", "-vf",
            f"fps={FPS}," + _credit(cmain, csub), *fx.ENC, str(dest)])
    for q in parts + [lst]:
        q.unlink(missing_ok=True)


def render_parallax(key: str, dur: float, dest: Path) -> None:
    """A 2.5D move on a still, composited from depth layers.

    pipeline/parallax.py writes layers for Remotion's <ParallaxPhoto>; the rest
    of this film is assembled in ffmpeg, so they are composited here instead of
    pulling Remotion into the picture chain for one shot. Nearest layer moves
    most, far layer least, and the drift stays small because the inpainting
    behind the subject is classical and smears if pushed.

    NOTE: `crop` has no `eval` option - that belongs to scale and overlay - and
    it re-evaluates x/y every frame regardless. Passing eval=frame makes ffmpeg
    reject the entire filter graph.
    """
    name, ldir, cmain, csub = PARALLAX[key]
    layers = [ROOT / ldir / f"{name}_L{i}.png" for i in range(3)]
    for lp in layers:
        if not lp.exists():
            raise FileNotFoundError(f"parallax {key}: {lp}")
    n = max(2, int(round(dur * FPS)))
    spec = [(1.10, 16, 6), (1.15, 34, 10), (1.21, 58, 16)]
    ins, filt = [], []
    for i, (lp, (z, dx, dy)) in enumerate(zip(layers, spec)):
        ins += ["-loop", "1", "-t", f"{dur + 0.12:.4f}", "-i", str(lp)]
        sw, sh = int(W * z) // 2 * 2, int(H * z) // 2 * 2
        e = f"(1-pow(1-min(1,n/{n}),3))"
        filt.append(
            f"[{i}:v]scale={sw}:{sh}:flags=lanczos,"
            f"crop={W}:{H}:x='({sw}-{W})/2+{dx}*({e}-0.5)*2'"
            f":y='({sh}-{H})/2+{dy}*({e}-0.5)*2'[l{i}]")
    filt.append("[l0][l1]overlay=0:0:format=auto[a]")
    filt.append("[a][l2]overlay=0:0:format=auto[b]")
    filt.append(f"[b]fps={FPS},{_fade(dur)},format=yuv420p,"
                + _credit(cmain, csub) + "[v]")
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *ins,
            "-filter_complex", ";".join(filt), "-map", "[v]",
            "-t", f"{dur + 0.12:.4f}", *fx.ENC, str(dest)])


def render_card(key: str, dur: float, dest: Path) -> None:
    png = CARDS / f"{key}.png"
    if not png.exists():
        raise FileNotFoundError(f"card {key} not rendered: {png}")
    # A card is flat dark ground: a 10% zoom changes almost no pixels and the
    # shot measures as frozen even though the maths is moving.
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          f"{_push(dur + 0.12, 0.30)},{_fade(dur)},format=yuv420p")
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(png), "-t", f"{dur + 0.12:.4f}", "-an",
            "-vf", vf, *fx.ENC, str(dest)])


# ------------------------------------------------------------ frame-exact
def nb_frames(p: Path) -> int:
    """Exact frame count.

    ffprobe emits `70,` - with a trailing comma - for some files and `70` for
    others, so an `isdigit()` test reports 0 for perfectly good pieces. That
    made every affected shot look as though it had rendered short, and
    exact_frames would then refuse to continue. Take the first integer in the
    output and ignore the punctuation.
    """
    if not p.exists():
        return 0
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(p)],
        capture_output=True, text=True, timeout=900).stdout
    m = re.search(r"\d+", r or "")
    return int(m.group()) if m else 0


def exact_frames(p: Path, want: int) -> None:
    """Copy-trim to an exact frame count. Never pads: a padded frame is a
    frozen frame, and a previous fix for drift produced an 18-second stall."""
    got = nb_frames(p)
    if got == want:
        return
    if got < want:
        raise RuntimeError(f"{p.name}: {got} frames, needed {want} - "
                           f"rendered short, will not pad with a freeze")
    tmp = p.with_suffix(".trim.mp4")
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i",
            str(p), "-frames:v", str(want), "-c", "copy", str(tmp)])
    tmp.replace(p)


# ------------------------------------------------------------------ spans
def spans(edl: dict, audio_dur: float) -> list[tuple[float, float, object]]:
    out: list[tuple[float, float, object]] = []
    segs = edl["segs"]
    out.append((0.0, segs[0]["start"], -1))              # music lead-in
    for i, s in enumerate(segs):
        out.append((s["start"], s["end"], s["i"]))
        if i + 1 < len(segs) and segs[i + 1]["start"] - s["end"] > 0.05:
            out.append((s["end"], segs[i + 1]["start"], 6.5))   # title break
    if audio_dur - segs[-1]["end"] > 0.05:
        out.append((segs[-1]["end"], audio_dur, "TAIL"))
    return out


def allocate(edl: dict, audio_dur: float) -> list[dict]:
    """Turn spans into frame-exact shots. Nothing is rendered here."""
    total_frames = int(round(audio_dur * FPS))
    sp = spans(edl, audio_dur)

    # Frame boundaries for the spans themselves, so span edges never drift.
    edges = [0]
    for _, e, _ in sp:
        edges.append(int(round(e * FPS)))
    edges[-1] = total_frames

    shots: list[dict] = []
    for idx, (s0, s1, key) in enumerate(sp):
        f0, f1 = edges[idx], edges[idx + 1]
        span_frames = f1 - f0
        if span_frames <= 0:
            continue
        entry = PLAN.get(key if key != "TAIL" else "TAIL")
        if entry is None and key == "TAIL":
            entry = ([(1, ("card", "card_end"))], "music tail, no narration")
        if entry is None:
            raise KeyError(f"no plan for span {key} ({s0:.2f}-{s1:.2f})")
        slots, why = entry

        # Fixed slots first. A sync slot is fixed by whichever window it can
        # actually get, capped by the plan and by what is left of the span.
        resolved: list[dict] = []
        for slot in slots:
            if slot[0] == "fix":
                cap, spec = float(slot[1]), slot[2]
            else:
                cap, spec = None, slot[1]
            resolved.append({"cap": cap, "share": (
                0.0 if slot[0] == "fix" else float(slot[0])), "spec": spec})

        # Clinical stills are always short (rule 13) whatever the plan says.
        for r in resolved:
            if r["spec"][0] == "clin" and (r["cap"] is None or r["cap"] > 2.4):
                r["cap"], r["share"] = 2.2, 0.0

        fixed_frames = 0
        for r in resolved:
            if r["cap"] is not None:
                r["frames"] = max(1, int(round(min(r["cap"], MAX_SHOT) * FPS)))
                fixed_frames += r["frames"]
        share_total = sum(r["share"] for r in resolved if r["cap"] is None)
        left = span_frames - fixed_frames

        if share_total > 0:
            if left < int(MIN_SHOT * FPS) * sum(
                    1 for r in resolved if r["cap"] is None):
                raise RuntimeError(
                    f"span {key} ({s0:.2f}-{s1:.2f}, {span_frames/FPS:.2f}s): "
                    f"fixed slots take {fixed_frames/FPS:.2f}s and leave "
                    f"{left/FPS:.2f}s for "
                    f"{sum(1 for r in resolved if r['cap'] is None)} shots. "
                    f"Shorten the fixed slots in the plan.")
            acc = 0
            flex = [r for r in resolved if r["cap"] is None]
            for j, r in enumerate(flex):
                if j == len(flex) - 1:
                    r["frames"] = left - acc
                else:
                    r["frames"] = int(round(left * r["share"] / share_total))
                    acc += r["frames"]
        else:
            # No flexible slot: scale the fixed ones to fill the span exactly.
            scale = span_frames / max(1, fixed_frames)
            acc = 0
            for j, r in enumerate(resolved):
                if j == len(resolved) - 1:
                    r["frames"] = span_frames - acc
                else:
                    r["frames"] = max(1, int(round(r["frames"] * scale)))
                    acc += r["frames"]

        at = f0
        for j, r in enumerate(resolved):
            n = r["frames"]
            dur = n / FPS
            if dur > MAX_SHOT + 0.02:
                raise RuntimeError(
                    f"span {key} slot {j} is {dur:.2f}s - rule 4 caps a shot "
                    f"at {MAX_SHOT}s. Add another slot to the plan.")
            if dur < MIN_SHOT:
                raise RuntimeError(
                    f"span {key} slot {j} is only {dur:.2f}s - too short to "
                    f"read. Remove a slot from the plan.")
            shots.append({"span": str(key), "slot": j, "why": why,
                          "prog_start": at / FPS, "frames": n, "dur": dur,
                          "spec": r["spec"],
                          "name": f"{len(shots):03d}_{key}_{j}"
                                  .replace(".", "p").replace("-", "m")})
            at += n
        assert at == f1, (key, at, f1)

    got = sum(s["frames"] for s in shots)
    if got != total_frames:
        raise RuntimeError(f"allocated {got} frames, audio needs "
                           f"{total_frames}")
    return shots


def bind(shots: list[dict]) -> None:
    """Choose the actual asset for every shot.

    Within a pass, in programme order, because reuse, look-alike proximity and
    set diversity are all positional: which window is acceptable at 6:12
    depends on what was used at 6:00.

    But SYNC binds first, in its own pass. A bite's sync window is unique to
    that bite - it is him saying those words at that timecode, and there is no
    substitute - whereas a cutaway has 85 alternatives. Binding in one pass let
    a cutaway at 8:00 consume a DOAC look and then blocked the 10:20 bite's
    only sync window for resembling it, which is the priority exactly backwards.
    Two passes means a cutaway can be rejected for looking like a bite, and
    never the reverse.
    """
    for i, sh in enumerate(shots):
        sh["_idx"] = i
    per_source: dict[str, int] = {}
    order = ([s for s in shots if s["spec"][0] == "sync"]
             + [s for s in shots if s["spec"][0] != "sync"])
    for s in order:
        kind = s["spec"][0]
        idx = s["_idx"]
        t, dur = s["prog_start"], s["dur"]
        if kind == "sync":
            segi = int(float(s["span"]))
            e = take_sync(segi, t, dur)
            if e is None:
                raise Exhausted(
                    f"seg {segi} at {t:.2f}s asked for {dur:.2f}s of sync and "
                    f"no verified clean window is long enough. Give this bite "
                    f"illustrative picture in the plan instead.")
            REG.take(e["key"], s["name"])
            s["asset"] = e
            s["kind"] = "footage"
            s["archive"] = False
            s["variant"] = per_source.get(e["source"], 0)
            per_source[e["source"]] = s["variant"] + 1
            _assigned[idx] = e["source"]
            remember(t, s["name"], e.get("_hash"))
        elif kind in ("jimmy", "teen"):
            opts = s["spec"][1] if len(s["spec"]) > 1 else {}
            e = take_jimmy(t, dur, opts, teen=(kind == "teen"),
                           forbid=_neighbours(idx))
            REG.take(e["key"], s["name"])
            s["asset"] = e
            s["kind"] = "footage"
            s["archive"] = (kind == "teen")
            s["variant"] = per_source.get(e["source"], 0)
            per_source[e["source"]] = s["variant"] + 1
            _assigned[idx] = e["source"]
            remember(t, s["name"], e.get("_hash"))
        elif kind == "broll":
            it = take_broll(s["spec"][1], dur, t)
            REG.take(it["file"], s["name"])
            s["asset"] = it
            s["kind"] = "broll"
            _assigned[idx] = "stock"
        elif kind == "doc":
            REG.take(f"doc:{s['spec'][1]}", s["name"])
            s["kind"] = "doc"
            _assigned[idx] = "doc"
        elif kind == "still":
            REG.take(f"still:{s['spec'][1]}", s["name"])
            s["kind"] = "still"
            _assigned[idx] = "still"
        elif kind == "clin":
            REG.take(f"clin:{s['spec'][1]}", s["name"])
            s["kind"] = "clin"
            _assigned[idx] = "clin"
        elif kind in ("clip", "flash", "parallax"):
            REG.take(f"{kind}:{s['spec'][1]}", s["name"])
            s["kind"] = kind
            _assigned[idx] = kind
        elif kind == "card":
            REG.take(f"card:{s['spec'][1]}", s["name"])
            s["kind"] = "card"
            _assigned[idx] = "card"
        else:
            raise KeyError(f"unknown slot kind {kind}")


def _fingerprint(s: dict) -> str:
    """What this piece is made of. Shot names are positional, so a name alone
    does not identify content: change a clip in the allow-list and the old
    render would be served forever."""
    a = s.get("asset") or {}
    return json.dumps({
        "kind": s["kind"], "frames": s["frames"],
        "spec": [str(x) for x in s["spec"]],
        "asset": (a.get("key") or a.get("file") or ""),
        "start": round(float(a.get("start", 0) or 0), 3),
        "variant": s.get("variant", 0),
        "archive": s.get("archive", False),
        "crop": a.get("crop"),
    }, sort_keys=True)


def render_one(s: dict) -> Path:
    dest = WORK / f"{s['name']}.mp4"
    fp = dest.with_suffix(".fp.json")
    want = _fingerprint(s)
    if (dest.exists() and nb_frames(dest) == s["frames"]
            and fp.exists() and fp.read_text(encoding="utf-8") == want):
        return dest
    dest.unlink(missing_ok=True)
    k = s["kind"]
    if k == "footage":
        render_footage(s["asset"], s["dur"], dest, s["archive"],
                       s.get("variant", 0))
    elif k == "broll":
        render_broll(s["asset"], s["dur"], dest)
    elif k == "doc":
        render_doc(s["spec"][1], s["dur"], dest)
    elif k == "still":
        render_still(s["spec"][1], s["dur"], dest, clinical=False)
    elif k == "clin":
        render_still(s["spec"][1], s["dur"], dest, clinical=True)
    elif k == "parallax":
        render_parallax(s["spec"][1], s["dur"], dest)
    elif k == "clip":
        render_clip(s["spec"][1], s["dur"], dest)
    elif k == "flash":
        render_flash(s["spec"][1], s["dur"], dest)
    elif k == "card":
        render_card(s["spec"][1], s["dur"], dest)
    exact_frames(dest, s["frames"])
    fp.write_text(want, encoding="utf-8")
    return dest


def main() -> int:
    if not AUDIO.exists():
        raise FileNotFoundError(AUDIO)
    WORK.mkdir(parents=True, exist_ok=True)
    audio_dur = fx.probe_dur(AUDIO)
    edl = json.loads(EDL.read_text(encoding="utf-8"))
    load()

    shots = allocate(edl, audio_dur)
    print(f"[plan] {len(shots)} shots over {audio_dur:.2f}s "
          f"(median {np.median([s['dur'] for s in shots]):.2f}s, "
          f"longest {max(s['dur'] for s in shots):.2f}s)", flush=True)

    # Trim BEFORE binding, so a preview only needs the assets its own range
    # uses. Binding is positional - reuse, look-alike proximity and set
    # diversity all depend on what came before - so a preview's choices can
    # differ slightly from the same range in the full build. That is fine for
    # looking at it, and the full build is the one that ships.
    if ONLY:
        a, b = (float(x) for x in ONLY.split("-"))
        shots = [s for s in shots if a <= s["prog_start"] < b]
        print(f"[only] {ONLY}s -> {len(shots)} shots (preview: bound in "
              f"isolation, so asset choices may differ from the full build)",
              flush=True)
    bind(shots)

    from collections import Counter
    mix = Counter(s["kind"] for s in shots)
    print("[mix]", ", ".join(f"{k} {v}" for k, v in mix.most_common()),
          flush=True)

    SHOTLIST.write_text(json.dumps([
        {k: v for k, v in s.items()
         if k not in ("asset",)} | {
            "asset": (s.get("asset", {}).get("key")
                      or s.get("asset", {}).get("file") or "")}
        for s in shots], indent=2, default=str), encoding="utf-8")

    workers = max(2, min(10, (os.cpu_count() or 8)
                         // max(1, int(fx.ENC_THREADS))))
    def stale(s):
        p = WORK / f"{s['name']}.mp4"
        fp = p.with_suffix(".fp.json")
        return (not p.exists() or nb_frames(p) != s["frames"]
                or not fp.exists()
                or fp.read_text(encoding="utf-8") != _fingerprint(s))

    todo = [s for s in shots if stale(s)]
    print(f"[render] {len(todo)}/{len(shots)} shots on {workers} workers",
          flush=True)
    t0, done = time.time(), 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(render_one, s): s for s in todo}
        for f in as_completed(futs):
            f.result()
            done += 1
            if done % 10 == 0:
                el = time.time() - t0
                print(f"[render] {done}/{len(todo)}  "
                      f"{done/el*60:.1f} shots/min", flush=True)
    print(f"[render] done in {time.time()-t0:.0f}s", flush=True)

    pieces = []
    for s in shots:
        p = WORK / f"{s['name']}.mp4"
        got = nb_frames(p)
        if got != s["frames"]:
            raise RuntimeError(f"{s['name']}: {got} frames, want {s['frames']}")
        pieces.append(p)

    lst = WORK / "concat.txt"
    lst.write_text("\n".join(f"file '{p.absolute().as_posix()}'"
                             for p in pieces), encoding="utf-8")
    silent = WORK / "silent.mp4"
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f",
            "concat", "-safe", "0", "-i", str(lst), "-an", "-vf",
            f"fps={FPS}", *fx.ENC, str(silent)], timeout=10800)

    vdur = fx.probe_dur(silent)
    print(f"[picture] {vdur:.3f}s   [audio] {audio_dur:.3f}s   "
          f"delta {vdur-audio_dur:+.3f}s", flush=True)
    if not ONLY and abs(vdur - audio_dur) > 0.25:
        raise RuntimeError(
            f"HARD SYNC GATE: picture and audio differ by "
            f"{vdur-audio_dur:+.3f}s (limit 0.25s). Refusing to mux.")

    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i",
            str(silent), "-i", str(AUDIO), "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest",
            "-movflags", "+faststart", str(OUT)], timeout=3600)
    print(f"[OK] {OUT}")
    print(f"[OK] {len(pieces)} shots, {fx.probe_dur(OUT)/60:.2f} min, "
          f"nothing reused")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
