#!/usr/bin/env python3
"""bruce_treatments.py - per-beat treatments for TRAIN LIKE BRUCE LEE.

Windows from dossier/bruce_lee/WATCH_NOTES.md (verified watch pass).
Documents from library/bruce_refs (RESEARCH.md provenance). Anchors match
the faster-whisper transcript exactly (see beats.json texts).
Writes manifest/assets_v5.json, interludes.json, bugs.json.
"""
import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "manifest"
DOS = ROOT / "dossier" / "bruce_lee"
REF = ROOT / "library" / "bruce_refs"
FOOD = ROOT / "library" / "food"
EX = ROOT / "library" / "exloops"
ACCENT = "#F2C230"

beats = json.loads((MAN / "beats.json").read_text())["beats"]
bmap = {b["beat_id"]: b for b in beats}
order = [b["beat_id"] for b in beats]

BY, ODS, LB, EP, LM, WD = ("2yp-O580Ru0", "odsQwCAOU2k", "YHHQF1SHHLw",
                           "EP8yIiZD_os", "LmSu_gnF9pI", "-OI1zyajOpw")
CROPS = {
 BY:  [0.03, 0.15, 0.03, 0.15],
 ODS: [0.02, 0.14, 0.02, 0.14],
 LB:  [0.125, 0.14, 0.125, 0.11],
 EP:  [0.02, 0.14, 0.02, 0.14],
 LM:  [0.0, 0.03, 0.0, 0.03],
 WD:  [0.12, 0.0, 0.12, 0.0],
}
A = {}


def find(phrase):
    p = phrase.lower()
    for b in beats:
        if p in b["text"].lower().replace(" -", "-").replace("- ", "-"):
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
         "crop_box": CROPS[src]}
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
                         "cps": 30}, span_until)


def rows(bid, title, items, span_until=None):
    card(bid, "StepCards2",
         {"title": title,
          "steps": [{"text": t, "atMs": 250 + i * 650}
                    for i, t in enumerate(items)]}, span_until)


S = {
 "open":    "b_000", "kid": find("It starts in San Francisco"),
 "america": find("In 1959 he was sent"),
 "fight":   find("the fight that actually built"),
 "system":  find("where this story becomes"),
 "fuel":    find("The diet ran on one idea"),
 "twice":   find("in 1970, the whole machine stopped"),
 "thirty":  find("July 20, 1973"),
 "plan":    find("You need his rules"),
 "outro":   find("Honest question"),
}

POOLS = {
 "train": [(ODS, 4.0, 36.0), (ODS, 40.0, 58.0), (ODS, 65.0, 82.0),
           (BY, 518.0, 578.0), (BY, 1495.0, 1540.0), (BY, 1255.0, 1315.0),
           (BY, 1740.0, 1945.0), (BY, 1381.0, 1435.0), (BY, 561.0, 660.0),
           (EP, 65.0, 110.0)],
 "demo": [(LB, 12.0, 45.0), (LB, 65.0, 88.0), (LB, 165.0, 178.0),
          (LB, 195.0, 232.0), (LB, 235.0, 252.0), (LB, 270.0, 295.0),
          (LM, 26.0, 38.0), (LM, 43.0, 57.0), (EP, 165.0, 220.0),
          (EP, 440.0, 465.0)],
 "spar": [(LB, 305.0, 380.0), (LB, 395.0, 495.0)],
 "film": [(WD, 39.0, 46.0), (WD, 49.0, 68.0), (WD, 68.0, 85.0),
          (WD, 86.0, 108.0), (WD, 109.0, 125.0), (WD, 130.0, 137.0)],
}
_next = {k: 0 for k in POOLS}


def pool(bid, name):
    src, t0, t1 = POOLS[name][_next[name] % len(POOLS[name])]
    _next[name] += 1
    need = bmap[bid]["end"] - bmap[bid]["start"]
    lap = _next[name] // len(POOLS[name])
    t0a = t0 + lap * (need + 2.0)
    if t0a + need + 0.2 > t1:
        t0a = t0
    cut(bid, src, t0a, t1)


def section_of(i):
    cur = "open"
    for n, bid in S.items():
        if order.index(bid) <= i:
            cur = n
    return cur


FILL = {"open": "demo", "kid": "train", "america": "demo", "fight": "spar",
        "system": "train", "fuel": "train", "twice": "film",
        "thirty": "film", "plan": "train", "outro": "film"}
for i, bid in enumerate(order):
    pool(bid, FILL[section_of(i)])

# ---- COLD OPEN ----------------------------------------------------------
doc("b_000", "doc_definite_chief_aim_1969.jpg",
    "Bruce Lee Enterprises archive", "1969",
    "his handwritten letter to himself - stamped SECRET", pan=(0.0, 0.15))
