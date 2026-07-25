#!/usr/bin/env python3
"""v6_remap.py - semantic card re-assignment + OCR-aligned site highlights.

Replaces V5's 15 identical BarsRise cards with per-meaning designs
(max 2 uses per design, never adjacent), varies IconBurst layouts, and
snaps the SiteZoom yellow highlight to the exact text line via RapidOCR
on the screenshot. Purges affected pieces for re-render.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "manifest"

a5 = json.loads((MAN / "assets_v5.json").read_text())

# semantic re-map for every former stat/graphic beat
SEMANTIC = {
 "b_010": ("PlateCounter", {"display": "6'2\"", "title": "The frame",
                            "sub": "Ryan Reynolds - height"}),
 "b_019": ("DonutGauge", {"pct": 90, "title": '"Diet is 90% of the battle"',
                          "sub": "- Ryan Reynolds"}),
 "b_027": ("RangeSplit", {"left": "3-5", "right": "6-12",
                          "leftSub": "sets", "rightSub": "reps",
                          "title": "Monday - working ranges"}),
 "b_040": ("BigCounter", {"from": 0, "to": 25, "suffix": " min",
                          "title": "Post-lift HIIT",
                          "sub": "sprints - bike - prowler"}),
 "b_055": ("ClockRing", {"fromH": 0, "toH": 1,
                         "title": "Steady-state option: 45-60 min"}),
 "b_060": ("RangeSplit", {"left": "3-5", "right": "6-15",
                          "leftSub": "sets", "rightSub": "reps",
                          "title": "Every exercise"}),
 "b_064": ("MacroApp", {}),
 "b_065": ("GramsBar", {"icon": "🍗", "display": "200-250 g",
                        "title": "Protein / day", "frac": 0.9}),
 "b_066": ("GramsBar", {"icon": "🍚", "display": "150-300 g",
                        "title": "Carbs / day - cycled", "frac": 0.65}),
 "b_067": ("GramsBar", {"icon": "🥑", "display": "70-100 g",
                        "title": "Fats / day", "frac": 0.4}),
 "b_080": ("TicketStub", {"big": "1 CHEAT MEAL", "small":
                          "every 7-14 days - meals, not days",
                          "title": "The release valve"}),
 "b_085": ("ClockRing", {"fromH": 7, "toH": 9,
                         "title": "Recovery is trained too"}),
 "b_088": ("CalendarGrid", {"activeDays": 5,
                            "title": "The realistic split"}),
 "b_089": ("StepsRing", {"display": "10,000",
                         "title": "Or just move"}),
 "b_090": ("GramsBar", {"icon": "💪", "display": "0.8-1 g / lb",
                        "title": "Protein - realistic version",
                        "frac": 0.85}),
 "b_092": ("BigCounter", {"from": 0, "to": 3000, "suffix": "+",
                          "title": "The overeating trap",
                          "sub": "calories without the volume"}),
 "b_094": ("RangeSplit", {"left": "8 wks", "right": "8 mo",
                          "leftSub": "what people expect",
                          "rightSub": "what it takes",
                          "title": "Movie-star timing"}),
 "b_013": ("YearsTimeline", {"years": [
     {"y": "2008", "label": "meets Don Saladino"},
     {"y": "2016", "label": "Deadpool"},
     {"y": "2018", "label": "Deadpool 2"},
     {"y": "2024", "label": "D&W - still training"}],
     "title": "15+ years, one coach"}),
}

# IconBurst variety: alternate center icons per section so lists differ
CENTER = {"b_023": "📅", "b_026": "🏋️", "b_028": "🔗", "b_030": "🔥",
          "b_036": "🧱", "b_043": "🤸", "b_049": "⚡", "b_052": "🥊",
          "b_069": "☕", "b_071": "🍳", "b_072": "🍗", "b_073": "🐟",
          "b_077": "🥗", "b_078": "🔄", "b_083": "🏃", "b_096": "🏆"}

purge = []
for bid, (comp, props) in SEMANTIC.items():
    if bid in a5:
        a5[bid] = {"type": "v5card", "comp": comp, "props": props}
        purge.append(bid)
for bid, icon in CENTER.items():
    if bid in a5 and a5[bid].get("comp") == "IconBurst":
        a5[bid]["props"]["center"] = icon
        purge.append(bid)

# adjacency check on card designs
order = sorted(a5)
prev = None
for bid in order:
    a = a5[bid]
    cur = a.get("comp") if a["type"] == "v5card" else None
    if cur and cur == prev and cur not in ("IconBurst",):
        print(f"[warn] adjacent same design at {bid}: {cur}")
    prev = cur

# OCR-align the Saladino SiteZoom highlight to the exact '(9 weeks, $99)' line
try:
    from rapidocr_onnxruntime import RapidOCR
    import cv2
    img_path = ROOT / "library" / "sites" / "saladino_programs.png"
    img = cv2.imread(str(img_path))
    H, W = img.shape[:2]
    res, _ = RapidOCR()(img)
    best = None
    for box, text, conf in (res or []):
        if "9 weeks" in text or "$99" in text:
            xs = [p[0] for p in box]; ys = [p[1] for p in box]
            best = {"x": min(xs) / W * 100, "y": min(ys) / H * 100,
                    "w": (max(xs) - min(xs)) / W * 100,
                    "h": (max(ys) - min(ys)) / H * 100 + 0.4}
            print(f"[OCR] highlight line found: '{text[:60]}' -> {best}")
            break
    if best and "b_004" in a5 and a5["b_004"].get("comp") == "SiteZoom":
        a5["b_004"]["props"]["highlightRect"] = best
        # zoom focus onto the highlight line
        a5["b_004"]["props"]["focusY"] = min(best["y"] / 100 + 0.02, 0.9)
        purge.append("b_004")
except Exception as e:
    print(f"[warn] OCR align failed: {e}")

json.dump(a5, open(MAN / "assets_v5.json", "w"), indent=1)
n = 0
for bid in set(purge):
    idx = order.index(bid)
    p = ROOT / "final_video" / "v5_work" / f"p_{idx:03d}_{bid}.mp4"
    if p.exists():
        p.unlink()
        n += 1
print(f"[OK] {len(SEMANTIC)} semantic remaps, {len(CENTER)} icon varieties, "
      f"{n} pieces purged")
