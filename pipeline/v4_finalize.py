#!/usr/bin/env python3
"""
v4_finalize.py - apply a section's tournament results to assets.json under
the no-repeat registry rules. Deterministic code, not agent judgment.

In: candidates/<section>/tournament.json
  {beat_id: {ranked: [{kind: scene|image|ytclip, path?, scene?, src?,
                       start?, end?, identity_ok, score, why}, ...]}}
For each beat, walk the ranking; first candidate that passes the registry
(scene unused + <3 uses of source; image not near-duplicate) and has
identity_ok wins. Updates manifest/assets.json:
  scene  -> clip asset (from embed meta)
  ytclip -> clip asset pointing at the downloaded file (whole-file scene)
  image  -> still asset
Registers winners; purges the beat's rendered pieces. Falls back to the
existing asset if nothing passes (reported).

Run: py -3.12 pipeline/v4_finalize.py <section>
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from v4_core import Registry  # noqa: E402

MANIFEST = ROOT / "manifest"


def scene_meta(scene_id):
    meta = json.loads((ROOT / "library" / "shots_meta.json")
                      .read_text(encoding="utf-8"))
    for m in meta:
        if m["id"] == scene_id:
            return m
    return None


def probe(path):
    import subprocess
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of",
                        "default=noprint_wrappers=1:nokey=1", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def main():
    section = sys.argv[1]
    tf = ROOT / "candidates" / section / "tournament.json"
    tour = json.loads(tf.read_text(encoding="utf-8"))
    assets = json.loads((MANIFEST / "assets.json").read_text())
    reg = Registry()
    report = []

    for bid, entry in tour.items():
        chosen = None
        for c in entry.get("ranked", []):
            if not c.get("identity_ok", True):
                continue
            if c["kind"] == "scene":
                sid = c.get("scene", "")
                if reg.scene_ok(sid):
                    m = scene_meta(sid)
                    if m:
                        chosen = ("clip", {"kind": "clip", **m,
                                           "score": c.get("score", 0)})
                        reg.use_scene(sid, bid)
                        break
            elif c["kind"] == "ytclip":
                p = Path(c.get("path", ""))
                if p.exists() and p.stat().st_size > 200_000:
                    dur = probe(p)
                    if dur >= 1.5:
                        sid = f"v4yt_{p.stem}|0"
                        if reg.scene_ok(sid):
                            chosen = ("clip", {"kind": "clip", "id": sid,
                                               "src": str(p),
                                               "source": f"v4yt_{p.stem}",
                                               "scene": 0, "start": 0.1,
                                               "end": dur - 0.1,
                                               "dur": dur - 0.2})
                            reg.use_scene(sid, bid)
                            break
            elif c["kind"] == "image":
                p = Path(c.get("path", ""))
                if p.exists() and p.stat().st_size > 20_000 \
                        and reg.image_ok(p):
                    chosen = ("still", {"kind": "still", "path": str(p),
                                        "source": c.get("src", "v4web"),
                                        "license": c.get("src", "v4web"),
                                        "page": ""})
                    reg.use_image(p, bid)
                    break
        if chosen:
            kind, asset = chosen
            a = assets[bid]
            prev_tr = a["treatment"]
            if kind == "clip" and prev_tr in ("still_pushin",
                                              "split_compare"):
                a["treatment"] = "motion_broll"
            if kind == "still" and prev_tr == "split_compare":
                a["treatment"] = "still_pushin"
            if kind == "still" and prev_tr in ("motion_broll",
                                               "exercise_demo"):
                a["treatment"] = "still_pushin"
            # graphics beats keep treatment; new asset becomes their bg clip
            if prev_tr in ("infographic_list", "stat_callout",
                           "person_card") and kind == "clip":
                (a.get("asset") or {})["bg"] = asset
            else:
                a["asset"] = asset
            a["v4"] = "tournament"
            report.append(f"{bid}: {kind} <- "
                          f"{asset.get('id', asset.get('path', ''))[:60]}")
            idx = int(bid.split("_")[1])
            for f in (ROOT / "final_video" / "v2_work").glob(
                    f"piece_{idx:03d}_{bid}*.mp4"):
                f.unlink()
            uf = ROOT / "final_video" / "v2_work" / f"u_{bid}.mp4"
            if uf.exists():
                uf.unlink()
        else:
            report.append(f"{bid}: KEPT existing (no candidate passed)")

    (MANIFEST / "assets.json").write_text(json.dumps(assets, indent=1),
                                          encoding="utf-8")
    reg.save()
    print("\n".join(report))
    print(f"[OK] {section} finalized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
