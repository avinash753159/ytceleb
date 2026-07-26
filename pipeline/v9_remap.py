#!/usr/bin/env python3
"""v9_remap.py - photo-based infographics + bigger everything.

- Every exercise list card -> real exercise photos (PhotoTiles2 /
  StepCards2 / Checklist2 / PhotoBurst), Sun rest -> dude doing yoga.
- IconBursts replaced entirely (emojis gone).
- Chapter chips composited on section-start beats (bugs.json).
- End SubscribeCard gets the YouTube end-screen safe zone.
Purges affected pieces/segments.
"""
import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "manifest"
EX = ROOT / "library" / "exercises"


def durl(p):
    return "data:image/jpeg;base64," + \
        base64.b64encode(Path(p).read_bytes()).decode()


def ex(name):
    return durl(EX / f"{name}.jpg")


a5 = json.loads((MAN / "assets_v5.json").read_text())
beats = {b["beat_id"]: b for b in
         json.loads((MAN / "beats.json").read_text())["beats"]}


def keep_ms(bid, items_old):
    return [it["atMs"] for it in items_old]


R = {}

# ---- workout list cards -> photos --------------------------------------
R["b_026"] = ("PhotoTiles2", {"title": "Monday - main lifts", "tiles": [
    {"src": ex("incline_bench"), "label": "Incline bench", "atMs": 400},
    {"src": ex("dumbbell_press"), "label": "Dumbbell press", "atMs": 1100},
    {"src": ex("cable_fly"), "label": "Cable flies", "atMs": 1800}]})
R["b_028"] = ("StepCards2", {"title": "Supersets", "steps": [
    {"text": "Dips + Pushups", "src": ex("dips"), "atMs": 500},
    {"text": "Overhead ext. + Skull crushers", "src": ex("overhead_ext"),
     "atMs": 1400}]})
R["b_030"] = ("Checklist2", {"title": "Metabolic finisher", "items": [
    {"text": "Battle ropes", "src": ex("battle_ropes"), "atMs": 400},
    {"text": "Medicine ball slams", "src": ex("ball_slam"), "atMs": 1100},
    {"text": "Jump rope", "src": ex("jump_rope"), "atMs": 1800}]})
R["b_036"] = ("StepCards2", {"title": "Core circuit", "steps": [
    {"text": "Hanging leg raises", "src": ex("leg_raise"), "atMs": 400},
    {"text": "Ab wheel rollouts", "src": ex("ab_wheel"), "atMs": 1200},
    {"text": "Pallof presses", "src": ex("cable_core"), "atMs": 2000}]})
R["b_043"] = ("PhotoTiles2", {"title": "Shoulders - all 3 heads",
    "tiles": [
    {"src": ex("overhead_press"), "label": "Overhead press", "atMs": 400},
    {"src": ex("lateral_raise"), "label": "Lateral raises", "atMs": 1100},
    {"src": ex("rear_delt"), "label": "Rear-delt flies", "atMs": 1800}]})
R["b_049"] = ("StepCards2", {"title": "Functional circuit", "steps": [
    {"text": "Kettlebell swings", "src": ex("kb_swing"), "atMs": 400},
    {"text": "Box jumps", "src": ex("box_jump"), "atMs": 1200},
    {"text": "Medicine ball throws", "src": ex("mb_throw"), "atMs": 2000}]})
R["b_052"] = ("Checklist2", {"title": "Saturday - conditioning",
    "items": [
    {"text": "Jump rope", "src": ex("jump_rope"), "atMs": 400},
    {"text": "Shadowboxing", "src": ex("shadowbox"), "atMs": 1100},
    {"text": "Pad work / drills", "src": ex("pad_work"), "atMs": 1800}]})

# ---- IconBursts -> PhotoBursts (emojis gone) ---------------------------
old = a5["b_023"]["props"]["satellites"]
DAYS = [("chest_day", "Mon - Chest + Triceps"),
        ("back_day", "Tue - Back + Biceps"),
        ("leg_day", "Wed - Legs + HIIT"),
        ("overhead_press", "Thu - Shoulders + Arms"),
        ("posterior", "Fri - Posterior Chain"),
        ("conditioning", "Sat - Conditioning"),
        ("yoga_man", "Sun - Rest + Yoga")]
