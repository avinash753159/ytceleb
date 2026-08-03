"""Render every medical still with its plan crop applied, and sheet them.

The point is the crop boxes. `mechanism.png` is a fully labelled textbook
plate - IL-12, TGF, Retinoic acid, "Normal" / "Crohn's Disease" - and at speed
a labelled figure reads as homework, not as evidence. The plan crops each
still to the illustration and leaves the caption out of frame, so the crop is
the thing that has to be checked by eye, not the source file.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from picture_plan_v8 import CLIN, STILLS                         # noqa: E402

OUT = ROOT / "work/docs_v8"
FONT = "graphics/public/fonts/Anton-Regular.ttf"
FIT = ("scale=480:270:force_original_aspect_ratio=decrease,"
       "pad=480:270:(ow-iw)/2:(oh-ih)/2:color=#111111")
FILL = ("scale=480:270:force_original_aspect_ratio=increase,crop=480:270")


def tile(src: Path, dest: Path, crop: str, label: str, grade: str = "",
         fill: bool = False) -> None:
    vf = (f"{crop}{FILL if fill else FIT},{grade}"
          f"drawbox=x=0:y=238:w=480:h=32:color=black@0.80:t=fill,"
          f"drawtext=fontfile='{FONT}':text='{label}'"
          f":fontcolor=#FFE04D:fontsize=21:x=6:y=241")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-i", str(src), "-vf", vf, "-frames:v", "1",
                    str(dest)], check=True, timeout=300)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tiles = []

    def box_crop(box):
        l, t, r, b = box
        return (f"crop=iw*{1-l-r:.4f}:ih*{1-t-b:.4f}:"
                f"iw*{l:.4f}:ih*{t:.4f},")

    for k, (rel, box, _m, _s, fill) in STILLS.items():
        d = OUT / f"still_{k}.jpg"
        tile(ROOT / rel, d, box_crop(box), f"{k}{' fill' if fill else ''}",
             fill=fill)
        tiles.append(d)
        print("ok", k)
    for k, (rel, box, _m, _s) in CLIN.items():
        d = OUT / f"clin_{k}.jpg"
        tile(ROOT / rel, d, box_crop(box), f"clin {k}",
             "eq=brightness=-0.07:saturation=0.72,", fill=True)
        tiles.append(d)
        print("ok clin", k)

    ins, sc = [], []
    for i, t in enumerate(tiles):
        ins += ["-i", str(t)]
        sc.append(f"[{i}:v]null[a{i}]")
    n, cols = len(tiles), 3
    lay = "|".join(f"{(i % cols)*480}_{(i//cols)*270}" for i in range(n))
    lb = "".join(f"[a{i}]" for i in range(n))
    sheet = OUT / "stills_check.jpg"
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
