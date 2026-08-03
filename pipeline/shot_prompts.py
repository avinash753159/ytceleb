#!/usr/bin/env python3
"""Generative prompts, one per segment, written to be pasted straight into Flow.

THE RULE THIS FILE WAS REWRITTEN TO FOLLOW
------------------------------------------
The picture has to be about the sentence it sits under. The previous deck was
written to a house look first and the sentence second, and it showed: segment
0 says "the most productive person on the internet, three hundred million
subscribers, videos that cost more than films" and the prompt was an aerial
over a warehouse of stacked shipping crates. That is a metaphor for "scale"
that reads as a logistics advert. The same failure ran through the gear
machine, the burning calendars and the abstract grids.

So each prompt is now keyed to its exact narration line, and split by what the
line is doing:

  FACT   - the line states something true and specific (three hundred million
           subscribers, 190 pounds down to 139, the inflammation goes through
           the whole thickness of the wall, six hundred days). Show the thing
           itself. A viewer should be able to point at the frame and say what
           the sentence just said.

  FEELING - the line is interpretation, not fact ("the first thing it ate was
           everything that was not the machine"). There is nothing literal to
           photograph, so these stay metaphor - but a metaphor that resolves
           inside one second, not one you have to be told.

Every prompt carries the segment's narration in a comment above it, so the
next person editing this file cannot drift from the words the way this deck
did.

TWO STANDING CONSTRAINTS, BOTH FROM REJECTED CUTS
-------------------------------------------------
NO STAND-IN PEOPLE (HANDOFF rule 9). Nothing cast as Jimmy - no silhouette
training, no legs walking, no torso being measured. Twenty stock clips were
withdrawn for exactly this, and every walk clip went with them, because legs
performing the activity the narration attributes to him read as him. Where the
old deck used a body, this one uses the object the body would have held.

BITES ARE NOT HERE, ON PURPOSE. A bite is Jimmy's own recorded voice at a
known timecode; the picture over it has to be the real man saying the real
words. Generating a likeness of a real person delivering a real quote would be
a fabrication, and it is what made the last cut feel out of sync. Those
segments carry a source and an in-point instead - see REAL at the bottom.

The exceptions are the eight bites where no clean Jimmy-only frame exists
(Airrack's video, and two Rogan stretches with a web page burned in behind
him). Those DO get a prompt, because something has to be on screen. Segments
18 and 20 were flagged "illustrate instead" in REAL and then never given a
prompt at all - that gap is closed here.

HOUSE LOOK
----------
Near-black grade, deep reds as the only warm accent, anamorphic wide lenses,
slow deliberate camera, shallow depth of field. LOOK forbids text and logos.
LOOK_SCREEN relaxes that for the handful of shots whose subject IS a screen or
a document, where "no text" would produce a blank monitor - it asks instead
for unreadable text and no brand marks, which is what we actually want.
"""

LOOK = ("cinematic, shot on anamorphic lenses, shallow depth of field, "
        "near-black shadows, muted desaturated palette with deep red as the "
        "only warm accent, slow deliberate camera move, volumetric haze, "
        "no text, no logos, no recognisable faces, 24fps")

LOOK_SCREEN = ("cinematic, shot on anamorphic lenses, shallow depth of field, "
               "near-black shadows, muted desaturated palette with deep red "
               "as the only warm accent, slow deliberate camera move, screens "
               "and paper carry soft unreadable text, no brand marks, no "
               "logos, no recognisable faces, 24fps")

LOOK_MED = ("photoreal medical visualisation, macro, wet biological surfaces, "
            "near-black surround, deep red and raw pink as the only saturated "
            "colours, slow deliberate camera move, shallow depth of field, "
            "no text, no labels, no logos, 24fps")

