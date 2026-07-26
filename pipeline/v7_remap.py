#!/usr/bin/env python3
"""v7_remap.py - V7 changes:
1. Replace most IconBursts with IndexCards/Checklist/PhotoTiles/StepCards
   (keep 3 IconBursts max). Food beats -> PhotoTiles with REAL food photos,
   one tile per named food, word-synced.
2. b_013 -> 3D InstaCard for @donsaladino (real avatar + grid photos).
3. Arrow callouts on era footage beats (composited in assembler via
   manifest/callouts.json).
4. Sentence-snap all interlude windows to caption sentence boundaries.
Purges affected pieces/segments.
"""
import base64
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "manifest"


def durl(p, mime="image/jpeg"):
    return f"data:{mime};base64," + \
        base64.b64encode(Path(p).read_bytes()).decode()


def food(name):
    return durl(ROOT / "library" / "food" / f"{name}.jpg")


a5 = json.loads((MAN / "assets_v5.json").read_text())
beats = {b["beat_id"]: b for b in
         json.loads((MAN / "beats.json").read_text())["beats"]}


def ms_seq(bid, n):
    span = int((beats[bid]["end"] - beats[bid]["start"]) * 1000)
    return [int(span * (i + 0.55) / (n + 1)) for i in range(n)]


# ---- list-card variety re-map (former IconBursts) ----------------------
def tiles(bid, items):
    ms = ms_seq(bid, len(items))
    return [{"src": food(f), "label": lbl, "atMs": ms[i]}
            for i, (f, lbl) in enumerate(items)]


R = {}
R["b_026"] = ("IndexCards", {"title": "Monday - main lifts", "cards": [
    {"text": "Incline bench press", "icon": "🏋️", "atMs": 400},
    {"text": "Flat dumbbell press", "icon": "💪", "atMs": 1100},
    {"text": "Cable flies", "icon": "🎯", "atMs": 1800}]})
R["b_028"] = ("StepCards", {"title": "Supersets", "steps": [
    {"text": "Dips + Pushups", "atMs": 500},
    {"text": "Overhead extensions + Skull crushers", "atMs": 1400}]})
R["b_030"] = ("Checklist", {"title": "Metabolic finisher - 10-12 min",
    "items": [{"text": "Battle ropes", "atMs": 400},
              {"text": "Medicine ball slams", "atMs": 1100},
              {"text": "Jump rope", "atMs": 1800}]})
R["b_036"] = ("StepCards", {"title": "Core circuit", "steps": [
    {"text": "Hanging leg raises", "atMs": 400},
    {"text": "Ab wheel rollouts", "atMs": 1200},
    {"text": "Pallof presses", "atMs": 2000}]})
R["b_043"] = ("IndexCards", {"title": "Shoulders - all 3 heads", "cards": [
    {"text": "Overhead press", "icon": "🏋️", "atMs": 400},
    {"text": "Lateral raises", "icon": "↔️", "atMs": 1100},
    {"text": "Rear-delt flies", "icon": "🔙", "atMs": 1800}]})
R["b_049"] = ("StepCards", {"title": "Functional circuit", "steps": [
    {"text": "Kettlebell swings", "atMs": 400},
    {"text": "Box jumps", "atMs": 1200},
    {"text": "Medicine ball throws", "atMs": 2000}]})
R["b_052"] = ("Checklist", {"title": "Saturday - conditioning",
    "items": [{"text": "Jump rope", "atMs": 400},
              {"text": "Shadowboxing", "atMs": 1100},
              {"text": "Pad work / drills", "atMs": 1800}]})
R["b_069"] = ("PhotoTiles", {"title": "Pre-workout", "tiles":
    tiles("b_069", [("coffee", "Black coffee"), ("oats", "Oats + whey"),
                    ("eggs", "or eggs")])})
R["b_071"] = ("PhotoTiles", {"title": "Meal 1", "tiles":
    tiles("b_071", [("egg_whites", "Egg whites + eggs"),
                    ("greens", "Vegetables"), ("oats", "Oats")])})
