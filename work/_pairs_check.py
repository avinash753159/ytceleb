"""Sheet the closest look-alike pairs side by side so they can be judged.

QC flags a pair by number; only looking settles whether it reads as a repeat.
Rendered-basis distributions measured over 625 same-source pairs: min 9,
p1 15, p5 20, median 57, against cross-source min 45. So the low end is where
two different windows genuinely render almost identically, which is exactly
what rule 6 exists to catch - and the high twenties are probably just two
shots of one man in one room.
"""
import itertools
import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "manifest/picture_v8_shots.json"
W = ROOT / "work/picture_v8"
OUT = ROOT / "work/qc_v8/pairs"
FONT = "graphics/public/fonts/Anton-Regular.ttf"
TOPN = 10


def dh(p: Path, t: float):
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.3f}",
         "-i", str(p), "-frames:v", "1", "-vf", "scale=17:16,format=gray",
         "-f", "rawvideo", "-"], capture_output=True, timeout=120).stdout
    if len(r) < 272:
        return None
    g = np.frombuffer(r[:272], dtype=np.uint8).reshape(16, 17).astype(np.int16)
    return (g[:, 1:] > g[:, :-1]).flatten()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    shots = json.loads(SHOTS.read_text(encoding="utf-8"))
    H = {}
    for s in shots:
        p = W / f"{s['name']}.mp4"
        if not p.exists():
            continue
        x = dh(p, s["dur"] * 0.5)
        if x is not None:
            H[s["name"]] = (s, x)
    pairs = []
    for a, b in itertools.combinations(H, 2):
        sa, ha = H[a]
        sb, hb = H[b]
        d = int(np.count_nonzero(ha != hb))
        if abs(sa["prog_start"] - sb["prog_start"]) < 150.0:
            pairs.append((d, sa, sb))
    pairs.sort(key=lambda x: x[0])
    pairs = pairs[:TOPN]

    tiles = []
    for i, (d, sa, sb) in enumerate(pairs):
        for s, side in ((sa, "A"), (sb, "B")):
            lab = (f"{side} {s['prog_start']:.0f}s h{d} "
                   f"{(s.get('asset') or '').split('/')[-1][:20]}")
            t = OUT / f"p{i:02d}{side}.jpg"
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                 "-ss", f"{s['dur']*0.5:.3f}", "-i",
                 str(W / f"{s['name']}.mp4"), "-frames:v", "1", "-vf",
                 f"scale=470:264,drawbox=x=0:y=232:w=470:h=32"
                 f":color=black@0.8:t=fill,"
                 f"drawtext=fontfile='{FONT}':text='{lab}'"
                 f":fontcolor=#FFE04D:fontsize=20:x=5:y=235", str(t)],
                check=True, timeout=300)
            tiles.append(t)
        print(f"pair {i}: h{d}  {sa['prog_start']:.0f}s vs "
              f"{sb['prog_start']:.0f}s")

    ins, sc = [], []
    for i, t in enumerate(tiles):
        ins += ["-i", str(t)]
        sc.append(f"[{i}:v]null[a{i}]")
    n, cols = len(tiles), 4
    lay = "|".join(f"{(i % cols)*470}_{(i//cols)*264}" for i in range(n))
    lb = "".join(f"[a{i}]" for i in range(n))
    sheet = OUT / "pairs.jpg"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *ins,
         "-filter_complex",
         f"{';'.join(sc)};{lb}xstack=inputs={n}:layout={lay}:fill=black",
         "-frames:v", "1", "-q:v", "3", str(sheet)],
        check=True, timeout=900)
    print("[OK]", sheet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
