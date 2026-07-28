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


from edl import (  # noqa: E402
    gate_card_containment, gate_fitness_ratio, gate_promise_resolved,
    gate_silence_budget, gate_speaker_cap, gate_voice_ratio, validate,
)


def test_voice_ratio_passes_at_forty_percent(good_edl):
    assert gate_voice_ratio(good_edl) == []


def test_voice_ratio_fails_below_threshold(good_edl):
    good_edl.segs[0].dur = 5.0          # bite time 30/80 = 37.5%
    p = gate_voice_ratio(good_edl)
    assert len(p) == 1 and p[0].code == "V1"


def test_card_outside_protocol_act_fails(good_edl):
    good_edl.segs[3].chapter = "open"
    p = gate_card_containment(good_edl)
    assert len(p) == 1 and p[0].code == "V2"
    assert "c0" in p[0].msg


def test_unresolved_promise_fails(good_edl):
    good_edl.segs[5].resolves = ""
    p = gate_promise_resolved(good_edl)
    assert len(p) == 1 and p[0].code == "V3"


def test_promise_resolved_before_it_is_made_fails(good_edl):
    good_edl.segs[0].promise = ""
    good_edl.segs[0].resolves = "the_photo"
    good_edl.segs[5].resolves = ""
    good_edl.segs[5].promise = "the_photo"
    p = gate_promise_resolved(good_edl)
    assert len(p) == 1 and p[0].code == "V3"


def test_silence_budget_fails_with_too_few_beats(good_edl):
    p = gate_silence_budget(good_edl)      # only 1 beat seg, needs 6
    assert len(p) == 1 and p[0].code == "V4"


def test_speaker_cap_fails_for_long_supporting_speaker(good_edl):
    good_edl.segs[0].speaker = "coach"     # 25s, under cap
    good_edl.segs[5].speaker = "coach"     # +25s = 50s, still under
    assert gate_speaker_cap(good_edl) == []
    good_edl.segs[5].dur = 70.0            # 95s total, over cap
    p = gate_speaker_cap(good_edl)
    assert len(p) == 1 and p[0].code == "V5"
    assert "coach" in p[0].msg


def test_subject_speaker_is_exempt_from_cap(good_edl):
    good_edl.segs[5].dur = 500.0
    assert gate_speaker_cap(good_edl) == []


def test_fitness_ratio_fails_when_protocol_act_is_not_training(good_edl):
    good_edl.segs[3].fitness = False       # 15/30 of protocol = 50%
    p = gate_fitness_ratio(good_edl)
    assert any(x.code == "V6" for x in p)


def test_validate_aggregates_all_gates(good_edl):
    codes = {p.code for p in validate(good_edl)}
    assert codes == {"V4"}                 # only the beat-count gate fails


from edl import build_edl  # noqa: E402


def test_build_edl_maps_id_to_seg_id():
    doc = {"protocol_chapter": "protocol", "subject_speaker": "subject",
           "segments": [{"kind": "narr", "dur": 2.0, "id": "n0",
                         "chapter": "open"}]}
    e = build_edl(doc)
    assert e.segs[0].seg_id == "n0"
    assert e.protocol_chapter == "protocol"
    assert e.subject_speaker == "subject"


def test_build_edl_applies_defaults():
    doc = {"segments": [{"kind": "bite", "dur": 2.0, "id": "b0",
                         "chapter": "open"}]}
    e = build_edl(doc)
    assert e.segs[0].jcut == 0.0
    assert e.segs[0].fitness is False
    assert e.protocol_chapter == "protocol"


def test_build_edl_rejects_unknown_kind():
    doc = {"segments": [{"kind": "sfx", "dur": 1.0, "id": "x",
                         "chapter": "open"}]}
    try:
        build_edl(doc)
    except ValueError as ex:
        assert "sfx" in str(ex)
    else:
        raise AssertionError("expected ValueError")


def test_build_edl_rejects_duplicate_ids():
    doc = {"segments": [{"kind": "narr", "dur": 1.0, "id": "n0",
                         "chapter": "open"},
                        {"kind": "narr", "dur": 1.0, "id": "n0",
                         "chapter": "open"}]}
    try:
        build_edl(doc)
    except ValueError as ex:
        assert "n0" in str(ex)
    else:
        raise AssertionError("expected ValueError")
