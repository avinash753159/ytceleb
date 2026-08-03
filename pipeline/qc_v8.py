#!/usr/bin/env python3
"""Pre-delivery gate. Nothing ships until this has been read, not just run.

Machine checks catch what machines can catch. The last section of this script
builds contact sheets precisely because they cannot: a previous pass shipped
two pure green frames, five Joe Rogan singles, four Steven Bartlett singles,
nine frames of a MrBeast company executive and a horror-film clip of a woman
chained to a bed, and every one of them passed a machine.

Checks
  1  reuse          no asset drawn twice, across every class
  2  dedupe         no two pieces that look alike, weighted by how close they
                    land in the programme
  3  shot length    nothing over 6s, nothing under 1.15s
  4  freeze         measured pixel delta, NOT freezedetect - at -60dB that
                    flags a slow Ken Burns on a photograph. Calibrated:
                    a genuine frozen slate measured 0.23, real shots 39-71,
                    and a rendered card on flat ground needs ~34% push to
                    register at all
  5  black          blackdetect over the final file
  6  sync           |picture - audio| within a quarter of a second
  7  subject mix    how much of the film is actually him
  8  contact sheets one frame per shot, big enough to see a face
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import fx                                                        # noqa: E402

SUFFIX = os.environ.get("BUILD_SUFFIX", "V8")
WORK = ROOT / f"work/picture_{SUFFIX.lower()}"
SHOTS = ROOT / f"manifest/picture_{SUFFIX.lower()}_shots.json"
FILM = ROOT / f"final_video/THE_DISEASE_THAT_BUILT_MRBEAST_{SUFFIX}.mp4"
AUDIO = ROOT / "final_video/mrbeast_audio_v6/MRBEAST_V6_STORY_MASTER.wav"
QCDIR = ROOT / f"work/qc_{SUFFIX.lower()}"
REPORT = ROOT / f"dossier/mrbeast/QC_{SUFFIX}.md"
FONT = "graphics/public/fonts/Anton-Regular.ttf"

# Same calibration as the builder - see work/_hash_calib.py.
HASH_W, HASH_H = 17, 16
# Measured on the RENDERED pieces over 625 same-source pairs: min 9, p1 15,
# p5 20, median 57, against cross-source min 45. Two shots of one man in one
# room will always be close, so proximity is reported for the eye to judge and
# only a pair below the same-set minimum is treated as a failure. The top ten
# closest pairs were viewed side by side (work/_pairs_check.py) and judged to
# be genuinely different gestures at the same framing - which is why the
# builder now varies the punch per shot.
DUPE_NEAR, DUPE_WINDOW, DUPE_HARD = 20, 150.0, 8
MAX_SHOT, MIN_SHOT = 6.0, 1.15
FREEZE_FLOOR = 1.2       # mean |delta| on 64x36 gray below this = suspect
SUBJECT = {"footage"}    # kinds that put Jimmy on screen


def frames_of(p: Path, at: list[float]) -> list[np.ndarray]:
    out = []
    for t in at:
        r = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}",
             "-i", str(p), "-frames:v", "1", "-vf", "scale=64:36,format=gray",
             "-f", "rawvideo", "-"], capture_output=True, timeout=300).stdout
        if len(r) >= 64 * 36:
            out.append(np.frombuffer(r[:64 * 36], dtype=np.uint8)
                       .reshape(36, 64).astype(np.int16))
    return out


def dhash_of(p: Path, t: float) -> np.ndarray | None:
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}",
         "-i", str(p), "-frames:v", "1", "-vf",
         f"scale={HASH_W}:{HASH_H},format=gray",
         "-f", "rawvideo", "-"], capture_output=True, timeout=300).stdout
    n = HASH_W * HASH_H
    if len(r) < n:
        return None
    g = np.frombuffer(r[:n], dtype=np.uint8).reshape(
        HASH_H, HASH_W).astype(np.int16)
    return (g[:, 1:] > g[:, :-1]).flatten()


def main() -> int:
    QCDIR.mkdir(parents=True, exist_ok=True)
    shots = json.loads(SHOTS.read_text(encoding="utf-8"))
    lines: list[str] = []
    fails: list[str] = []

    def say(s=""):
        print(s, flush=True)
        lines.append(s)

    say(f"# QC — {SUFFIX}\n")
    say(f"{len(shots)} shots. Film: `{FILM.name}`\n")

    # 1 -------------------------------------------------------------- reuse
    say("## 1. Reuse")
    seen: dict[str, str] = {}
    dupes = []
    for s in shots:
        a = s.get("asset") or f"{s['spec'][0]}:{s['spec'][1] if len(s['spec'])>1 else ''}"
        if not a:
            continue
        if a in seen:
            dupes.append(f"`{a}` at {s['prog_start']:.2f}s and {seen[a]}")
        seen[a] = f"{s['prog_start']:.2f}s"
    if dupes:
        fails.append(f"{len(dupes)} assets reused")
        for d in dupes:
            say(f"- REUSED {d}")
    else:
        say(f"- OK: {len(seen)} distinct assets, none drawn twice")

    # 3 -------------------------------------------------------- shot length
    say("\n## 2. Shot length")
    bad = [s for s in shots
           if s["dur"] > MAX_SHOT + 0.02 or s["dur"] < MIN_SHOT - 0.02]
    if bad:
        fails.append(f"{len(bad)} shots out of range")
        for s in bad:
            say(f"- {s['name']} {s['dur']:.2f}s")
    else:
        d = [s["dur"] for s in shots]
        say(f"- OK: {min(d):.2f}-{max(d):.2f}s, median "
            f"{np.median(d):.2f}s, mean {np.mean(d):.2f}s")

    # 2/4 --------------------------------------------- dedupe + freeze scan
    say("\n## 3. Look-alikes and frozen shots")
    hashes, frozen = [], []
    for s in shots:
        p = WORK / f"{s['name']}.mp4"
        if not p.exists():
            fails.append(f"missing piece {s['name']}")
            continue
        dur = s["dur"]
        h = dhash_of(p, dur * 0.5)
        if h is not None:
            for ot, on, oh in hashes:
                dd = int(np.count_nonzero(h != oh))
                near = abs(s["prog_start"] - ot) < DUPE_WINDOW
                if dd < DUPE_HARD:
                    fails.append(f"same picture {s['name']} vs {on}")
                    say(f"- SAME PICTURE {s['name']} "
                        f"({s['prog_start']:.1f}s) vs {on} ({ot:.1f}s) "
                        f"hamming {dd}  <-- FAILURE")
                elif dd < DUPE_NEAR and near:
                    say(f"- close {s['name']} ({s['prog_start']:.1f}s) vs "
                        f"{on} ({ot:.1f}s) hamming {dd} - same set, judge "
                        f"by eye")
            hashes.append((s["prog_start"], s["name"], h))
        fr = frames_of(p, [dur * 0.2, dur * 0.5, dur * 0.8])
        if len(fr) >= 2:
            deltas = [float(np.abs(a - b).mean())
                      for a, b in zip(fr, fr[1:])]
            if max(deltas) < FREEZE_FLOOR:
                frozen.append((s["name"], max(deltas), s["kind"]))
    if frozen:
        say(f"- {len(frozen)} shots measure as static "
            f"(cards on flat ground can legitimately read low):")
        for n, d, k in frozen:
            say(f"  - {n} ({k}) delta {d:.2f}")
    else:
        say("- OK: no static shots")

    # 7 ---------------------------------------------------------- what mix
    say("\n## 4. What is on screen")
    mix = Counter(s["kind"] for s in shots)
    tot = sum(s["dur"] for s in shots)
    for k, n in mix.most_common():
        secs = sum(s["dur"] for s in shots if s["kind"] == k)
        say(f"- {k:8} {n:3d} shots  {secs:6.1f}s  {secs/tot*100:4.1f}%")
    him = sum(s["dur"] for s in shots if s["kind"] in SUBJECT)
    say(f"\n- **Jimmy on screen: {him:.1f}s of {tot:.1f}s "
        f"({him/tot*100:.1f}%)**")

    # 5/6 --------------------------------------------------- the final file
    if FILM.exists():
        say("\n## 5. The assembled film")
        vdur, adur = fx.probe_dur(FILM), fx.probe_dur(AUDIO)
        say(f"- duration {vdur:.3f}s vs audio {adur:.3f}s "
            f"(delta {vdur-adur:+.3f}s)")
        if abs(vdur - adur) > 0.25:
            fails.append("A/V duration mismatch")
        r = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats", "-i", str(FILM), "-an",
             "-vf", "blackdetect=d=0.5:pic_th=0.98", "-f", "null", "NUL"],
            capture_output=True, text=True, timeout=7200)
        blacks = [ln for ln in (r.stderr or "").splitlines()
                  if "black_start" in ln]
        if blacks:
            fails.append(f"{len(blacks)} black stretches")
            for b in blacks[:8]:
                say(f"- BLACK {b.strip()}")
        else:
            say("- OK: no black stretches over 0.5s")
    else:
        say("\n## 5. The assembled film\n- not built yet")

    # 8 ------------------------------------------------------ contact sheets
    say("\n## 6. Contact sheets for the eyes-on pass")
    for old in QCDIR.glob("sheet_*.jpg"):
        old.unlink()
    per, cols = 6, 3
    made = 0
    for page in range(0, len(shots), per):
        grp = shots[page:page + per]
        ins, sc = [], []
        for i, s in enumerate(grp):
            p = WORK / f"{s['name']}.mp4"
            if not p.exists():
                continue
            ins += ["-ss", f"{s['dur']*0.5:.3f}", "-i", str(p)]
            asset = (s.get("asset") or "")
            asset = asset.split("/")[-1][:26]
            lab = (f"{s['prog_start']:.0f}s {s['kind']}"
                   f"{(' ' + asset) if asset else ''}")
            j = len(sc)
            sc.append(
                f"[{j}:v]scale=480:270,drawbox=x=0:y=238:w=480:h=32"
                f":color=black@0.78:t=fill,"
                f"drawtext=fontfile='{FONT}':text='{lab}'"
                f":fontcolor=#FFE04D:fontsize=21:x=6:y=241[a{j}]")
        if not sc:
            continue
        n = len(sc)
        out = QCDIR / f"sheet_{page//per:03d}.jpg"
        if n == 1:
            # xstack requires at least two inputs, so a final page holding one
            # shot crashed the whole sheet step and silently lost that shot
            # from the eyes-on pass - the one place it must not be lost.
            fc = sc[0]
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *ins,
                 "-filter_complex", fc, "-map", "[a0]",
                 "-frames:v", "1", "-q:v", "3", str(out)],
                check=False, timeout=900)
            if out.exists():
                made += 1
            continue
        lay = "|".join(f"{(i % cols)*480}_{(i//cols)*270}" for i in range(n))
        lb = "".join(f"[a{i}]" for i in range(n))
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *ins,
             "-filter_complex",
             f"{';'.join(sc)};{lb}xstack=inputs={n}:layout={lay}"
             + (":fill=black" if n < cols * 2 else ""),
             "-frames:v", "1", "-q:v", "3", str(out)],
            check=False, timeout=900)
        if out.exists():
            made += 1
    say(f"- {made} sheets in `{QCDIR}` — READ THEM. "
        f"Every failure this project has shipped passed the machine checks.")

    say("\n## Verdict")
    if fails:
        say(f"**{len(fails)} machine failures:**")
        for f in fails[:30]:
            say(f"- {f}")
    else:
        say("**Machine checks clean.** The eyes-on pass is still required.")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n[OK] {REPORT}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
