#!/usr/bin/env python3
"""corenswet_treatments.py - per-beat treatments for TRAIN LIKE DAVID
CORENSWET (Superman).

Footage reality (WATCH_NOTES): almost no real Corenswet gym footage
exists publicly. Spine = document cards (his actual GQ workout list +
the press paper trail), his own interview voice (interludes + talking
head), Superman film-persona (trailer + BTS), and GENERIC exercise-demo
loops during program-description beats (never labeled as him). The
Cavill/Reeve gym footage is deliberately NOT used as David (F11
misattribution).

Anchors match the faster-whisper transcript (beats.json). Writes
assets_v5.json, interludes.json, bugs.json.
"""
import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "manifest"
DOS = ROOT / "dossier" / "david_corenswet"
REF = ROOT / "library" / "corenswet_refs"
FOOD = ROOT / "library" / "food"
EX = ROOT / "library" / "exloops"
ACCENT = "#D9232E"

beats = json.loads((MAN / "beats.json").read_text())["beats"]
bmap = {b["beat_id"]: b for b in beats}
order = [b["beat_id"] for b in beats]

TRAILER, BTS, GQV = "Ox8ZLF6cGM0", "0IwY7Mfzw_w", "u8zoxUlFo7E"
# all clean 16:9 1080p - no crop needed
NOCROP = [0.0, 0.0, 0.0, 0.0]
A = {}


import re as _re


def _norm(s):
    return _re.sub(r"[^a-z0-9 ]", "", s.lower().replace("-", " "))


def find(phrase):
    p = _re.sub(r"\s+", " ", _norm(phrase)).strip()
    for b in beats:
        if p in _re.sub(r"\s+", " ", _norm(b["text"])).strip():
            return b["beat_id"]
    raise SystemExit(f"anchor not found: {phrase}")


def durl(p):
    p = Path(p)
    mime = "image/png" if p.suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def cut(bid, src, t0, t1):
    need = bmap[bid]["end"] - bmap[bid]["start"]
    e = {"type": "cut", "src": str(DOS / f"{src}.mp4"),
         "t0": round(t0, 2), "vid": f"{src}@{t0}", "verified": True,
         "crop_box": NOCROP}
    if t1 - t0 < need:
        e["t1"] = round(t1, 2)
        e["loop"] = True
    else:
        e["t1"] = round(t0 + need + 0.2, 2)
    A[bid] = e


def exloop(bid, name):
    need = bmap[bid]["end"] - bmap[bid]["start"]
    A[bid] = {"type": "cut", "src": str(EX / f"{name}.mp4"),
              "t0": 0.0, "t1": round(need + 0.2, 2),
              "vid": f"exloop:{name}", "verified": True, "loop": True}


def span_mark(bid, span_until):
    if span_until and span_until != bid:
        for x in order[order.index(bid) + 1:order.index(span_until) + 1]:
            A[x] = {"type": "spanned"}
        return span_until
    return None


def doc(bid, img, outlet, date, note, pan=(0.0, 0.4), span_until=None):
    e = {"type": "v5card", "comp": "DocumentCard", "props": {
        "src": durl(REF / img), "outlet": outlet, "date": date,
        "note": note, "accent": ACCENT,
        "panFrom": pan[0], "panTo": pan[1]}}
    su = span_mark(bid, span_until)
    if su:
        e["span_until"] = su
    A[bid] = e


def card(bid, comp, props, span_until=None):
    e = {"type": "v5card", "comp": comp, "props": props}
    su = span_mark(bid, span_until)
    if su:
        e["span_until"] = su
    A[bid] = e


def typeon(bid, lines, span_until=None):
    card(bid, "TypeOn", {"text": "\n".join(lines), "accent": ACCENT,
                         "cps": 30, "variant": "quote"}, span_until)


def rows(bid, title, items, span_until=None):
    card(bid, "StepCards2",
         {"title": title,
          "steps": [{"text": t, "atMs": 250 + i * 620}
                    for i, t in enumerate(items)]}, span_until)


S = {
 "open": "b_000",
 "kid": find("Start in Philadelphia"),
 "secrets": find("Warner Brothers calls him in"),
 "math": find("Gunn hand"),
 "fuel": find("The eating was the harder job"),
 "forty": find("no other superhero"),
 "bruise": find("Training dropped to three"),
 "again": find("The sequel, Man of Tomorrow"),
 "plan": find("You don't need a Warner"),
 "outro": find("Honest question"),
}

