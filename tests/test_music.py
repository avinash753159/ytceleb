import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from music import score_plan  # noqa: E402


CUES = [
    {"file": "dread_a.mp3", "function": "dread", "bpm": 70, "dur": 180.0,
     "source": "YouTube Audio Library", "license": "YTAL",
     "content_id_checked": True},
    {"file": "protocol_a.mp3", "function": "protocol", "bpm": 120,
     "dur": 200.0, "source": "Pixabay", "license": "CC0",
     "content_id_checked": True},
    # unverified listed FIRST so a naive implementation would pick it
    {"file": "payoff_unverified.mp3", "function": "payoff", "bpm": 60,
     "dur": 200.0, "source": "Uppbeat", "license": "free",
     "content_id_checked": False},
    {"file": "payoff_a.mp3", "function": "payoff", "bpm": 60, "dur": 200.0,
     "source": "YouTube Audio Library", "license": "YTAL",
     "content_id_checked": True},
]

CHAPTER_FN = {"open": "dread", "protocol": "protocol", "payoff": "payoff"}


def test_score_plan_assigns_one_cue_per_chapter(good_edl):
    plan = score_plan(good_edl, CUES, CHAPTER_FN)
    assert [p["chapter"] for p in plan] == ["open", "protocol", "payoff"]


def test_score_plan_cue_enters_at_chapter_start(good_edl):
    plan = score_plan(good_edl, CUES, CHAPTER_FN)
    assert plan[0]["at"] == 0.0
    assert plan[1]["at"] == 45.0        # 25 + 15 + 5
    assert plan[2]["at"] == 75.0        # + 15 + 15


def test_score_plan_cue_spans_the_whole_chapter(good_edl):
    plan = score_plan(good_edl, CUES, CHAPTER_FN)
    assert plan[0]["dur"] == 45.0
    assert plan[1]["dur"] == 30.0
    assert plan[2]["dur"] == 25.0


def test_score_plan_never_picks_an_unverified_cue(good_edl):
    plan = score_plan(good_edl, CUES, CHAPTER_FN)
    assert plan[2]["cue"] == "payoff_a.mp3"


def test_score_plan_raises_when_a_function_has_only_unverified_cues(
        good_edl):
    cues = [c for c in CUES if c["file"] != "payoff_a.mp3"]
    try:
        score_plan(good_edl, cues, CHAPTER_FN)
    except ValueError as ex:
        assert "payoff" in str(ex)
    else:
        raise AssertionError("expected ValueError")


def test_score_plan_raises_when_no_cue_for_a_used_function(good_edl):
    try:
        score_plan(good_edl, [CUES[1]], CHAPTER_FN)
    except ValueError as ex:
        assert "dread" in str(ex)
    else:
        raise AssertionError("expected ValueError")


def test_score_plan_ignores_chapters_with_no_dramatic_function(good_edl):
    plan = score_plan(good_edl, CUES, {"protocol": "protocol"})
    assert [p["chapter"] for p in plan] == ["protocol"]
