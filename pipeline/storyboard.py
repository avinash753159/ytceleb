#!/usr/bin/env python3
"""Generate the V7 storyboard as a self-contained HTML page.

Every thumbnail is a REAL frame from a source that will actually be used, so
the storyboard shows the film that would exist rather than a description of
one. Sources are restricted to footage of Jimmy Donaldson himself.
"""

from __future__ import annotations

import base64
import json
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "dossier/mrbeast/sources"
ARC = ROOT / "dossier/mrbeast/archive"
MED = ROOT / "dossier/mrbeast/medical"
DOC = ROOT / "dossier/mrbeast/documents"
WORK = ROOT / "work/storyboard"
OUT = WORK / "storyboard.html"
UA = "ytceleb-research/1.0 (contact info@xleagle.com)"

CLINICAL = {
    "skin_leg": "Metastatic cutaneous Crohn disease on lower right leg.jpg",
    "skin_leg2": "Metastatic cutaneous Crohn disease on lower leg.jpg",
}


def fetch_clinical():
    MED.mkdir(parents=True, exist_ok=True)
    titles = "|".join(f"File:{t}" for t in CLINICAL.values())
    url = ("https://commons.wikimedia.org/w/api.php?"
           + urllib.parse.urlencode({
               "action": "query", "titles": titles, "prop": "imageinfo",
               "iiprop": "url|extmetadata", "format": "json"}))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.loads(r.read().decode("utf-8"))
    got = {}
    for page in data["query"]["pages"].values():
        if "imageinfo" not in page:
            continue
        ii = page["imageinfo"][0]
        title = page["title"].replace("File:", "")
        key = next((k for k, v in CLINICAL.items() if v == title), None)
        if not key:
            continue
        dest = MED / f"{key}.jpg"
        if not dest.exists():
            rq = urllib.request.Request(ii["url"],
                                        headers={"User-Agent": UA})
            with urllib.request.urlopen(rq, timeout=180) as rr:
                dest.write_bytes(rr.read())
        got[key] = dest
        print(f"[clinical] {key}: {title}")
    return got


def frame(video: Path, t: float, dest: Path, w=440):
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
         "-vf", f"scale={w}:-2", "-q:v", "5", str(dest)],
        check=True, timeout=300)
    return dest


def still(img: Path, dest: Path, w=440):
    # force_original_aspect_ratio needs BOTH dimensions given; combining it
    # with -2 is rejected by ffmpeg.
    h = int(w * 9 / 16) // 2 * 2          # even, or the encoder refuses
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(img), "-vf",
         f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
         f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=white",
         "-q:v", "5", str(dest)],
        check=True, timeout=300)
    return dest


def b64(p: Path) -> str:
    return ("data:image/jpeg;base64,"
            + base64.b64encode(p.read_bytes()).decode("ascii"))