# ---- pools of verified David footage --------------------------------------
POOLS = {
 # his GQ interview talking head (grey pullover) - clean windows
 "talk": [(GQV, 96, 128), (GQV, 168, 187), (GQV, 72, 95), (GQV, 240, 252),
          (GQV, 328, 352), (GQV, 192, 203), (GQV, 372, 391), (GQV, 28, 35)],
 # Superman trailer film-persona (Clark + Superman)
 "film": [(TRAILER, 24, 34), (TRAILER, 72, 87), (TRAILER, 18, 22),
          (TRAILER, 54, 58), (TRAILER, 133, 138), (TRAILER, 42, 45)],
 # set BTS (David-as-Superman being filmed)
 "set": [(BTS, 22, 32), (BTS, 94, 100), (BTS, 2, 8), (BTS, 56, 74)],
 # generic exercise demos (program-description beats only, never "him")
 "gym": [(EX, "deadlift"), (EX, "power_clean"), (EX, "rowing_erg"),
         (EX, "pullup"), (EX, "kettlebell_carry"), (EX, "pushup"),
         (EX, "boxing"), (EX, "ball_slam"), (EX, "burpee")],
}
_n = {k: 0 for k in POOLS}


def pool(bid, name):
    items = POOLS[name]
    pick = items[_n[name] % len(items)]
    _n[name] += 1
    if name == "gym":
        exloop(bid, pick[1])
    else:
        src, t0, t1 = pick
        lap = _n[name] // len(items)
        need = bmap[bid]["end"] - bmap[bid]["start"]
        t0a = t0 + lap * (need + 1.0)
        if t0a + need + 0.2 > t1:
            t0a = t0
        cut(bid, src, t0a, t1)


def section_of(i):
    cur = "open"
    for nm, bid in S.items():
        if order.index(bid) <= i:
            cur = nm
    return cur


FILL = {"open": "film", "kid": "talk", "secrets": "talk", "math": "gym",
        "fuel": "talk", "forty": "talk", "bruise": "film", "again": "film",
        "plan": "gym", "outro": "film"}
for i, bid in enumerate(order):
    pool(bid, FILL[section_of(i)])

# ---- COLD OPEN ------------------------------------------------------------
doc("b_000", "card_mh2019_headline.jpg", "Men's Health", "Dec 2, 2019",
    "the rumor - 3 1/2 years before he was cast", pan=(0.0, 0.3),
    span_until=find("replace Henry Cavill"))
doc(find("told an interviewer exactly"), "card_mh2025_headline.jpg",
    "Men's Health", "his 2020 interview", "\"I'll take that in writing\"",
    pan=(0.0, 0.3), span_until=find("start a petition"))
cut(find("the phone rang"), BTS, 22, 32)          # Superman + Gunn
typeon(find("hey David, it's James Gunn"),
       ["\"HEY DAVID,", "IT'S JAMES GUNN.\""])
cut(find("turned a 195"), TRAILER, 72, 87)        # flight action
card(find("40 pounds in a matter of months"), "TypeOn", {
     "text": "TRAIN LIKE\nDAVID CORENSWET\n+40 lbs for Superman",
     "accent": ACCENT, "variant": "quote"},
     span_until=find("outgrow before it was finished"))

# ---- PART 1: THE THEATER KID ----------------------------------------------
cut(S["kid"], GQV, 96, 128)
typeon(find("don't let that be an excuse"),
       ["\"...work harder than", "everybody else.\"",
        "- his high-school acting teacher"],
       span_until=find("everybody else"))
cut(find("last person he personally told"), GQV, 168, 187)
cut(find("Juilliard, class of 2016"), GQV, 72, 95)
typeon(find("super high intensity"),
       ["JUILLIARD MOVEMENT:", "\"almost to the point",
        "of being impossible.\""], span_until=find("being impossible"))
rows(find("by his own account"), "THE STARTING FRAME",
     ["6 ft 4 in tall", "About 195 pounds",
      "\"not very much for someone 6-4\""],
     span_until=find("not very much for somebody"))
cut(find("Politician made him a face"), GQV, 240, 252)

# ---- PART 2: TWO SECRETS --------------------------------------------------
doc(S["secrets"], "card_people_headline.jpg", "People", "cover story 2025",
    "the screen test - and the secret at home", pan=(0.0, 0.3))
cut(find("three Clark Kent"), TRAILER, 18, 22)
typeon(find("wife Julia told him she was pregnant"),
       ["TWO SECRETS,", "AT THE SAME TIME:", "the audition, and the baby"],
       span_until=find("tell no one about either"))
