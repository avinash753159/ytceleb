#!/usr/bin/env python3
"""The shot plan: what is on screen for every second of the locked audio.

Read with `manifest/edl_full.json` open beside it. Segment numbers here are
EDL segment indices, and the EDL is the ONLY source of timing - the previous
build took timings from a Whisper transcript, which merges long pauses, so
baseball footage landed twelve seconds early on top of a silent title break.

Each segment maps to a list of SLOTS that tile it exactly. A slot is
(duration_share, spec). Shares are relative, so a segment of 12.4s with
shares (1, 1, 1) becomes three 4.13s shots. A slot may instead fix its
duration with ("fix", seconds) as the first element, which is how clinical
stills are held to ~2.2s.

Slot specs
----------
("sync",)            the actual moment, from this bite's own source and
                     timecode - his lips match the words. Only where a
                     window survived the identity pass AND the burned-in
                     text screen.
("jimmy", ...)       any unspent verified window of present-day Jimmy.
                     `avoid` / `prefer` name source ids.
("teen",)            2015 bedroom archive, archive treatment.
("doc", key)         a real screenshot or scanned page. No lower-third:
                     rule 10 gives credits only to interview sources.
("still", key)       licensed medical diagram, cropped away from its labels.
("clin", key)        licensed clinical photograph. Held ~2.2s, faded both
                     ends, never captioned or implied to be Jimmy.
("broll", group)     an unspent OBJECT-class stock clip from `group`.
                     No people: rule 9.
("card", key)        a card this film rendered.

Why some bites get no sync
--------------------------
Six bites (34, 36, 53, 55, 67, 69) come from Airrack's video. Twelve windows
there were frame-checked in an earlier session and not one is Jimmy alone, so
the audio stays and the picture goes elsewhere. Cutting to Jimmy in a
DIFFERENT room while his voice runs would fake a sync that does not exist, so
those bites are carried by objects, documents and cards instead.

Two more (18, 20) are Jimmy in the Rogan studio at a moment when Rogan had the
Crohn's & Colitis Foundation website up on a monitor that sits in frame. The
panel overlaps him horizontally, so no crop removes it. Both go illustrative.
"""

from __future__ import annotations

# ---------------------------------------------------------------- documents
# Real captures and scans only. Nothing this film drew and dressed up as
# evidence: the previous post card was hand-lettered in Anton on a dark
# rectangle and read as a graphic, which is the opposite of what a primary
# document is for.
DOCS = {
    # (path, crop box l/t/r/b, push, fit-to-frame?)
    "post_obese":   ("work/post_cards/post_obese.png", (0, 0, 0, 0), 0.05, False),
    "post_gains":   ("work/post_cards/post_gains.png", (0, 0, 0, 0), 0.05, False),
    # DEFINED BUT NOT DRAWN. Both are captures of his live channel page and
    # both say "510M subscribers", which the locked narration contradicts
    # ("three hundred million"). They are also light-mode white and their
    # thumbnail grids are full of other people. Kept here only so nobody
    # re-adds them without reading this.
    "yt_subs":      ("dossier/mrbeast/primary/yt_channel.png",
                     (0.02, 0.08, 0.40, 0.42), 0.10, False),
    "yt_grid":      ("dossier/mrbeast/primary/yt_videos.png",
                     (0.02, 0.30, 0.02, 0.06), 0.09, False),
    "niddk_def":    ("dossier/mrbeast/documents/niddk_definition.png",
                     (0.06, 0.34, 0.06, 0.16), 0.06, True),
    "niddk_treat":  ("dossier/mrbeast/documents/niddk_treatment.png",
                     (0.06, 0.36, 0.06, 0.14), 0.06, True),
    "niddk_diet":   ("dossier/mrbeast/documents/niddk_diet.png",
                     (0.06, 0.34, 0.06, 0.16), 0.06, True),
    # Lifted from his own uploads by prep_docs_v8.py. The dashboard is the
    # only hard number we have for where he actually started, and the dating
    # card is his own text, so both are documents rather than graphics.
    "dash_2015":    ("work/docs_v8/dash_2015.png",
                     (0.0, 0.0, 0.0, 0.0), 0.02, True),
    "his2015card":  ("work/docs_v8/his2015card.png", (0, 0, 0, 0), 0.06,
                     False),
    # FIT, not fill: the capture is 2.15:1, so filling to 16:9 crops 17% of
    # the width and cuts "What" off the heading. Fitted it sits inside the
    # frame with a shallow band top and bottom.
    "ccf_page":     ("work/docs_v8/ccf_page.png",
                     (0.0, 0.0, 0.0, 0.04), 0.03, True),
    # --- owner-supplied, credited on screen ---
    # NOTE the .png extensions. All three arrived from their servers as WEBP
    # or AVIF wearing a .jpg name, and ffmpeg's webp/avif demuxers reject
    # `-loop 1`, so a still could not be held: "Option loop not found".
    # Converted once to real PNG rather than re-fetched.
    "nypost_before": ("dossier/mrbeast/owner_links/nypost_transformation.png",
                      (0.0, 0.06, 0.0, 0.06), 0.05, True,
                      "NEW YORK POST", "JUNE 2023"),
    "drvaidji_3d":  ("dossier/mrbeast/owner_links/drvaidji_crohns.png",
                     (0.0, 0.0, 0.0, 0.0), 0.02, True,
                     "DRVAIDJI.COM", "CROHN'S DISEASE"),
    "menshealth_ba": ("dossier/mrbeast/owner_links/menshealth_beforeafter.png",
                      (0.0, 0.0, 0.0, 0.0), 0.03, True,
                      "MEN'S HEALTH UK", "190 LB TO 139 LB"),
}

