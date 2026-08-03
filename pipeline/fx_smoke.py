#!/usr/bin/env python3
"""Smoke-test every treatment in fx.py against real sources.

Each effect either renders a playable piece or reports why it failed. This
exists because ffmpeg expression syntax fails silently-ish at runtime, not
at import, so "the module imports" proves nothing.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "fx_smoke"
AIRRACK = ROOT / "dossier/mrbeast/sources/7r3ORKgNUjw.mp4"
ARCHIVE = ROOT / "dossier/mrbeast/archive/AKJfakEsgy0.mp4"
COLIN = ROOT / "dossier/mrbeast/sources/9IQ_ldV9z_A.mp4"

CASES = [
    ("archive_teen",
     lambda p: fx.archive_treatment(ARCHIVE, 40.0, 3.0, p, era="teen")),
    ("archive_sd",
     lambda p: fx.archive_treatment(ARCHIVE, 60.0, 3.0, p, era="sd")),
    ("archive_early",
     lambda p: fx.archive_treatment(ARCHIVE, 80.0, 3.0, p, era="early")),
    ("punch_in",
     lambda p: fx.punch_in(AIRRACK, 430.0, 3.0, p, zoom_to=1.20)),
    ("freeze_punch",
     lambda p: fx.freeze_punch(AIRRACK, 1083.0, 3.0, p)),
    ("letterbox_squeeze",
     lambda p: fx.letterbox_squeeze(COLIN, 731.0, 3.0, p)),
    ("speed_ramp_in",
     lambda p: fx.speed_ramp(AIRRACK, 430.0, 2.0, p, ramp="in")),
    ("speed_ramp_both",
     lambda p: fx.speed_ramp(AIRRACK, 450.0, 2.0, p, ramp="both")),
    ("flash_cut",
     lambda p: fx.flash_cut(p, dur=0.14)),
    ("source_label",
     lambda p: fx.source_label(
         OUT / "punch_in.mp4", p, "AIRRACK", "YOUTUBE / DOCUMENTARY")),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if not AIRRACK.exists():
        print(f"missing source: {AIRRACK}")
        return 2

    results = []
    for name, fn in CASES:
        dest = OUT / f"{name}.mp4"
        try:
            fn(dest)
            d = fx.probe_dur(dest)
            w, h = fx.probe_size(dest)
            results.append((name, "OK", f"{d:6.2f}s {w}x{h}"))
        except Exception as e:  # noqa: BLE001
            first = str(e).strip().splitlines()
            results.append((name, "FAIL", first[-1] if first else repr(e)))
            traceback.print_exc(limit=1)

    # transitions need two finished pieces
    a, b = OUT / "punch_in.mp4", OUT / "archive_teen.mp4"
    if a.exists() and b.exists():
        for name, fn in [
            ("whip_pan", lambda p: fx.whip_pan(a, b, p, dur=0.30)),
            ("film_dissolve", lambda p: fx.film_dissolve(a, b, p, dur=0.5)),
        ]:
            dest = OUT / f"{name}.mp4"
            try:
                fn(dest)
                results.append((name, "OK", f"{fx.probe_dur(dest):6.2f}s"))
            except Exception as e:  # noqa: BLE001
                ln = str(e).strip().splitlines()
                results.append((name, "FAIL", ln[-1] if ln else repr(e)))
                traceback.print_exc(limit=1)

    print("\n==== fx.py smoke results ====")
    ok = 0
    for name, status, note in results:
        print(f"  {status:5} {name:20} {note}")
        ok += status == "OK"
    print(f"  {ok}/{len(results)} passed")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
