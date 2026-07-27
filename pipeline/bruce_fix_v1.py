#!/usr/bin/env python3
"""bruce_fix_v1.py - fixes from the piece contact-sheet review.

- TypeOn quote cards were tiny search pills -> variant: quote (big type)
- FOOD=FUEL had 6 tiles (overflows 1920) -> 4
- b_072 typescript title page too sparse -> dense p3
- b_074 window caught the Way of the Dragon kitten cutaway -> shift
- window dedupes: b_009 span b_010, b_019, b_027, b_032, b_038, b_086,
  b_088, b_093
"""
import base64
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "manifest"
DOS = ROOT / "dossier" / "bruce_lee"
REF = ROOT / "library" / "bruce_refs"
FOOD = ROOT / "library" / "food"
WORK = ROOT / "final_video" / "v5_work"

A = json.loads((MAN / "assets_v5.json").read_text())
order = sorted(A)
changed = set()


def durl(p):
    p = Path(p)
    mime = "image/png" if p.suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def rewindow(bid, src, t0, t1, crop):
    need_loop = A[bid].get("loop", False)
    A[bid].update({"src": str(DOS / f"{src}.mp4"), "t0": t0, "t1": t1,
                   "vid": f"{src}@{t0}", "crop_box": crop})
    changed.add(bid)


CB = {"2yp-O580Ru0": [0.03, 0.15, 0.03, 0.15],
      "EP8yIiZD_os": [0.02, 0.14, 0.02, 0.14],
      "YHHQF1SHHLw": [0.125, 0.14, 0.125, 0.11],
      "-OI1zyajOpw": [0.12, 0.0, 0.12, 0.0]}

# 1. TypeOn -> quote variant
for bid, a in A.items():
    if a.get("type") == "v5card" and a.get("comp") == "TypeOn":
        a["props"]["variant"] = "quote"
        changed.add(bid)

# 2. FOOD=FUEL -> 4 tiles
for bid, a in A.items():
    if a.get("type") == "v5card" and \
            a.get("props", {}).get("title") == "FOOD = FUEL":
        a["props"]["tiles"] = [
            {"src": durl(FOOD / "rice.jpg"), "label": "Rice", "atMs": 300},
            {"src": durl(FOOD / "greens.jpg"), "label": "Vegetables",
             "atMs": 900},
            {"src": durl(FOOD / "salmon.jpg"), "label": "Fish",
             "atMs": 1500},
            {"src": durl(FOOD / "beef.jpg"), "label": "Beef",
             "atMs": 2100}]
        changed.add(bid)

# 3. b_072: dense typescript page instead of sparse title page
A["b_072"]["props"]["src"] = durl(REF / "doc_jkd_manuscript_p3.png")
A["b_072"]["props"]["panFrom"] = 0.1
A["b_072"]["props"]["panTo"] = 0.5
changed.add("b_072")

# 4-11. window fixes
rewindow("b_074", "-OI1zyajOpw", 74.5, 85.0, CB["-OI1zyajOpw"])
rewindow("b_086", "-OI1zyajOpw", 92.0, 107.0, CB["-OI1zyajOpw"])
rewindow("b_019", "2yp-O580Ru0", 561.0, 660.0, CB["2yp-O580Ru0"])
rewindow("b_032", "2yp-O580Ru0", 1381.0, 1435.0, CB["2yp-O580Ru0"])
rewindow("b_038", "EP8yIiZD_os", 88.0, 110.0, CB["EP8yIiZD_os"])
rewindow("b_027", "YHHQF1SHHLw", 350.0, 380.0, CB["YHHQF1SHHLw"])
rewindow("b_088", "2yp-O580Ru0", 1900.0, 1945.0, CB["2yp-O580Ru0"])
rewindow("b_093", "EP8yIiZD_os", 440.0, 465.0, CB["EP8yIiZD_os"])

# 9. b_009 spans b_010 (kills the ods@65 dupe at b_010)
A["b_009"]["span_until"] = "b_010"
A["b_010"] = {"type": "spanned"}
changed.add("b_009")
changed.add("b_010")

json.dump(A, open(MAN / "assets_v5.json", "w"), indent=1)

for bid in changed:
    p = WORK / f"p_{order.index(bid):03d}_{bid}.mp4"
    if p.exists():
        p.unlink()
bundle = WORK / "remotion_bundle"
if bundle.exists():
    shutil.rmtree(bundle)      # TypeOn changed
print(f"[OK] {len(changed)} beats patched, pieces invalidated")
