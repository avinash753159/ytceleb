#!/usr/bin/env python3
"""V8 storyboard - rebuilt on operator notes.

Changes from V7, each traceable to a specific instruction:
  - transformation is the spine, not a footnote: before/after at the open,
    at the payoff, and dated on screen
  - labelled anatomy chart and microscope slide dropped ("shows me nothing")
    and replaced with real tissue and a zoom to the impact site, unlabelled
  - clinical imagery becomes a STRIP of several brief shots, not one
  - gym-routine stock under the protocol beats
  - the production system becomes an infographic
  - Airrack windows are Jimmy alone; Eric is gone
  - his first upload, the microscope, and the bedroom callback ending: cut
  - Minecraft appears exactly once
"""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "dossier/mrbeast/sources"
ARC = ROOT / "dossier/mrbeast/archive"
MED = ROOT / "dossier/mrbeast/medical"
LIB = ROOT / "library"
WORK = ROOT / "work/storyboard2"
OUT = WORK / "storyboard.html"

W = 440
H = W * 9 // 16 // 2 * 2


def run(args):
    subprocess.run(args, check=True, timeout=600,
                   capture_output=True)


def grab(video: Path, t: float, dest: Path, w=W):
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
         "-vf", f"scale={w}:-2", "-q:v", "4", str(dest)])
    return dest


def fit(img: Path, dest: Path, w=W, h=H, bg="white"):
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(img), "-vf",
         f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
         f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color={bg}",
         "-q:v", "4", str(dest)])
    return dest


def crop_zoom(img: Path, dest: Path, box, w=W, h=H):
    """Crop to a fraction box (l,t,r,b) then fill - the 'zoom to where it
    actually happens, no labels' treatment."""
    l, t, r, b = box
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(img), "-vf",
         f"crop=iw*{1-l-r:.4f}:ih*{1-t-b:.4f}:iw*{l:.4f}:ih*{t:.4f},"
         f"scale={w}:{h}:force_original_aspect_ratio=increase,"
         f"crop={w}:{h}", "-q:v", "4", str(dest)])
    return dest


def side_by_side(a: Path, b: Path, dest: Path, w=W, h=H):
    """Before/after pair with a hard seam - the transformation shot."""
    half = w // 2
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(a), "-i", str(b), "-filter_complex",
         f"[0:v]scale={half}:{h}:force_original_aspect_ratio=increase,"
         f"crop={half}:{h}[l];"
         f"[1:v]scale={half}:{h}:force_original_aspect_ratio=increase,"
         f"crop={half}:{h}[r];[l][r]hstack=inputs=2",
         "-frames:v", "1", "-q:v", "4", str(dest)])
    return dest


def strip(imgs, dest: Path, w=W, h=H):
    """Several small clinical shots as one storyboard entry."""
    n = len(imgs)
    cell = w // n
    ins = []
    for p in imgs:
        ins += ["-i", str(p)]
    sc = ";".join(
        f"[{i}:v]scale={cell}:{h}:force_original_aspect_ratio=increase,"
        f"crop={cell}:{h}[c{i}]" for i in range(n))
    lab = "".join(f"[c{i}]" for i in range(n))
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *ins,
         "-filter_complex", f"{sc};{lab}hstack=inputs={n}",
         "-frames:v", "1", "-q:v", "4", str(dest)])
    return dest


def b64(p: Path) -> str:
    return ("data:image/jpeg;base64,"
            + base64.b64encode(p.read_bytes()).decode("ascii"))