R["b_072"] = ("PhotoTiles", {"title": "Meal 2", "tiles":
    tiles("b_072", [("chicken", "Grilled chicken"),
                    ("sweet_potato", "Sweet potato"),
                    ("broccoli", "Broccoli")])})
R["b_073"] = ("PhotoTiles", {"title": "Meal 3", "tiles":
    tiles("b_073", [("salmon", "Salmon or turkey"),
                    ("rice", "Rice or quinoa"),
                    ("avocado", "Avocado")])})
R["b_077"] = ("Checklist", {"title": "Nutrition rules",
    "items": [{"text": "90% whole foods", "atMs": 400},
              {"text": "Zero processed junk", "atMs": 1200},
              {"text": "High-carb: Mon / Wed / Fri", "atMs": 2000}]})
R["b_078"] = ("IndexCards", {"title": "Carb cycling", "cards": [
    {"text": "Low-carb: Tue / Thu / Sat", "icon": "📉", "atMs": 500},
    {"text": "Sugar + alcohol: near zero", "icon": "🚫", "atMs": 1400}]})
# keep IconBurst: b_023 (7-day split), b_083 (his cardio), b_096 (system)

# ---- extra food beats that SAY foods but showed something else ---------
R["b_070"] = ("PhotoTiles", {"title": "Post-workout", "tiles":
    tiles("b_070", [("protein_shake", "Protein shake"),
                    ("banana", "Banana"),
                    ("rice_cakes", "or rice cakes")])})
R["b_075"] = ("PhotoTiles", {"title": "Evening snack", "tiles":
    tiles("b_075", [("greek_yogurt", "Greek yogurt"),
                    ("cottage_cheese", "or cottage cheese"),
                    ("almonds", "Almonds")])})
R["b_074"] = ("PhotoTiles", {"title": "Meal 4", "tiles":
    tiles("b_074", [("beef", "Lean beef"), ("white_fish", "or white fish"),
                    ("greens", "Greens"), ("olive_oil", "Olive oil")])})
R["b_076"] = ("PhotoTiles", {"title": "Before bed", "tiles":
    tiles("b_076", [("casein", "Casein shake")])})

# ---- Instagram 3D card for Don --------------------------------------
grid = []
for i in range(1, 4):
    p = ROOT / "library" / "refs" / f"don_saladino_{i}.jpg"
    if p.exists():
        grid.append(durl(p))
for extra in ("saladino_home.png",):
    p = ROOT / "library" / "sites" / extra
    if p.exists():
        grid.append(durl(p, "image/png"))
R["b_013"] = ("InstaCard", {
    "handle": "donsaladino", "name": "Don Saladino",
    "bio": "Celebrity trainer - Ryan Reynolds, Blake Lively, Sebastian "
           "Stan - Programs at donsaladino.com",
    "avatarSrc": durl(ROOT / "library" / "refs" / "don_saladino_1.jpg"),
    "gridSrcs": grid * 2})

order = sorted(a5)
purge = []
for bid, (comp, props) in R.items():
    a5[bid] = {"type": "v5card", "comp": comp, "props": props}
    purge.append(bid)

json.dump(a5, open(MAN / "assets_v5.json", "w"), indent=1)

# ---- arrow callouts on era footage (composited by assembler) ----------
CALLOUTS = {
 "b_015": {"name": "Ryan Reynolds", "sub": "early 2000s - before",
           "targetX": 0.5, "targetY": 0.3},
 "b_016": {"name": "Ryan Reynolds - 27", "sub": "Blade: Trinity (2004)",
           "targetX": 0.45, "targetY": 0.3},
 "b_017": {"name": "Ryan Reynolds - 34", "sub": "Green Lantern era (2011)",
           "targetX": 0.5, "targetY": 0.3},
 "b_018": {"name": "Ryan Reynolds - 47", "sub": "Deadpool & Wolverine (2024)",
           "targetX": 0.5, "targetY": 0.3},
 "b_002": {"name": "Ryan Reynolds", "sub": "training with Don Saladino",
           "targetX": 0.4, "targetY": 0.3},
}
json.dump(CALLOUTS, open(MAN / "callouts.json", "w"), indent=1)

