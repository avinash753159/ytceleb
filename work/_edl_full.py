"""Dump the WHOLE authoritative program timeline, not just the first 80s.

_edl_times.py stops at t>80. Minutes 2-12 were built off the storyboard's
round-number guesses (14, 24, 34, ...) which are not the edit. This prints
every segment of the finished audio with its real start/end, so the picture
can be cut to the sentence actually being spoken.

Writes manifest/edl_full.json as well as printing it.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
os.environ["MRBEAST_SCRIPT_VERSION"] = "V6"
os.environ["MRBEAST_VOICE_MODE"] = "final"

import mrbeast_radio as radio                                    # noqa: E402
from edl import build_edl                                        # noqa: E402
from v11_assemble import fit_run_durations, probe_dur            # noqa: E402
from mrbeast_audio_v4 import (LEAD_IN, TITLE_BREAK, BREAK_BEFORE,
                              chapter_spans)                     # noqa: E402

doc = radio.parse_script()
edl = build_edl(doc)
runs = sorted(Path("final_video/mrbeast_radio_v6_final").glob("vo_run_*.wav"))
runs = runs[:len(radio.narration_texts(edl))]
fit_run_durations(edl, [probe_dur(p) for p in runs])

offs = edl.offsets()

ins_at = None
for i, seg in enumerate(edl.segs):
    if seg.kind == "narr" and BREAK_BEFORE.lower() in (
            getattr(seg, "text", "") or "").lower():
        ins_at = offs[i]
        break
if ins_at is None:
    ins_at = chapter_spans(edl)[0][2]

BITES = {b["id"]: b for b in json.loads(
    (ROOT / "manifest/mrbeast_soundbites.json").read_text(encoding="utf-8"))}

rows = []
print("%3s %8s %8s %6s %-5s %-12s %s"
      % ("#", "start", "end", "dur", "kind", "chapter", "what"))
for i, seg in enumerate(edl.segs):
    t = offs[i] + LEAD_IN + (TITLE_BREAK if offs[i] >= ins_at - 1e-6 else 0)
    sid = getattr(seg, "seg_id", "") or ""
    bite = BITES.get(sid.split("_", 1)[-1] if sid.startswith("b") else sid)
    what = getattr(seg, "text", "") or ""
    if not what and bite:
        what = bite["text"]
    if not what:
        what = getattr(seg, "source", "") or ""
    rows.append({"i": i, "start": round(t, 3), "end": round(t + seg.dur, 3),
                 "dur": round(seg.dur, 3), "kind": seg.kind,
                 "chapter": seg.chapter, "text": what,
                 "seg_id": sid,
                 "speaker": getattr(seg, "speaker", "") or "",
                 "src_t0": getattr(seg, "t0", None),
                 "source": getattr(seg, "source", "") or ""})
    print("%3d %8.2f %8.2f %6.2f %-5s %-12s %-11s %s"
          % (i, t, t + seg.dur, seg.dur, seg.kind, seg.chapter,
             (getattr(seg, "source", "") or "")[:11], what[:80]))

brk = (round(ins_at + LEAD_IN, 3), round(ins_at + LEAD_IN + TITLE_BREAK, 3))
print("\nLEAD_IN %.2f   TITLE_BREAK %.2f at %.2f -> %.2f"
      % (LEAD_IN, TITLE_BREAK, brk[0], brk[1]))
end = rows[-1]["end"]
print("program end %.2f  (%d:%05.2f)" % (end, int(end // 60), end % 60))

out = ROOT / "manifest/edl_full.json"
out.write_text(json.dumps({"lead_in": LEAD_IN, "title_break": TITLE_BREAK,
                           "break_at": brk, "end": round(end, 3),
                           "segs": rows}, indent=2), encoding="utf-8")
print("[OK] ->", out)