# segment -> generative prompt
PROMPTS: dict = {

 # LEAD-IN 0:00-0:02, music only. FEELING - the film has not spoken yet.
 -1: "Extreme slow push onto a single overhead work light hanging dead still "
     "in a vast pitch-black space, its beam picking out nothing but dust in "
     "the air, everything beyond the beam pure black. " + LOOK,

 # 0 FACT - "This is the most productive person on the internet. Three hundred
 # million subscribers. Videos that cost more than films. A pace nobody in the
 # industry has matched."   Show the scale of the production, not a metaphor
 # for scale. This is what "costs more than films" actually looks like.
 0: "High aerial slowly descending over an enormous outdoor film set at night "
    "- lighting towers, camera cranes, generator trucks, scaffold rigs and "
    "dozens of crew working around one huge built structure, the whole thing "
    "lit like a stadium in the middle of total darkness, the descent "
    "continuously revealing more set beyond the edge of frame. " + LOOK,

 # 2 FACT - "Since he was fifteen, his own immune system has been attacking
 # him from the inside, and there are days it wins."
 2: "Dark-field microscopy inside a human gut: a dense swarm of pale immune "
    "cells converging on smooth healthy pink tissue and turning it raw and "
    "angry red everywhere they land, the damage spreading outward across the "
    "surface, wet and biological rather than gory, macro, slow drift. "
    + LOOK_MED,

 # 3 FEELING - "not a story about a workout. It is a story about a body that
 # kept taking things away from a kid, and what he did to take some of it
 # back."   Objects, not a child - rule 9.
 3: "A plain wooden table in a black room holding a boy's things - a worn "
    "baseball glove, a bat, a full dinner plate - under one hard overhead "
    "light. One by one the objects are lifted away by nothing visible until "
    "only bare table is left. Then a single hand enters frame from the dark "
    "and pulls one object firmly back. Locked-off medium, slow. " + LOOK,

 # 4 BEAT, music only. The athlete, before.
 4: "An empty running track at dawn, mist sitting low in the lanes, first "
    "light just catching the white lines, absolutely still, locked-off wide. "
    + LOOK,

 # 5 FACT - "Before any of it, he was an athlete. A kid who played
 # constantly."   Equipment and ground, never a child actor - rule 9.
 5: "Low tracking at knee height across a worn baseball diamond in late "
    "golden light, drifting past scuffed home plate, a chalk baseline, a bat "
    "leaning on the fence and a glove left in the dirt, dust and insects "
    "hanging in the low sun, nobody present. " + LOOK,

 # 6.5 TITLE BREAK 0:54.10-0:58.10, 4s, music only, before the diagnosis.
 6.5: "A deserted baseball diamond at dusk, floodlights dead, infield dirt "
      "raked smooth and untouched, long shadows across it, absolutely "
      "motionless, locked-off wide held. " + LOOK,

 # 7 FACT - "The diagnosis had a name. Crohn's disease."
 7: "Photoreal anatomical render of a human digestive tract rotating slowly "
    "against pure black, the last stretch of small intestine glowing hot "
    "inflamed red while everything around it sits pale and translucent, soft "
    "rim light, slow orbit. " + LOOK_MED,

 # 9 FACT - "A body. A future closing. A decision. Baseball was taken, and the
 # internet was what was left."
 9: "One continuous move in a single shot: a bank of stadium floodlights "
    "powers down to nothing, and as the frame travels on through darkness a "
    "small computer monitor flickers up in a suburban bedroom, the only light "
    "left in the world. " + LOOK_SCREEN,

 # 10 BEAT, music only.
 10: "A teenager's bedroom at three in the morning lit only by monitor glow, "
     "an empty desk chair slowly rotating to a stop, cables and a cheap "
     "microphone on the desk, nobody in the room, slow push. " + LOOK_SCREEN,

 # 11 FEELING - "Most videos skip this part, because it is not inspiring. But
 # you cannot understand anything he did later without sitting in it first."
 11: "A closed door at the far end of a long dark hallway with a hard strip "
     "of cold light underneath it, the shot holding far longer than is "
     "comfortable, nobody coming and nobody going, locked-off. " + LOOK,

 # 13 FACT - "A body that will not keep what you feed it. You can eat and
 # still starve."   The plate empties with no one eating - rule 9.
 13: "Locked-off overhead on a full plate of hot food on a bare table. As the "
     "shot holds, the food disappears portion by portion with nobody touching "
     "it and no cutlery moving, until the plate is completely clean and "
     "nothing has been gained by it. Static, unsentimental. " + LOOK,

 # 14 FACT - "The immune system misidentifies the lining of your own digestive
 # tract as the enemy and attacks that instead."
 14: "Photoreal cross-section of a bowel wall split into two halves side by "
     "side, the left smooth and pale pink and intact, the right with "
     "inflammation burning through every single layer from the inner lining "
     "outward, slow rotation revealing the full thickness of both. "
     + LOOK_MED,

 # 15 FACT - "The inflammation goes through the entire thickness of the bowel
 # wall. That wall thickens, narrows, and scars, so the passage gets tighter."
 15: "Macro endoscopic view travelling forward through an inflamed intestine, "
     "cobblestone ulceration and deep fissures in the tissue passing the "
     "lens, wet surfaces catching a small onboard light, and ahead the "
     "passage visibly thickening and narrowing to a tight scarred ring the "
     "lens cannot pass through. Slow forward tracking. " + LOOK_MED,

 # 16 FACT - "He was eating. The food was going through him without ever being
 # absorbed. His body was starving with a full stomach."
 16: "A translucent anatomical human figure against black, glowing warm "
     "particles of nutrition entering at the mouth and travelling down "
     "through the digestive tract, then dimming and dissolving to nothing "
     "before any of them can cross the wall and be absorbed, while the figure "
     "itself grows visibly thinner. Slow push. " + LOOK_MED,

 # 17 FACT - "It does not run on a schedule. It flares and it quiets, and
 # severity varies enormously between patients. You cannot plan around it."
 17: "A large wall calendar in a dark room where individual days ignite and "
     "burn out at completely unpredictable intervals, embers dropping from "
     "the page, no pattern to which days catch and no rhythm to it, "
     "locked-off medium. " + LOOK,

 # 18 BITE, Rogan - "Sometimes I'll flare up and then I'm just like, I'm dead.
 # I just lay in bed all day."   NO CLEAN FRAME behind him, so this is
 # illustrated. This entry did not exist in the previous deck.
 18: "An unmade empty bed in a dim room with the curtains drawn against hard "
     "daylight outside, the room completely motionless while the blade of "
     "light around the curtain edge travels the full width of the wall across "
     "an entire day. Locked-off wide, nobody present. " + LOOK,

 # 20 BITE, Rogan - "I'm on what's called Remicade, every eight weeks they do
 # an IV with a huge bag, which essentially suppresses my immune system."
 # NO CLEAN FRAME. This entry did not exist in the previous deck either.
 20: "A clinical infusion room: one reclining treatment chair, a tall IV pole "
     "beside it carrying a large full bag, tubing running down and coiled "
     "over the armrest, flat overhead light, the chair empty. Slow push past "
     "the bag toward the drip chamber. " + LOOK,

 # 19 FACT - "Hundreds of thousands of Americans live with this. There is no
 # cure. There is only management."
 19: "Hundreds of thousands of small identical glowing points spread across a "
     "vast dark plane, each one a person, camera pulling back steadily and "
     "continuously to reveal there is no edge to them in any direction. "
     + LOOK,

 # 21 FACT - "For the rest of his life. The only way to call off a defence
 # system that has turned on you is to shut the whole thing down."
 21: "Macro on an IV drip chamber, a single drop forming and falling in slow "
     "motion, then the identical shot repeating over and over while the light "
     "through the window behind it cycles day to night to day to night, time "
     "passing with nothing about the shot changing. " + LOOK,

 # 23 FACT - "Every meal, every year, forever, checked against a list."
 23: "The same plain meal on the same plate on the same table shot from "
     "directly overhead, the plate swapping out again and again while the "
     "meal never varies at all, seasons of light sweeping across the "
     "tabletop in time-lapse around it. Locked-off overhead. " + LOOK,

 # 24 BEAT, music only.
 24: "A single glass of water on a bedside table in a dark room, condensation "
     "running slowly down the outside of it, absolutely still. " + LOOK,

 # 25 FACT - "he did not do it after he got better. There was no after."
 # The recovery that never happened, walled in by the work that did.
 25: "A single empty recovery armchair in the centre of a bare room, and "
     "around it in fast time-lapse a workspace assembles itself over months - "
     "desks, monitors, cameras, lights, stacked hard drives - closing in "
     "until the chair is completely walled in and unreachable and nobody has "
     "ever sat in it. Locked-off wide, day-night cycles flickering past. "
     + LOOK_SCREEN,

 # 27 FACT - "Ten years of treating one problem as solvable - testing,
 # failing, rebuilding."
 27: "A dark room where an editing timeline is scrubbed back and forth on a "
     "monitor, cuts made and undone, while behind the desk a wall fills up "
     "with hundreds of printed rejected thumbnail variations pinned in grid "
     "after grid, the seasons changing in the window across the whole shot. "
     "Over-shoulder, screen slightly out of focus, chair empty. "
     + LOOK_SCREEN,

 # 29 FEELING - "The machine he built was extraordinary, and it was hungry,
 # and the first thing it ate was everything that was not the machine."
 29: "An enormous machine of interlocking gears and conveyor belts running at "
     "speed in a dark industrial hall, taking in a steady feed of glowing "
     "material at one end and giving nothing back, camera tracking alongside "
     "it, relentless and indifferent. " + LOOK,

 # 30 BEAT, music only.
 30: "Macro on a mechanical clock escapement ticking in near darkness, one "
     "hard rim light, extremely shallow focus. " + LOOK,

 # 31 FEELING - "A man who could optimise anything, running a system that
 # consumed every hour, inside a body he had never been able to optimise at
 # all. Something was going to break."
 31: "A vast clockwork mechanism turning in the dark with one small warm "
     "light held at its centre, gears sweeping past and through the space "
     "around that light, the light dimming further every time the machine "
     "speeds up. Slow orbit. " + LOOK,

 # 33 FEELING - "Not motivation. Not a new year. It was a second person and a
 # rule."
 33: "Two plain chairs facing each other across a bare table in an empty "
     "room, one single sheet of paper on the table between them, one hard "
     "light directly above. Nothing else anywhere in the room. Slow push down "
     "onto the paper. " + LOOK_SCREEN,

 # 34 BITE, Eric's voice on Airrack's video - "I signed a legally binding
 # contract with MrBeast that says we both have to work out every day for 600
 # days."   No Jimmy-only frame exists in that video, so illustrate.
 34: "A legal contract lying on a desk in hard raking light, a hand entering "
     "frame and signing at the bottom in wet black ink, extreme close on the "
     "nib and the fibre of the paper, slow push. " + LOOK_SCREEN,

 # 35 FACT - "Signed, with a penalty attached."
 35: "Macro along a single printed clause on paper, focus racking down the "
     "line until the words fall out of legibility entirely. " + LOOK_SCREEN,

 # 36 BITE, Airrack's voice - the forehead tattoo penalty. Illustrate.
 36: "Extreme macro of a tattoo needle loaded with black ink descending "
     "toward bare skin and making first contact, slow motion, clinical and "
     "permanent, cropped so no face or identifying feature is in frame. "
     + LOOK,

 # 37 FEELING - "make quitting immediate, public and irreversible, and the
 # worst day stops being a decision."
 37: "A single signed sheet of paper pinned at eye height on a wall in a "
     "busy public corridor, held in hard focus while blurred figures pass "
     "continuously in front of it in both directions, the page never once out "
     "of view. Locked-off. " + LOOK_SCREEN,

 # 39 FACT - "That was not three hundred and ten unbroken sessions. Programmed
 # rest counted, deliberately, from the start."
 39: "A calendar grid of three hundred and ten squares on black filling in "
     "one at a time at speed, with scattered squares deliberately skipped and "
     "marked in deep red as they are passed, revealing at the end that the "
     "run was never unbroken and was never meant to be. Clean motion "
     "graphics. " + LOOK_SCREEN,

 # 40 BEAT, music only.
 40: "An empty squat rack in a dark gym, chalk dust hanging in a single shaft "
     "of light, nobody present, static. " + LOOK,

 # 41 FACT - "Most videos invent this part. Here is only what he has said
 # himself."
 41: "A printed document held under hard light with almost every line heavily "
     "blacked out, only three or four short phrases left legible anywhere on "
     "the page, slow push in toward the surviving lines. " + LOOK_SCREEN,

 # 43 FEELING - "In a life that had previously had room for exactly one."
 43: "One chair alone in the centre of a vast empty room in cold light, then "
     "two more chairs fading into existence either side of it, wide "
     "locked-off, held. " + LOOK,

 # 45 FACT - "He knew this was costing him uploads and did it anyway. For a
 # person whose entire identity was output, choosing to produce less is the
 # most radical thing in this story."   No walking legs - rule 9.
 45: "A dense grid of small glowing rectangles on black, each one a finished "
     "video, filling steadily left to right at a relentless rate; then the "
     "rate visibly slows and a clean empty band opens across the grid and is "
     "deliberately left empty as the filling continues past it. Elegant "
     "motion graphics. " + LOOK_SCREEN,

 # 47 FACT - "he has never published a training split, a set and rep scheme,
 # or a calorie target. Any video handing you one is filling in blanks."
 47: "A single sheet of paper on black carrying only three or four short "
     "lines of handwriting at the very top, the rest of the page completely "
     "blank, camera pushing in slowly until the blankness fills the frame. "
     + LOOK_SCREEN,

 # 48 CARD, 1.2s - MrBeastProtocolCard.
 48: "A hard flash frame of a simple white diagram on pure black, one second, "
     "graphic and abrupt. " + LOOK_SCREEN,

 # 50 FACT - "A season. That is all it takes to stop deciding. Repetition,
 # continued until the choice disappears."
 50: "Time-lapse across three months from one fixed camera position looking "
     "out of a window, the light and the weather and the season changing "
     "completely while the same small routine repeats below at the same time "
     "every day, until it stops reading as effort at all. " + LOOK,

 # 51 BEAT, music only.
 51: "A loaded barbell resting on the floor of an empty gym, chalk "
     "handprints on the knurling, nobody present, static close. " + LOOK,

 # 52 FEELING - "And then the story does something a transformation video
 # would never allow. It stops working."   Effort with no distance gained,
 # and no body in frame - rule 9.
 52: "An enormous stone block being pushed slowly across a dark floor by "
     "nothing visible, deep drag marks opening behind it and then erasing "
     "themselves as fast as they appear, so the block never ends up any "
     "further from where it started. Wide locked-off, slow. " + LOOK,

 # 53 BITE, Airrack's video - "Way harder, infinitely harder... trying to get
 # in one year what normal people get in two."   Illustrate.
 53: "A loaded barbell moving up and down in an unbroken mechanical rhythm, "
     "shot in tight macro on the plates and the knurled bar, chalk dust and "
     "sweat catching the light, relentless repetition, cropped so no body is "
     "in frame. " + LOOK,

 # 54 FACT - "He had modelled it the way he models everything. Input, time,
 # output. Bodies do not read the spreadsheet."
 54: "A clean mathematical equation drawn in light on black that refuses to "
     "balance, one side collapsing again and again no matter how carefully "
     "the other side is adjusted, elegant motion graphics. " + LOOK_SCREEN,

 # 55 BITE, Airrack's video - "I can't believe how little progress I've made
 # in the amount of time."   Illustrate. No waist, no body - rule 9.
 55: "A steel tape measure on a black surface being drawn out by an unseen "
     "hand to exactly the same mark, released, and drawn out to that same "
     "mark again and again, the number identical every single time, macro, "
     "cold flat light. " + LOOK_SCREEN,

 # 56 FEELING - "he put in the effort and the problem did not move. That is
 # not modesty. That is the method failing."   No straining silhouette.
 56: "A massive hydraulic ram pressing at full force against a solid concrete "
     "wall in an empty industrial space, the pressure gauge pinned hard at "
     "maximum and shaking, the wall completely unmarked and unmoved. Wide "
     "locked-off. " + LOOK,

 # 57 BEAT, music only - the pause before the machine takes it back.
 57: "A phone lying face down on a table beside a cold untouched cup of "
     "coffee in a dim room, absolutely still, slow push. " + LOOK,

 # 58 FEELING - "And then the machine took it back."
 58: "The enormous gear machine from earlier closing in on the one small "
     "pocket of open space left in the frame, gears filling in from every "
     "edge until there is no room left at all, slow push. " + LOOK,

 # 61 FACT - "Six hundred days of proof that he could do it, and it still lost
 # to a production schedule."
 61: "A counter of six hundred glowing days laid out as a grid on black, "
     "complete and steady, then going dark from one end in a single "
     "continuous sweep until none are lit. Clean motion graphics. "
     + LOOK_SCREEN,

 # 63 FACT - "It is the first moment where he sizes a plan to the life he
 # actually has. And notice what he refuses to fix first. It is not the
 # training."
 63: "A small, calm version of the same routine at first light - one pair of "
     "trainers set by a door, a clock reading forty-five minutes, curtains "
     "drawn open onto early morning - three quiet static frames, sustainable "
     "rather than heroic. " + LOOK,

 # 64 BEAT, music only.
 64: "A dark bedroom before sunrise with one thin line of light under the "
     "curtain, absolutely still, held. " + LOOK,

 # 65 FACT/question - "So - did the disease build MrBeast?"
 65: "Pure black frame with a single shaft of light entering from one side "
     "and slowly widening across it, minimal and quiet. " + LOOK,

 # 66 FACT - "It took a future from a teenager and handed him nothing back.
 # What it did was narrow the road until one path was left, and he ran down
 # that one harder than anybody alive."
 66: "The same baseball diamond years later - weeds through the infield dirt, "
     "backstop rusted through, floodlights dead - and the camera drifting off "
     "it to find one narrow worn path leading away into darkness with "
     "everything either side of it closed off and impassable. Dusk. " + LOOK,

 # 68 FACT - "What he got to keep is not a physique. It is a pattern. Reserve
 # the time. Put the promise somewhere another person can see it. Let recovery
 # count. Then lose it, and start again."
 68: "Trainers waiting by a door in the blue dark of very early morning, a "
     "hand entering frame to pick them up, then a door opening onto hard "
     "first light, cropped at the wrist so no body is in frame, three slow "
     "static frames. " + LOOK,

 # 69 BITE, Airrack's video - "mostly because I just don't want to die."
 # Illustrate. Entirely undramatic on purpose.
 69: "A small unmarked pill bottle and an ordinary glass of water on a "
     "kitchen counter in flat morning light, a hand entering frame to take "
     "them, completely routine, macro. " + LOOK,

 # 70 FACT - "his body has spent a decade trying to shut him down, and
 # training is one of the few arguments he still gets to win."
 70: "Time-lapse macro of running water wearing a hard stone visibly smooth "
     "over years, patient and relentless and never once forcing it, hard side "
     "light against black. " + LOOK,

 # 72 FACT/FEELING - "It's just life. The disease did not build him. He built
 # himself, in spite of it."   The one warm light that does not go out.
 72: "Slow crane up and back from one small warm lamp burning alone on the "
     "floor of a vast dark space, the space opening out further and further "
     "around it as the camera rises, the lamp never dimming and never going "
     "out. " + LOOK,

 # 73 CTA - "tell me in the comments which part you did not know."
 73: "A single practical light in a dark room switched off by an unseen hand, "
     "the frame settling to black, locked-off. " + LOOK,
}


