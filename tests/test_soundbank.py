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
