#!/usr/bin/env python3
"""qc_v11.py - V11 format gates.

Runs the pure EDL validators (V1-V6) and, when given a rendered file,
checks the render matches the timeline (V7).

This sits ALONGSIDE qc.py - qc.py's G1-G8 render checks still apply.

Run: py -3.12 pipeline/qc_v11.py manifest/cutlist.json [rendered.mp4]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from edl import load_edl, validate  # noqa: E402
from v11_assemble import SYNC_TOLERANCE, probe_dur  # noqa: E402


def report(edl, rendered_dur=None):
    problems = [{"code": p.code, "msg": p.msg} for p in validate(edl)]
    total = edl.total()
    if rendered_dur is not None and abs(rendered_dur - total) > \
            SYNC_TOLERANCE:
        problems.append({
            "code": "V7",
            "msg": f"rendered {rendered_dur:.2f}s vs timeline {total:.2f}s "
                   f"(drift {rendered_dur - total:+.2f}s)"})
    return {"passed": not problems, "problems": problems,
            "runtime_s": total}


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    edl = load_edl(argv[0])
    dur = probe_dur(argv[1]) if len(argv) > 1 else None
    r = report(edl, dur)
    print(json.dumps(r, indent=1))
    for p in r["problems"]:
        print(f"  FAIL {p['code']}: {p['msg']}", file=sys.stderr)
    print(f"[{'OK' if r['passed'] else 'FAIL'}] "
          f"{r['runtime_s'] / 60:.1f} min, {len(r['problems'])} problems")
    Path("qc_v11_report.json").write_text(json.dumps(r, indent=1),
                                          encoding="utf-8")
    return 0 if r["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