# What the reference images should show. One entry per prompt, describing the
# LITERAL subject of that prompt in the words a person would type into an
# image search - not a mood, not a vibe.
#
# This lives next to the prompts on purpose. The previous version kept the
# search terms in a separate hand-written dict inside the doc builder, and the
# two drifted apart: segment 14's prompt was a bowel-wall cross-section and
# its query was "intestinal wall histology cross section", which returns
# whatever a text index matches rather than the picture described. Keeping
# them in one file means a prompt edit and a query edit are the same edit.
#
# Value is (query, kind). kind "med" routes to medical sources and pins the
# already-licensed stills in dossier/mrbeast/medical/ as the first options.
REF_QUERY: dict = {
 -1: ("single work light hanging in dark empty warehouse", None),
 0:  ("large film production set at night lighting cranes crew aerial", None),
 2:  ("inflamed intestinal mucosa histology micrograph immune cell "
      "infiltrate", "med"),
 3:  ("baseball glove and bat on dark wooden table still life", None),
 4:  ("empty running track at dawn with mist", None),
 5:  ("baseball home plate and glove in dirt golden hour close up", None),
 6.5: ("empty baseball diamond at dusk infield dirt", None),
 7:  ("crohn's disease terminal ileum digestive tract anatomy "
      "illustration", "medart"),
 9:  ("stadium floodlights switching off at night", None),
 10: ("dark bedroom lit by computer monitor at night empty chair", None),
 11: ("long dark hallway with light under a closed door", None),
 13: ("hot dinner plate of food on bare table shot from above", None),
 14: ("bowel wall layers cross section 3d medical render inflamed",
      "medart"),
 15: ("crohn's disease colonoscopy cobblestoning ulceration endoscopy "
      "photograph", "med"),
 16: ("intestinal villi nutrient absorption 3d medical render", "medart"),
 17: ("large wall calendar hanging in a dim room", None),
 18: ("unmade bed dark room curtains drawn daylight", None),
 19: ("thousands of tiny points of light across a vast dark plane", None),
 20: ("hospital infusion suite treatment chair and IV pole in room", None),
 21: ("intravenous drip chamber with falling drop close up hospital", None),
 23: ("plain meal on plate overhead on table", None),
 24: ("glass of water on a wooden nightstand in a dark bedroom", None),
 25: ("home studio room filled with camera gear monitors and lights", None),
 27: ("video editing timeline on monitor in dark room at night", None),
 29: ("heavy industrial gears and conveyor machinery dark factory", None),
 30: ("mechanical clock escapement macro", None),
 31: ("giant clockwork gears with light at the centre", None),
 33: ("two empty chairs facing each other in a bare room", None),
 34: ("hand signing a contract with a pen close up", None),
 35: ("extreme close up of printed text on paper shallow depth of field", None),
 36: ("tattoo machine needle macro close up", None),
 37: ("single sheet of paper pinned to a notice board close up", None),
 39: ("wall calendar with days crossed off in red marker", None),
 40: ("empty squat rack in dark gym with light shaft", None),
 41: ("redacted document with blacked out lines", None),
 43: ("single chair alone in large empty room", None),
 45: ("abstract grid of small glowing squares on black background", None),
 47: ("mostly blank sheet of paper with a few handwritten lines", None),
 # 48 has no reference row on purpose: it is the CARD, a generated
 # graphic built by render_cards_v8.py. Searching for "white diagram
 # on black" three different ways returned blueprints, gradient
 # wallpaper and two dead links. Prompt only.
 50: ("same landscape in four seasons from one viewpoint", None),
 51: ("barbell on gym floor with chalk close up", None),
 52: ("huge rectangular stone block resting on bare ground", None),
 53: ("barbell plates and knurled bar macro with chalk", None),
 54: ("glowing mathematical equation on blackboard dark", None),
 55: ("steel tape measure macro on dark surface", None),
 56: ("hydraulic ram pressing against concrete wall industrial", None),
 57: ("smartphone lying face down on a table beside a coffee cup", None),
 58: ("interlocking gears filling the frame close up", None),
 61: ("grid of glowing squares fading into black abstract", None),
 63: ("shoes by the front door in a home entryway hallway", None),
 64: ("dark bedroom before sunrise light under curtain", None),
 65: ("shaft of light entering darkness", None),
 66: ("abandoned overgrown baseball field rusted backstop", None),
 68: ("home entryway with shoes and an open front door letting in light", None),
 69: ("pill bottle and glass of water on kitchen counter", None),
 70: ("water eroding smooth stone macro", None),
 72: ("single lamp glowing alone in a vast dark space", None),
 73: ("hand reaching to switch off a bedside lamp in a dark room", None),
}


