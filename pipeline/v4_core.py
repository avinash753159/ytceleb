#!/usr/bin/env python3
"""
v4_core.py - section splitting + global no-repeat registry.

Sections: beats grouped by the script's natural structure so each section is
produced (researched, judged, rendered) as its own small unit.

Registry (manifest/used_registry.json): every asset that reaches the timeline
registers scene-id / image average-hash / source-video counter. Rules:
  - a scene id is used AT MOST once per video (rare designated callbacks
    excepted via allow_callback)
  - an image whose average-hash is within hamming distance 5 of a used one
    is a duplicate
  - max 3 shots from any single source video
"""
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest"
REG_FILE = MANIFEST / "used_registry.json"

# beat ranges per section (from the Reynolds transcript structure)
SECTIONS = [
    ("s01_hook",      "b_000", "b_009"),
    ("s02_context",   "b_010", "b_014"),
    ("s03_timeline",  "b_015", "b_022"),
    ("s04_monday",    "b_023", "b_031"),
    ("s05_tuesday",   "b_032", "b_037"),
    ("s06_wednesday", "b_038", "b_041"),
    ("s07_thursday",  "b_042", "b_046"),
    ("s08_friday",    "b_047", "b_050"),
    ("s09_weekend",   "b_051", "b_058"),
    ("s10_notes",     "b_059", "b_062"),
    ("s11_macros",    "b_063", "b_068"),
    ("s12_meals",     "b_069", "b_081"),
    ("s13_cardio_rec", "b_082", "b_086"),
    ("s14_realistic", "b_087", "b_094"),
    ("s15_outro",     "b_095", "b_100"),
]


def section_of(beat_id):
    n = int(beat_id.split("_")[1])
    for name, a, b in SECTIONS:
        if int(a.split("_")[1]) <= n <= int(b.split("_")[1]):
            return name
    return "s99_misc"


def beats_of(section):
    for name, a, b in SECTIONS:
        if name == section:
            return [f"b_{i:03d}" for i in
                    range(int(a.split("_")[1]), int(b.split("_")[1]) + 1)]
    return []


def ahash(path, size=8):
    """Average hash for near-duplicate image detection (no deps)."""
    from PIL import Image
    im = Image.open(path).convert("L").resize((size, size), Image.LANCZOS)
    px = list(im.getdata())
    avg = sum(px) / len(px)
    return "".join("1" if p > avg else "0" for p in px)


def hamming(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


class Registry:
    def __init__(self):
        self.d = json.loads(REG_FILE.read_text()) if REG_FILE.exists() else {
            "scenes": {}, "hashes": {}, "source_counts": {}}

    def save(self):
        REG_FILE.write_text(json.dumps(self.d, indent=0), encoding="utf-8")

    def scene_ok(self, scene_id, allow_callback=False):
        if scene_id in self.d["scenes"] and not allow_callback:
            return False
        src = scene_id.split("|")[0]
        return self.d["source_counts"].get(src, 0) < 3

    def image_ok(self, path):
        try:
            h = ahash(path)
        except Exception:
            return True
        return all(hamming(h, u) > 5 for u in self.d["hashes"].values())

    def use_scene(self, scene_id, beat_id):
        self.d["scenes"][scene_id] = beat_id
        src = scene_id.split("|")[0]
        self.d["source_counts"][src] = self.d["source_counts"].get(src, 0) + 1

    def use_image(self, path, beat_id):
        try:
            self.d["hashes"][str(path)] = ahash(path)
        except Exception:
            pass


if __name__ == "__main__":
    beats = json.loads((MANIFEST / "beats.json").read_text())["beats"]
    for name, a, b in SECTIONS:
        bs = beats_of(name)
        t0 = next(x["start"] for x in beats if x["beat_id"] == bs[0])
        t1 = next(x["end"] for x in beats if x["beat_id"] == bs[-1])
        print(f"{name:14s} {bs[0]}..{bs[-1]}  {t0:5.0f}-{t1:5.0f}s")
