#!/usr/bin/env python3
"""
expand_library_v3.py - V3 footage expansion: ~20 targeted downloads.

Ryan-specific searches (the subject must dominate the video) plus the
exercise demos the library provably lacks (squat/lunge/curl/RDL/box jump).
Uses the fixed HD downloader (merged bestvideo+bestaudio, >=720p verified).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from CELEB_VIDEO import download_one  # noqa: E402

QUERIES = [
    # subject-first: real Ryan training / BTS / physique motion footage
    ("Ryan Reynolds Don Saladino workout video", "v3_ryan_saladino_a"),
    ("Don Saladino trains Ryan Reynolds program", "v3_ryan_saladino_b"),
    ("Ryan Reynolds Deadpool 2 training footage", "v3_ryan_dp2"),
    ("Ryan Reynolds Deadpool Wolverine 2024 training", "v3_ryan_dpw"),
    ("Ryan Reynolds gym workout footage", "v3_ryan_gym_a"),
    ("Ryan Reynolds training motivation edit", "v3_ryan_gym_b"),
    ("Ryan Reynolds stunt training behind the scenes", "v3_ryan_stunt"),
    ("Ryan Reynolds Free Guy behind the scenes", "v3_ryan_freeguy"),
    ("Ryan Reynolds boxing training", "v3_ryan_boxing"),
    ("Ryan Reynolds physique transformation video", "v3_ryan_physique"),
    ("Ryan Reynolds interview 2024 fitness", "v3_ryan_int24"),
    ("Ryan Reynolds red carpet 2024", "v3_ryan_carpet"),
    # exercise gaps the judges proved are missing
    ("barbell back squat form demonstration", "v3_ex_squat"),
    ("walking lunges dumbbell demonstration", "v3_ex_lunge"),
    ("preacher curl bicep demonstration", "v3_ex_curl"),
    ("romanian deadlift hip hinge demonstration", "v3_ex_rdl"),
    ("box jump plyometric training", "v3_ex_boxjump"),
    ("battle ropes HIIT workout", "v3_ex_ropes"),
    ("foam rolling recovery routine", "v3_ex_foam"),
    ("hiking trail cardio outdoors", "v3_ex_hike"),
]


def main():
    out_dir = ROOT / "youtube_videos"
    out_dir.mkdir(exist_ok=True)
    got = 0
    for query, stem in QUERIES:
        out = out_dir / f"{stem}.mp4"
        if out.exists():
            print(f"  [=] {stem} exists")
            got += 1
            continue
        print(f"  [*] {stem}: {query}", flush=True)
        if download_one(query, out):
            print(f"      OK ({out.stat().st_size / 1e6:.0f} MB)")
            got += 1
        else:
            print("      FAILED - continuing")
    print(f"[OK] {got}/{len(QUERIES)} v3 downloads ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