# Medical stills we already hold, licensed and credited, in
# dossier/mrbeast/medical/ (see CREDITS.json and CREDITS2.json). These are
# pinned as the first reference under a "med" segment so that every medical
# block is guaranteed at least one image that is verified real Crohn's
# material rather than whatever an image search happened to return.
#
# severe_colitis.jpg is deliberately NOT used anywhere here: CREDITS2 records
# it as ULCERATIVE COLITIS, usable "only if captioned as related IBD, never as
# Crohn's". It was once full-frame and uncaptioned under his own Crohn's bite,
# and was withdrawn for that.
# One file per segment where possible, and never the same file twice: pinning
# tract.png AND small_intestine.png under both 7 and 14 made those two blocks
# open with an identical pair of thumbnails.
#
# badas_crohn.jpg is deliberately not pinned anywhere. It is a genuine Crohn's
# clinical photograph, but of SKIN on the lower legs - as the first reference
# under segment 15, whose prompt travels through an inflamed intestine, it read
# as an unexplained photograph of somebody's feet.
MED_LOCAL: dict = {
 2:  ["mechanism.png"],
 7:  ["tract.png"],
 14: ["small_intestine.png"],
 15: ["crohn_resected.jpg"],
 16: ["villi_histology.jpg", "villi_closeup.jpg"],
}


