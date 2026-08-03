#!/usr/bin/env python3
"""Build the V6 picture against the locked V6 audio master.

Design rules, all from operator decisions earlier in this project:
  - NO CelebWorkout logo or watermark anywhere. Source credit bottom-left on
    borrowed footage; licence credit on medical illustrations.
  - Pace curve, not uniform cutting. The reference documentary measured
    5.15s / 5.25s / 2.92s median shot across thirds - slow, then accelerating.
    Long narration blocks are subdivided into more shots later in the film.
  - Nothing fabricated. Archive is treated so it reads as archive; no stock
    person stands in for Jimmy; medical illustration is labelled as such.
  - Every window is taken from a per-source cursor so no shot repeats.

Timeline is reconstructed with the SAME lead-in and title-break arithmetic
the audio builder used, so picture and sound cannot drift.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
os.environ["MRBEAST_SCRIPT_VERSION"] = "V6"
os.environ.setdefault("MRBEAST_VOICE_MODE", "final")

import clean_windows as cw  # noqa: E402
import fx  # noqa: E402
import mrbeast_radio as radio  # noqa: E402
from edl import build_edl  # noqa: E402
from v11_assemble import fit_run_durations, probe_dur  # noqa: E402
from mrbeast_audio_v4 import LEAD_IN, TITLE_BREAK, chapter_spans  # noqa: E402

W, H, FPS = fx.W, fx.H, fx.FPS
AUDIO = ROOT / "final_video/mrbeast_audio_v6/MRBEAST_V6_STORY_MASTER.wav"
OUT = ROOT / "final_video/THE_DISEASE_THAT_BUILT_MRBEAST_V6.mp4"
WORK = ROOT / "work/mrbeast_picture_v6"
PLAN = ROOT / "manifest/mrbeast_picture_plan_v6.json"

SRC = ROOT / "dossier/mrbeast/sources"
ARC = ROOT / "dossier/mrbeast/archive"
MED = ROOT / "dossier/mrbeast/medical"
DOC = ROOT / "dossier/mrbeast/documents"

CREDIT = {
    "FjrJ2DJN_pA": ("THE DIARY OF A CEO", "YOUTUBE / INTERVIEW"),
    "cLRLEnPaJLM": ("POWERFULJRE", "JOE ROGAN EXPERIENCE #1788"),
    "9IQ_ldV9z_A": ("COLIN AND SAMIR", "YOUTUBE / JUNE 2023"),
    "7r3ORKgNUjw": ("AIRRACK", "600-DAY CHALLENGE / 2024"),
    "c8VcUnz3nVc": ("COLIN AND SAMIR", "THE FULL STORY OF MRBEAST"),
    "cWEUE8X7p-k": ("MRBEAST", "YOUTUBE"),
    "NdjcGrpNSF4": ("MRBEAST", "YOUTUBE / BEHIND THE SCENES"),
    "WwVs1qVaOb4": ("CHRIS HEMSWORTH", "YOUTUBE / SEPT. 2024"),
    "AKJfakEsgy0": ("MRBEAST", "ARCHIVE UPLOAD"),
    "2XVcLrB7B3Y": ("MRBEAST", "EARLY ARCHIVE"),
    "F0OkwXKcPSE": ("MRBEAST", "EARLY ARCHIVE"),
}
ARCHIVE_IDS = {"AKJfakEsgy0", "2XVcLrB7B3Y", "F0OkwXKcPSE"}

# Per-act B-roll rolls for narration. (source_id, first_window_start).
# The cursor advances so a source is never cut at the same place twice.
ROLL = {
    "open":       [("NdjcGrpNSF4", 120), ("cWEUE8X7p-k", 300),
                   ("NdjcGrpNSF4", 640)],
    "origin":     [("AKJfakEsgy0", 30), ("2XVcLrB7B3Y", 12),
                   ("AKJfakEsgy0", 96)],
    "illness":    [("AKJfakEsgy0", 150), ("cWEUE8X7p-k", 520)],
    "machine":    [("cWEUE8X7p-k", 120), ("NdjcGrpNSF4", 420),
                   ("c8VcUnz3nVc", 300), ("cWEUE8X7p-k", 700)],
    "contract":   [("7r3ORKgNUjw", 140), ("7r3ORKgNUjw", 300),
                   ("WwVs1qVaOb4", 110)],
    "protocol":   [("WwVs1qVaOb4", 150), ("7r3ORKgNUjw", 250),
                   ("WwVs1qVaOb4", 190), ("7r3ORKgNUjw", 600)],
    "limit":      [("7r3ORKgNUjw", 700), ("7r3ORKgNUjw", 860),
                   ("WwVs1qVaOb4", 230)],
    "fall":       [("NdjcGrpNSF4", 300), ("7r3ORKgNUjw", 960),
                   ("cWEUE8X7p-k", 880)],
    "resolution": [("7r3ORKgNUjw", 1130), ("AKJfakEsgy0", 190),
                   ("WwVs1qVaOb4", 260)],
}

# Narration segments that must show a specific asset instead of B-roll.
# Matched by an ordinal within the act, because segment ids shift on rewrite.
MEDICAL = {
    # (act, nth narration block in that act) -> (asset, label, sublabel)
    ("illness", 2): (MED / "tract.png", "DIGESTIVE TRACT",
                     "BLAUSEN MEDICAL / CC BY 3.0"),
    ("illness", 3): (MED / "mechanism.png", "HEALTHY LINING vs CROHN'S",
                     "WIKIMEDIA COMMONS / CC0"),
    ("illness", 4): (MED / "villi_histology.jpg", "INTESTINAL VILLI",
                     "WIKIMEDIA COMMONS / CC0"),
    ("illness", 5): (MED / "villi_closeup.jpg", "ABSORPTIVE SURFACE",
                     "WIKIMEDIA COMMONS / CC BY 4.0"),
    ("illness", 6): (DOC / "niddk_definition.png", "MEDICAL CONTEXT",
                     "NIH - NIDDK"),
    ("illness", 7): (DOC / "niddk_treatment.png", "MEDICAL CONTEXT",
                     "NIH - NIDDK"),
}

# Crop boxes so a dense figure reads at 1080p (l, t, r, b as fractions).
CROP = {"mechanism.png": (0.02, 0.02, 0.02, 0.46)}

# Target shot length by act - the accelerating pace curve.
PACE = {"open": 5.0, "origin": 5.2, "illness": 5.4, "machine": 4.6,
        "contract": 4.2, "protocol": 4.0, "limit": 3.4, "fall": 3.2,
        "resolution": 3.6}


_DUR: dict[str, float] = {}


def src_dur(p: Path) -> float:
    k = str(p)
    if k not in _DUR:
        _DUR[k] = fx.probe_dur(p)
    return _DUR[k]


def safe_window(path: Path, want: float, dur: float) -> float:
    """Keep a window inside the file.

    The archive uploads are SHORT - AKJfakEsgy0 is 127s, 2XVcLrB7B3Y is 156s -
    while the B-roll cursor advances 17s per use. Seeking past the end yields
    a zero-frame piece, which is what killed the first render at shot 015.
    Wrap into the usable range instead of clamping, so repeated draws still
    land on different footage.
    """
    total = src_dur(path)
    usable = total - dur - 1.0
    if usable <= 1.0:
        raise ValueError(f"{path.name} is {total:.1f}s - too short for a "
                         f"{dur:.1f}s shot")
    return 0.5 + (want % usable)


def esc(v):
    return (v.replace("\\", r"\\").replace(":", r"\:")
             .replace("'", "").replace("%", r"\%"))


FONT = "graphics/public/fonts/Anton-Regular.ttf"


def credit_vf(main, sub, accent="#E3120B"):
    return (f"drawbox=x=34:y=ih-126:w=660:h=84:color=black@0.70:t=fill,"
            f"drawbox=x=34:y=ih-126:w=7:h=84:color={accent}:t=fill,"
            f"drawtext=fontfile='{FONT}':text='{esc(main)}'"
            f":fontcolor=white:fontsize=30:x=58:y=h-114,"
            f"drawtext=fontfile='{FONT}':text='{esc(sub)}'"
            f":fontcolor=#C8C8C8:fontsize=21:x=58:y=h-74")


def footage(src: Path, t0, dur, dest, main, sub, archive=False, punch=True):
    if archive:
        fx.archive_treatment(src, t0, dur, dest, era="teen")
        tmp = dest.with_suffix(".lab.mp4")
        fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(dest), "-an", "-vf", credit_vf(main, sub),
                *fx.ENC, str(tmp)])
        tmp.replace(dest)
        return dest
    if punch:
        tmp = dest.with_suffix(".raw.mp4")
        fx.punch_in(src, t0, dur, tmp, zoom_from=1.02, zoom_to=1.13)
        fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(tmp), "-an", "-vf", credit_vf(main, sub),
                *fx.ENC, str(dest)])
        tmp.unlink(missing_ok=True)
        return dest
    vf = f"{fx.FIT},fps={FPS}," + credit_vf(main, sub)
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{t0:.3f}", "-i", str(src), "-t", f"{dur:.4f}",
            "-an", "-vf", vf, *fx.ENC, str(dest)])
    return dest


# Labelled diagrams must be shown whole - crop-filling a square anatomy
# chart to 16:9 clipped its own labels ("Pharynx" rendered as "arynx").
FIT_WHOLE = {"tract.png"}


def still(img: Path, dur, dest, main, sub, zoom=(1.03, 1.16)):
    """Eased push on a still, with the credit slate."""
    n = max(2, int(round(dur * FPS)))
    c = CROP.get(img.name)
    pre = ""
    if c:
        l, t, r, b = c
        pre = (f"crop=iw*{1 - l - r:.4f}:ih*{1 - t - b:.4f}:"
               f"iw*{l:.4f}:ih*{t:.4f},")

    if img.name in FIT_WHOLE:
        # Letterbox the whole diagram onto a neutral field and push gently,
        # so nothing on the edges is ever lost.
        z0, z1 = 1.0, 1.05
        p = f"(1-pow(1-min(1,on/{n}),3))"
        z = f"{z0:.4f}+{z1 - z0:.4f}*{p}"
        vf = (f"{pre}scale={int(W * 1.6)}:{int(H * 1.6)}:"
              f"force_original_aspect_ratio=decrease,"
              f"pad={int(W * 1.6)}:{int(H * 1.6)}:(ow-iw)/2:(oh-ih)/2"
              f":color=#0E0E10,"
              f"zoompan=z='{z}':d={n}:x='iw/2-(iw/zoom/2)':"
              f"y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
              f"format=yuv420p," + credit_vf(main, sub))
    else:
        p = f"(1-pow(1-min(1,on/{n}),3))"
        z = f"{zoom[0]:.4f}+{zoom[1] - zoom[0]:.4f}*{p}"
        vf = (f"{pre}scale={W * 2}:-2,"
              f"zoompan=z='{z}':d={n}:x='iw/2-(iw/zoom/2)':"
              f"y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
              f"format=yuv420p," + credit_vf(main, sub))

    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-loop", "1", "-i", str(img), "-t", f"{dur:.4f}",
            "-an", "-vf", vf, *fx.ENC, str(dest)])
    return dest


def build_timeline():
    """Segment list with program times matching the audio master exactly."""
    doc = radio.parse_script()
    edl = build_edl(doc)
    runs = sorted((ROOT / "final_video/mrbeast_radio_v6_final")
                  .glob("vo_run_*.wav"))
    runs = runs[:len(radio.narration_texts(edl))]
    fit_run_durations(edl, [probe_dur(p) for p in runs])

    spans = chapter_spans(edl)
    open_end = spans[0][2]
    offs = edl.offsets()
    out = []
    for i, seg in enumerate(edl.segs):
        t = offs[i] + LEAD_IN
        if offs[i] >= open_end - 1e-6:
            t += TITLE_BREAK
        out.append({"id": seg.seg_id, "kind": seg.kind, "chapter": seg.chapter,
                    "dur": seg.dur, "t": t,
                    "source": getattr(seg, "source", None),
                    "t0": getattr(seg, "t0", None)})
    return out, open_end + LEAD_IN


def main() -> int:
    if not AUDIO.exists():
        raise FileNotFoundError(AUDIO)
    WORK.mkdir(parents=True, exist_ok=True)
    segs, break_at = build_timeline()

    cursor: dict[str, float] = {}
    roll_i: dict[str, int] = {}
    narr_n: dict[str, int] = {}
    pieces, plan = [], []
    # Spec of the most recent footage shot, so the final one can be
    # re-rendered longer to absorb accumulated frame rounding.
    tail_spec = [None]

    # ---- pre-compute clean window pools, in parallel -------------------
    # OCR inside the planning loop meant one window checked at a time on a
    # 20-core machine. Every source is scanned concurrently instead, once.
    # Draws per act, split across that act's roll - the previous version
    # credited every source in a roll with every draw, over-counting ~3x
    # and scanning far more candidate windows than the film could use.
    draws = Counter()
    for s in segs:
        if s["kind"] in ("narr", "beat", "card"):
            n_shots = (1 if s["kind"] != "narr"
                       else max(1, min(4, int(round(
                           s["dur"] / PACE.get(s["chapter"], 4.5))))))
            draws[s["chapter"]] += n_shots
    need = Counter()
    for act, d in draws.items():
        per = -(-d // len(ROLL[act]))          # ceil
        for sid, _ in ROLL[act]:
            need[sid] += per

    # One process pool for the whole scan. Measured: a pool per source spent
    # most of its time loading the OCR model eight times over and returned
    # only a 1.6x speedup.
    paths = {sid: (ARC if sid in ARCHIVE_IDS else SRC) / f"{sid}.mp4"
             for sid in need}
    cands = {sid: cw.candidates(paths[sid], 6.0, max(6, n))
             for sid, n in need.items()}
    jobs_ocr = [(paths[sid], t, 6.0) for sid, ts in cands.items() for t in ts]
    print(f"[ocr] scanning {len(jobs_ocr)} windows across {len(need)} "
          f"sources on 8 processes...", flush=True)
    t_ocr = time.time()
    cw.scan_many(jobs_ocr, workers=8)
    cw.save_cache()
    pools = {sid: cw.verdicts(paths[sid], ts, 6.0)
             for sid, ts in cands.items()}
    print(f"[ocr] done in {time.time() - t_ocr:.0f}s", flush=True)
    for sid, n in need.items():
        print(f"[ocr]   {sid:14} need {n:3d} -> {len(pools[sid]):3d} clean",
              flush=True)

    pool_i: dict[str, int] = {}
    rejected: list[str] = []

    def next_broll(act, dur):
        """Draw the next unused clean window for this act."""
        r = ROLL[act]
        i = roll_i.get(act, 0)
        roll_i[act] = i + 1
        sid, base = r[i % len(r)]
        path = (ARC if sid in ARCHIVE_IDS else SRC) / f"{sid}.mp4"
        pool = pools.get(sid) or []
        if pool:
            j = pool_i.get(sid, 0)
            pool_i[sid] = j + 1
            return sid, path, pool[j % len(pool)]
        # No clean window anywhere in this source - fall back and say so.
        rejected.append(f"{sid}: no clean windows found")
        adv = cursor.get(sid, 0.0)
        cursor[sid] = adv + 17.0
        return sid, path, safe_window(path, base + adv, dur)

    idx = 0

    jobs: list[tuple[Path, object, float, dict]] = []

    def emit(dur, fn, note):
        """Queue a shot. Rendering happens in parallel after planning."""
        nonlocal idx
        p = WORK / f"{idx:03d}.mp4"
        jobs.append((p, fn, dur, dict(note, i=idx)))
        pieces.append(p)
        plan.append({"i": idx, "dur": round(dur, 3), **note})
        idx += 1

    for s in segs:
        act, dur = s["chapter"], s["dur"]

        if s["kind"] == "bite":
            sid = s["source"]
            main, sub = CREDIT.get(sid, ("SOURCE", ""))
            emit(dur, lambda p, d, sid=sid, t0=s["t0"], m=main, sb=sub:
                 footage(SRC / f"{sid}.mp4", t0, d, p, m, sb,
                         punch=(d > 6.0)),
                 {"kind": "bite", "act": act, "src": sid})
            continue

        if s["kind"] in ("beat", "card"):
            sid, path, t0 = next_broll(act, dur)
            main, sub = CREDIT.get(sid, ("SOURCE", ""))
            emit(dur, lambda p, d, pa=path, t0=t0, sid=sid, m=main, sb=sub:
                 footage(pa, t0, d, p, m, sb,
                         archive=(sid in ARCHIVE_IDS), punch=False),
                 {"kind": "beat", "act": act, "src": sid})
            continue

        # ---- narration ----
        k = narr_n.get(act, 0)
        narr_n[act] = k + 1
        med = MEDICAL.get((act, k))
        if med:
            img, main, sub = med
            if img.exists():
                emit(dur, lambda p, d, im=img, m=main, sb=sub:
                     still(im, d, p, m, sb),
                     {"kind": "medical", "act": act, "asset": img.name})
                continue

        # Subdivide long narration into multiple shots, tighter later on.
        target = PACE.get(act, 4.5)
        shots = max(1, min(4, int(round(dur / target))))
        each = dur / shots
        for _ in range(shots):
            sid, path, t0 = next_broll(act, each)
            main, sub = CREDIT.get(sid, ("SOURCE", ""))
            tail_spec[0] = {"path": path, "t0": t0, "dur": each,
                            "main": main, "sub": sub,
                            "archive": sid in ARCHIVE_IDS}
            emit(each,
                 lambda p, d, pa=path, t0=t0, sid=sid, m=main, sb=sub:
                 footage(pa, t0, d, p, m, sb,
                         archive=(sid in ARCHIVE_IDS),
                         punch=(d > 3.0)),
                 {"kind": "narr", "act": act, "src": sid})

    # ---- render every queued shot in parallel --------------------------
    # Each shot is an independent ffmpeg job, so they saturate the cores
    # instead of running one at a time.
    # workers x fx.ENC_THREADS should land near the core count, not far past
    # it. 14 workers each spawning ~20 x264 threads starved the machine.
    cores = os.cpu_count() or 8
    workers = max(2, min(10, cores // max(1, int(fx.ENC_THREADS))))

    # Killing a render leaves half-written pieces behind. ffprobe reports
    # their duration as 'N/A', so validate the cache and drop anything
    # corrupt or short - it simply re-renders rather than crashing the build
    # or, worse, concatenating a truncated shot.
    def piece_len(p: Path):
        try:
            return probe_dur(p)
        except Exception:
            return None

    salvaged = 0
    for p, _fn, dur, _note in jobs:
        if not p.exists():
            continue
        got = piece_len(p)
        if got is None or abs(got - dur) > 0.12:
            p.unlink(missing_ok=True)
            salvaged += 1
    if salvaged:
        print(f"[cache] discarded {salvaged} corrupt/short cached shots",
              flush=True)

    todo = [j for j in jobs if not j[0].exists()]
    print(f"[render] {len(todo)} shots on {workers} workers", flush=True)
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fn, p, dur): (p, dur, note)
                for p, fn, dur, note in todo}
        for f in as_completed(futs):
            p, dur, note = futs[f]
            f.result()                       # surface any ffmpeg failure
            done += 1
            if done % 20 == 0:
                print(f"[render] {done}/{len(todo)}", flush=True)

    # A shot that came out short means its window ran off the end of the
    # source. Concatenating it would desync everything after it against the
    # locked audio, so this is a hard failure, not a warning.
    for p, _fn, dur, note in jobs:
        got = piece_len(p)
        if got is None or abs(got - dur) > 0.12:
            p.unlink(missing_ok=True)
            raise RuntimeError(
                f"shot {note['i']:03d} ({note.get('src')}) is "
                f"{'unreadable' if got is None else f'{got:.2f}s'}, "
                f"expected {dur:.2f}s")

    # ---- title break: hold a wide, no credit clutter ----
    tb = WORK / "title_break.mp4"
    if not tb.exists():
        footage(ARC / "AKJfakEsgy0.mp4", 8.0, TITLE_BREAK, tb,
                "MRBEAST", "ARCHIVE UPLOAD", archive=True)
    ins = next(i for i, p in enumerate(plan)
               if p["act"] != "open")
    pieces.insert(ins, tb)
    plan.insert(ins, {"i": -1, "dur": TITLE_BREAK, "kind": "title_break",
                      "act": "open", "src": "AKJfakEsgy0"})

    # ---- lead-in ----
    lead = WORK / "lead_in.mp4"
    if not lead.exists():
        footage(SRC / "NdjcGrpNSF4.mp4", 60.0, LEAD_IN, lead,
                "MRBEAST", "YOUTUBE / BEHIND THE SCENES", punch=False)
    pieces.insert(0, lead)
    plan.insert(0, {"i": -2, "dur": LEAD_IN, "kind": "lead_in",
                    "act": "open", "src": "NdjcGrpNSF4"})

    PLAN.write_text(json.dumps(plan, indent=2), encoding="utf-8")

    lst = WORK / "concat.txt"
    lst.write_text("\n".join(f"file '{p.absolute().as_posix()}'"
                             for p in pieces), encoding="utf-8")
    silent = WORK / "silent.mp4"
    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(lst), "-an",
            "-vf", f"fps={FPS}", *fx.ENC, str(silent)], timeout=7200)

    vdur, adur = probe_dur(silent), probe_dur(AUDIO)
    print(f"[picture] {vdur:.2f}s  [audio] {adur:.2f}s  "
          f"delta {vdur - adur:+.2f}s")

    # Per-piece frame rounding accumulates across 130+ shots (~29ms each,
    # ~3.8s total). The deficit has to land AFTER all sync-critical content -
    # putting it anywhere earlier would shift every following shot against
    # the locked audio - so the final shot absorbs it.
    #
    # It is re-rendered longer from live footage rather than padded with a
    # frozen frame: freezing produced a visible 3.8s stall over the outro.
    if abs(vdur - adur) > 0.04:
        if vdur < adur:
            deficit = adur - vdur
            spec = tail_spec[0]
            new_dur = spec["dur"] + deficit
            last = pieces[-1]
            last.unlink(missing_ok=True)
            t0 = safe_window(spec["path"], spec["t0"], new_dur)
            footage(spec["path"], t0, new_dur, last, spec["main"],
                    spec["sub"], archive=spec["archive"], punch=False)
            print(f"[fit] final shot extended {spec['dur']:.2f}s -> "
                  f"{new_dur:.2f}s to absorb {deficit:.2f}s of rounding")
            lst.write_text("\n".join(f"file '{p.absolute().as_posix()}'"
                                     for p in pieces), encoding="utf-8")
            fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "concat", "-safe", "0", "-i", str(lst), "-an",
                    "-vf", f"fps={FPS}", *fx.ENC, str(silent)], timeout=7200)
        else:
            fixed = WORK / "silent_fitted.mp4"
            fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-i", str(silent), "-t", f"{adur:.4f}", "-an",
                    "-c:v", "copy", str(fixed)], timeout=3600)
            silent = fixed
        print(f"[fit] picture now {probe_dur(silent):.2f}s")

    fx.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(silent), "-i", str(AUDIO),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
            "-shortest", "-movflags", "+faststart", str(OUT)], timeout=3600)

    cw.save_cache()
    print(f"[OK] {OUT}")
    print(f"[OK] {len(pieces)} shots, {probe_dur(OUT) / 60:.2f} min")
    print(f"[ocr] {len(rejected)} candidate windows rejected for overlays")
    for r in rejected[:25]:
        print(f"      {r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