# Medical diagrams. The `mechanism.png` figure is a fully labelled textbook
# plate - IL-12, TGF, Retinoic acid - and at speed it reads as homework, so
# each entry crops to the illustration and leaves the caption out of frame.
STILLS = {
    # (path, crop l/t/r/b, credit main, credit sub, fill-frame?)
    #
    # Every box here was retuned after looking at the rendered crop. The
    # first set still had the labels in frame: "Salivary g...", "Duodenum",
    # "Jejunum", "Ileum" on the anatomy plates, and "Normal" / "Crohn's
    # Disease" on the mechanism figure - which is also a narration echo,
    # because the script says exactly that over it.
    #
    # fill=True crops to fill the frame. The microscopy images are nearly
    # square and fitting them left black bars down both sides, which reads as
    # letterboxed archive.
    "tract":       ("dossier/mrbeast/medical/tract.png",
                    (0.33, 0.05, 0.33, 0.07), "WIKIMEDIA COMMONS", "CC BY",
                    False),
    "intestine":   ("dossier/mrbeast/medical/small_intestine.png",
                    (0.37, 0.30, 0.15, 0.14), "WIKIMEDIA COMMONS", "CC BY",
                    True),
    "mech_left":   ("dossier/mrbeast/medical/mechanism.png",
                    (0.05, 0.17, 0.55, 0.49), "WIKIMEDIA COMMONS", "CC0",
                    True),
    "mech_right":  ("dossier/mrbeast/medical/mechanism.png",
                    (0.53, 0.17, 0.05, 0.49), "WIKIMEDIA COMMONS", "CC0",
                    True),
    "villi":       ("dossier/mrbeast/medical/villi_closeup.jpg",
                    (0.20, 0.07, 0.20, 0.07), "WIKIMEDIA COMMONS", "CC BY",
                    True),

}