doc(find("highest-paid Oriental"), "doc_definite_chief_aim_1969.jpg",
    "My Definite Chief Aim", "1969",
    "\"...the first highest paid Oriental super star\"",
    pan=(0.18, 0.6), span_until=find("$10 million"))
cut(find("His TV show had been cancelled"), LB, 92.0, 105.0)
cut(find("Four years later"), WD, 39.0, 46.0)
typeon(find("This is how Bruce Lee built"),
       ["TRAIN LIKE BRUCE LEE", "built twice. written down."])
doc(find("he wrote it all down"), "doc_tao_jkd_sequence_training_p1.png",
    "Tao of Jeet Kune Do", "published 1975",
    "his actual training notes - it's all on paper", pan=(0.05, 0.35))

# ---- PART 1: THE KID ----------------------------------------------------
doc(S["kid"], "photo_infant_3months.jpg", "family archive", "1940",
    "Lee Jun-fan, three months old", pan=(0.0, 0.3))
doc(find("given a girl"), "photo_1940s_child_with_parents.jpg",
    "family archive", "1940s", "\"small phoenix\" - with his parents",
    pan=(0.05, 0.4))
doc(find("child movie actor by six"), "photo_1946_child_actor.jpg",
    "The Birth of Mankind", "1946", "a working actor at six years old",
    pan=(0.0, 0.35))
cut(find("rooftops, fight after fight"), EP, 5.0, 55.0)
cut(find("he was taken to learn"), EP, 65.0, 110.0)
cut(find("European blood"), BY, 518.0, 578.0)
rows(find("1958 he proved the point"), "1958 - SAME YEAR",
     ["KO - Hong Kong schools boxing final",
      "1st - Crown Colony cha-cha title"],
     span_until=find("cha-cha championship"))

# ---- PART 2: AMERICA / LONG BEACH ---------------------------------------
cut(S["america"], ODS, 4.0, 36.0)
cut(find("University of Washington"), BY, 1255.0, 1315.0)
cut(find("teaching his own kung fu"), BY, 1740.0, 1830.0)
cut(find("August 1964"), LB, 165.0, 178.0)
cut(find("Push-ups on two fingers"), LM, 3.0, 12.0)
cut(find("a punch thrown from one inch"), LB, 195.0, 232.0)
typeon(find("Bob Baker, later said"),
       ["\"I had to stay home from work.",
        "The pain in my chest was unbearable.\"",
        "- Bob Baker, volunteer"],
       span_until=find("unbearable"))

# ---- PART 3: THE FIGHT --------------------------------------------------
cut(S["fight"], LB, 305.0, 380.0)
cut(find("A challenge from a kung fu man"), LB, 395.0, 495.0)
cut(find("his wife said three minutes"), LB, 320.0, 380.0)
cut(find("He was winded"), BY, 1495.0, 1540.0)
typeon(find("I realized Wing Chun was not"),
       ["\"I realized Wing Chun was not too",
        "practical, and began to alter",
        "my way of fighting.\"", "- Black Belt magazine"])
cut(find("won a fight and changed everything"), ODS, 40.0, 58.0)

# ---- PART 4: THE SYSTEM ON PAPER ----------------------------------------
doc(find("documented, in his own handwriting"),
    "doc_letter_1965-08-06_training_program.png",
    "Letters of the Dragon", "Aug 6, 1965",
    "the written program he mailed from Hong Kong", pan=(0.0, 0.45))
doc(find("limbering for the waist"),
    "doc_letter_1965-08-06_training_program.png",
    "Letters of the Dragon", "Aug 6, 1965",
    "limbering, punching, kicking, technique", pan=(0.45, 0.75))
typeon(find("the hell with conventional methods"),
       ["\"The hell with conventional",
        "methods and opinions.\"", "- letter, Aug 1965"])
cut(find("equipment starts appearing"), BY, 1740.0, 1830.0)
cut(find("Eight iron rings"), EP, 65.0, 110.0)
cut(find("wrist roller and a grip machine"), BY, 1830.0, 1900.0)
typeon(find("protein powder, ordered across"),
       ["\"As of today, I haven't yet",
        "received the protein... it should",
        "arrive tomorrow.\"", "- letter, 1965"],
       span_until=find("arrive tomorrow"))
cut(find("mixing supplements before most gyms"), ODS, 65.0, 82.0)
doc(find("January 1968, the system"),
    "doc_letter_1968-01_daily_training_isometrics.png",
    "Letters of the Dragon", "Jan 1968",
    "\"I now train an average of two-and-a-half hours a day\"",
    pan=(0.1, 0.5), span_until=find("free hand exercises"))
