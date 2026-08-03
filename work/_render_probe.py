"""Render one shot of each non-pool kind and sheet them.

Cheap insurance before a 175-shot render: the document, still, clinical and
card paths all build long filter chains by string concatenation, and a bad
`zoompan` expression or a crop that lands off-image only shows up as a failed
or wrong-looking piece. Doing four now beats finding out at shot 140.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import mrbeast_picture_v8 as v8                                  # noqa: E402

OUT = ROOT / "work/render_probe"
FONT = "graphics/public/fonts/Anton-Regular.ttf"

JOBS = [
    ("doc_post_obese", lambda p: v8.render_doc("post_obese", 4.4, p)),
    ("doc_dash2015", lambda p: v8.render_doc("dash_2015", 4.3, p)),
    ("doc_his2015card", lambda p: v8.render_doc("his2015card", 4.0, p)),
    ("doc_ccf", lambda p: v8.render_doc("ccf_page", 4.2, p)),
    ("doc_ytsubs", lambda p: v8.render_doc("yt_subs", 4.9, p)),
    ("doc_ytgrid", lambda p: v8.render_doc("yt_grid", 5.0, p)),
    ("still_tract", lambda p: v8.render_still("tract", 3.8, p, False)),
    ("still_mechleft", lambda p: v8.render_still("mech_left", 4.8, p, False)),
    ("still_villi", lambda p: v8.render_still("villi", 2.2, p, False)),
    ("clin_colitis", lambda p: v8.render_still("colitis", 2.2, p, True)),
    ("clin_resected", lambda p: v8.render_still("resected", 2.2, p, True)),
    ("card_end", lambda p: v8.render_card("card_end", 3.9, p)),
    ("card_600", lambda p: v8.render_card("card_600", 4.4, p)),
    ("card_weight", lambda p: v8.render_card("card_weight", 5.0, p)),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    v8.WORK = OUT
    made = []
    for name, fn in JOBS:
        dest = OUT / f"{name}.mp4"
        try:
            fn(dest)
            n = v8.nb_frames(dest)
            print(f"ok  {name:18} {n} frames")
            made.append((name, dest))
        except Exception as e:                                 # noqa: BLE001
            print(f"FAIL {name}: {type(e).__name__} {e}")
    ins, sc = [], []
    for i, (name, d) in enumerate(made):
        ins += ["-ss", "1.2", "-i", str(d)]
        sc.append(f"[{i}:v]scale=480:270,"
                  f"drawbox=x=0:y=238:w=480:h=32:color=black@0.78:t=fill,"
                  f"drawtext=fontfile='{FONT}':text='{name}'"
                  f":fontcolor=#FFE04D:fontsize=21:x=6:y=241[a{i}]")
    n, cols = len(made), 3
    lay = "|".join(f"{(i % cols)*480}_{(i//cols)*270}" for i in range(n))
    lb = "".join(f"[a{i}]" for i in range(n))
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *ins,
         "-filter_complex",
         f"{';'.join(sc)};{lb}xstack=inputs={n}:layout={lay}:fill=black",
         "-frames:v", "1", "-q:v", "3", str(OUT / "probe.jpg")],
        check=True, timeout=900)
    print(f"[OK] {OUT/'probe.jpg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