cut(find("we had these two quite huge secrets"), GQV, 328, 352)
typeon(find("can you prove that"),
       ["THE CALL:", "\"Hey David, it's James Gunn.\"",
        "\"...Can you prove that?\""], span_until=find("can you prove that"))
typeon(find("work on your shoulders and your vulnerability"),
       ["THE BRIEF:", "\"Work on your shoulders", "and your vulnerability.\"",
        "- James Gunn"], span_until=find("your vulnerability"))
rows(find("costume department built his suit"), "THE SUIT WAS BUILT FOR",
     ["6 ft 4 in", "195 pounds", "(remember that number)"],
     span_until=find("Six foot four"))

# ---- PART 3: THE LONELY MATH ----------------------------------------------
doc(S["math"], "card_gq_headline.jpg", "GQ", "July 11, 2025",
    "his trainer Paolo Mascitti broke down the plan", pan=(0.0, 0.28))
exloop(find("none of it was exotic"), "power_clean")
rows(find("Push, pull, legs"), "THE SPLIT",
     ["Push - presses", "Pull - pull-ups, pull-downs, rows",
      "Legs - squats", "5-6 days a week"],
     span_until=find("Five to six days a week"))
exloop(find("Presses, pull"), "deadlift")
typeon(find("progressive overload as the entire religion"),
       ["THE RELIGION:", "PROGRESSIVE OVERLOAD",
        "track the reps. track the weight.", "advance every week."],
       span_until=find("advance every week"))
card(find("Most sets in the six to"), "StatCard", {
     "value": "6-12", "label": "reps, compounds", "accent": ACCENT},
     span_until=find("finish the muscle off"))
doc(find("published push day looks like this"),
    "card_gq_workout_list.jpg", "GQ - Mascitti's program", "2025",
    "his actual published push day", pan=(0.0, 0.55))
rows(find("Bench press superset"), "THE PUSH DAY",
     ["Incline dumbbell press", "Bench press + cable fly",
      "Shoulder press + lateral raise", "Triceps + curls",
      "4 x 10, last set to failure"],
     span_until=find("last set to failure"))
cut(find("this body had a job"), BTS, 94, 100)
cut(find("surviving the wires"), BTS, 56, 74)
typeon(find("holding every limb in one steady"),
       ["\"strung up by my underpants,", "holding every limb",
        "in one steady, exact position.\""],
       span_until=find("steady, exact position"))
typeon(find("His one weakness, per his trainer"),
       ["HIS ONE WEAKNESS:", "walking lunges.",
        "\"great at squats, just hates lunges.\""],
       span_until=find("with jazz in his headphones"))
card(find("best training quote of the year"), "TypeOn", {
     "text": "\"There is a certain loneliness\nthat comes at the gym.\"",
     "accent": ACCENT, "variant": "quote", "cps": 26})
typeon(find("going for that ninth rep"),
       ["\"...on the ninth rep,", "nobody's going to do it for you.",
        "It's just you, alone in your mind.\"", "- David Corenswet"],
       span_until=find("further than you thought you could"))

# ---- PART 4: THE FUEL -----------------------------------------------------
card(find("aiming for about"), "StatCard", {
     "value": "4,500", "label": "calories/day (his number)",
     "accent": ACCENT})
doc(find("peak even higher"), "card_bi_headline.jpg", "Business Insider",
    "May 31, 2025", "his trainer's diet breakdown", pan=(0.0, 0.3),
    span_until=find("trade a little mass for definition"))
rows(find("50 % carbs"), "THE MACROS",
     ["50% carbs", "30% protein", "20% fat", "~7 meals a day"],
     span_until=find("seven meals and snacks a day"))
card(find("Breakfast alone"), "PhotoTiles2", {
     "title": "BREAKFAST (ONE OF SEVEN)",
     "tiles": [{"src": durl(FOOD / "egg_whites.jpg"),
                "label": "6 egg whites + 2 eggs", "atMs": 300},
               {"src": durl(FOOD / "oats.jpg"),
                "label": "2 cups oatmeal", "atMs": 900},
               {"src": durl(FOOD / "berries.jpg"), "label": "Berries",
                "atMs": 1500},
               {"src": durl(FOOD / "greek_yogurt.jpg"),
                "label": "Greek yogurt + almonds", "atMs": 2100},
               {"src": durl(FOOD / "protein_shake.jpg"),
                "label": "Protein shake", "atMs": 2700}]},
     span_until=find("a protein shake"))
