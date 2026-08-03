"""Apply the owner's review-deck notes to the picture plan.

Every change below is traceable to a numbered slide note in
manifest/deck_feedback.json. The two direction changes he confirmed:
rule 9 relaxed (anonymous people may perform the activity) and his linked
third-party images used as commentary with on-screen credit.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
q = ROOT / "pipeline/picture_plan_v8.py"
t = q.read_text(encoding="utf-8")

NEW = '''
# ------------------------------------------------- owner-supplied assets
# Linked by the owner in the review deck. Third-party press and commercial
# images, used on his instruction as commentary, each credited on screen to
# its outlet and again in the description. A deliberate departure from the
# film's previous position (Pexels + Wikimedia CC + his own posts only).
#
# Resolution caveats, both real: the drvaidji render is 600x394 and their CDN
# serves no larger master, and the Tenor capture is 640x360. Neither is blown
# up to fill 1920 - the render is fitted, the clip is placed inset - because
# an obvious upscale is its own defect.
CLIPS = {
    # key: (path, credit main, credit sub, width as a fraction of the frame)
    "tenor_100m": ("dossier/mrbeast/owner_links/tenor_100m.mp4",
                   "TENOR", "100 MILLION SUBSCRIBERS", 0.60),
}

# "five little images of real images of people with Crohn's disease and it
# just flashes in and out for like five seconds" - the owner, slide 31.
# These are the clinical photographs previously held back under rule 13. He
# asked for them directly, so they run as a fast graded sequence rather than
# a single held image.
FLASH = {
    "crohns_real": ([
        "dossier/mrbeast/medical/badas_crohn.jpg",
        "dossier/mrbeast/medical/skin_leg.jpg",
        "dossier/mrbeast/medical/severe_colitis.jpg",
        "dossier/mrbeast/medical/skin_leg2.jpg",
        "dossier/mrbeast/medical/crohn_resected.jpg",
    ], "CLINICAL - WIKIMEDIA COMMONS", "CC0 / CC BY / CC BY-SA 4.0"),
}

'''
anchor = "# ------------------------------------------------------------------- plan"
assert anchor in t
t = t.replace(anchor, NEW + anchor, 1)

DOCS_ADD = '''    "ccf_page":     ("work/docs_v8/ccf_page.png",
                     (0.0, 0.0, 0.0, 0.04), 0.03, True),
    # --- owner-supplied, credited on screen ---
    "nypost_before": ("dossier/mrbeast/owner_links/nypost_transformation.jpg",
                      (0.0, 0.06, 0.0, 0.06), 0.05, True,
                      "NEW YORK POST", "JUNE 2023"),
    "drvaidji_3d":  ("dossier/mrbeast/owner_links/drvaidji_crohns.jpg",
                     (0.0, 0.0, 0.0, 0.0), 0.02, True,
                     "DRVAIDJI.COM", "CROHN'S DISEASE"),
    "menshealth_ba": ("dossier/mrbeast/owner_links/menshealth_beforeafter.jpg",
                      (0.0, 0.0, 0.0, 0.0), 0.03, True,
                      "MEN'S HEALTH UK", "190 LB TO 139 LB"),'''
OLD_DOCS = '''    "ccf_page":     ("work/docs_v8/ccf_page.png",
                     (0.0, 0.0, 0.0, 0.04), 0.03, True),'''
assert OLD_DOCS in t
t = t.replace(OLD_DOCS, DOCS_ADD, 1)

S = [
 ('seg(-1, [(1, ("jimmy", {"prefer": "FjrJ2DJN_pA"}))],\n    "lead-in: his face, held, before a word is spoken")',
  'seg(-1, [(1, ("doc", "nypost_before"))],\n    "OWNER slide 1: do not lead on a talking head - open on the photograph")'),
 ('seg(0, [(1, ("card", "card_machine")), (1, ("jimmy", {"prefer": "c8VcUnz3nVc"}))],',
  'seg(0, [(1, ("clip", "tenor_100m")), (1, ("broll", "editing"))],'),
 ('seg(1, [(1, ("sync",))],',
  'seg(1, [(1, ("broll", "tired"))],'),
 ('seg(2, [(1, ("jimmy", {"avoid": "cLRLEnPaJLM"})), (1, ("broll", "bed"))],',
  'seg(2, [(1, ("broll", "tired")), (1, ("broll", "bed"))],'),
 ('seg(4, [(1, ("jimmy", {}))],\n    "beat before the origin chapter: held on him")',
  'seg(4, [(1, ("broll", "athlete"))],\n    "OWNER slide 9: stock. Beat into the origin chapter")'),
 ('seg(5, [(1, ("broll", "bb_gear")), (1, ("broll", "bb_field")),\n        (1, ("broll", "bb_gear"))],',
  'seg(5, [(1, ("broll", "athlete")), (1, ("broll", "training")),\n        (1, ("broll", "athlete"))],'),
 ('seg(6, [("fix", 6.0, ("sync",)), (1, ("teen",))],',
  'seg(6, [("fix", 6.0, ("sync",)), (1, ("broll", "bb_gear"))],'),
 ('seg(6.5, [(1, ("doc", "his2015card"))],',
  'seg(6.5, [(1, ("broll", "bb_field"))],'),
 ('seg(7, [(1, ("doc", "niddk_def")), (1, ("still", "tract")),\n        (1, ("still", "intestine"))],',
  'seg(7, [(1, ("doc", "drvaidji_3d")), (1, ("still", "tract")),\n        (1, ("still", "intestine"))],'),
 ('seg(7, [(1, ("doc", "niddk_def")), (1, ("jimmy", {})),\n        (1, ("still", "tract"))],',
  'seg(7, [(1, ("doc", "drvaidji_3d")), (1, ("still", "tract")),\n        (1, ("still", "intestine"))],'),
 ('seg(8, [("fix", 6.0, ("sync",)), (1, ("card", "card_weight")),\n        (1, ("broll", "bb_field"))],',
  'seg(8, [("fix", 6.0, ("sync",)), (1, ("doc", "menshealth_ba")),\n        (1, ("broll", "bb_field"))],'),
 ('seg(9, [(1, ("teen",)), (1, ("doc", "dash_2015")), (1, ("jimmy", {}))],',
  'seg(9, [(1, ("broll", "editing")), (1, ("doc", "dash_2015")),\n        (1, ("broll", "athlete"))],'),
 ('seg(11, [(1, ("jimmy", {})), (1, ("broll", "clinic"))],',
  'seg(11, [(1, ("broll", "gut_pain")), (1, ("broll", "clinic"))],'),
 ('seg(12, [("fix", 6.0, ("sync",)), (1, ("broll", "food")),\n         ("fix", 2.2, ("still", "mech_right")), (1, ("jimmy", {}))],',
  'seg(12, [("fix", 6.0, ("sync",)), (1, ("broll", "gut_pain")),\n         ("fix", 5.0, ("flash", "crohns_real")), (1, ("broll", "eating"))],'),
 ('seg(13, [(1, ("doc", "niddk_diet")), ("fix", 2.2, ("still", "villi")),\n         (1, ("broll", "food"))],',
  'seg(13, [(1, ("broll", "eating")), ("fix", 2.2, ("still", "villi")),\n         (1, ("broll", "gut_pain"))],'),
 ('seg(14, [(1, ("jimmy", {})), (1, ("still", "mech_left")),\n         (1, ("still", "intestine"))],',
  'seg(14, [(1, ("still", "mech_left")), (1, ("broll", "gut_pain")),\n         (1, ("still", "mech_right"))],'),
 ('seg(15, [(1, ("jimmy", {})), ("fix", 2.2, ("clin", "resected")),\n         (1, ("broll", "clinic")), (1, ("jimmy", {}))],',
  'seg(15, [(1, ("broll", "tired")), ("fix", 2.2, ("clin", "resected")),\n         (1, ("broll", "clinic")), (1, ("broll", "eating"))],'),
 ('seg(16, [("fix", 2.2, ("clin", "histology")), (1, ("teen",)),\n         (1, ("broll", "food"))],',
  'seg(16, [("fix", 2.2, ("clin", "histology")), (1, ("broll", "eating")),\n         (1, ("broll", "food"))],'),
 ('seg(17, [(1, ("broll", "clinic")), (1, ("broll", "clock")),\n         (1, ("doc", "ccf_page"))],',
  'seg(17, [(1, ("broll", "clinic")), (1, ("broll", "clock")),\n         (1, ("broll", "meds"))],'),
 ('seg(19, [(1, ("doc", "niddk_treat")), (1, ("broll", "clinic")),\n         (1, ("jimmy", {}))],',
  'seg(19, [(1, ("broll", "tired")), (1, ("broll", "clinic")),\n         (1, ("broll", "meds"))],'),
]

miss = []
applied = 0
for a, b in S:
    if a not in t:
        miss.append(a.split("\n")[0][:66])
        continue
    t = t.replace(a, b, 1)
    applied += 1
q.write_text(t, encoding="utf-8")
print(f"applied {applied} of {len(S)}")
for m in miss:
    print("  not found (may already be applied):", m)
