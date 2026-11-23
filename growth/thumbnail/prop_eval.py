"""Prop eval: a meal/bottle cutout fails if any side except the bottom is a straight cut
(a long run of solid pixels on the first/last column or top row = sliced object)."""
import os, sys, numpy as np
from PIL import Image
D = sys.argv[1] if len(sys.argv) > 1 else "props/final"
def straight(col, n):
    run = best = 0
    for v in col:
        run = run + 1 if v else 0; best = max(best, run)
    return best / n
bad = []
for f in sorted(os.listdir(D)):
    a = np.array(Image.open(os.path.join(D, f)).convert("RGBA"))[..., 3] > 128
    h, w = a.shape
    s = {"left": straight(a[:, 0], h), "right": straight(a[:, -1], h), "top": straight(a[0, :], w)}
    fail = {k: round(v, 2) for k, v in s.items() if v > 0.25}
    print(("FAIL " if fail else "ok   ") + f, fail if fail else "")
    if fail: bad.append(f)
sys.exit(1 if bad else 0)