# ---- sentence-snap interludes -----------------------------------------
def parse_vtt(f):
    rows = []
    t = None
    for line in Path(f).read_text(encoding="utf-8",
                                  errors="ignore").splitlines():
        m = re.match(r"(\d+):(\d+):(\d+)\.(\d+) --> ", line)
        if m:
            t = (int(m.group(1)) * 3600 + int(m.group(2)) * 60
                 + int(m.group(3)) + int(m.group(4)) / 1000)
            continue
        txt = re.sub(r"<[^>]+>", "", line).strip()
        if txt and t is not None and not txt.startswith(
                ("WEBVTT", "Kind:", "Language:")):
            if not rows or rows[-1][1] != txt:
                rows.append((t, txt))
    return rows


inters = json.loads((MAN / "interludes.json").read_text())
for it in inters:
    vtts = sorted((ROOT / "dossier" / "captions").glob(f"{it['vid']}*.vtt"))
    if not vtts:
        continue
    rows = parse_vtt(vtts[0])
    # snap t0 -> nearest caption line START at/before planned t0 that
    # begins a sentence (previous line ended with . ! ?); t1 -> end of the
    # last line that ENDS a sentence within +6s of planned t1
    def sent_start(i):
        return i == 0 or re.search(r"[.!?]['\"]?$", rows[i - 1][1])
    def sent_end(i):
        return re.search(r"[.!?]['\"]?$", rows[i][1])
    starts = [i for i, (t, _) in enumerate(rows)
              if t <= it["t0"] + 2.5 and sent_start(i)]
    ends = [i for i, (t, _) in enumerate(rows)
            if it["t1"] - 6 <= t <= it["t1"] + 6 and sent_end(i)]
    if starts and ends:
        s_i, e_i = starts[-1], ends[-1]
        new_t0 = max(rows[s_i][0] - 0.15, 0)
        new_t1 = (rows[e_i + 1][0] if e_i + 1 < len(rows)
                  else rows[e_i][0] + 3.0)
        if new_t1 - new_t0 >= 6:
            print(f"{it['id']}: {it['t0']}-{it['t1']} -> "
                  f"{new_t0:.1f}-{new_t1:.1f} (sentence-snapped)")
            it["t0"], it["t1"] = round(new_t0, 2), round(new_t1, 2)
        else:
            print(f"{it['id']}: snap too short - keeping planned window")
    else:
        print(f"{it['id']}: no clean sentence bounds - DROPPING")
        it["drop"] = True
inters = [it for it in inters if not it.get("drop")]
json.dump(inters, open(MAN / "interludes.json", "w"), indent=1)

# ---- purge pieces + segments ------------------------------------------
n = 0
for bid in set(purge):
    idx = order.index(bid)
    for f in (ROOT / "final_video" / "v5_work").glob(
            f"p_{idx:03d}_{bid}.mp4"):
        f.unlink()
        n += 1
    for f in (ROOT / "final_video" / "v6_work").glob(
            f"seg_{idx:03d}_{bid}*.mp4"):
        f.unlink()
        n += 1
for f in (ROOT / "final_video" / "v6_work").glob("seg_*_zz_*.mp4"):
    f.unlink()
    n += 1
# callout beats need re-composite: purge their segments (pieces stay)
for bid in CALLOUTS:
    idx = order.index(bid)
    for f in (ROOT / "final_video" / "v6_work").glob(
            f"seg_{idx:03d}_{bid}.mp4"):
        f.unlink()
        n += 1
print(f"[OK] {len(R)} card remaps, {len(CALLOUTS)} callouts, "
      f"{len(inters)} interludes kept, {n} artifacts purged")