rows(find("Monday, Wednesday, Friday"), "SEQUENCE 1 - MON WED FRI",
     ["Rope jumping", "Forward bend + cat stretch", "Jumping jack",
      "Squat", "High kick"], span_until=find("squat, high kick"))
rows(find("Tuesday, Thursday, Saturday"), "SEQUENCE 2 - TUE THU SAT",
     ["Groin stretch + side leg raise", "Jumping squat",
      "Shoulder circling", "Alternate splits", "Leg stretch"],
     span_until=find("alternate splits, leg stretch"))
rows(find("forearm and waist sequence"), "FOREARM + WAIST",
     ["Waist twisting + side bends", "Palm-up / palm-down curls",
      "Roman chair", "Wrist roller"])
doc(find("press lockout"), "doc_tao_jkd_sequence_training_p2_power.png",
    "Tao of Jeet Kune Do", "his notes, pub. 1975",
    "the nine-station power routine",
    pan=(0.1, 0.55), span_until=find("frog kick"))
doc(find("in 24 to 25 minutes"),
    "doc_fighting_method_1977_pp16-17_running_exercycle.png",
    "Bruce Lee's Fighting Method", "1977",
    "4 miles a day in 24-25 minutes", pan=(0.0, 0.4))
doc(find("35 to 40 miles an hour"),
    "doc_fighting_method_1977_pp16-17_running_exercycle.png",
    "Bruce Lee's Fighting Method", "1977",
    "the exercycle: 35-40 mph, 45-60 minutes", pan=(0.5, 0.85))
typeon(find("training is one of the most neglected"),
       ["\"Training is one of the most",
        "neglected phases of athletics.\"", "- Tao of Jeet Kune Do"],
       span_until=find("development of the individual"))

# ---- PART 5: FUEL -------------------------------------------------------
card(find("high performance engine"), "PhotoTiles2", {
     "title": "FOOD = FUEL",
     "tiles": [{"src": durl(FOOD / "rice.jpg"), "label": "Rice",
                "atMs": 300},
               {"src": durl(FOOD / "greens.jpg"), "label": "Vegetables",
                "atMs": 800},
               {"src": durl(FOOD / "salmon.jpg"), "label": "Fish",
                "atMs": 1300},
               {"src": durl(FOOD / "beef.jpg"), "label": "Beef",
                "atMs": 1800},
               {"src": durl(FOOD / "shrimp.jpg"), "label": "Shrimp",
                "atMs": 2300},
               {"src": durl(FOOD / "tofu.jpg"), "label": "Tofu",
                "atMs": 2800}]},
     span_until=find("chicken, tofu"))
rows(find("Four or five smaller meals"), "THE PATTERN",
     ["4-5 small meals a day", "Fruit between meals",
      "Zero empty calories"])
card(find("powdered milk, blended"), "PhotoTiles2", {
     "title": "THE SHAKE",
     "tiles": [{"src": durl(FOOD / "protein_shake.jpg"),
                "label": "Powdered-milk protein shake", "atMs": 300},
               {"src": durl(FOOD / "greens.jpg"),
                "label": "Vegetables in the blender", "atMs": 1100},
               {"src": durl(FOOD / "tea.jpg"), "label": "Tea, not coffee",
                "atMs": 1900}]},
     span_until=find("never coffee"))

# ---- PART 6: BUILT TWICE ------------------------------------------------
doc(S["twice"], "doc_tao_jkd_1975_intro_back_injury.png",
    "Tao of Jeet Kune Do, introduction", "1975",
    "\"flat on his back for six months\"",
    pan=(0.1, 0.5), span_until=find("six months"))
typeon(find("Most careers end there"),
       ["Most careers end there.", "Bruce Lee wrote."])
doc(find("became Tao of Jeet"), "doc_jkd_manuscript_title_page.png",
    "his JKD typescript", "c. 1971",
    "the notes from that bed became a book", pan=(0.0, 0.35))
cut(find("rebuilt the body a second time"), WD, 49.0, 68.0)
cut(find("Fist of Fury broke them again"), WD, 68.0, 85.0)
doc(find("October 1971"),
    "doc_letter_1971-10-28_golden_harvest_back_injury_note.png",
    "Golden Harvest letterhead", "Oct 28, 1971",
    "\"damn the torpedo, full speed ahead!!\"",
    pan=(0.05, 0.45), span_until=find("Full speed ahead"))
cut(find("the longest on-camera interview"), WD, 109.0, 125.0)
cut(find("wouldn't put a Chinese lead"), WD, 130.0, 137.0)

# ---- PART 7: THIRTY-TWO -------------------------------------------------
doc(S["thirty"], "photo_1973.jpg", "1973", "his final year", "",
    pan=(0.0, 0.3))
