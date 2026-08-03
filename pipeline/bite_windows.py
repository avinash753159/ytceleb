#!/usr/bin/env python3
"""Find the picture that belongs to each BITE - the actual moment, in sync.

A bite is Jimmy's own voice, lifted from an interview. The honest picture over
it is him saying it, at that timecode, in that room. Everything else is a
cutaway pretending to be sync.

The catch is that a 22-second bite spans several of the podcast's own camera
cuts, so a single window lands half on Jimmy and half on the host - which is
exactly how Joe Rogan and Steven Bartlett got into a film they are banned
from. So: enumerate the uninterrupted runs INSIDE each bite's own span, keep
the ones long enough to hold a shot, and put every one in front of a human.

Bites sourced from 7r3ORKgNUjw are Airrack's video. Twelve windows there were
frame-checked in an earlier session and not one is Jimmy alone, so those
bites get illustrative picture instead of sync - the audio stays, the video
never shows him.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "dossier/mrbeast/sources"
WORK = ROOT / "work/bite_windows"
CUTS = ROOT / "work/jimmy_pool2"
EDL = ROOT / "manifest/edl_full.json"
BITES = ROOT / "manifest/mrbeast_soundbites.json"
OUT = ROOT / "manifest/bite_windows.json"
FONT = "graphics/public/fonts/Anton-Regular.ttf"

BANNED_SOURCES = {"7r3ORKgNUjw", "WwVs1qVaOb4"}
MIN_RUN = 2.6
MAX_SHOT = 6.0
# See jimmy_pool2.py - these are calibrated on labelled frames. A red-curtain
# podcast single is max-channel 0.53 and a dark one is luma std 13.7, so the
# first guess (14.0 / 0.42) silently discarded all eight Rogan bites.
FLAT_STD = 6.0
CHROMA_MAX = 0.72

CREDIT = {
    "cLRLEnPaJLM": ("POWERFULJRE", "JOE ROGAN EXPERIENCE #1788"),
    "FjrJ2DJN_pA": ("THE DIARY OF A CEO", "YOUTUBE"),
    "9IQ_ldV9z_A": ("COLIN AND SAMIR", "YOUTUBE / JUNE 2023"),
    "c8VcUnz3nVc": ("COLIN AND SAMIR", "THE FULL STORY OF MRBEAST"),
}


def cuts_for(sid: str) -> list[float]:
    for p in (CUTS / f"{sid}_cuts.json",
              ROOT / "work/jimmy_pool" / f"{sid}_cuts.json"):
        if p.exists():
            return json.loads(p.read_text())
    raise FileNotFoundError(f"no cut scan for {sid}: run jimmy_pool2.py")


def degenerate(arr: np.ndarray) -> str | None:
    g = np.asarray(Image.fromarray(arr).convert("L"), dtype=np.float32)
    if float(g.std()) < FLAT_STD:
        return f"flat ({g.std():.1f})"
    f = arr.astype(np.float32) + 1.0
    share = f.sum(axis=(0, 1)) / f.sum()
    if float(share.max()) > CHROMA_MAX:
        return f"single-channel ({'RGB'[int(share.argmax())]})"
    return None


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    edl = json.loads(EDL.read_text(encoding="utf-8"))
    bank = {b["id"]: b for b in json.loads(BITES.read_text(encoding="utf-8"))}

    rows = []
    for seg in edl["segs"]:
        if seg["kind"] != "bite":
            continue
        sid = seg["source"]
        bid = (seg.get("seg_id") or "").split("_", 1)[-1]
        b = bank.get(bid)
        # The bite's in-point in the source, and how much of it the edit uses.
        t0 = seg.get("src_t0")
        if t0 is None and b:
            t0 = b["t0"]
        t1 = t0 + seg["dur"]
        rec = {"i": seg["i"], "prog_start": seg["start"],
               "prog_end": seg["end"], "dur": seg["dur"], "source": sid,
               "bite_id": bid, "src_t0": round(t0, 2), "src_t1": round(t1, 2),
               "chapter": seg["chapter"], "text": seg["text"],
               "sync_possible": sid not in BANNED_SOURCES, "runs": []}
        if sid in BANNED_SOURCES:
            rec["note"] = ("Airrack's video - no Jimmy-only window exists; "
                           "this bite gets illustrative picture")
            rows.append(rec)
            continue

        # Uninterrupted runs inside the bite's own span, with a little
        # latitude either side: an edit point 0.4s before the bite starts is
        # still usable picture for it.
        lo, hi = max(0.0, t0 - 1.5), t1 + 1.5
        edges = [lo] + [c for c in cuts_for(sid) if lo < c < hi] + [hi]
        for a, bb in zip(edges, edges[1:]):
            if bb - a < MIN_RUN:
                continue
            st = a + 0.25
            span = min(bb - 0.2, st + MAX_SHOT) - st
            if span < MIN_RUN - 0.3:
                continue
            key = f"{sid}@{st:.2f}"
            tp = WORK / f"{sid}_{st:.0f}.jpg"
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                 "-ss", f"{st + span/2:.2f}", "-i", str(SRC / f"{sid}.mp4"),
                 "-frames:v", "1", "-threads", "1", "-vf", "scale=320:180",
                 str(tp)], check=False, timeout=300)
            if not tp.exists() or tp.stat().st_size == 0:
                continue
            why = degenerate(np.asarray(Image.open(tp).convert("RGB")))
            if why:
                tp.unlink(missing_ok=True)
                continue
            rec["runs"].append({"key": key, "t0": round(st, 2),
                                "run_end": round(bb - 0.2, 2),
                                "usable": round(span, 2), "thumb": tp.name,
                                "verified_jimmy": None})
        rows.append(rec)
        print(f"[{seg['i']:3d}] {seg['prog_start'] if 'prog_start' in seg else seg['start']:7.2f}  "
              f"{sid}  {len(rec['runs'])} runs for {seg['dur']:.1f}s",
              flush=True)

    # Carry forward verdicts already given.
    prior = {}
    if OUT.exists():
        for r in json.loads(OUT.read_text(encoding="utf-8")):
            for w in r.get("runs", []):
                if w.get("verified_jimmy") is not None:
                    prior[w["key"]] = w["verified_jimmy"]
    for r in rows:
        for w in r["runs"]:
            if w["key"] in prior:
                w["verified_jimmy"] = prior[w["key"]]

    OUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    # One contact sheet per source, tiles labelled with the program time the
    # window would sit at, so a verdict can name a window unambiguously.
    todo = [(r, w) for r in rows for w in r["runs"]
            if w["verified_jimmy"] is None]
    by_src: dict[str, list] = {}
    for r, w in todo:
        by_src.setdefault(r["source"], []).append((r, w))
    for sid, items in by_src.items():
        items.sort(key=lambda rw: rw[1]["t0"])
        for page in range(0, len(items), 20):
            grp = items[page:page + 20]
            ins, sc = [], []
            for i, (r, w) in enumerate(grp):
                ins += ["-i", str(WORK / w["thumb"])]
                lab = f"{i+1}  seg{r['i']}  {w['t0']:.0f}s"
                sc.append(f"[{i}:v]scale=320:180,"
                          f"drawbox=x=0:y=156:w=320:h=24:color=black@0.75"
                          f":t=fill,drawtext=fontfile='{FONT}'"
                          f":text='{lab}':fontcolor=#FFE04D:fontsize=18"
                          f":x=6:y=158[a{i}]")
            cols = 5
            lay = "|".join(f"{(i % cols)*320}_{(i//cols)*180}"
                           for i in range(len(grp)))
            lb = "".join(f"[a{i}]" for i in range(len(grp)))
            out = WORK / f"sheet_{sid}_{page//20}.jpg"
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *ins,
                 "-filter_complex",
                 f"{';'.join(sc)};{lb}xstack=inputs={len(grp)}:layout={lay}",
                 "-frames:v", "1", "-q:v", "3", str(out)],
                check=False, timeout=900)
            out.with_suffix(".json").write_text(json.dumps(
                [{"tile": i + 1, "seg": r["i"], "key": w["key"],
                  "t0": w["t0"], "usable": w["usable"]}
                 for i, (r, w) in enumerate(grp)], indent=2),
                encoding="utf-8")
            print(f"[sheet] {out.name}  {len(grp)} tiles", flush=True)

    n = sum(len(r["runs"]) for r in rows)
    nosync = [r["i"] for r in rows if not r["sync_possible"]]
    print(f"\n[OK] {len(rows)} bites, {n} candidate sync windows -> {OUT}")
    print(f"     bites with no sync possible (Airrack): {nosync}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
