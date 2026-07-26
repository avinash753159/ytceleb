#!/usr/bin/env python3
"""statham_treatments.py - author assets_v5.json for all 113 Statham beats.

Sources: WATCH_NOTES-verified windows (cuts), markers (cards), era stills,
free-exercise-db photo pairs, Pexels exercise loops, site screenshots.
Also writes bugs.json (chapter chips + like/sub bug) and clears callouts.
"""
import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "manifest"
DOS = ROOT / "dossier" / "statham"
ACCENT = "#44708E"


def durl(p, mime=None):
    p = Path(p)
    if mime is None:
        mime = "image/png" if p.suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def vurl(name):
    return durl(ROOT / "library" / "exloops" / f"{name}.mp4", "video/mp4")


def still(name):
    return durl(ROOT / "library" / "statham_refs" / f"{name}.jpg")


def exdb(name):
    return durl(ROOT / "library" / "exdb" / f"{name}.jpg")


def food(name):
    return durl(ROOT / "library" / "food" / f"{name}.jpg")


def expic(name):
    return durl(ROOT / "library" / "exercises" / f"{name}.jpg")


beats = json.loads((MAN / "beats.json").read_text())["beats"]
bmap = {b["beat_id"]: b for b in beats}
order = [b["beat_id"] for b in beats]

A = {}

# ------------------------------------------------------------------ cuts
def cut(bid, src, t0, pad=0.3):
    b = bmap[bid]
    dur = b["end"] - b["start"]
    A[bid] = {"type": "cut",
              "src": str(DOS / f"{src}.mp4"), "t0": round(t0, 2),
              "t1": round(t0 + dur + pad, 2), "vid": src, "verified": True}


# window pools per section: (source, start) - verified in WATCH_NOTES.md
POOLS = {
 "open": [("tr_beekeeper", 127), ("tr_deathrace", 45), ("tr_transporter", 26),
          ("tr_lockstock", 88), ("tr_meg", 116)],
 "diver": [("xrxH5n93CzM", 2), ("xrxH5n93CzM", 26), ("xrxH5n93CzM", 56),
           ("xrxH5n93CzM", 68), ("xrxH5n93CzM", 86), ("xrxH5n93CzM", 110),
           ("tr_snatch", 22), ("xrxH5n93CzM", 98), ("xrxH5n93CzM", 122),
           ("tr_lockstock", 90), ("tr_snatch", 70), ("xrxH5n93CzM", 134),
           ("tr_lockstock", 60)],
 "system": [("tr_deathrace", 50), ("C6YTQsvuiBw", 232), ("tr_wrath", 2),
            ("tr_beekeeper", 65), ("C6YTQsvuiBw", 330), ("tr_deathrace", 80),
            ("tr_crank", 34), ("C6YTQsvuiBw", 432), ("tr_transporter", 74),
            ("tr_beekeeper", 135), ("C6YTQsvuiBw", 512), ("tr_crank", 58),
            ("tr_deathrace", 104), ("C6YTQsvuiBw", 610), ("tr_wrath", 26),
            ("tr_beekeeper", 114), ("C6YTQsvuiBw", 700), ("tr_deathrace", 140),
            ("tr_crank", 10), ("C6YTQsvuiBw", 30)],
 "week": [("tr_expendables", 32), ("tr_expendables", 62), ("tr_meg", 110),
          ("tr_furious7", 98), ("tr_expendables", 140), ("tr_furious7", 104),
          ("tr_beekeeper", 107), ("tr_expendables", 98), ("tr_wrath", 50),
          ("tr_deathrace", 110), ("tr_beekeeper", 16)],
 "diet": [("C6YTQsvuiBw", 275), ("tr_beekeeper", 23), ("C6YTQsvuiBw", 375),
          ("tr_crank", 14), ("C6YTQsvuiBw", 475), ("tr_snatch", 90)],
 "evo": [("tr_furious7", 98), ("tr_meg", 116), ("tr_meg", 134),
         ("tr_wrath", 2), ("tr_beekeeper", 128), ("AiAnWmlT4Bc", 45),
         ("C6YTQsvuiBw", 555), ("tr_meg", 38), ("tr_beekeeper", 135),
         ("tr_wrath", 32), ("AiAnWmlT4Bc", 60), ("tr_beekeeper", 149)],
 "plan": [("exloop:trail_run", 0), ("exloop:boxing", 0),
          ("exloop:deadlift", 0), ("xrxH5n93CzM", 110),
          ("exloop:rowing_erg", 0), ("tr_beekeeper", 65),
          ("exloop:pullup", 0), ("tr_expendables", 140),
          ("exloop:burpee", 0), ("tr_meg", 116), ("tr_deathrace", 140),
          ("xrxH5n93CzM", 14), ("tr_beekeeper", 114)],
}
SECTIONS = [("open", "b_000", "b_006"), ("diver", "b_007", "b_015"),
            ("system", "b_016", "b_044"), ("week", "b_045", "b_070"),
            ("diet", "b_071", "b_083"), ("evo", "b_084", "b_096"),
            ("plan", "b_097", "b_112")]

