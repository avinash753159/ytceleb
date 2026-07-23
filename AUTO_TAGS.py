#!/usr/bin/env python3
"""
AUTO_TAGS - automatic scene classification with a vision model.

Replaces the MANUAL contact-sheet review (GEN_TAGS2.py) that the pipeline
used to depend on. Reads the labeled contact sheets produced by
VISION_INDEX.py / INDEX_NEW.py, asks Gemini to classify every scene into the
selector's category vocabulary, and writes vision_tags.json / vision_tags2.json
that GENERATE_FINAL_VIDEO.py already knows how to consume.

This is the "better B-roll" upgrade: shots get chosen on what is actually IN
the footage instead of a filename guess. It degrades gracefully -- if no valid
Gemini key is present, or a sheet fails, those scenes are simply left untagged
and the editor falls back to its filename heuristic, so a render is never
blocked.

Key lookup (first hit wins): GEMINI_API_KEY env -> gemini_key.txt in project.
Get a key at https://aistudio.google.com/apikey  (the Cloud-Assist
GOOGLE_API_KEY in some shells is NOT accepted by the public Gemini API).

Run:  python AUTO_TAGS.py          # tags both batches if present
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# (contact-sheet dir, cell-map json, output tags json)
BATCHES = [
    (ROOT / "vision_sheets",  ROOT / "sheets_map.json",  ROOT / "vision_tags.json"),
    (ROOT / "vision_sheets2", ROOT / "sheets_map2.json", ROOT / "vision_tags2.json"),
]

# The exact vocabulary GENERATE_FINAL_VIDEO.py's buckets understand. "ryan_" is
# the convention for "the main subject" regardless of who the celebrity is.
VOCAB = """
SUBJECT (the main celebrity of this video), on camera talking / posing:
  ryan_interview  - subject talking to camera, interview, sit-down
  ryan_press      - press junket, red carpet, podium, microphone
  ryan_event      - premiere, award, crowd/event with the subject
SUBJECT training or showing physique:
  ryan_gym        - subject working out / lifting / in a gym
  ryan_photoshoot - subject posing, cover shoot, flexing for camera
  ryan_abs        - close physique / abs / muscular torso of the subject
  ryan_shirtless  - subject shirtless, physique on display
SUBJECT other:
  ryan_movie      - subject in a film scene / costume / action
  ryan_bts        - behind the scenes, on set, candid with subject
  ryan_photo      - still photo / magazine of the subject
  ryan_outdoor    - subject outdoors, walking, lifestyle
  ryan_home       - subject at home / casual indoor
COACH / TRAINER (a different man, not the celebrity):
  coach_gym       - the trainer demonstrating or coaching in a gym
  coach_talk      - the trainer talking to camera
GENERIC EXERCISE B-ROLL (any anonymous person, gym/fitness):
  chest, back, legs, shoulders, arms, cardio, equipment, recovery
NUTRITION:
  food            - food, meals, cooking, ingredients, supplements
UNUSABLE (set use=0, cat="x"): women as the main subject, on-screen graphics/
  title cards/logos, text slides, cartoons, webcam reaction shots, black or
  badly blurred frames.
""".strip()

PROMPT = """You are classifying frames from source footage for a documentary
about the male celebrity {subject}{coach_hint}.

This image is a contact sheet: a {cols}x{rows} grid of video frames, read
LEFT to RIGHT, TOP to BOTTOM. Each cell has a white label at the bottom like
"#<id> <source> s<scene>". Classify EACH listed cell.

Categories (use these exact strings):
{vocab}

For every id below, output [category, gender, use, quality]:
  category = one exact string above ("x" if unusable)
  gender   = "m" (man) | "f" (woman) | "n" (no person / object / food)
  use      = 1 if usable subject/exercise/food B-roll, else 0
  quality  = 0 (bad) | 1 (ok) | 2 (great, clean, on-topic)

Cells on THIS sheet (id: label):
{cells}

Return ONLY a JSON object mapping each id (as a string) to its 4-item array.
No prose. Example: {{"0": ["ryan_gym","m",1,2], "1": ["x","n",0,0]}}"""

COLS, ROWS = 4, 5


def get_key():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        kf = ROOT / "gemini_key.txt"
        if kf.exists():
            key = kf.read_text().strip()
    return key


def client_or_none(key):
    try:
        from google import genai
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install",
                        "google-genai", "-q"], check=True)
        from google import genai
    try:
        c = genai.Client(api_key=key)
        c.models.generate_content(model=MODEL, contents="OK")  # validate key
        return c
    except Exception as e:
        print(f"[!] Gemini key rejected ({str(e)[:80]}). "
              "Leaving footage for the filename fallback.")
        return None


def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {}


def classify_batch(client, sheets_dir, map_file, out_file):
    if not (map_file.exists() and sheets_dir.exists()):
        return 0
    from PIL import Image
    cells = json.loads(map_file.read_text())
    by_id = {c["id"]: c for c in cells}
    tags = json.loads(out_file.read_text()) if out_file.exists() else {}

    per = COLS * ROWS
    sheets = sorted(sheets_dir.glob("sheet_*.jpg"))
    done = 0
    for s_idx, sheet_path in enumerate(sheets):
        ids = [c["id"] for c in cells
               if s_idx * per <= c["id"] < (s_idx + 1) * per]
        if not ids:
            continue
        cell_lines = "\n".join(
            f'  {i}: "{by_id[i]["source"][:26]} s{by_id[i]["scene"]}"'
            for i in ids)
        prompt = PROMPT.format(subject=os.environ.get("CELEB_SUBJECT",
                                                      "the subject"),
                               coach_hint="", cols=COLS, rows=ROWS,
                               vocab=VOCAB, cells=cell_lines)
        try:
            img = Image.open(sheet_path)
            resp = client.models.generate_content(model=MODEL,
                                                  contents=[prompt, img])
            got = parse_json(resp.text)
            for k, v in got.items():
                if (isinstance(v, list) and len(v) == 4
                        and int(k) in by_id):
                    tags[str(int(k))] = [str(v[0]), str(v[1]),
                                         int(v[2]), int(v[3])]
                    done += 1
            print(f"    {sheet_path.name}: tagged {len(got)} cells")
        except Exception as e:
            print(f"    [!] {sheet_path.name} failed ({str(e)[:60]}) - skipped")
    out_file.write_text(json.dumps(tags, indent=0))
    return done


def main():
    key = get_key()
    if not key:
        print("[i] No Gemini key (GEMINI_API_KEY / gemini_key.txt). "
              "Skipping auto-tag; editor will use the filename fallback.")
        print("    Get one free at https://aistudio.google.com/apikey")
        return 0
    client = client_or_none(key)
    if client is None:
        return 0
    total = 0
    for sheets_dir, map_file, out_file in BATCHES:
        total += classify_batch(client, sheets_dir, map_file, out_file)
    print(f"[OK] auto-classified {total} scenes with {MODEL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