# ----------------------------------------------------------------- shots
SHOTS = [
    ("ba_open", "Cold open", "0:02",
     "TRANSFORMATION, COLD. 2013 beside today, dated on screen. No "
     "narration yet — just the two bodies.",
     "MrBeast archive + present-day interview",
     "You said the film needs the transformation and it was buried. It now "
     "opens the film, before a word is spoken."),
    ("rogan_energy", "Cold open", "0:14",
     "Jimmy, still, mid-sentence: “one of the least energetic people "
     "you’ll ever meet”",
     "Joe Rogan Experience #1788",
     "Music stops dead on this cut. The contradiction the film exists to "
     "explain."),
    ("present_hold", "Cold open", "0:34",
     "Present-day Jimmy, held, no cutting — the 12s music-only break",
     "Colin and Samir — June 2023",
     "Hand-picked hero shot. Was filler."),

    ("teen_alone", "The body he lost", "0:52",
     "The kid, alone, talking to a camera in his bedroom",
     "MrBeast — “Hi Me In 5 Years”",
     "The ‘before’ body, in his own footage. This is the only archive "
     "shot of him in the act."),
    ("doaceo_collapse", "The body he lost", "1:16",
     "Jimmy, uninterrupted: 190 pounds down to 139",
     "The Diary of a CEO",
     "The hinge. Completely dry, no score."),
    ("card_weight", "The body he lost", "1:31",
     "190 → 139 — the number falls as he says it",
     "Designed card (RangeSplit)",
     "Replaces the archive-treatment shot you cut. The weight loss is the "
     "fact; it deserves a graphic."),

    ("doaceo_symptoms", "What it feels like", "2:02",
     "Eight to ten bathroom trips a day, in his own words",
     "The Diary of a CEO",
     "Room tone forward. No scoring."),
    ("zoom_wall", "What it feels like", "2:21",
     "ZOOM to the bowel wall itself — labels cropped away entirely",
     "Blausen Medical / CC BY 3.0",
     "You said no labels, just where it impacts. The chart is now a "
     "close-up of tissue, not a diagram."),
    ("real_tissue", "What it feels like", "2:38",
     "REAL resected Crohn’s ileum — thickened, narrowed, scarred",
     "Wikimedia Commons / CC BY-SA 4.0",
     "The ‘what it actually looks like’ shot. Not an illustration."),
    ("mechanism", "What it feels like", "2:52",
     "Healthy lining beside Crohn’s-damaged lining, graded and pushed in",
     "Wikimedia Commons / CC0",
     "Kept — you said this one works. Treated for contrast so the "
     "difference reads in a second."),
    ("clinical_strip", "What it feels like", "3:04",
     "STRIP: four brief clinical shots, ~0.6s each — skin, tissue, damage",
     "Wikimedia Commons / CC BY 4.0, CC BY 2.0, CC0",
     "Replaces the microscope slide. Several short shots instead of one "
     "long one, exactly as you asked. Never implied to be Jimmy."),
    ("rogan_dead", "What it feels like", "3:26",
     "“I’m dead. I just lay in bed all day.”",
     "Joe Rogan Experience #1788",
     "Zero music. Do not cut away from his face."),
    ("rogan_remicade", "What it feels like", "3:48",
     "Naming the treatment — an IV every eight weeks, for life",
     "Joe Rogan Experience #1788",
     "Cuts to a calendar of infusion dates running years forward."),

    ("minecraft", "The machine", "4:26",
     "His own 2013 Minecraft upload — used ONCE, here only",
     "MrBeast — “Worst Minecraft Saw Trap Ever???”",
     "Under the line about uploading to nobody. You said it was "
     "everywhere; it now appears exactly once, where it means something."),
    ("card_machine", "The machine", "4:41",
     "INFOGRAPHIC: uploads, hours, scale — the system he built, animated",
     "Designed graphic",
     "Replaces the BTS monitors shot. You were right that this is a data "
     "idea, not a footage idea."),
    ("rogan_obsession", "The machine", "4:58",
     "“Obsessed over YouTube every day for a decade”",
     "Joe Rogan Experience #1788",
     "Motif ducks hard under his voice."),

    ("colin_jimmy", "The contract", "5:38",
     "Jimmy: he realised he had stopped taking care of himself",
     "Colin and Samir — June 2023",
     "The decision that starts the rise."),
    ("gym_310", "The contract", "6:22",
     "Real gym footage — the routine — with DAY 310 counting up over it",
     "Stock gym library + counter",
     "You said stock footage of a gym routine, not a bare card. Card and "
     "footage together."),

    ("gym_steps", "The verified protocol", "7:31",
     "Training b-roll, 15,000 STEPS ring filling across it",
     "Stock gym library + counter",
     "Same treatment."),
    ("jimmy_training", "The verified protocol", "8:02",
     "Jimmy alone in frame, training",
     "Airrack 600-day — Jimmy-only window",
     "No other creator in shot. That is the only condition on which this "
     "source is used at all."),

    ("jimmy_progress", "The limit of control", "9:12",
     "Jimmy alone: “I can’t believe how little progress I’ve made”",
     "Airrack 600-day — Jimmy-only window",
     "Tight on him. Nobody else in frame."),
    ("doaceo_treatment", "The limit of control", "9:34",
     "The treatment burden — immune system suppressed",
     "The Diary of a CEO",
     "Cuts against any implication that training cured anything."),

    ("doaceo_give", "Something had to give", "10:08",
     "Beast Games, the workload — training was what broke",
     "The Diary of a CEO",
     "The reversal a transformation video would hide."),
    ("doaceo_sleep", "Something had to give", "10:41",
     "“I’ve got to fix sleep first”",
     "The Diary of a CEO",
     "Cut to a dark, made bed."),

    ("ba_payoff", "Reclaiming the body", "11:18",
     "THE TRANSFORMATION, FULL — 2013 and today, both dated, held long",
     "MrBeast archive + present-day interview",
     "Replaces the Jimmy-and-Eric shot you cut. The payoff of the image "
     "the film opened on, landing on the line about what he got to keep."),
    ("rogan_life", "Reclaiming the body", "11:52",
     "“It’s just life.”",
     "Joe Rogan Experience #1788",
     "No score. Nothing underneath it."),
    ("present_end", "Reclaiming the body", "12:09",
     "Present-day Jimmy, held to the end — not the teenager",
     "The Diary of a CEO",
     "Replaces the bedroom callback. The film ends on who he is now, "
     "which is the whole point of a transformation story."),
]