# ---------------------------------------------------------------- shot list
# (key, act, timecode, on-screen, source label, why it earns its place)
SHOTS = [
    ("bts_scale", "Cold open", "0:02",
     "Production floor: crews, rigs, the scale of a shoot",
     "MrBeast — own BTS channel",
     "Narration calls him the most productive person on the internet. The "
     "picture has to show that machine before it is contradicted."),
    ("rogan_energy", "Cold open", "0:14",
     "Jimmy, still, mid-sentence at the Rogan desk",
     "Joe Rogan Experience #1788",
     "The thesis in his own face: “one of the least energetic people "
     "you’ll ever meet.” Music stops dead on this cut."),
    ("bedroom_5yr", "Cold open", "0:34",
     "Teenage Jimmy alone in his bedroom, talking to a camera",
     "MrBeast — “Hi Me In 5 Years”",
     "The 12s music-only title break. Currently filler; this is the "
     "strongest image in the archive and it belongs here."),

    ("first_video", "The body he lost", "0:52",
     "His actual first upload, 2012",
     "MrBeast — “MrBeast6000’s First Video”",
     "Downloaded weeks ago and never used once. It is the literal "
     "beginning of the story."),
    ("doaceo_collapse", "The body he lost", "1:16",
     "Jimmy close-up, no interruption — 190 to 139 pounds",
     "The Diary of a CEO",
     "The hinge of the film. Held completely dry, no score."),
    ("bedroom_talk", "The body he lost", "1:31",
     "Same bedroom, archive-treated: grain, gate weave, desaturated",
     "MrBeast — “Hi Me In 5 Years”",
     "The treatment dates it so a 2013 upload cannot be mistaken for now."),

    ("doaceo_symptoms", "What it feels like", "2:02",
     "Jimmy describing eight to ten bathroom trips a day",
     "The Diary of a CEO",
     "Room tone forward. No scoring — the account carries it."),
    ("tract", "What it feels like", "2:21",
     "Labelled digestive tract, whole diagram, gentle push",
     "Blausen Medical / CC BY 3.0",
     "Letterboxed so the labels survive. The previous cut clipped them."),
    ("mechanism", "What it feels like", "2:38",
     "Healthy intestinal lining beside a Crohn’s-damaged one",
     "Wikimedia Commons / CC0",
     "Cropped to the villi comparison. This single image explains the "
     "whole disease."),
    ("skin_leg", "What it feels like", "2:52",
     "Cutaneous Crohn’s on a patient’s leg — 2 seconds, no longer",
     "Wikimedia Commons / CC BY 4.0",
     "You asked for the human cost on skin. Held briefly and never "
     "implied to be Jimmy."),
    ("villi", "What it feels like", "3:04",
     "Absorptive surface under the microscope, slow push",
     "Wikimedia Commons / CC0",
     "Under the line explaining why he starved with a full stomach."),
    ("rogan_dead", "What it feels like", "3:26",
     "Jimmy: “I’m dead. I just lay in bed all day.”",
     "Joe Rogan Experience #1788",
     "The emotional floor. Zero music. Do not cut away from his face."),
    ("rogan_remicade", "What it feels like", "3:48",
     "Jimmy naming the treatment — an IV every eight weeks, for life",
     "Joe Rogan Experience #1788",
     "Cuts to a calendar of infusion dates running years forward."),

    ("minecraft", "The machine", "4:26",
     "His own 2013 Minecraft upload — under narration about early uploads",
     "MrBeast — “Worst Minecraft Saw Trap Ever???”",
     "This is his real early content. It was in the last cut at random, "
     "which is why it made no sense. Placed under the line about "
     "uploading to nobody, it is the point."),
    ("hi_10yr", "The machine", "4:41",
     "“Hi Me In 10 Years” — a kid addressing a future audience",
     "MrBeast — own archive",
     "Never used in any cut. Devastating in context."),
    ("rogan_obsession", "The machine", "4:58",
     "Jimmy: obsessed over YouTube every day for a decade",
     "Joe Rogan Experience #1788",
     "Motif ducks hard under his voice."),
    ("bts_edit", "The machine", "5:12",
     "Revisions, monitors, the production system he built",
     "MrBeast — own BTS channel",
     "Hand-picked window, not a random draw."),

    ("colin_jimmy", "The contract", "5:38",
     "Jimmy at Colin and Samir, source and date on screen",
     "Colin and Samir — June 2023",
     "The decision: he realised he had stopped taking care of himself."),
    ("card_310", "The contract", "6:22",
     "DAY 310 — animated counter, programmed rest noted beneath",
     "Designed card (BigCounter)",
     "Built weeks ago, used zero times. The number deserves a card, not "
     "stock gym footage."),

    ("card_steps", "The verified protocol", "7:31",
     "15,000 STEPS — ring fills as narration lands",
     "Designed card (StepsRing)",
     "Same: every figure in the narration gets a graphic."),
    ("airrack_jimmy", "The verified protocol", "8:02",
     "Jimmy training — verified-Jimmy window only",
     "Airrack 600-day (Jimmy on screen)",
     "The ONLY basis on which this source survives."),

    ("airrack_progress", "The limit of control", "9:12",
     "Jimmy: “I can’t believe how little progress I’ve made”",
     "Airrack 600-day (Jimmy on screen)",
     "The method failing, in his own words. No impact hit."),
    ("doaceo_treatment", "The limit of control", "9:34",
     "The treatment burden — immune system suppressed",
     "The Diary of a CEO",
     "Cuts against any implication that training cured anything."),

    ("doaceo_give", "Something had to give", "10:08",
     "Jimmy: Beast Games, the workload, and training was what broke",
     "The Diary of a CEO",
     "The honest reversal a transformation video would hide."),
    ("doaceo_sleep", "Something had to give", "10:41",
     "“I’ve got to fix sleep first”",
     "The Diary of a CEO",
     "Cut to a dark, made bed. Warm bed enters only after he finishes."),

    ("airrack_changed", "Reclaiming the body", "11:18",
     "Jimmy and Eric — gratitude, no motivational sting",
     "Airrack 600-day (Jimmy on screen)",
     "Verified-Jimmy window."),
    ("rogan_life", "Reclaiming the body", "11:52",
     "Jimmy: “It’s just life.”",
     "Joe Rogan Experience #1788",
     "No score. Nothing underneath it."),
    ("bedroom_end", "Reclaiming the body", "12:09",
     "Return to the bedroom from the opening — the callback closes",
     "MrBeast — “Hi Me In 5 Years”",
     "Ends where it started, on him, alone, talking to a camera."),
]

