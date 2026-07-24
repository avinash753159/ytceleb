#!/usr/bin/env python3
"""
apply_audit.py - apply the adversarial shot-relevance audit to assets.json.

In:  scratchpad audit.json  {verdicts:[{beat_id,img,match,why}...]}
Logic:
  * every scene judged 0 anywhere is blacklisted; a SOURCE is blacklisted
    when a 0-verdict cites watermark/text/logo/sign (burned branding is
    source-wide, not scene-specific)
  * flagged beats get the next-best clean candidate from the embedding
    index (skipping blacklists and the 90s reuse rule); if none clears the
    floor, the beat falls back to still_pushin (stills are always
    acceptable; wrong video never is)
  * beats > 12s (music tail) get ceil(dur/5) distinct shots, all <= 6s
Out: updated manifest/assets.json + manifest/swap_report.json, and
     purges the affected piece_*.mp4 so assemble re-renders only them.

Run:  py -3.12 pipeline/apply_audit.py <audit.json>
"""
import json
import math
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest"
WORK = ROOT / "final_video" / "v2_work"
sys.path.insert(0, str(ROOT / "pipeline"))

TEXTY = re.compile(r"watermark|text|logo|sign|graphic|card|caption|burned",
                   re.I)
FLOOR = 0.04


def main():
    audit = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    verdicts = audit["verdicts"]
    assets = json.loads((MANIFEST / "assets.json").read_text())
    plan = {p["beat_id"]: p for p in
            json.loads((MANIFEST / "plan.json").read_text())["plan"]}
    beats = {b["beat_id"]: b for b in
             json.loads((MANIFEST / "beats.json").read_text())["beats"]}

    # scene id per verdict img (clip2 imgs end _a/_b)
    def scenes_of(bid):
        a = (assets[bid].get("asset") or {})
        if a.get("kind") == "clip":
            return {"": a["id"]}
        if a.get("kind") == "clip2":
            return {"_a": a["a"]["id"], "_b": a["b"]["id"]}
        if a.get("kind") == "clips":
            return {f"_{i}": c["id"] for i, c in enumerate(a["list"])}
        return {}

    black_scenes, black_sources, flagged = set(), set(), {}
    for v in verdicts:
        if v["match"] != 0:
            continue
        bid = v["beat_id"]
        flagged.setdefault(bid, []).append(v["why"])
        stem = Path(v["img"]).stem            # e.g. b_040_a
        suf = stem[len(bid):]                 # "", "_a", "_b"
        sid = scenes_of(bid).get(suf)
        if sid:
            black_scenes.add(sid)
            if TEXTY.search(v["why"]):
                black_sources.add(sid.split("|")[0])

    print(f"[*] flagged beats: {len(flagged)} | blacklisted scenes: "
          f"{len(black_scenes)} | blacklisted sources: "
          f"{sorted(black_sources)}")

    import embed_index
    from fetch_stills import fetch_still

    # rebuild reuse map from unflagged beats
    used = {}
    for bid, a in assets.items():
        ass = a.get("asset") or {}
        for sid in scenes_of(bid).values():
            if bid not in flagged:
                used[sid] = beats[bid]["end"]

    def ok(c, b):
        if c["id"] in black_scenes or c["source"] in black_sources:
            return False
        if c["dur"] < 1.2 or c["score"] < FLOOR:
            return False
        last = used.get(c["id"])
        return last is None or abs(b["start"] - last) >= 90

    report, purge = [], []
    # also re-shape any surviving beat with shots > 6s (the music tail)
    for bid, a in assets.items():
        ass = a.get("asset") or {}
        b = beats[bid]
        dur = b["end"] - b["start"]
        needs_reshape = (ass.get("kind") == "clip2" and dur > 12)
        if bid not in flagged and not needs_reshape:
            continue
        p = plan[bid]
        query = p.get("retrieval_query", "") or b["text"][:80]
        cands = [c for c in embed_index.query(query, 40) if ok(c, b)]
        n_shots = max(1, math.ceil(dur / 5.0)) if dur > 6 else 1
        if len(cands) >= n_shots:
            picks = cands[:n_shots]
            for c in picks:
                used[c["id"]] = b["end"]
            if n_shots == 1:
                a["asset"] = {"kind": "clip", **picks[0]}
            else:
                a["asset"] = {"kind": "clips", "list": picks}
            a["treatment"] = a["treatment"] if a["treatment"] in (
                "motion_broll", "exercise_demo") else "motion_broll"
            a["audit"] = "swapped"
            report.append({"beat_id": bid, "action": "swap",
                           "new": [c["id"] for c in picks],
                           "why": flagged.get(bid, ["reshape>12s"])[:1]})
        else:
            s = fetch_still(query, bid + "_audit")
            if s:
                a["treatment"] = "still_pushin"
                a["asset"] = {"kind": "still", **s}
                a["audit"] = "fallback_still"
                report.append({"beat_id": bid, "action": "fallback_still",
                               "why": flagged.get(bid, [""])[:1]})
            else:
                a["audit"] = "UNRESOLVED"
                report.append({"beat_id": bid, "action": "UNRESOLVED"})
        # purge the piece so assemble re-renders it
        idx = int(bid.split("_")[1])
        for f in WORK.glob(f"piece_{idx:03d}_{bid}*.mp4"):
            f.unlink(missing_ok=True)
            purge.append(f.name)
        for f in (WORK / f"u_{bid}.mp4", WORK / f"h1_{bid}.mp4",
                  WORK / f"h2_{bid}.mp4", WORK / f"cc_{bid}.txt"):
            if f.exists():
                f.unlink()

    (MANIFEST / "assets.json").write_text(json.dumps(assets, indent=1),
                                          encoding="utf-8")
    (MANIFEST / "swap_report.json").write_text(json.dumps(report, indent=1),
                                               encoding="utf-8")
    unres = sum(1 for r in report if r["action"] == "UNRESOLVED")
    print(f"[OK] {len(report)} beats updated ({unres} unresolved), "
          f"{len(purge)} pieces purged")
    return 1 if unres else 0


if __name__ == "__main__":
    raise SystemExit(main())