# Clinical photographs. Rule 13: short, faded, never implied to be Jimmy.
#
# Both surviving specimens carry third-party text that has to be cropped away:
# severe_colitis is photographed beside a ruler printed with "(800) 383-7796",
# and crohn_resected has a specimen label reading "1691 ILEON TERMINAL,
# CAECUM, COLON ASCENDANT" along its top edge.
#
# DROPPED, and why:
#   contact.jpg     is a CONTACT SHEET of the other medical images. It was in
#                   the clinical set and would have gone on screen as though
#                   it were evidence.
#   badas_crohn     bare feet and ankles with lesions
#   skin_leg(2)     a leg with an ulcer
#                   Both are identifiable human body parts, and rule 13 says
#                   clinical imagery must never be implied to be Jimmy. The
#                   film does not need them.
CLIN = {
    "histology": ("dossier/mrbeast/medical/villi_histology.jpg",
                  (0.06, 0.06, 0.06, 0.06), "WIKIMEDIA COMMONS", "CC BY"),
    # severe_colitis.jpg was DROPPED. It is "Severe ulcerative colitis.jpg",
    # and CREDITS2.json states the constraint itself: "Only usable if
    # captioned as related IBD, never as Crohn's." The film had it full-frame,
    # full-colour and uncaptioned under his own Crohn's bite - i.e. presenting
    # ulcerative colitis AS Crohn's, sixty seconds after showing the viewer
    # the NIDDK page that distinguishes them. In a film whose whole claim is
    # sourcing, that is the worst possible error.
    "resected": ("dossier/mrbeast/medical/crohn_resected.jpg",
                 (0.05, 0.30, 0.10, 0.30), "WIKIMEDIA COMMONS",
                 "CC BY-SA 4.0"),
}


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
# "it needs to be a parallax image of jimmy - use this feature" - the owner,
# slide 28. Depth layers are generated by pipeline/parallax.py, whose
# suitability gate passed this still at HIGH confidence (edge alignment 4.15,
# the only measure that actually discriminates). The QC contact sheet was
# checked by eye: the depth model cut him cleanly off the wall, which is the
# locked-off-subject case this technique works on.
PARALLAX = {
    # key: (layer name, layers dir, credit main, credit sub)
    "jimmy_symptoms": ("jimmy_symptoms", "work/parallax",
                       "THE DIARY OF A CEO", "YOUTUBE"),
}

FLASH = {
    "crohns_real": ([
        "dossier/mrbeast/medical/badas_crohn.jpg",
        "dossier/mrbeast/medical/skin_leg.jpg",
        "dossier/mrbeast/medical/severe_colitis.jpg",
        "dossier/mrbeast/medical/skin_leg2.jpg",
        "dossier/mrbeast/medical/crohn_resected.jpg",
    ], "CLINICAL - WIKIMEDIA COMMONS", "CC0 / CC BY / CC BY-SA 4.0"),
}

# ------------------------------------------------------------------- plan
# seg -> (slots, why-this-picture)
PLAN: dict[int, tuple[list, str]] = {}


def seg(i, slots, why):
    PLAN[i] = (slots, why)


# ============================================================ COLD OPEN
# 0.00-2.00 is the music lead-in ahead of the first word. Opening on his face,
# quiet and still, sets the contradiction up before the narration states it.
seg(-1, [(1, ("doc", "nypost_before"))],
    "OWNER slide 1: do not lead on a talking head - open on the photograph")

seg(0, [(1, ("card", "card_scale")), (1, ("clip", "tenor_100m"))],
    "'three hundred million subscribers ... a pace nobody has matched' - the "
    "8,726-to-300-million card, then him. His live channel page was cut here: "
    "it reads 510M subscribers, which contradicts the locked narration on "
    "screen, it is bright white against a dark film, and its thumbnails are "
    "full of other people")

seg(1, [(1, ("broll", "tired"))],
    "'one of the least energetic people you'll ever meet' - him saying it")

seg(2, [(1, ("broll", "tired")), (1, ("broll", "bed"))],
    "'since he was fifteen his immune system has been attacking him ... "
    "there are days it wins' - hold on him, then an empty bed for the days "
    "it wins. No stand-in lying in it")

seg(3, [(1, ("broll", "gym_room")), (1, ("doc", "post_obese"))],
    "'not a story about a workout ... what he did to take some of it back' "
    "- an empty gym, then his own June 2023 post in his own words")

seg(4, [(1, ("broll", "athlete"))],
    "OWNER slide 9: stock. Beat into the origin chapter")

# ============================================================ ORIGIN
seg(5, [(1, ("broll", "athlete")), (1, ("broll", "training")),
        (1, ("broll", "athlete"))],
    "'he was an athlete, a kid who played constantly' - equipment and an "
    "empty field. Rule 9: no stock child cast as young Jimmy")