R["b_023"] = ("PhotoBurst", {"label": "The 7-day split", "satellites": [
    {"src": ex(img), "label": lbl, "atMs": old[i]["atMs"]}
    for i, (img, lbl) in enumerate(DAYS)]})

old = a5["b_083"]["props"]["satellites"]
CARDIO = [("jump_rope", "Jump rope"), ("battle_ropes", "Battle ropes"),
          ("sprint", "Sprints"), ("martial_arts", "Martial arts")]
R["b_083"] = ("PhotoBurst", {"label": "His cardio", "satellites": [
    {"src": ex(img), "label": lbl, "atMs": old[i]["atMs"]}
    for i, (img, lbl) in enumerate(CARDIO)]})

old = a5["b_096"]["props"]["satellites"]
SYS = [("deadlift", "Training"), ("diet_cat", "Diet"),
       ("cardio_cat", "Cardio"), ("recovery_cat", "Recovery")]
R["b_096"] = ("PhotoBurst", {"label": "The full system", "satellites": [
    {"src": ex(img), "label": lbl, "atMs": old[i]["atMs"]}
    for i, (img, lbl) in enumerate(SYS)]})

# ---- carb-cycling card: bigger, food photos ----------------------------
FOOD = ROOT / "library" / "food"
R["b_078"] = ("Checklist2", {"title": "Carb cycling", "items": [
    {"text": "Low-carb: Tue / Thu / Sat", "src": durl(FOOD / "greens.jpg"),
     "atMs": 500},
    {"text": "Sugar + alcohol: near zero", "atMs": 1400}]})

# ---- end screen safe zone ----------------------------------------------
# (b_100 endcap card is built by v9_endcap step in the b_100 piece)

purge = []
for bid, (comp, props) in R.items():
    a5[bid] = {"type": "v5card", "comp": comp, "props": props}
    purge.append(bid)
json.dump(a5, open(MAN / "assets_v5.json", "w"), indent=1)

# ---- chapter chips on section-start beats ------------------------------
bugs = json.loads((MAN / "bugs.json").read_text()) \
    if (MAN / "bugs.json").exists() else {}
CHAPTERS = {
    "b_014": ("PART 1", "The Transformation"),
    "b_025": ("PART 2", "The Split"),
    "b_068": ("PART 3", "The Diet"),
    "b_079": ("PART 4", "The Rules"),
    "b_087": ("PART 5", "Your Plan"),
}
for bid, (part, title) in CHAPTERS.items():
    if a5.get(bid, {}).get("type") in ("cut", "library"):
        bugs[bid] = {"comp": "ChapterChip",
                     "props": {"part": part, "title": title}}
        purge.append(bid)
json.dump(bugs, open(MAN / "bugs.json", "w"), indent=1)

# ---- purge -------------------------------------------------------------
order = sorted(a5)
n = 0
for bid in set(purge):
    idx = order.index(bid)
    for f in (ROOT / "final_video/v5_work").glob(f"p_{idx:03d}_{bid}.mp4"):
        if bid in R:            # cards re-render; chip beats keep pieces
            f.unlink()
            n += 1
    for f in (ROOT / "final_video/v6_work").glob(f"seg_{idx:03d}_{bid}.mp4"):
        f.unlink()
        n += 1
# every v5card segment re-muxes so ALL cards get the entrance whoosh;
# every interlude segment re-cuts so ALL get the J-cut audio lead
for idx, bid in enumerate(order):
    if a5[bid].get("type") == "v5card":
        for f in (ROOT / "final_video/v6_work").glob(
                f"seg_{idx:03d}_{bid}.mp4"):
            f.unlink()
            n += 1
for f in (ROOT / "final_video/v6_work").glob("seg_*_zz_*.mp4"):
    f.unlink()
    n += 1
print(f"[OK] {len(R)} photo remaps, {len(CHAPTERS)} chapter chips, "
      f"{n} artifacts purged")
