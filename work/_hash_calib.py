"""Calibrate the perceptual-hash thresholds on the real verified pool.

The 9x8 dHash (72 bits) cannot separate two genuinely different windows of the
same interview: a static two-camera podcast changes only the subject's pose, so
two distinct Rogan singles land inside 8 bits of each other and the "same
picture" rule rejects one of them. That is what blocked the baseball bite.

What matters is the SEPARATION between three populations:
  same       the identical frame, re-hashed (must be 0)
  same-set   two different, human-verified windows of one interview
  cross-set  windows from different sources

A threshold is only usable if it sits in the gap between `same` and
`same-set`. Printed for 9x8, 13x12 and 17x16 so the choice is made on numbers.
"""
import itertools
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "manifest/jimmy_pool2.json"
THUMBS = ROOT / "work/jimmy_pool2"
SIZES = [(9, 8), (13, 12), (17, 16)]


def dhash(p: Path, w: int, h: int):
    g = np.asarray(Image.open(p).convert("L").resize((w, h), Image.LANCZOS),
                   dtype=np.int16)
    return (g[:, 1:] > g[:, :-1]).flatten()


def main() -> int:
    pool = [e for e in json.loads(POOL.read_text(encoding="utf-8"))
            if e.get("verified_jimmy") and not e.get("has_text")]
    by_src: dict[str, list[Path]] = {}
    for e in pool:
        p = THUMBS / (e.get("thumb") or "")
        if p.exists():
            by_src.setdefault(e["source"], []).append(p)
    print("verified thumbs per source:",
          {k: len(v) for k, v in sorted(by_src.items())})

    rng = random.Random(0)
    for w, h in SIZES:
        bits = (w - 1) * h
        cache = {}

        def H(p):
            if p not in cache:
                cache[p] = dhash(p, w, h)
            return cache[p]

        same, within, cross = [], [], []
        for src, ps in by_src.items():
            for p in ps[:8]:
                same.append(0)                       # identical by definition
            for a, b in itertools.combinations(ps, 2):
                within.append(int(np.count_nonzero(H(a) != H(b))))
        srcs = [s for s in by_src if len(by_src[s]) > 1]
        for _ in range(600):
            s1, s2 = rng.sample(srcs, 2)
            a = rng.choice(by_src[s1])
            b = rng.choice(by_src[s2])
            cross.append(int(np.count_nonzero(H(a) != H(b))))

        def pct(v, q):
            return np.percentile(v, q) if v else float("nan")

        print(f"\n=== {w}x{h}  ({bits} bits) ===")
        print(f"  same frame            0")
        print(f"  same-set pairs  n={len(within):5d}  "
              f"min {min(within):3d}  p1 {pct(within,1):5.1f}  "
              f"p5 {pct(within,5):5.1f}  median {pct(within,50):5.1f}")
        print(f"  cross-set pairs n={len(cross):5d}  "
              f"min {min(cross):3d}  p1 {pct(cross,1):5.1f}  "
              f"median {pct(cross,50):5.1f}")
        print(f"  -> a HARD threshold must be < {min(within)} "
              f"(the closest genuinely-distinct pair)")
        print(f"     as a fraction of bits: {min(within)/bits:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