seg(6, [("fix", 6.0, ("sync",)), (1, ("broll", "bb_gear"))],
    "'I played baseball nonstop, then when I got Crohn's I lost like 50 "
    "pounds' - him saying it, then his own 2015 footage, already thin")

seg(6.5, [(1, ("broll", "bb_field"))],
    "TITLE BREAK 54.10-58.10, music only. Held on the 2015 archive. The "
    "previous build put the 2023 post here, eight years out of place")

seg(7, [(1, ("doc", "drvaidji_3d")), (1, ("still", "tract")),
        (1, ("still", "intestine"))],
    "'the diagnosis had a name' - the NIDDK definition page, him, the tract")

seg(8, [("fix", 6.0, ("sync",)), (1, ("doc", "menshealth_ba")),
        (1, ("broll", "bb_field"))],
    "'190 pounds down to 139 ... not playing baseball in college anymore' - "
    "him, the two numbers, the field he left")

seg(9, [(1, ("broll", "editing")), (1, ("doc", "dash_2015")),
        (1, ("broll", "athlete"))],
    "'the illness closed one door and he ran at the other one' - the bedroom, "
    "his own 2015 dashboard at 8,726 subscribers, the bedroom again")

seg(10, [(1, ("broll", "desk"))],
    "beat: a desk at night, where the other door led")

# ============================================================ ILLNESS
seg(11, [(1, ("broll", "gut_pain")), (1, ("broll", "clinic"))],
    "'most videos skip this part' - him, then a corridor")

seg(12, [("fix", 6.0, ("parallax", "jimmy_symptoms")),
         (1, ("broll", "gut_pain")),
         ("fix", 5.0, ("flash", "crohns_real")), (1, ("broll", "eating"))],
    "'bathroom eight, nine, ten times a day, not digesting food' - him, an "
    "untouched plate, 2.2s of real inflamed bowel, back to him")

seg(13, [(1, ("broll", "eating")), ("fix", 2.2, ("still", "villi")),
         (1, ("broll", "gut_pain"))],
    "'a body that will not keep what you feed it. You can eat and still "
    "starve' - food, the villi that should absorb it, food")

seg(14, [(1, ("still", "mech_left")), (1, ("broll", "gut_pain")),
         (1, ("still", "mech_right"))],
    "the explainer: what Crohn's is, from the primary source and the diagrams")

seg(15, [(1, ("broll", "tired")), ("fix", 2.2, ("clin", "resected")),
         (1, ("broll", "clinic")), (1, ("broll", "eating"))],
    "'the inflammation goes through the entire thickness' - him, then 2.2s "
    "of a resected ileum whose wall is visibly thickened, which is better "
    "evidence for this sentence than a second diagram. mech_right was cut "
    "here: it is another crop of the mech_left figure and read as the same "
    "picture fifteen seconds later")

seg(16, [("fix", 2.2, ("clin", "histology")), (1, ("broll", "eating")),
         (1, ("broll", "food"))],
    "'explains a teenager losing fifty pounds. He was eating. The food was "
    "not reaching him' - the villi, the actual teenager, the food")

seg(17, [(1, ("broll", "clinic")), (1, ("broll", "clock")),
         (1, ("broll", "meds"))],
    "'it does not run on a schedule. It flares and it quiets' - a calendar, "
    "a clock, the treatment page")

seg(18, [(1, ("broll", "bed"))],
    "'I'm dead. I just lay in bed all day.' NO SYNC - the Rogan monitor has "
    "the Crohn's Foundation site up across his face for this whole bite. An "
    "empty bed carries it, and nobody is cast as him lying in it")

seg(19, [(1, ("broll", "tired")), (1, ("broll", "clinic")),
         (1, ("broll", "meds"))],
    "'hundreds of thousands live with this. There is no cure' - the page, "
    "a clinic, him")

seg(20, [(1, ("broll", "iv")), (1, ("card", "card_infusion"))],
    "'Remicade, every eight weeks they do an IV'. NO SYNC (same panel) - "
    "the drip itself, then every eight weeks drawn out to a lifetime")

