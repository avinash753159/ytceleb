#!/usr/bin/env python3
"""Build the V7 picture from the APPROVED storyboard, against locked audio.

Every shot comes from pipeline/storyboard3.PLAN - the thing that was signed
off - rather than from a per-act rota. Source palette is restricted to
footage where Jimmy is verifiably on screen, licensed stills, purpose-fetched
b-roll, and rendered cards. Airrack, Hemsworth and the Minecraft upload are
absent by construction, not by filtering.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
os.environ["MRBEAST_SCRIPT_VERSION"] = "V6"
os.environ.setdefault("MRBEAST_VOICE_MODE", "final")

import fx  # noqa: E402
from storyboard3 import PLAN, GRABS  # noqa: E402

W, H, FPS = fx.W, fx.H, fx.FPS
AUDIO = ROOT / "final_video/mrbeast_audio_v6/MRBEAST_V6_STORY_MASTER.wav"
OUT = ROOT / "final_video/THE_DISEASE_THAT_BUILT_MRBEAST_V7.mp4"
WORK = ROOT / "work/picture_v7"
PLANJSON = ROOT / "manifest/mrbeast_picture_plan_v7.json"

MED = ROOT / "dossier/mrbeast/medical"
BROLL = ROOT / "library/broll"
CARDS = ROOT / "work/cards"
PRIMARY = ROOT / "dossier/mrbeast/primary"
FONT = "graphics/public/fonts/Anton-Regular.ttf"

CREDIT = {
    "cLRLEnPaJLM.mp4": ("POWERFULJRE", "JOE ROGAN EXPERIENCE #1788"),
    "FjrJ2DJN_pA.mp4": ("THE DIARY OF A CEO", "YOUTUBE"),
    "9IQ_ldV9z_A.mp4": ("COLIN AND SAMIR", "YOUTUBE / JUNE 2023"),
    "AKJfakEsgy0.mp4": ("MRBEAST", "HI ME IN 5 YEARS / ARCHIVE"),
}
ARCHIVE = {"AKJfakEsgy0.mp4"}

# Stills and their on-screen credit.
STILL = {
    "ibd_real": (MED / "severe_colitis.jpg", "INFLAMMATORY BOWEL DAMAGE",
                 "WIKIMEDIA COMMONS / CC0", (0.18, 0.18, 0.18, 0.18)),
    "real_tissue": (MED / "crohn_resected.jpg", "RESECTED CROHN'S ILEUM",
                    "WIKIMEDIA COMMONS / CC BY-SA 4.0",
                    (0.05, 0.10, 0.05, 0.10)),
    "mechanism": (MED / "mechanism.png", "HEALTHY LINING vs CROHN'S",
                  "WIKIMEDIA COMMONS / CC0", (0.02, 0.02, 0.02, 0.50)),
    "the_post": (PRIMARY / "mrbeast_transformation_2023-06-29.jpg",
                 "@MRBEAST", "29 JUNE 2023", (0.0, 0.02, 0.0, 0.02)),
}
CLINICAL = [MED / n for n in ("skin_leg.jpg", "skin_leg2.jpg",
                              "badas_crohn.jpg", "severe_colitis.jpg")]

BROLL_MAP = {
    "gym_a": ("gym_lifting.mp4", 2.0, "PEXELS", "PRESSMASTER"),
    "gym_b": ("gym_dumbbell.mp4", 3.0, "PEXELS", "MICHELANGELO BUONARROTI"),
    "gym_c": ("gym_barbell.mp4", 1.5, "PEXELS", "OJYRAI FILMS"),
    "gym_d": ("gym_lifting.mp4", 7.0, "PEXELS", "PRESSMASTER"),
    "gym_e": ("gym_empty.mp4", 3.0, "PEXELS", "DS BABARIYA"),
    "gym_f": ("bedroom_dark.mp4", 3.0, "PEXELS", "FILM GEEK"),
    "walk_steps": ("walking_street.mp4", 2.0, "PEXELS", "MARY TAYLOR"),
    "tired": ("man_tired.mp4", 3.0, "PEXELS", "RDNE STOCK PROJECT"),
}
CARD_KEYS = {"card_weight", "card_310", "card_steps", "card_time",
             "card_rest", "card_record"}
# Keys with no artwork yet fall back to a clean slate rather than crashing.
FALLBACK_CARD = {"card_machine": ("A DECADE", "OF ONE PROBLEM")}

# Beats that were static text slates, now played over footage with the line
# burned on. (clip, credit_main, credit_sub, title shown on first piece)
TITLED = {
    "card_infusion": ("calendar_pages.mp4", "PEXELS",
                      "BORIS PAVLIKOVSKY", "EVERY EIGHT WEEKS. FOR LIFE."),
    "card_end": ("walking_treadmill.mp4", "PEXELS",
                 "LUIS QUINTERO", ""),
}


_SCENES: dict[tuple, list[float]] = {}


def scene_cuts(src: Path, t0: float, span: float) -> list[float]:
    """Absolute times of camera cuts inside a region of a source."""
    key = (str(src), round(t0, 1), round(span, 1))
    if key in _SCENES:
        return _SCENES[key]
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{max(0, t0):.2f}",
         "-t", f"{span:.2f}", "-i", str(src), "-vf",
         "select='gt(scene,0.30)',metadata=print", "-an", "-f", "null",
         "NUL"], capture_output=True, text=True, timeout=900)
    import re as _re
    cuts = [max(0, t0) + float(m)
            for m in _re.findall(r"pts_time:([\d.]+)", r.stderr or "")]
    _SCENES[key] = cuts
    return cuts


def uncut_window(src: Path, want: float, dur: float) -> float:
    """Return a start time whose `dur` seconds contain no camera cut.

    Interview windows of 10-22s routinely cross the podcast's own edits, so
    a shot that begins on Jimmy ends on the host. This finds the longest
    uninterrupted run near the requested point and sits inside it.
    """
    lo = max(0.0, want - 25.0)
    span = dur + 55.0
    cuts = scene_cuts(src, lo, span)
    hi = min(lo + span, fx.probe_dur(src))
    edges = [lo] + [c for c in cuts if lo < c < hi] + [hi]
    best, best_gap = None, 0.0
    for a, b in zip(edges, edges[1:]):
        gap = b - a
        if gap >= dur + 0.6 and gap > best_gap:
            # prefer runs near the intended moment
            if best is None or abs(a - want) < abs(best - want) or \
                    gap > best_gap * 1.4:
                best, best_gap = a + 0.3, gap
    return best if best is not None else want


def esc(v):
    return (v.replace("\\", r"\\").replace(":", r"\:")
             .replace("'", "").replace("%", r"\%"))


def credit_vf(main, sub, accent="#E3120B"):
    return (f"drawbox=x=34:y=ih-126:w=680:h=84:color=black@0.70:t=fill,"
            f"drawbox=x=34:y=ih-126:w=7:h=84:color={accent}:t=fill,"
            f"drawtext=fontfile='{FONT}':text='{esc(main)}'"
            f":fontcolor=white:fontsize=29:x=58:y=h-114,"
            f"drawtext=fontfile='{FONT}':text='{esc(sub)}'"
            f":fontcolor=#C8C8C8:fontsize=20:x=58:y=h-74")


def shot_footage(src, t0, dur, dest, main, sub, archive=False, punch=True):
    if archive:
        fx.archive_treatment(src, t0, dur, dest, era="teen")
        tmp = dest.with_suffix(".lab.mp4")
        fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(dest), "-an", "-vf", credit_vf(main, sub),
                *fx.ENC, str(tmp)])
        tmp.replace(dest)
        return dest
    if punch and dur > 3.0:
        tmp = dest.with_suffix(".raw.mp4")
        fx.punch_in(src, t0, dur, tmp, zoom_from=1.02, zoom_to=1.12)
        fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(tmp), "-an", "-vf", credit_vf(main, sub),
                *fx.ENC, str(dest)])
        tmp.unlink(missing_ok=True)
        return dest
    # Stock clips are 8-12s and some shots need longer. Loop rather than
    # silently returning a short piece, which desyncs everything after it.
    total = fx.probe_dur(src)
    pre = []
    if t0 + dur > total - 0.2:
        pre = ["-stream_loop", str(int(dur // max(1.0, total)) + 1)]
        t0 = 0.0
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *pre,
            "-ss", f"{t0:.3f}", "-i", str(src), "-t", f"{dur:.4f}", "-an",
            "-vf", f"{fx.FIT},fps={FPS}," + credit_vf(main, sub),
            *fx.ENC, str(dest)])
    return dest


def shot_still(img, dur, dest, main, sub, box=(0, 0, 0, 0), push=0.10):
    """Eased push on a still.

    `push` matters more than it looks. A rendered card is mostly flat dark
    ground, so a 10% zoom changes almost no pixels and the shot measures as
    frozen (0.20 mean delta) even though the maths is moving. Cards get a
    much larger push so the frame visibly lives.
    """
    n = max(2, int(round(dur * FPS)))
    l, t, r, b = box
    pre = ""
    if any(box):
        pre = (f"crop=iw*{1-l-r:.4f}:ih*{1-t-b:.4f}:"
               f"iw*{l:.4f}:ih*{t:.4f},")
    p = f"(1-pow(1-min(1,on/{n}),3))"
    z = f"1.02+{push:.3f}*{p}"
    vf = (f"{pre}scale={W*2}:-2,zoompan=z='{z}':d={n}:"
          f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
          f"format=yuv420p," + credit_vf(main, sub))
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(img), "-t", f"{dur:.4f}", "-an",
            "-vf", vf, *fx.ENC, str(dest)])
    return dest


def shot_pair(a, b, dur, dest, main, sub):
    """Before/after transformation with a slow push on both halves.

    The first build stacked two stills with no movement at all - fourteen
    seconds of frozen frame, which freezedetect flagged and a viewer would
    read as the video having stalled.
    """
    half = W // 2
    n = max(2, int(round(dur * FPS)))
    p = f"(1-pow(1-min(1,on/{n}),3))"
    zl, zr = f"1.02+0.09*{p}", f"1.10-0.08*{p}"   # halves drift oppositely
    fc = (f"[0:v]scale={half*2}:-2,zoompan=z='{zl}':d={n}:"
          f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
          f"s={half}x{H}:fps={FPS}[l];"
          f"[1:v]scale={half*2}:-2,zoompan=z='{zr}':d={n}:"
          f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
          f"s={half}x{H}:fps={FPS}[r];[l][r]hstack=inputs=2,"
          f"drawbox=x={half-3}:y=0:w=6:h={H}:color=#E3120B:t=fill,"
          f"format=yuv420p," + credit_vf(main, sub))
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(a), "-loop", "1", "-i", str(b),
            "-t", f"{dur:.4f}", "-an", "-filter_complex", fc,
            "-r", str(FPS), *fx.ENC, str(dest)])
    return dest


def shot_strip(imgs, dur, dest, main, sub):
    """Several brief clinical shots inside one segment."""
    n = len(imgs)
    each = dur / n
    parts = []
    for i, im in enumerate(imgs):
        p = dest.with_suffix(f".{i}.mp4")
        shot_still(im, each, p, main, sub)
        parts.append(p)
    lst = dest.with_suffix(".txt")
    lst.write_text("\n".join(f"file '{p.absolute().as_posix()}'"
                             for p in parts), encoding="utf-8")
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(lst), "-an",
            "-vf", f"fps={FPS}", *fx.ENC, str(dest)])
    for p in parts + [lst]:
        p.unlink(missing_ok=True)
    return dest


def shot_card(title, sub, dur, dest):
    """Text slate on a graded ground.

    NOT near-black: an 18-second #0A0A0C card tripped blackdetect and read
    as the film having died. The ground is lifted, given a soft accent
    wash, and the type drifts so the frame is never static.
    """
    # drawtext exposes `t` (seconds) and `n` (frame); `on` belongs to
    # zoompan and makes the expression unparseable here.
    drift = "'(h-text_h)/2-40-10*sin(t*0.55)'"
    vf = (f"drawbox=x=0:y=0:w=22:h={H}:color=#E3120B:t=fill,"
          f"drawbox=x=0:y=0:w={W}:h={H}:color=#E3120B@0.06:t=fill,"
          f"drawtext=fontfile='{FONT}':text='{esc(title)}'"
          f":fontcolor=white:fontsize=78:x=(w-text_w)/2:y={drift}")
    if sub:
        vf += (f",drawtext=fontfile='{FONT}':text='{esc(sub)}'"
               f":fontcolor=#CFCFCF:fontsize=36:x=(w-text_w)/2:y=(h/2)+80")
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"color=c=#191419:s={W}x{H}:r={FPS}",
            "-t", f"{dur:.4f}", "-an", "-vf", vf + ",format=yuv420p",
            *fx.ENC, str(dest)])
    return dest


def build_jobs():
    """One render job per storyboard entry; long b-roll is subdivided."""
    jobs = []
    for start, end, key, label, srclabel, kind in PLAN:
        dur = end - start
        if key in GRABS:
            v, t0 = GRABS[key]
            main, sub = CREDIT.get(v.name, ("SOURCE", ""))
            arch = v.name in ARCHIVE
            # Subdivide everything into short pieces. A long interview
            # window crosses the podcast's own edits and lands on the host;
            # each piece is then snapped inside a single camera angle.
            parts = max(1, round(dur / (9 if arch else 6)))
            for i in range(parts):
                d = dur / parts
                want = t0 + i * (d + 1.5)
                start = want if arch else uncut_window(v, want, d)
                jobs.append((key if parts == 1 else f"{key}_{i}", d,
                             ("footage", v, start, main, sub, arch)))
        elif key in STILL:
            img, main, sub, box = STILL[key]
            jobs.append((key, dur, ("still", img, main, sub, box)))
        elif key == "clinical_strip":
            jobs.append((key, dur, ("strip", CLINICAL,
                                    "CLINICAL", "WIKIMEDIA / CC BY, CC0")))
        elif key in ("ba_open", "ba_payoff"):
            before = PRIMARY / "mrbeast_transformation_2023-06-29.jpg"
            jobs.append((key, dur, ("pair", before, key,
                                    "@MRBEAST 29 JUN 2023", "AND TODAY")))
        elif key in BROLL_MAP:
            clip, t0, main, sub = BROLL_MAP[key]
            src = BROLL / clip
            # ~6s sub-shots: keeps the cut moving and stays inside the
            # length of a typical stock clip.
            parts = max(1, round(dur / 6))
            for i in range(parts):
                d = dur / parts
                jobs.append((f"{key}_{i}", d,
                             ("footage", src, t0 + i * 3.0, main, sub,
                              False)))
        elif key in TITLED:
            # Text slates that ran 18-19s measured a pixel delta of 0.23 -
            # static. They now play over real footage with the line on top.
            clip, main, sub, title = TITLED[key]
            src = BROLL / clip
            parts = max(1, round(dur / 6))
            for i in range(parts):
                jobs.append((f"{key}_{i}", dur / parts,
                             ("titled", src, 1.0 + i * 2.5, main, sub,
                              title if i == 0 else "")))
        elif key == "card_machine":
            # The system infographic was never built and fell back to an
            # 18-second near-black text slate. Until it exists, this beat
            # runs on his own archive - which is what the narration is
            # about anyway.
            v = ROOT / "dossier/mrbeast/archive/AKJfakEsgy0.mp4"
            parts = max(1, round(dur / 6))
            for i in range(parts):
                jobs.append((f"{key}_{i}", dur / parts,
                             ("footage", v, 30.0 + i * 11.0,
                              "MRBEAST", "HI ME IN 5 YEARS / ARCHIVE",
                              True)))
        elif key in CARD_KEYS and (CARDS / f"{key}.png").exists():
            jobs.append((key, dur, ("still", CARDS / f"{key}.png",
                                    "", "", (0, 0, 0, 0))))
        else:
            title, sub = FALLBACK_CARD.get(key, (label.upper()[:38], ""))
            jobs.append((key, dur, ("card", title, sub)))
    return jobs


def render_one(name, dur, spec):
    dest = WORK / f"{name}.mp4"
    if dest.exists():
        return dest
    kind = spec[0]
    if kind == "footage":
        _, v, t0, main, sub, arch = spec
        room = fx.probe_dur(v) - dur - 0.5
        if room > 0.5:                      # only clamp when it fits
            t0 = max(0.5, min(t0, room))
        return shot_footage(v, t0, dur, dest, main, sub, archive=arch)
    if kind == "titled":
        _, v, t0, main, sub, title = spec
        total = fx.probe_dur(v)
        pre = []
        if t0 + dur > total - 0.2:
            pre = ["-stream_loop", str(int(dur // max(1.0, total)) + 1)]
            t0 = 0.0
        vf = f"{fx.FIT},fps={FPS},eq=brightness=-0.06:saturation=0.85"
        if title:
            vf += (f",drawbox=x=0:y=0:w={W}:h={H}:color=black@0.30:t=fill,"
                   f"drawtext=fontfile='{FONT}':text='{esc(title)}'"
                   f":fontcolor=white:fontsize=66:x=(w-text_w)/2"
                   f":y=(h-text_h)/2")
        vf += "," + credit_vf(main, sub)
        fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *pre,
                "-ss", f"{t0:.3f}", "-i", str(v), "-t", f"{dur:.4f}", "-an",
                "-vf", vf, *fx.ENC, str(dest)])
        return dest
    if kind == "still":
        _, img, main, sub, box = spec
        # Rendered cards are flat dark ground - they need a far bigger push
        # than a photograph to read as moving at all.
        is_card = CARDS in Path(img).parents
        return shot_still(img, dur, dest, main, sub, box,
                          push=0.34 if is_card else 0.12)
    if kind == "strip":
        _, imgs, main, sub = spec
        return shot_strip([i for i in imgs if i.exists()], dur, dest,
                          main, sub)
    if kind == "pair":
        _, before, key, main, sub = spec
        after_src = (ROOT / "dossier/mrbeast/sources/9IQ_ldV9z_A.mp4"
                     if key == "ba_open"
                     else ROOT / "dossier/mrbeast/sources/FjrJ2DJN_pA.mp4")
        after_png = WORK / f"_after_{key}.png"
        if not after_png.exists():
            fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", "712" if key == "ba_open" else "120",
                    "-i", str(after_src), "-frames:v", "1", str(after_png)])
        return shot_pair(before, after_png, dur, dest, main, sub)
    _, title, sub = spec
    return shot_card(title, sub, dur, dest)


def main() -> int:
    if not AUDIO.exists():
        raise FileNotFoundError(AUDIO)
    WORK.mkdir(parents=True, exist_ok=True)
    jobs = build_jobs()
    print(f"[plan] {len(jobs)} shots, "
          f"{sum(d for _, d, _ in jobs):.1f}s", flush=True)

    workers = max(2, min(10, (os.cpu_count() or 8)
                         // max(1, int(fx.ENC_THREADS))))
    todo = [j for j in jobs if not (WORK / f"{j[0]}.mp4").exists()]
    print(f"[render] {len(todo)} shots on {workers} workers", flush=True)
    t0 = time.time()
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(render_one, n, d, s): n for n, d, s in todo}
        for f in as_completed(futs):
            f.result()
            done += 1
            if done % 10 == 0:
                print(f"[render] {done}/{len(todo)}", flush=True)
    print(f"[render] done in {time.time()-t0:.0f}s", flush=True)

    pieces = []
    for name, dur, _ in jobs:
        p = WORK / f"{name}.mp4"
        got = fx.probe_dur(p)
        if abs(got - dur) > 0.12:
            p.unlink(missing_ok=True)
            raise RuntimeError(f"{name}: {got:.2f}s, expected {dur:.2f}s")
        pieces.append(p)

    lst = WORK / "concat.txt"
    lst.write_text("\n".join(f"file '{p.absolute().as_posix()}'"
                             for p in pieces), encoding="utf-8")
    silent = WORK / "silent.mp4"
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f",
            "concat", "-safe", "0", "-i", str(lst), "-an", "-vf",
            f"fps={FPS}", *fx.ENC, str(silent)], timeout=7200)

    vdur, adur = fx.probe_dur(silent), fx.probe_dur(AUDIO)
    print(f"[picture] {vdur:.2f}s  [audio] {adur:.2f}s "
          f"delta {vdur-adur:+.2f}s", flush=True)
    if vdur < adur - 0.04:
        # Extend the final shot with live picture rather than a freeze.
        #
        # The extended copy goes to its OWN path. Overwriting the canonical
        # cached piece meant the next run reused a 7.93s file where the plan
        # said 6.00s, and the duration check rejected it - the guard firing
        # on damage this step had caused.
        name, dur, spec = jobs[-1]
        ext_name = f"{name}__ext"
        (WORK / f"{ext_name}.mp4").unlink(missing_ok=True)
        render_one(ext_name, dur + (adur - vdur), spec)
        pieces[-1] = WORK / f"{ext_name}.mp4"
        lst.write_text("\n".join(f"file '{q.absolute().as_posix()}'"
                                 for q in pieces), encoding="utf-8")
        fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f",
                "concat", "-safe", "0", "-i", str(lst), "-an", "-vf",
                f"fps={FPS}", *fx.ENC, str(silent)], timeout=7200)
        print(f"[fit] picture now {fx.probe_dur(silent):.2f}s", flush=True)
    elif vdur > adur + 0.04:
        trimmed = WORK / "silent_fit.mp4"
        fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i",
                str(silent), "-t", f"{adur:.4f}", "-an", "-c:v", "copy",
                str(trimmed)])
        silent = trimmed

    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i",
            str(silent), "-i", str(AUDIO), "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest",
            "-movflags", "+faststart", str(OUT)], timeout=3600)

    PLANJSON.write_text(json.dumps(
        [{"name": n, "dur": round(d, 3), "kind": s[0]} for n, d, s in jobs],
        indent=2), encoding="utf-8")
    print(f"[OK] {OUT}")
    print(f"[OK] {len(pieces)} shots, {fx.probe_dur(OUT)/60:.2f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