doc(find("cerebral edema"), "photo_1973_ap_death.jpg",
    "AP wire photo", "July 1973", "the news went worldwide",
    pan=(0.0, 0.25))
rows(find("Five foot seven and a half"), "BRUCE LEE",
     ["5 ft 7 1/2 in", "141 pounds", "32 years old"],
     span_until=find("who ever lived"))
doc(find("He left the paperwork"),
    "doc_letter_1965-08-06_training_program.png",
    "Letters of the Dragon", "1958-1973",
    "seven years of letters, planners and logs",
    pan=(0.2, 0.6), span_until=find("workout diaries and letters"))

# ---- THE PLAN -----------------------------------------------------------
exloop(find("train the engine"), "boxing")
exloop(find("circuit your week"), "jump_rope")
exloop(find("your cardio"), "trail_run")
exloop(find("build the details"), "high_kick")
card(find("fuel like an engine"), "PhotoTiles2", {
     "title": "RULE 5 - FUEL",
     "tiles": [{"src": durl(FOOD / "rice.jpg"), "label": "Real food",
                "atMs": 300},
               {"src": durl(FOOD / "salmon.jpg"), "label": "Protein",
                "atMs": 1000},
               {"src": durl(FOOD / "greens.jpg"),
                "label": "No empty calories", "atMs": 1700}]})
typeon(find("absorb what is useful"),
       ["\"Absorb what is useful...", "the hell with conventional",
        "methods and opinions.\""])

# ---- OUTRO --------------------------------------------------------------
card(find("drop your answer in the comments"), "CommentPrompt", {
     "a": "I'd survive the circuits",
     "b": "The 4-mile run ends me",
     "prompt": "Could you survive his day?"},
     span_until=find("circuits even start"))
card(find("subscribe"), "SubscribeCard", {"safeZone": True},
     span_until=order[-1])

json.dump(A, open(MAN / "assets_v5.json", "w"), indent=1)

inters = [
 {"id": "int_styles", "after": find("won a fight and changed everything"),
  "vid": "uk1lzkH-e4U", "t0": 419.9, "t1": 458.0,
  "label": "Bruce Lee — The Pierre Berton Show, 1971",
  "mode": "audio_over", "broll": [["2yp-O580Ru0", 1740.0, 1790.0]]},
 {"id": "int_trainbody",
  "after": find("development of the individual"),
  "vid": "uk1lzkH-e4U", "t0": 488.5, "t1": 537.2,
  "label": "Bruce Lee — The Pierre Berton Show, 1971",
  "mode": "video", "crop_box": [0.125, 0.10, 0.125, 0.16]},
 {"id": "int_water", "after": find("half a century later"),
  "vid": "uk1lzkH-e4U", "t0": 948.5, "t1": 975.7,
  "label": "Bruce Lee — \"Be water, my friend\", 1971",
  "mode": "audio_over", "broll": [["-OI1zyajOpw", 109.0, 137.0]]},
 {"id": "int_hollywood",
  "after": find("wouldn't put a Chinese lead"),
  "vid": "uk1lzkH-e4U", "t0": 1162.9, "t1": 1181.1,
  "label": "Bruce Lee — The Pierre Berton Show, 1971",
  "mode": "audio_over", "broll": [["YHHQF1SHHLw", 165.0, 190.0]]},
]
json.dump(inters, open(MAN / "interludes.json", "w"), indent=1)

bugs = {}
for sec, label in [("kid", "PART 1 · THE KID"),
                   ("america", "PART 2 · ONE INCH"),
                   ("fight", "PART 3 · THE FIGHT"),
                   ("system", "PART 4 · THE SYSTEM"),
                   ("fuel", "PART 5 · THE FUEL"),
                   ("twice", "PART 6 · BUILT TWICE"),
                   ("plan", "PART 7 · YOUR TURN")]:
    if A.get(S[sec], {}).get("type") != "spanned":
        bugs[S[sec]] = {"comp": "ChapterChip",
                        "props": {"label": label, "accent": ACCENT}}
bugs[find("University of Washington")] = {"comp": "LikeSubBug",
                                          "props": {}}
json.dump(bugs, open(MAN / "bugs.json", "w"), indent=1)

cards = sum(1 for a in A.values() if a.get("type") == "v5card")
cuts = sum(1 for a in A.values() if a.get("type") == "cut")
spanned = sum(1 for a in A.values() if a.get("type") == "spanned")
lee = sum(1 for a in A.values() if a.get("type") == "cut"
          and "exloop" not in a["vid"])
print(f"[OK] {len(A)} beats: {cards} cards, {cuts} cuts "
      f"({lee} real-Lee), {spanned} spanned, {len(inters)} interludes, "
      f"{len(bugs)} bugs")