seg(21, [(1, ("card", "card_protocol_ig")), (1, ("broll", "meds")),
         (1, ("jimmy", {}))],
    "'for the rest of his life ... call off a defence system that has turned "
    "on you' - the years, the medication, him")

seg(22, [(1, ("sync",))],
    "'Corn. Anything spicy. Anything overly processed.' - him saying it. "
    "Panel map confirms the monitor is dark 5306.75-5330.75")

seg(23, [(1, ("broll", "food")), (1, ("broll", "meds"))],
    "'not the pain, the permanence. Every meal, every year' - a plate, "
    "a calendar")

seg(24, [(1, ("jimmy", {}))], "beat: held on him")

# ============================================================ MACHINE
seg(25, [(1, ("teen",)), (1, ("jimmy", {}))],
    "'he did not do it despite the illness' - the bedroom and the numbers "
    "he was actually posting to")

seg(26, [("fix", 4.0, ("sync",)), (1, ("teen",))],
    "'no money, no nothing, and I obsessed over YouTube every day' - him, "
    "then the room he did it in")

seg(27, [(1, ("broll", "desk")), (1, ("jimmy", {}))],
    "'ten years of testing, failing, rebuilding' - the desk, the hours, him")

seg(28, [("fix", 6.0, ("sync",)), (1, ("jimmy", {})), (1, ("broll", "desk")),
         (1, ("teen",))],
    "'I didn't talk to anyone. I hardly had any friends' - him, an empty "
    "room, the desk, the boy alone in it")

seg(29, [(1, ("jimmy", {"prefer": "NdjcGrpNSF4"})),
         (1, ("card", "card_decade"))],
    "'the machine was hungry and the first thing it ate was him' - him, "
    "then the scale of the system, in verified figures only")

seg(30, [(1, ("jimmy", {}))], "beat: held on him, the hours running")

seg(31, [(1, ("broll", "meds")), (1, ("jimmy", {})),
         (1, ("jimmy", {}))],
    "'a system that consumed every hour, inside a body that was rationing "
    "them' - the figures, him, the desk")

# ============================================================ CONTRACT
seg(32, [("fix", 4.0, ("sync",)), (1, ("broll", "gym_room")),
         ("fix", 6.0, ("sync",)),
         (1, ("jimmy", {"avoid": "9IQ_ldV9z_A"}))],
    "'I have not been working out or taking care of myself' - him twice, "
    "the empty gym, then him elsewhere so the set changes")

seg(33, [(1, ("card", "card_nomotivation")), (1, ("broll", "training"))],
    "'not motivation, not a new year. A second person and a written penalty'")

seg(34, [(1, ("card", "card_contract2"))],
    "Airrack's own voice describing the contract. He is banned from screen "
    "and no Jimmy-only window exists in his video, so the terms are stated "
    "as a card rather than faked as sync")

seg(35, [(1, ("broll", "eq_dumbbell"))], "'signed, with a penalty attached'")

seg(36, [(1, ("card", "card_contract_ig")), (1, ("broll", "eq_machine"))],
    "'if I miss a single day I have to get MrBeast's name tattooed' - "
    "Airrack again: the stake as a card, then equipment")

seg(37, [(1, ("jimmy", {})), (1, ("broll", "eq_barbell")), (1, ("jimmy", {}))],
    "'it sounds like a bit. It is good behavioural design.'")

seg(38, [("fix", 6.0, ("sync",)), (1, ("card", "card_310")), ("fix", 6.0, ("sync",)),
         (1, ("jimmy", {}))],
    "'Today was day 310. Me and Eric signed a contract' - him, the count, "
    "him again, the bar")

seg(39, [(1, ("jimmy", {})), (1, ("broll", "eq_dumbbell")),
         (1, ("jimmy", {}))],
    "'that was NOT three hundred and ten unbroken sessions - programmed rest "
    "counted'. The correction gets its own card because the internet has it "
    "wrong")

seg(40, [(1, ("jimmy", {}))], "beat")

