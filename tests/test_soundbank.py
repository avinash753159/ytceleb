import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from soundbank import merge_words  # noqa: E402


def w(t0, t1, word):
    return (t0, t1, word)


def test_merge_splits_on_sentence_end():
    words = [w(0.0, 0.4, "He"), w(0.4, 0.8, "was"), w(0.8, 1.4, "fifteen."),
             w(1.5, 1.9, "Nobody"), w(1.9, 2.4, "knew.")]
    out = merge_words(words)
    assert len(out) == 2
    assert out[0]["text"] == "He was fifteen."
    assert out[0]["t0"] == 0.0 and out[0]["t1"] == 1.4
    assert out[1]["text"] == "Nobody knew."


def test_merge_splits_on_long_gap():
    words = [w(0.0, 0.4, "He"), w(0.4, 0.8, "was"),
             w(5.0, 5.4, "gone")]
    out = merge_words(words, max_gap=0.6)
    assert len(out) == 2
    assert out[0]["text"] == "He was"
    assert out[1]["text"] == "gone"


def test_merge_splits_when_utterance_exceeds_max_dur():
    words = [w(float(i), float(i) + 0.5, f"x{i}") for i in range(40)]
    out = merge_words(words, max_gap=2.0, max_dur=10.0)
    assert all(u["t1"] - u["t0"] <= 10.0 for u in out)
    assert len(out) >= 4


def test_merge_handles_quoted_sentence_end():
    words = [w(0.0, 0.5, 'gone."'), w(0.6, 1.0, "Next")]
    out = merge_words(words)
    assert len(out) == 2


def test_merge_of_empty_input_is_empty():
    assert merge_words([]) == []


def test_merge_single_oversized_word():
    """A single word exceeding max_dur is emitted as its own utterance."""
    words = [w(0.0, 12.0, "longword"), w(13.0, 13.5, "next")]
    out = merge_words(words, max_dur=10.0)
    assert len(out) == 2
    assert out[0]["text"] == "longword"
    assert out[0]["t0"] == 0.0 and out[0]["t1"] == 12.0
    assert out[1]["text"] == "next"
    assert out[1]["t0"] == 13.0 and out[1]["t1"] == 13.5


def test_merge_mixed_normal_and_oversized():
    """Post-append check isolates oversized words from normal text."""
    words = [
        w(0.0, 0.5, "hello"),
        w(0.6, 0.9, "world"),
        w(1.0, 11.5, "verylongword"),
        w(12.0, 12.5, "bye"),
    ]
    out = merge_words(words, max_dur=10.0)
    # Should be: "hello world" + "verylongword" + "bye"
    assert len(out) == 3
    assert out[0]["text"] == "hello world"
    assert out[0]["t1"] - out[0]["t0"] <= 10.0
    assert out[1]["text"] == "verylongword"
    # Oversized word will exceed max_dur (cannot be split)
    assert out[2]["text"] == "bye"
    assert out[2]["t1"] - out[2]["t0"] <= 10.0


from soundbank import query  # noqa: E402


def rec(sid, t0, t1, speaker, text, tags=(), emotion="", clean=True):
    return {"source_id": sid, "t0": t0, "t1": t1, "speaker": speaker,
            "text": text, "topic_tags": list(tags), "emotion": emotion,
            "on_camera": True, "audio_clean": clean}


BANK = [
    rec("a", 0, 5, "subject", "I was going ten times a day.",
        tags=["crohns"], emotion="pain"),
    rec("b", 0, 4, "coach", "He never missed a session.", tags=["training"]),
    rec("c", 0, 40, "subject", "Long rambling crohns answer.",
        tags=["crohns"]),
    rec("d", 0, 3, "subject", "The crohns thing was brutal.", clean=False),
]


def test_query_filters_by_speaker():
    out = query(BANK, speaker="coach")
    assert [r["source_id"] for r in out] == ["b"]


def test_query_excludes_bites_over_max_dur():
    out = query(BANK, topic="crohns", max_dur=30.0)
    assert "c" not in [r["source_id"] for r in out]


def test_query_ranks_tag_match_above_text_match():
    out = query(BANK, topic="crohns", max_dur=30.0)
    assert out[0]["source_id"] == "a"


def test_query_emotion_boosts_score():
    out = query(BANK, topic="crohns", emotion="pain", max_dur=30.0)
    assert out[0]["source_id"] == "a"


def test_query_respects_limit():
    assert len(query(BANK, limit=2)) == 2


def test_query_with_no_criteria_returns_everything_under_max_dur():
    assert len(query(BANK, max_dur=30.0)) == 3


def test_query_tie_break_prefers_shorter_bite():
    """When two records score identically, shorter duration wins."""
    bank = [
        rec("short", 0, 4, "subject", "I have crohns disease.",
            tags=["crohns"], emotion="pain", clean=True),
        rec("long", 0, 20, "subject", "I have crohns disease and it was very painful.",
            tags=["crohns"], emotion="pain", clean=True),
    ]
    out = query(bank, topic="crohns", emotion="pain")
    assert [r["source_id"] for r in out] == ["short", "long"]


def test_query_orders_by_score_then_duration():
    """Score dominates over duration; within ties, shorter wins."""
    bank = [
        rec("high_score_medium", 0, 15, "subject", "crohns disease management",
            tags=["crohns"], emotion="pain", clean=True),
        rec("high_score_long", 0, 25, "subject", "I have crohns and it affects everything",
            tags=["crohns"], emotion="pain", clean=True),
        rec("low_score_short", 0, 3, "subject", "The crohns thing",
            tags=["training"], emotion="", clean=True),
    ]
    out = query(bank, topic="crohns", emotion="pain")
    assert [r["source_id"] for r in out] == ["high_score_medium", "high_score_long", "low_score_short"]
