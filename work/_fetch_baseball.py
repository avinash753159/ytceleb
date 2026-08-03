"""Fetch more youth-baseball options and contact-sheet them for review.

The b-roll here stands in for Jimmy as a boy, so it has to plausibly read
as him - a stand-in that doesn't match the subject breaks the illusion the
shot exists to create.
"""
import json
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(r"C:\Users\avina\ytceleb")
DEST = ROOT / "library" / "broll"
KEY = "OqvEHNfwvEjuuvosrZXe5keUApJkPuapj79araQgOWtaxZ1xRY9DRsC8"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

QUERIES = ["boy baseball practice", "little league baseball",
           "child batting practice", "teen baseball player",
           "boy throwing baseball", "baseball glove boy"]


def api(u):
    r = urllib.request.Request(u, headers={
        "Authorization": KEY, "User-Agent": UA,
        "Accept": "application/json"})
    with urllib.request.urlopen(r, timeout=90) as f:
        return json.loads(f.read().decode())


got = []
seen = set()
for q in QUERIES:
    u = ("https://api.pexels.com/videos/search?" + urllib.parse.urlencode(
        {"query": q, "per_page": 10, "orientation": "landscape"}))
    try:
        d = api(u)
    except Exception as e:
        print("ERR", q, e)
        continue
    for v in d.get("videos") or []:
        if v["id"] in seen or len(got) >= 10:
            continue
        if not (7 <= v.get("duration", 0) <= 40):
            continue
        best = None
        for f in v.get("video_files", []):
            w = f.get("width") or 0
            if 1200 <= w <= 2100 and f.get("file_type") == "video/mp4":
                if best is None or w > best.get("width", 0):
                    best = f
        if not best:
            continue
        seen.add(v["id"])
        out = DEST / f"bb_cand_{len(got)}.mp4"
        req = urllib.request.Request(best["link"],
                                     headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=600) as r:
            out.write_bytes(r.read())
        got.append((out, q, v.get("user", {}).get("name"), v["id"]))
        print(f"{out.stem}  {q}  by {v.get('user', {}).get('name')}")

# contact sheet for visual review
tiles = []
work = ROOT / "work" / "bb_review"
work.mkdir(parents=True, exist_ok=True)
for i, (p, q, who, _vid) in enumerate(got):
    t = work / f"{i}.jpg"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", "2", "-i", str(p), "-frames:v", "1",
                    "-vf", "scale=340:191", str(t)], check=False)
    if t.exists():
        tiles.append(t)
if tiles:
    ins = []
    for t in tiles:
        ins += ["-i", str(t)]
    n = len(tiles)
    cols = 5
    lay = "|".join(f"{(i % cols)*340}_{(i//cols)*191}" for i in range(n))
    sc = ";".join(f"[{i}:v]scale=340:191[a{i}]" for i in range(n))
    lb = "".join(f"[a{i}]" for i in range(n))
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    *ins, "-filter_complex",
                    f"{sc};{lb}xstack=inputs={n}:layout={lay}",
                    "-frames:v", "1", str(work / "review.jpg")], check=False)
    print("sheet:", work / "review.jpg")
print(json.dumps([{"file": p.name, "query": q, "by": w}
                  for p, q, w, _ in got], indent=2))
