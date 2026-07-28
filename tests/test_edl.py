import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from edl import EDL, Seg  # noqa: E402


def mk(kind, dur, seg_id, chapter="c1", **kw):
    return Seg(kind=kind, dur=dur, seg_id=seg_id, chapter=chapter, **kw)


def test_total_is_sum_of_durations():
    e = EDL(segs=[mk("narr", 3.0, "n0"), mk("bite", 2.5, "b0")],
            protocol_chapter="protocol", subject_speaker="subject")
    assert e.total() == 5.5


def test_offsets_accumulate_from_zero():
    e = EDL(segs=[mk("narr", 3.0, "n0"), mk("bite", 2.5, "b0"),
                  mk("beat", 1.5, "s0")],
            protocol_chapter="protocol", subject_speaker="subject")
    assert e.offsets() == [0.0, 3.0, 5.5]


def test_runs_groups_consecutive_narration():
    e = EDL(segs=[mk("narr", 1.0, "n0"), mk("narr", 1.0, "n1"),
                  mk("bite", 1.0, "b0"), mk("narr", 1.0, "n2")],
            protocol_chapter="protocol", subject_speaker="subject")
    assert e.runs() == [(0, 2), (3, 4)]


def test_runs_is_empty_when_no_narration():
    e = EDL(segs=[mk("bite", 1.0, "b0")],
            protocol_chapter="protocol", subject_speaker="subject")
    assert e.runs() == []