# Bites: the real man, the real words. Source and in-point, not a prompt.
REAL = {
 1: ("Joe Rogan Experience #1788", "1:27:45",
     "“I'm probably one of the least energetic people you'll ever "
     "meet.”"),
 6: ("Joe Rogan Experience #1788", "1:26:39",
     "the baseball and Crohn's line, in full"),
 8: ("The Diary Of A CEO", "13:45", "190 pounds down to 139, and going all in"),
 12: ("The Diary Of A CEO", "15:18", "the symptoms, in his own words"),
 18: ("Joe Rogan Experience #1788", "1:29:14",
      "NO CLEAN FRAME - the studio monitor behind him is showing a web page "
      "for this whole bite. Illustrate instead."),
 20: ("Joe Rogan Experience #1788", "1:29:23",
      "NO CLEAN FRAME - same monitor. Illustrate instead."),
 22: ("Joe Rogan Experience #1788", "1:28:29", "corn, spicy, processed"),
 26: ("Joe Rogan Experience #1788", "2:54", "no money, no nothing"),
 28: ("Joe Rogan Experience #1788", "8:58", "I didn't talk to anyone"),
 32: ("Colin and Samir (June 2023)", "12:36", "I have not been working out"),
 34: ("Airrack", "0:00",
      "AIRRACK'S VOICE, and no Jimmy-only frame exists in his video. "
      "Illustrate instead."),
 36: ("Airrack", "0:13", "AIRRACK'S VOICE. Illustrate instead."),
 38: ("Colin and Samir (June 2023)", "12:12", "day 310, and the contract"),
 42: ("Colin and Samir (June 2023)", "11:49", "three things"),
 44: ("Colin and Samir (June 2023)", "13:33", "I'd upload more if I didn't"),
 46: ("Colin and Samir (June 2023)", "12:59", "losing fat versus muscle"),
 49: ("Colin and Samir (June 2023)", "13:14", "three months consistently"),
 53: ("Airrack", "8:09", "AIRRACK'S VIDEO. Illustrate instead."),
 55: ("Airrack", "18:02", "AIRRACK'S VIDEO. Illustrate instead."),
 59: ("The Diary Of A CEO", "46:16", "Beast Games and the upload schedule"),
 60: ("The Diary Of A CEO", "45:21",
      "“it's really killing me” - his hands come up over his face. "
      "The best-matched frame in the film."),
 62: ("The Diary Of A CEO", "46:32", "45 minutes, and the sleep problem"),
 67: ("Airrack", "17:49", "AIRRACK'S VIDEO. Illustrate instead."),
 69: ("Airrack", "18:35", "AIRRACK'S VIDEO. Illustrate instead."),
 71: ("Joe Rogan Experience #1788", "1:30:16",
      "“It's just life.” ONLY ~2.2 SECONDS ARE USABLE - a web page "
      "appears on the monitor behind him after that."),
}