CUT = [
    ("Production floor / crews and rigs", "Cold open",
     "Generic BTS. Replaced by the transformation cold open."),
    ("“MrBeast6000’s First Video”, 2012", "The body he lost",
     "Cut entirely on your instruction."),
    ("Bedroom, archive-treated", "The body he lost",
     "Replaced by the 190→139 weight card."),
    ("Labelled digestive tract diagram", "What it feels like",
     "Replaced by an unlabelled zoom to the bowel wall."),
    ("Absorptive surface under microscope", "What it feels like",
     "“Shows me nothing.” Replaced by the clinical strip."),
    ("“Hi Me In 10 Years”", "The machine",
     "Redone as the system infographic."),
    ("BTS monitors / production system", "The machine",
     "Replaced by an infographic."),
    ("Jimmy and Eric — gratitude", "Reclaiming the body",
     "Cut. Eric is not in this film."),
    ("Bedroom callback ending", "Reclaiming the body",
     "Replaced by the present-day hold."),
]


def build():
    WORK.mkdir(parents=True, exist_ok=True)
    tmp = WORK / "_t"
    tmp.mkdir(exist_ok=True)
    imgs = {}

    # source frames
    plain = {
        "rogan_energy": (SRC / "cLRLEnPaJLM.mp4", 5266.4),
        "present_hold": (SRC / "9IQ_ldV9z_A.mp4", 712),
        "teen_alone": (ARC / "AKJfakEsgy0.mp4", 25),
        "doaceo_collapse": (SRC / "FjrJ2DJN_pA.mp4", 832),
        "doaceo_symptoms": (SRC / "FjrJ2DJN_pA.mp4", 925),
        "rogan_dead": (SRC / "cLRLEnPaJLM.mp4", 5356.5),
        "rogan_remicade": (SRC / "cLRLEnPaJLM.mp4", 5366),
        "minecraft": (ARC / "2XVcLrB7B3Y.mp4", 32),
        "rogan_obsession": (SRC / "cLRLEnPaJLM.mp4", 176),
        "colin_jimmy": (SRC / "9IQ_ldV9z_A.mp4", 758),
        "jimmy_training": (SRC / "7r3ORKgNUjw.mp4", 1105),
        "jimmy_progress": (SRC / "7r3ORKgNUjw.mp4", 1083),
        "doaceo_treatment": (SRC / "FjrJ2DJN_pA.mp4", 975),
        "doaceo_give": (SRC / "FjrJ2DJN_pA.mp4", 2782),
        "doaceo_sleep": (SRC / "FjrJ2DJN_pA.mp4", 2796),
        "rogan_life": (SRC / "cLRLEnPaJLM.mp4", 5418),
        "present_end": (SRC / "FjrJ2DJN_pA.mp4", 120),
    }
    for k, (v, t) in plain.items():
        if not v.exists():
            print(f"[skip] {k}: missing {v.name}")
            continue
        p = WORK / f"{k}.jpg"
        if not p.exists():
            grab(v, t, p)
        imgs[k] = b64(p)

    # transformation pairs
    before = grab(ARC / "AKJfakEsgy0.mp4", 25, tmp / "before.jpg", 900)
    after = grab(SRC / "9IQ_ldV9z_A.mp4", 712, tmp / "after.jpg", 900)
    after2 = grab(SRC / "FjrJ2DJN_pA.mp4", 120, tmp / "after2.jpg", 900)
    for key, b in (("ba_open", after), ("ba_payoff", after2)):
        p = WORK / f"{key}.jpg"
        if not p.exists():
            side_by_side(before, b, p)
        imgs[key] = b64(p)

    # medical
    if (MED / "small_intestine.png").exists():
        p = WORK / "zoom_wall.jpg"
        if not p.exists():
            crop_zoom(MED / "small_intestine.png", p, (0.30, 0.16, 0.30, 0.42))
        imgs["zoom_wall"] = b64(p)
    if (MED / "crohn_resected.jpg").exists():
        p = WORK / "real_tissue.jpg"
        if not p.exists():
            crop_zoom(MED / "crohn_resected.jpg", p, (0.04, 0.10, 0.04, 0.10))
        imgs["real_tissue"] = b64(p)
    if (MED / "mechanism.png").exists():
        p = WORK / "mechanism.jpg"
        if not p.exists():
            crop_zoom(MED / "mechanism.png", p, (0.02, 0.02, 0.02, 0.50))
        imgs["mechanism"] = b64(p)

    clin = [MED / n for n in ("skin_leg.jpg", "skin_leg2.jpg",
                              "badas_crohn.jpg", "severe_colitis.jpg")]
    clin = [c for c in clin if c.exists()]
    if clin:
        p = WORK / "clinical_strip.jpg"
        if not p.exists():
            strip(clin, p)
        imgs["clinical_strip"] = b64(p)

    # gym stock
    loops = sorted((LIB / "exloops").glob("*.mp4"))
    loops = [x for x in loops if ".bak" not in x.name]
    for key, idx in (("gym_310", 3), ("gym_steps", 6)):
        if len(loops) > idx:
            p = WORK / f"{key}.jpg"
            if not p.exists():
                grab(loops[idx], 1.0, p)
            imgs[key] = b64(p)
    return imgs


def main() -> int:
    imgs = build()
    from storyboard2_html import render
    OUT.write_text(render(SHOTS, CUT, imgs), encoding="utf-8")
    print(f"[OK] {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
    miss = [k for k, *_ in SHOTS if k not in imgs]
    print(f"[cards without art] {miss}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