# ============================================================ PROTOCOL
seg(41, [(1, ("jimmy", {}))],
    "'most videos invent this part. Here is only what he has said himself'")

seg(42, [("fix", 6.0, ("sync",)), (1, ("broll", "eq_machine")),
         (1, ("jimmy", {}))],
    "'three things my entire world revolves around: I work out every day'")

seg(43, [(1, ("broll", "desk"))],
    "'in a life that had previously had room for exactly one'")

seg(44, [("fix", 5.5, ("sync",)), (1, ("broll", "clock")),
         ("fix", 4.5, ("sync",))],
    "'I'd upload more if I didn't work out' - him twice, then the hours")

seg(45, [(1, ("jimmy", {})), (1, ("broll", "food")),
         (1, ("jimmy", {}))],
    "'the number that should stop you is not the step count, it is the "
    "admission attached to it' - 12,500, the walking, him")

seg(46, [("fix", 5.0, ("sync",)), (1, ("broll", "eq_dumbbell"))],
    "'I've just been losing fat. It's harder to put on muscle when you're "
    "losing fat'")

seg(47, [(1, ("card", "card_record")), (1, ("jimmy", {})),
         (1, ("broll", "eq_barbell")), (1, ("jimmy", {}))],
    "'he has never published a training split' - the limits of the record, "
    "stated as a card. This is where the film says the 40% figure is "
    "Airrack's, not his")

seg(48, [(1, ("broll", "meds"))],
    "the 1.2s card beat the EDL already carries. card_time was cut: it "
    "printed a broken '2-2h' range with sleep copy and no source")

seg(49, [("fix", 6.0, ("sync",)), (1, ("broll", "eq_dumbbell")),
         (1, ("jimmy", {}))],
    "'work out for three months really consistently and then it's easy'")

seg(50, [(1, ("broll", "calendar")), (1, ("card", "card_rest2")),
         (1, ("jimmy", {}))],
    "'a season. That is all it takes to stop deciding'")

seg(51, [(1, ("jimmy", {}))], "beat")

# ============================================================ LIMIT
seg(52, [(1, ("broll", "gym_room"))],
    "'and then the story does something a transformation video would never "
    "allow. It stops working.' - an empty gym, lights on nobody")

seg(53, [(1, ("broll", "eq_barbell")), (1, ("broll", "eq_machine")),
         (1, ("broll", "eq_dumbbell"))],
    "'way harder - infinitely harder'. Airrack's video is the source, so no "
    "sync: the effort as equipment, then the mismatch as a card")

seg(54, [(1, ("card", "card_time2")), (1, ("jimmy", {}))],
    "'input, time, output. Bodies do not read the spreadsheet.'")

seg(55, [(1, ("jimmy", {})), (1, ("broll", "eq_dumbbell")),
         (1, ("jimmy", {}))],
    "'I can't believe how little progress I've made' - Airrack source again, "
    "so the room carries it, empty")

seg(56, [(1, ("jimmy", {})), (1, ("card", "card_effort")),
         (1, ("jimmy", {}))],
    "'the man whose entire brand is that enough effort beats anything'")

seg(57, [(1, ("jimmy", {}))], "beat, turning toward the fall")

# ============================================================ FALL
seg(58, [(1, ("broll", "desk"))], "'and then the machine took it back'")

seg(59, [("fix", 6.0, ("sync",)), ("fix", 4.3, ("sync",)), (1, ("jimmy", {}))],
    "'Beast Games is a monster of a project and I have to maintain the same "
    "upload schedule'")

seg(60, [(1, ("sync",))],
    "'it's really killing me, to be honest' - him with his hands over his "
    "face. The single best-matched frame in the film")

seg(61, [(1, ("card", "card_600")), (1, ("jimmy", {})),
         (1, ("jimmy", {}))],
    "'six hundred days of proof, and it still lost to a production schedule'")

seg(62, [("fix", 6.0, ("sync",)), (1, ("broll", "bed")), (1, ("broll", "clock"))],
    "'45 minutes, 5 days a week ... but the bigger problem is sleep'")