card(find("rice, beef, chicken, fish"), "PhotoTiles2", {
     "title": "THEN, ON REPEAT",
     "tiles": [{"src": durl(FOOD / "rice.jpg"), "label": "Rice",
                "atMs": 300},
               {"src": durl(FOOD / "beef.jpg"), "label": "Beef",
                "atMs": 800},
               {"src": durl(FOOD / "chicken.jpg"), "label": "Chicken",
                "atMs": 1300},
               {"src": durl(FOOD / "salmon.jpg"), "label": "Fish",
                "atMs": 1800},
               {"src": durl(FOOD / "broccoli.jpg"), "label": "Vegetables",
                "atMs": 2300}]},
     span_until=find("carbs stacked before training"))
cut(find("quality of the calories mattered"), GQV, 192, 203)
card(find("he loves cereal"), "PhotoTiles2", {
     "title": "HIS KRYPTONITE",
     "tiles": [{"src": durl(FOOD / "cereal.jpg"),
                "label": "\"What's wrong with cereal?\"", "atMs": 300}]},
     span_until=find("what's wrong with cereal"))
typeon(find("everything is part of the puzzle"),
       ["THE THIRD PILLAR: SLEEP", "\"Take one of the things out,",
        "and it's not going to happen.\"", "- Paolo Mascitti"],
       span_until=find("not going to happen"))

# ---- PART 5: THE DOUBLE FORTY ---------------------------------------------
cut(S["forty"], GQV, 288, 292)
typeon(find("his wife was pregnant with their first child"),
       ["THE DOUBLE FORTY", "she gained ~40 lb pregnant.",
        "he gained ~40 lb for Superman.", "the same months."],
       span_until=find("in the same months"))
typeon(find("had to use her pregnancy pillow"),
       ["\"I started snoring,", "and had to use her",
        "pregnancy pillow.\""], span_until=find("her pregnancy pillow"))
typeon(find("It was a tape measure"),
       ["THE PROOF WASN'T A SELFIE.", "IT WAS A TAPE MEASURE."],
       span_until=find("It was a tape measure"))
rows(find("first costume fitting"), "THE FITTING",
     ["Suit built for 195 lb", "He arrived at 240 lb",
      "\"a bit of a squeeze\""],
     span_until=find("a bit of a squeeze"))

# ---- PART 6: SUPERMAN WITH A BRUISE ---------------------------------------
cut(S["bruise"], BTS, 56, 74)
cut(find("flying leap you"), TRAILER, 72, 87)
typeon(find("I couldn't lie about that"),
       ["THE STUNTS WERE REAL:", "he bruised himself on the flying take",
        "\"I couldn't lie about that. It's on film.\""],
       span_until=find("It's on film"))
cut(find("Superman opened to roughly"), TRAILER, 133, 138)
typeon(find("2019 rumor had become a fact"),
       ["THE 2019 RUMOR - A FACT.", "THE 2020 PETITION - A PROPHECY."],
       span_until=find("become a prophecy"))
typeon(find("more like a farm boy"),
       ["THE DESIGN BRIEF:", "\"a farm boy,",
        "not a complete bodybuilder.\"", "- Paolo Mascitti"],
       span_until=find("than a complete bodybuilder"))

# ---- PART 7: DO IT AGAIN --------------------------------------------------
cut(S["again"], TRAILER, 24, 34)
rows(find("Cameras rolled again"), "MAN OF TOMORROW",
     ["Announced Sept 2025", "Filming from April 2026",
      "In theaters July 2027"],
     span_until=find("July 2027 release"))
cut(find("the lonely math is running again"), TRAILER, 42, 45)

# ---- THE PLAN -------------------------------------------------------------
exloop(find("rules his team actually used"), "pushup")
typeon(find("train for the roll"),
       ["RULE 1", "TRAIN FOR THE ROLE,", "NOT THE MIRROR."],
       span_until=find("shoulders, and vulnerability"))
exloop(find("push, pull, legs, forever"), "deadlift")
typeon(find("progressive overload you actually write down"),
       ["RULE 2 - PUSH / PULL / LEGS", "6-12 reps, big compounds,",
        "overload you write down."], span_until=find("write down"))
typeon(find("master the lift, not the show"),
       ["RULE 3 - MASTER THE LIFT", "full range of motion.",
        "own the negative. add every week."],
       span_until=find("add weight or reps every week"))