GRABS = {
    "bts_scale": (SRC / "cWEUE8X7p-k.mp4", 300),
    "rogan_energy": (SRC / "cLRLEnPaJLM.mp4", 5266.4),
    "bedroom_5yr": (ARC / "AKJfakEsgy0.mp4", 25),
    "first_video": (ARC / "8TFq_vvO_Wg.mp4", 20),
    "doaceo_collapse": (SRC / "FjrJ2DJN_pA.mp4", 832),
    "bedroom_talk": (ARC / "AKJfakEsgy0.mp4", 58),
    "doaceo_symptoms": (SRC / "FjrJ2DJN_pA.mp4", 925),
    "rogan_dead": (SRC / "cLRLEnPaJLM.mp4", 5356.5),
    "rogan_remicade": (SRC / "cLRLEnPaJLM.mp4", 5366),
    "minecraft": (ARC / "2XVcLrB7B3Y.mp4", 32),
    "hi_10yr": (ARC / "F0OkwXKcPSE.mp4", 42),
    "rogan_obsession": (SRC / "cLRLEnPaJLM.mp4", 176),
    "bts_edit": (SRC / "cWEUE8X7p-k.mp4", 700),
    "colin_jimmy": (SRC / "9IQ_ldV9z_A.mp4", 735),
    "airrack_jimmy": (SRC / "7r3ORKgNUjw.mp4", 1105),
    "airrack_progress": (SRC / "7r3ORKgNUjw.mp4", 1083),
    "doaceo_treatment": (SRC / "FjrJ2DJN_pA.mp4", 975),
    "doaceo_give": (SRC / "FjrJ2DJN_pA.mp4", 2782),
    "doaceo_sleep": (SRC / "FjrJ2DJN_pA.mp4", 2796),
    "airrack_changed": (SRC / "7r3ORKgNUjw.mp4", 1106),
    "rogan_life": (SRC / "cLRLEnPaJLM.mp4", 5418),
    "bedroom_end": (ARC / "AKJfakEsgy0.mp4", 100),
}
STILLS = {
    "tract": MED / "tract.png",
    "mechanism": MED / "mechanism.png",
    "villi": MED / "villi_closeup.jpg",
    "skin_leg": MED / "skin_leg.jpg",
}


def build_images():
    WORK.mkdir(parents=True, exist_ok=True)
    imgs = {}
    for k, (v, t) in GRABS.items():
        if not v.exists():
            print(f"[skip] missing {v.name} for {k}")
            continue
        p = WORK / f"{k}.jpg"
        if not p.exists():
            frame(v, t, p)
        imgs[k] = b64(p)
    for k, src in STILLS.items():
        if not src.exists():
            print(f"[skip] missing still {src}")
            continue
        p = WORK / f"{k}.jpg"
        if not p.exists():
            still(src, p)
        imgs[k] = b64(p)
    return imgs


def main() -> int:
    fetch_clinical()
    imgs = build_images()
    from storyboard_html import render
    OUT.write_text(render(SHOTS, imgs), encoding="utf-8")
    kb = OUT.stat().st_size / 1024
    print(f"[OK] {OUT}  ({kb:.0f} KB)")
    missing = [k for k, *_ in SHOTS if k not in imgs
               and not k.startswith("card_")]
    if missing:
        print(f"[warn] no image for: {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