seg(63, [(1, ("jimmy", {})), (1, ("jimmy", {})), (1, ("jimmy", {}))],
    "'the first moment where he sizes a plan to the body he actually has'")

seg(64, [(1, ("jimmy", {}))], "beat")

# ============================================================ RESOLUTION
seg(65, [(1, ("jimmy", {}))], "'so - did the disease build MrBeast?'")

seg(66, [(1, ("teen",)), (1, ("broll", "bb_field")), (1, ("jimmy", {}))],
    "'it took a future from a teenager and handed him nothing back' - the "
    "teenager, the field he lost, the man now")

seg(67, [(1, ("doc", "post_gains")), (1, ("jimmy", {}))],
    "'you look like a different human being' - his own April 2025 post. "
    "Airrack source, so no sync; the document says it better anyway")

seg(68, [(1, ("broll", "clock")), (1, ("jimmy", {})),
         (1, ("jimmy", {}))],
    "'not a physique. A pattern. Reserve the time before the day takes it'")

seg(69, [(1, ("broll", "meds"))],
    "'mostly because I just don't want to die.' Airrack source. The "
    "medication, not a hospital - the film must not imply he is dying")

seg(70, [("fix", 2.2, ("broll", "iv")), (1, ("jimmy", {})),
         (1, ("jimmy", {}))],
    "'his body has spent a decade trying to shut him down' - 2.2s clinical, "
    "then him, then the ordinary work")

seg(71, [("fix", 2.2, ("sync",)), (1, ("jimmy", {}))],
    "'it's just life' - the hand-trimmed clean window that ends before the "
    "monitor panel enters at 5418.2, then him held")

seg(72, [(1, ("jimmy", {})), (1, ("teen",)), (1, ("jimmy", {})),
         (1, ("broll", "bb_field"))],
    "'said by a man who lost fifty pounds at fifteen and built the biggest "
    "channel on earth' - the two of him, then walking on")

seg(73, [(1, ("jimmy", {})), (1, ("jimmy", {}))],
    "the sign-off, and an end frame with no logo on it")

# The programme's picture must reach the audio's full length; the tail after
# the last narrated word is music only.
TAIL = ("card_end",)

# ==================================================================
# OWNER DIRECTION, review deck slide 44
# ==================================================================
# "Again change it up for 91 and all the images where you have his face,
#  which is pretty much all of them up until 172, you need to change it up
#  to something that does make more sense."
#
# And, asked which of the 21 sync shots survive: keep sync only on the
# biggest moments. So the talking head is stripped out of everything from
# the illness chapter onward, except on the lines that carry the film.
#
# This runs as a transform over PLAN so the intent above stays readable and
# the change stays reversible. Segments 16 and below are NOT touched - the
# owner gave those individual notes and they are applied by hand above.

# The lines that carry the film. Everything else loses its sync shot.
KEEP_SYNC = {
    6,    # "I played baseball nonstop, and then when I got Crohn's I lost
          #  like 50 pounds"        - the origin
    8,    # "190 pounds down to 139 ... all in on YouTube" - the pivot
    12,   # the symptoms, in his own words
    38,   # "Today was day 310. Me and Eric signed a contract"
    42,   # "three things my entire world revolves around"
    44,   # "I'd probably upload more if I didn't work out" - the cost
    49,   # "work out for three months really consistently"
    60,   # "it's really killing me, to be honest" - hands over his face
    62,   # "45 minutes, 5 days a week ... the bigger problem is sleep"
    71,   # "It's just life." - the closing line
}
SWEEP_FROM = 17          # slide 44 sits in segment 16; 16 and below are hand-set