idx_in = {s: 0 for s, _, _ in SECTIONS}
def section_of(bid):
    for s, a, z in SECTIONS:
        if a <= bid <= z:
            return s
    return "plan"

for bid in order:
    s = section_of(bid)
    pool = POOLS[s]
    src, t0 = pool[idx_in[s] % len(pool)]
    # reuse pass offsets windows +6s to avoid identical re-cuts
    bump = 6 * (idx_in[s] // len(pool))
    idx_in[s] += 1
    if src.startswith("exloop:"):
        A[bid] = {"type": "cut",
                  "src": str(ROOT / "library" / "exloops" /
                             f"{src.split(':')[1]}.mp4"),
                  "t0": 0.0, "t1": round(bmap[bid]["end"] -
                                         bmap[bid]["start"] + 0.2, 2),
                  "vid": src, "verified": True, "loop": True}
    else:
        cut(bid, src, t0 + bump)

# ------------------------------------------------------------- cards
DB = json.loads((ROOT / "library" / "free_exercise_db.json")
                .read_text(encoding="utf-8"))
def db_muscles(name):
    for e in DB:
        if e["name"].lower() == name.lower():
            return e.get("primaryMuscles", []), e.get("secondaryMuscles", [])
    return [], []

pm, sm = db_muscles("Barbell Deadlift")
A["b_051"] = {"type": "v5card", "comp": "ExerciseCard", "props": {
    "name": "Deadlift Day", "videoSrc": vurl("deadlift"),
    "primaryMuscles": pm, "secondaryMuscles": sm,
    "sets": "9", "reps": "135→365 lb", "rest": "singles",
    "accent": ACCENT}}
A["b_055"] = {"type": "v5card", "comp": "StepCards2", "props": {
    "title": "The Big Five 55", "steps": [
        {"text": "Front squats", "src": exdb("Barbell_Deadlift_0"),
         "atMs": 300},
        {"text": "Pull-ups", "src": expic("pullup"), "atMs": 900},
        {"text": "Decline push-ups", "src": expic("pushup"), "atMs": 1500},
        {"text": "Power cleans", "src": expic("deadlift"), "atMs": 2100},
        {"text": "Knees-to-elbows · 10→1 ladder · 55 reps",
         "src": expic("leg_raise"), "atMs": 2700}]}}
A["b_058"] = {"type": "v5card", "comp": "ExerciseCard", "props": {
    "name": "Rowing Intervals", "videoSrc": vurl("rowing_erg"),
    "primaryMuscles": ["middle back", "quadriceps"],
    "secondaryMuscles": ["biceps", "hamstrings"],
    "sets": "6×500m", "reps": "1:38–1:50", "rest": "3 min",
    "accent": ACCENT}}
pm, sm = db_muscles("Front Barbell Squat")
A["b_061"] = {"type": "v5card", "comp": "ExerciseCard", "props": {
    "name": "Front Squat Day", "videoSrc": vurl("front_squat"),
    "primaryMuscles": pm or ["quadriceps"],
    "secondaryMuscles": sm or ["glutes", "abdominals"],
    "sets": "5×5", "reps": "1.25× BW", "rest": "90s",
    "accent": ACCENT}}
A["b_064"] = {"type": "v5card", "comp": "StepCards2", "props": {
    "title": "The 23:53 Circuit", "steps": [
        {"text": "Rope climbs · arms only",
         "src": expic("battle_ropes"), "atMs": 300},
        {"text": "Ball slams + rope pulls", "src": expic("ball_slam"),
         "atMs": 1000},
        {"text": "Bench · dips · sled work",
         "src": expic("dips"), "atMs": 1700},
        {"text": "11 exercises · logged 23:53",
         "src": expic("conditioning"), "atMs": 2400}]}}
A["b_066"] = {"type": "v5card", "comp": "PhotoBurst", "props": {
    "label": "The Diary Week", "satellites": [
        {"src": expic("deadlift"), "label": "Mon · Deadlifts",
         "atMs": 400},
        {"src": expic("pullup"), "label": "Tue · Big Five 55",
         "atMs": 1000},
        {"src": expic("cardio_cat"), "label": "Wed · 6×500m row",
         "atMs": 1600},
        {"src": expic("leg_day"), "label": "Thu · Front squats",
         "atMs": 2200},
        {"src": expic("battle_ropes"), "label": "Fri · Circuit",
         "atMs": 2800},
        {"src": expic("sprint"), "label": "Sat · 73-min trail run",
         "atMs": 3400},
        {"src": expic("recovery_cat"), "label": "Sun · Rest",
         "atMs": 4000}]}}

A["b_005"] = {"type": "v5card", "comp": "PhotoBurst", "props": {
    "label": "Same machine, 25 years", "satellites": [
        {"src": still("era_lockstock"), "label": "Lock Stock · '98",
         "atMs": 300},
        {"src": still("era_transporter"), "label": "Transporter · '02",
         "atMs": 850},
        {"src": still("era_crank"), "label": "Crank · '06",
         "atMs": 1400},
        {"src": still("era_expendables"), "label": "Expendables · '10",
         "atMs": 1950},
        {"src": still("era_meg"), "label": "The Meg · '18",
         "atMs": 2500},
        {"src": still("era_beekeeper"), "label": "Beekeeper · '24",
         "atMs": 3050}]}}

A["b_020"] = {"type": "v5card", "comp": "SiteZoom", "props": {
    "src": durl(ROOT / "library/sites/mh_statham_p1.png"),
    "label": "menshealth.com · 2007 · the original diary",
    "zoomTo": 1.45, "focusY": 0.18, "accent": ACCENT}}
A["b_025"] = {"type": "v5card", "comp": "StepCards2", "props": {
    "title": "The Transformation", "steps": [
        {"text": "17 pounds lost", "atMs": 300},
        {"text": "6 weeks · 6 days a week", "atMs": 1100},
        {"text": "35 minutes a day, max", "atMs": 1900}]}}
A["b_035"] = {"type": "v5card", "comp": "Checklist2", "props": {
    "title": "The Two Rules", "items": [
        {"text": "Never repeat a workout", "atMs": 400},
        {"text": "Record everything", "atMs": 1400}]}}

A["b_073"] = {"type": "v5card", "comp": "PhotoBurst", "props": {
    "label": "Six small meals", "satellites": [
        {"src": food("egg_whites"), "label": "Egg whites", "atMs": 300},
        {"src": food("greens"), "label": "Vegetables", "atMs": 850},
        {"src": food("chicken"), "label": "Lean meats", "atMs": 1400},
        {"src": food("salmon"), "label": "Fish", "atMs": 1950},
        {"src": food("almonds"), "label": "Nuts", "atMs": 2500},
        {"src": food("protein_shake"), "label": "Shakes", "atMs": 3050}]}}
A["b_077"] = {"type": "v5card", "comp": "Checklist2", "props": {
    "title": "Banned, full stop", "items": [
        {"text": "No refined sugar", "atMs": 300},
        {"text": "No flour — no bread, no pasta", "atMs": 1000},
        {"text": "No juice · no booze", "atMs": 1700}]}}
A["b_083"] = {"type": "v5card", "comp": "StepCards2", "props": {
    "title": "The numbers he logged", "steps": [
        {"text": "2,000 kcal — 'the gospel'", "atMs": 300},
        {"text": "6 small meals a day", "atMs": 1100},
        {"text": "1.5 gallons of water", "atMs": 1900}]}}
A["b_108"] = {"type": "v5card", "comp": "Checklist2", "props": {
    "title": "The Statham rules", "items": [
        {"text": "Never repeat a workout", "atMs": 300},
        {"text": "Record everything", "atMs": 900},
        {"text": "35 hard minutes", "atMs": 1500},
        {"text": "Train early", "atMs": 2100},
        {"text": "2,000 clean calories", "atMs": 2700}]}}
A["b_111"] = {"type": "v5card", "comp": "CommentPrompt", "props": {
    "a": "Deadlift day?", "b": "The Big Five 55?",
    "prompt": "Drop your pick in the comments"}}
A["b_112"] = {"type": "v5card", "comp": "SubscribeCard", "props": {
    "channel": "Celeb Workout",
    "sub": "Another legend, next week", "safeZone": True}}

json.dump(A, open(MAN / "assets_v5.json", "w"), indent=1)

# ---------------------------------------------------- bugs (chips + sub)
bugs = {
 "b_007": {"comp": "ChapterChip",
           "props": {"part": "PART 1", "title": "The Diver"}},
 "b_016": {"comp": "ChapterChip",
           "props": {"part": "PART 2", "title": "The System"}},
 "b_046": {"comp": "ChapterChip",
           "props": {"part": "PART 3", "title": "The Week"}},
 "b_071": {"comp": "ChapterChip",
           "props": {"part": "PART 4", "title": "The Diet"}},
 "b_084": {"comp": "ChapterChip",
           "props": {"part": "PART 5", "title": "The Evolution"}},
 "b_097": {"comp": "ChapterChip",
           "props": {"part": "PART 6", "title": "Your Plan"}},
 "b_030": {"comp": "LikeSubBug", "props": {}},
}
json.dump(bugs, open(MAN / "bugs.json", "w"), indent=1)
json.dump({}, open(MAN / "callouts.json", "w"))

cards = sum(1 for a in A.values() if a["type"] == "v5card")
print(f"[OK] {len(A)} beats: {cards} cards, {len(A)-cards} cuts; "
      f"{len(bugs)} bugs")
