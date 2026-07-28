import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from qc_v11 import report  # noqa: E402


def test_report_flags_the_failing_gate(good_edl):
    r = report(good_edl)
    assert r["passed"] is False
    assert [p["code"] for p in r["problems"]] == ["V4"]


def test_report_passes_a_clean_edl(good_edl):
    from edl import Seg
    for i in range(6):
        good_edl.segs.append(
            Seg(kind="beat", dur=1.0, seg_id=f"s{i + 1}", chapter="payoff",
                fitness=True))
    r = report(good_edl)
    assert r["passed"] is True
    assert r["problems"] == []


def test_report_includes_runtime(good_edl):
    assert report(good_edl)["runtime_s"] == 100.0


def test_rendered_duration_mismatch_is_a_problem(good_edl):
    r = report(good_edl, rendered_dur=104.0)
    assert any(p["code"] == "V7" for p in r["problems"])


def test_rendered_duration_within_tolerance_is_fine(good_edl):
    r = report(good_edl, rendered_dur=100.1)
    assert not any(p["code"] == "V7" for p in r["problems"])