# What replaces a face shot, per chapter. Ordered by preference; the builder
# takes the first group with an unspent clip, so a thin group degrades to the
# next rather than failing the build.
_BY_CHAPTER = {
    "illness":    ["gut_pain", "eating", "tired", "meds", "clinic", "food",
                   "iv", "clock", "bed", "walk2", "walk"],
    "machine":    ["editing", "night_work", "desk", "clock", "tired",
                   "eating", "walk2", "walk", "food"],
    "contract":   ["training", "eq_barbell", "eq_dumbbell", "eq_machine",
                   "gym_room", "athlete", "walk2", "walk", "clock"],
    "protocol":   ["training", "walk", "walk2", "eq_machine", "eq_dumbbell",
                   "eq_barbell", "athlete", "gym_room", "food", "clock"],
    "limit":      ["gym_room", "eq_barbell", "eq_dumbbell", "eq_machine",
                   "tired", "training", "athlete", "walk2"],
    "fall":       ["tired", "bed", "night_work", "editing", "clock",
                   "clinic", "walk2", "desk", "eating"],
    "resolution": ["walk", "walk2", "athlete", "training", "bed", "meds",
                   "tired", "eq_dumbbell", "editing", "eating"],
}
# segment index -> chapter, read off manifest/edl_full.json
_CHAPTER_OF = {}
try:
    import json as _json
    import pathlib as _pl
    _edl = _json.loads((_pl.Path(__file__).resolve().parents[1]
                        / "manifest/edl_full.json").read_text(encoding="utf-8"))
    for _s in _edl["segs"]:
        _CHAPTER_OF[_s["i"]] = _s.get("chapter", "")
except Exception:                                              # noqa: BLE001
    pass


# Supply-aware selection. A fixed rotation still over-drew whichever groups
# appeared first in each chapter's palette - training wanted 9 shots from a
# group holding 3 - so the choice now reads the allow-list and takes whichever
# permitted group has the most headroom LEFT. The palette says what suits the
# chapter; the supply says what is actually available.
_SUPPLY: dict = {}
_DEMAND: dict = {}
try:
    import json as _j2
    import pathlib as _p2
    for _g, _items in _j2.loads(
            (_p2.Path(__file__).resolve().parents[1]
             / "manifest/broll_allow.json").read_text(encoding="utf-8")
    ).items():
        _SUPPLY[_g] = len(_items)
except Exception:                                              # noqa: BLE001
    pass


def _pick(groups):
    """The permitted group with the most unspent clips left."""
    best, best_left = None, None
    for g in groups:
        left = _SUPPLY.get(g, 0) - _DEMAND.get(g, 0)
        if best_left is None or left > best_left:
            best, best_left = g, left
    if best is None:
        best = groups[0]
    _DEMAND[best] = _DEMAND.get(best, 0) + 1
    return best


def _face_free(seg_i, slots):
    """Swap the talking head out of one segment's slots."""
    chapter = _CHAPTER_OF.get(seg_i, "")
    groups = _BY_CHAPTER.get(chapter) or ["tired", "training", "walk"]
    out = []
    for slot in slots:
        if slot[0] == "fix":
            cap, spec = slot[1], slot[2]
            head = ("fix", cap)
        else:
            cap, spec = None, slot[1]
            head = (slot[0],)
        kind = spec[0]
        drop = (kind in ("jimmy", "teen")
                or (kind == "sync" and seg_i not in KEEP_SYNC))
        if drop:
            spec = ("broll", _pick(groups))
            # a sync slot was sized to its window; as stock it is a normal slot
            if head[0] == "fix":
                head = (1,)
        out.append((*head, spec) if head[0] == "fix" else (head[0], spec))
    return out


# Seed the demand counter with the b-roll slots ALREADY written by hand
# anywhere in the plan. Without this the picker only sees its own choices and
# happily routes a tenth draw to a group whose seven clips are already spoken
# for by hand-written slots.
for _slots, _w in PLAN.values():
    for _slot in _slots:
        _spec = _slot[2] if _slot[0] == "fix" else _slot[1]
        if _spec[0] == "broll":
            _DEMAND[_spec[1]] = _DEMAND.get(_spec[1], 0) + 1

for _i in list(PLAN):
    try:
        _n = int(float(_i))
    except (TypeError, ValueError):
        continue
    if _n < SWEEP_FROM:
        continue
    _slots, _why = PLAN[_i]
    _new = _face_free(_n, _slots)
    if _new != _slots:
        PLAN[_i] = (_new, _why + "  [OWNER slide 44: talking head removed]")