card(find("eat like it"), "PhotoTiles2", {
     "title": "RULE 4 - EAT LIKE IT'S YOUR JOB",
     "tiles": [{"src": durl(FOOD / "chicken.jpg"), "label": "Protein",
                "atMs": 300},
               {"src": durl(FOOD / "rice.jpg"), "label": "Carbs pre-train",
                "atMs": 1000},
               {"src": durl(FOOD / "broccoli.jpg"), "label": "Real food",
                "atMs": 1700}]},
     span_until=find("the scale has no choice"))
typeon(find("sleep is the third pillar"),
       ["RULE 5 - SLEEP", "the third pillar.",
        "take one piece out, the puzzle breaks."],
       span_until=find("the puzzle doesn"))
card(find("keep your kryptonite"), "PhotoTiles2", {
     "title": "RULE 6 - KEEP YOUR KRYPTONITE",
     "tiles": [{"src": durl(FOOD / "cereal.jpg"),
                "label": "his was cereal - he kept it", "atMs": 300}]},
     span_until=find("kept it, and it kept him sane"))

# ---- OUTRO ----------------------------------------------------------------
card(find("could you even finish his breakfast"), "CommentPrompt", {
     "a": "I'd finish the breakfast",
     "b": "Meal 2 of 7 ends me",
     "prompt": "Could you eat like Superman?"},
     span_until=find("finish you first"))
card(find("subscribe"), "SubscribeCard", {"safeZone": True},
     span_until=order[-1])

json.dump(A, open(MAN / "assets_v5.json", "w"), indent=1)

# ---- interludes (his own voice) -------------------------------------------
inters = [
 {"id": "int_mandate", "after": find("Six foot four"),
  "vid": GQV, "t0": 422.8, "t1": 434.8,
  "label": "David Corenswet — GQ, 2025", "mode": "video",
  "crop_box": NOCROP},
 {"id": "int_stunts", "after": find("steady, exact position"),
  "vid": GQV, "t0": 322.4, "t1": 337.3,
  "label": "David Corenswet — GQ, 2025", "mode": "video",
  "crop_box": NOCROP},
 {"id": "int_yogurt", "after": find("what's wrong with cereal"),
  "vid": "bv3W8GmhYZM", "t0": 765.2, "t1": 777.4,
  "label": "David Corenswet — on his diet, 2025",
  "mode": "audio_over", "broll": [[GQV, 96, 128]]},
 {"id": "int_240again", "after": find("ninth rep nobody can do for you"),
  "vid": "bv3W8GmhYZM", "t0": 2371.8, "t1": 2375.2,
  "label": "David Corenswet, 2025", "mode": "audio_over",
  "broll": [[TRAILER, 133, 138]]},
]
json.dump(inters, open(MAN / "interludes.json", "w"), indent=1)

# ---- bugs: chapter chips + sub bug ----------------------------------------
bugs = {}
for sec, part, title in [("kid", "PART 1", "THE THEATER KID"),
                         ("secrets", "PART 2", "TWO SECRETS"),
                         ("math", "PART 3", "THE LONELY MATH"),
                         ("fuel", "PART 4", "THE FUEL"),
                         ("forty", "PART 5", "THE DOUBLE FORTY"),
                         ("bruise", "PART 6", "THE PAYOFF"),
                         ("plan", "PART 7", "YOUR TURN")]:
    if A.get(S[sec], {}).get("type") != "spanned":
        bugs[S[sec]] = {"comp": "ChapterChip",
                        "props": {"part": part, "title": title}}
lsb = find("Politician made him a face")
if A.get(lsb, {}).get("type") != "spanned":
    bugs[lsb] = {"comp": "LikeSubBug", "props": {}}
json.dump(bugs, open(MAN / "bugs.json", "w"), indent=1)

cards = sum(1 for a in A.values() if a.get("type") == "v5card")
cuts = sum(1 for a in A.values() if a.get("type") == "cut")
david = sum(1 for a in A.values() if a.get("type") == "cut"
            and "exloop" not in a["vid"])
gym = sum(1 for a in A.values() if a.get("type") == "cut"
          and "exloop" in a["vid"])
spanned = sum(1 for a in A.values() if a.get("type") == "spanned")
print(f"[OK] {len(A)} beats: {cards} cards, {cuts} cuts "
      f"({david} David / {gym} generic-demo), {spanned} spanned, "
      f"{len(inters)} interludes, {len(bugs)} bugs")
