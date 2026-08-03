"""Print the authoritative program timeline for the opening of the film.

These are the real edit times the audio was built from - not Whisper
transcript timestamps, which merge long pauses and drift by many seconds.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, "pipeline")
os.environ["MRBEAST_SCRIPT_VERSION"] = "V6"
os.environ["MRBEAST_VOICE_MODE"] = "final"

import mrbeast_radio as radio
from edl import build_edl
from v11_assemble import fit_run_durations, probe_dur
from mrbeast_audio_v4 import (LEAD_IN, TITLE_BREAK, BREAK_BEFORE,
                              chapter_spans)

doc = radio.parse_script()
edl = build_edl(doc)
runs = sorted(Path("final_video/mrbeast_radio_v6_final").glob("vo_run_*.wav"))
runs = runs[:len(radio.narration_texts(edl))]
fit_run_durations(edl, [probe_dur(p) for p in runs])

offs = edl.offsets()

# Same anchor the audio builder used: the break sits before this line.
ins_at = None
for i, seg in enumerate(edl.segs):
    if seg.kind == "narr" and BREAK_BEFORE.lower() in (
            getattr(seg, "text", "") or "").lower():
        ins_at = offs[i]
        break
if ins_at is None:
    ins_at = chapter_spans(edl)[0][2]

print("%7s %7s %-6s %-10s %s" % ("start", "end", "kind", "chapter", "what"))
for i, seg in enumerate(edl.segs):
    t = offs[i] + LEAD_IN + (TITLE_BREAK if offs[i] >= ins_at - 1e-6 else 0)
    if t > 80:
        break
    what = getattr(seg, "text", "") or getattr(seg, "source", "") or ""
    print("%7.2f %7.2f %-6s %-10s %s" % (t, t + seg.dur, seg.kind,
                                         seg.chapter, what[:72]))
print("\nTITLE BREAK (music only): %.2f -> %.2f"
      % (ins_at + LEAD_IN, ins_at + LEAD_IN + TITLE_BREAK))
