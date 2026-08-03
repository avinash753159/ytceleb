#!/usr/bin/env python3
"""Merge the eyes-on identity verdicts into the pool and the sync windows.

Verdicts arrive as `manifest/verdicts_*.json` - one file per reviewer, so two
reviewers can never race on the same file - and are matched on the stable
`sid@t0` key. The old verify_pool.py hard-coded *sheet indices*, so adding a
source silently re-pointed every verdict at a different frame.

A window is drawable only if BOTH gates pass:
  verified_jimmy is true  AND  has_text is false
Identity and cleanliness are independent failures and both are disqualifying.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAN = ROOT / "manifest"
POOL = MAN / "jimmy_pool2.json"
BITES = MAN / "bite_windows.json"

# Windows a reviewer trimmed by hand after finding contamination partway
# through. seg71 is the film's closing line - the panel enters at 5418.2, so
# the shot has to end before it.
TRIMMED = [
    {"seg": 71, "source": "cLRLEnPaJLM", "t0": 5415.70, "run_end": 5417.90,
     "usable": 2.20, "verified_jimmy": True, "has_text": False,
     "reason": "seg71 'it's just life' - hand-trimmed to end before the "
               "screen-share panel enters at 5418.2 (frame strip verified)"},
]

# Windows where the OCR text screen fired on something a human has looked at
# and judged to be part of the room rather than an overlay. The screen stays
# strict by default; every entry here is a recorded decision with a reason.
TEXT_OVERRIDE = {
    "9IQ_ldV9z_A@760.68":
        "OCR read 'DEEZ NUTZ' - it is a Feastables bar standing on the desk "
        "beside a water bottle, i.e. a physical prop in the interview set and "
        "his own brand, not burned-in third-party text. It is on the desk in "
        "essentially every frame of this source, so rejecting on it would "
        "delete the whole Colin & Samir 2023 interview including six sync "
        "windows. Frames checked at 761.5 / 763.0 / 765.0.",
}

# The pool's credit label said '2013 ARCHIVE'. Both archive videos carry his
# own on-screen date - 'Today Is October 4th, 2015' - and a Windows taskbar
# clock reading 10/4/2015. Shipping 2013 would have been a false date on
# screen.
CREDIT_FIX = {
    "AKJfakEsgy0": ("MRBEAST", "HI ME IN 5 YEARS / 4 OCTOBER 2015"),
    "F0OkwXKcPSE": ("MRBEAST", "HI ME IN 10 YEARS / 4 OCTOBER 2015"),
}


def load_verdicts() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in sorted(MAN.glob("verdicts_*.json")):
        try:
            rows = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"[skip] {p.name}: {e}")
            continue
        n = 0
        for r in rows:
            k = r.get("key")
            if not k or "verified_jimmy" not in r:
                continue
            if k in out and out[k]["verified_jimmy"] != r["verified_jimmy"]:
                print(f"[conflict] {k}: {out[k]['file']} says "
                      f"{out[k]['verified_jimmy']}, {p.name} says "
                      f"{r['verified_jimmy']} - taking the REJECT")
                if not r["verified_jimmy"]:
                    out[k] = {**r, "file": p.name}
                continue
            out[k] = {**r, "file": p.name}
            n += 1
        print(f"[verdicts] {p.name}: {n}")
    return out


def main() -> int:
    v = load_verdicts()
    print(f"[verdicts] {len(v)} unique keys\n")

    pool = json.loads(POOL.read_text(encoding="utf-8"))
    hits = 0
    for e in pool:
        if e["key"] in TEXT_OVERRIDE and e.get("has_text"):
            e["has_text"] = False
            e["text_override"] = TEXT_OVERRIDE[e["key"]]
            print(f"[override] {e['key']} text verdict cleared by review")
        if e["source"] in CREDIT_FIX:
            e["credit_main"], e["credit_sub"] = CREDIT_FIX[e["source"]]
        r = v.get(e["key"])
        if r:
            e["verified_jimmy"] = bool(r["verified_jimmy"])
            e["verdict_reason"] = r.get("reason", "")
            e["verdict_by"] = r.get("file", "")
            hits += 1
    POOL.write_text(json.dumps(pool, indent=2), encoding="utf-8")

    ok = [e for e in pool
          if e.get("verified_jimmy") and not e.get("has_text")]
    id_bad = [e for e in pool if e.get("verified_jimmy") is False]
    txt_bad = [e for e in pool if e.get("verified_jimmy") and e.get("has_text")]
    unjudged = [e for e in pool if e.get("verified_jimmy") is None]
    print(f"POOL  {len(pool)} candidates, {hits} judged")
    print(f"      DRAWABLE          {len(ok)}")
    print(f"      rejected on identity {len(id_bad)}")
    print(f"      rejected on burned-in text {len(txt_bad)}")
    print(f"      STILL UNJUDGED    {len(unjudged)}")
    for k, n in sorted(Counter(e["source"] for e in ok).items()):
        print(f"        {k:14} {n}")
    if unjudged:
        print("      unjudged keys:",
              ", ".join(e["key"] for e in unjudged[:12]),
              "..." if len(unjudged) > 12 else "")

    bites = json.loads(BITES.read_text(encoding="utf-8"))
    for r in bites:
        for w in r["runs"]:
            if w["key"] in TEXT_OVERRIDE and w.get("has_text"):
                w["has_text"] = False
                w["text_override"] = TEXT_OVERRIDE[w["key"]]
                print(f"[override] {w['key']} text verdict cleared by review")
            d = v.get(w["key"])
            if d:
                w["verified_jimmy"] = bool(d["verified_jimmy"])
                w["verdict_reason"] = d.get("reason", "")
        for t in TRIMMED:
            if t["seg"] == r["i"] and not any(
                    abs(w["t0"] - t["t0"]) < 0.01 for w in r["runs"]):
                r["runs"].append({
                    "key": f"{t['source']}@{t['t0']:.2f}", "t0": t["t0"],
                    "run_end": t["run_end"], "usable": t["usable"],
                    "thumb": "", "verified_jimmy": True, "has_text": False,
                    "verdict_reason": t["reason"], "hand_trimmed": True})
    BITES.write_text(json.dumps(bites, indent=2), encoding="utf-8")

    print("\nSYNC WINDOWS per bite (drawable = identity ok AND no text):")
    nosync = []
    for r in bites:
        good = [w for w in r["runs"]
                if w.get("verified_jimmy") and not w.get("has_text")]
        tag = "" if good else "   <-- NO SYNC, needs illustrative picture"
        print(f"  seg{r['i']:3d} {r['prog_start']:7.2f} {r['dur']:5.2f}s "
              f"{r['source']:12} {len(good)}/{len(r['runs'])} usable{tag}")
        if not good:
            nosync.append(r["i"])
    print(f"\nbites with no usable sync window: {nosync}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
