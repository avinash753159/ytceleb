import ast
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

import v11_assemble  # noqa: E402
from edl import EDL, Seg  # noqa: E402
from v11_assemble import (  # noqa: E402
    SyncError, bite_cmds, check_sync, concat_cmd, fade_cmds,
    fit_run_durations, music_mix_cmd, narration_texts, norm_cmds,
)

WORK = Path("/tmp/v11work")


def _edl():
    return EDL(
        segs=[Seg(kind="narr", dur=10.0, seg_id="n0", chapter="open",
                  text="He was fifteen."),
              Seg(kind="narr", dur=8.0, seg_id="n1", chapter="open",
                  text="Nobody knew."),
              Seg(kind="bite", dur=6.0, seg_id="b0", chapter="open",
                  source="vid1", t0=42.0, speaker="subject"),
              Seg(kind="narr", dur=5.0, seg_id="n2", chapter="open",
                  text="Not for eight years.")],
        protocol_chapter="protocol", subject_speaker="subject")


# ---- F7(3): narration is GENERATED per run, never sliced -------------

def test_one_tts_input_per_run_not_per_segment():
    texts = narration_texts(_edl())
    assert len(texts) == 2          # two runs, not three narr segments


def test_run_text_joins_its_segments_in_order():
    assert narration_texts(_edl())[0] == "He was fifteen. Nobody knew."


def test_fit_distributes_measured_duration_across_a_run():
    e = _edl()
    fit_run_durations(e, [30.0, 5.0])
    # run 0 texts are 15 and 12 chars -> 30s split 15:12
    assert round(e.segs[0].dur + e.segs[1].dur, 3) == 30.0
    assert e.segs[0].dur > e.segs[1].dur
    assert e.segs[3].dur == 5.0


def test_fit_leaves_bites_untouched():
    e = _edl()
    fit_run_durations(e, [30.0, 5.0])
    assert e.segs[2].dur == 6.0


def test_fit_rejects_wrong_number_of_runs():
    try:
        fit_run_durations(_edl(), [30.0])
    except ValueError as ex:
        assert "2 runs" in str(ex)
    else:
        raise AssertionError("expected ValueError")


# ---- F7(4): never acrossfade -----------------------------------------

def test_no_command_ever_uses_acrossfade():
    e = _edl()
    all_cmds = [c for c, _ in norm_cmds([Path("r0.wav")], WORK, "narr")]
    all_cmds += [c for c, _ in bite_cmds(e, {"vid1": Path("v1.mp4")}, WORK)]
    all_cmds += [c for c, _ in fade_cmds([(Path("a.wav"), 5.0)], WORK)]
    all_cmds.append(concat_cmd([Path("a.wav")], WORK / "l.txt",
                               WORK / "o.wav"))
    all_cmds.append(music_mix_cmd(
        WORK / "base.wav",
        [{"chapter": "open", "cue": "c.mp3", "at": 0.0, "dur": 10.0}],
        Path("cues"), WORK / "m.wav"))
    for c in all_cmds:
        assert "acrossfade" not in " ".join(c)

    # Source-level guard: the enumeration above only covers builders known
    # at test-writing time, so a future builder could add acrossfade and
    # silently escape it. Scan the module's own source instead. The rule
    # is legitimately named in docstrings, so strip docstrings via the
    # AST (not string matching) before asserting the literal is gone from
    # everything else - including any f-string template a builder emits.
    src = Path(v11_assemble.__file__).read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef,
                             ast.AsyncFunctionDef, ast.ClassDef)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                node.body[0].value.value = ""
    assert "acrossfade" not in ast.unparse(tree)


# ---- butt-join with 30ms edge fades ----------------------------------

def test_fade_applies_30ms_in_and_out_at_the_right_offset():
    (cmd, _), = fade_cmds([(Path("a.wav"), 5.0)], WORK)
    joined = " ".join(cmd)
    assert "afade=t=in:d=0.03" in joined
    assert "afade=t=out:st=4.970:d=0.03" in joined


def test_fade_out_start_never_goes_negative_on_a_tiny_chunk():
    (cmd, _), = fade_cmds([(Path("a.wav"), 0.01)], WORK)
    assert "afade=t=out:st=0.000:d=0.03" in " ".join(cmd)


def test_fade_normalises_to_stereo_48k():
    (cmd, _), = fade_cmds([(Path("a.wav"), 5.0)], WORK)
    joined = " ".join(cmd)
    assert "channel_layouts=stereo" in joined
    assert "sample_rates=48000" in joined


def test_concat_uses_the_demuxer_and_stream_copy():
    cmd = concat_cmd([Path("a.wav")], WORK / "l.txt", WORK / "o.wav")
    assert "-f" in cmd and "concat" in cmd
    assert "-c" in cmd and "copy" in cmd


# ---- F7(1)+(2): amix normalize=0, stereo before mixing ---------------

def test_music_mix_disables_amix_renormalisation():
    cmd = music_mix_cmd(
        WORK / "base.wav",
        [{"chapter": "open", "cue": "c.mp3", "at": 0.0, "dur": 10.0}],
        Path("cues"), WORK / "m.wav")
    assert "normalize=0" in " ".join(cmd)


def test_every_music_input_is_stereo_before_mixing():
    cmd = music_mix_cmd(
        WORK / "base.wav",
        [{"chapter": "open", "cue": "a.mp3", "at": 0.0, "dur": 10.0},
         {"chapter": "protocol", "cue": "b.mp3", "at": 10.0, "dur": 8.0}],
        Path("cues"), WORK / "m.wav")
    joined = " ".join(cmd)
    assert joined.count("channel_layouts=stereo") >= 2


def test_music_mix_aformats_the_base_track_before_mixing():
    # Correctness for rule 2 must hold inside this function, not rest on
    # an upstream invariant that fade_cmds/concat_cmd already produced
    # stereo - if a mono base ever reaches here, rule 2's original bug
    # (narration comes back 3dB hot) must still be impossible.
    cmd = music_mix_cmd(
        WORK / "base.wav",
        [{"chapter": "open", "cue": "c.mp3", "at": 0.0, "dur": 10.0}],
        Path("cues"), WORK / "m.wav")
    joined = " ".join(cmd)
    assert "[0:a]aformat=channel_layouts=stereo:sample_rates=48000" in joined


def test_music_cue_is_delayed_to_its_chapter_offset():
    cmd = music_mix_cmd(
        WORK / "base.wav",
        [{"chapter": "protocol", "cue": "b.mp3", "at": 12.5, "dur": 8.0}],
        Path("cues"), WORK / "m.wav")
    assert "adelay=12500|12500" in " ".join(cmd)


# ---- bites ------------------------------------------------------------

def test_bite_is_extracted_from_its_source_window():
    (cmd, _), = bite_cmds(_edl(), {"vid1": Path("v1.mp4")}, WORK)
    # Exact argv positions, not unanchored substrings - "-t 16.0" or a
    # t0 of 142.0 would still contain "6.0"/"42.0" as substrings.
    assert cmd[cmd.index("-ss") + 1] == "42.0"
    assert cmd[cmd.index("-t") + 1] == "6.0"


def test_bite_seeks_before_input_not_after():
    (cmd, _), = bite_cmds(_edl(), {"vid1": Path("v1.mp4")}, WORK)
    # -ss after -i silently switches ffmpeg from fast, accurate
    # input-seeking to slow output-seeking.
    assert cmd.index("-ss") < cmd.index("-i")


def test_bite_for_missing_source_raises():
    with pytest.raises(KeyError):
        bite_cmds(_edl(), {}, WORK)


# ---- the hard sync gate ----------------------------------------------

def test_sync_gate_passes_within_tolerance():
    check_sync(100.0, 100.2)


def test_sync_gate_raises_past_tolerance():
    with pytest.raises(SyncError):
        check_sync(100.0, 100.4)


def test_sync_gate_is_symmetric():
    with pytest.raises(SyncError):
        check_sync(100.4, 100.0)


def test_sync_gate_does_not_raise_at_exactly_the_tolerance():
    # code correctly uses > not >= - a mutation to >= would go uncaught
    # without this, in either drift direction.
    check_sync(100.0, 100.25)
    check_sync(100.25, 100.0)


from v11_assemble import audio_chunk_order  # noqa: E402


def test_chunk_order_interleaves_runs_and_bites():
    names = [p.name for p in audio_chunk_order(_edl(), WORK)]
    assert names == ["narr_00.wav", "bite_b0.wav", "narr_01.wav"]


def test_chunk_order_ignores_cards_and_beats():
    e = EDL(segs=[Seg(kind="card", dur=3.0, seg_id="c0",
                      chapter="protocol"),
                  Seg(kind="beat", dur=2.0, seg_id="s0", chapter="open"),
                  Seg(kind="narr", dur=4.0, seg_id="n0", chapter="open")],
            protocol_chapter="protocol", subject_speaker="subject")
    names = [p.name for p in audio_chunk_order(e, WORK)]
    assert names == ["narr_00.wav"]


def test_chunk_order_is_empty_for_an_empty_edl():
    e = EDL(segs=[], protocol_chapter="protocol",
            subject_speaker="subject")
    assert audio_chunk_order(e, WORK) == []


# ---- timeline_audio_plan(): the fix for the card/beat gap --------------

from v11_assemble import silence_cmd, timeline_audio_plan  # noqa: E402


def _edl_with_gaps():
    """narr, beat, bite, card, then a two-segment narration run - covers
    every kind audio_chunk_order() drops (card, beat) plus a multi-
    segment run, so silence placement and run-folding are both exercised.
    """
    return EDL(
        segs=[Seg(kind="narr", dur=10.0, seg_id="n0", chapter="open",
                  text="He was fifteen."),
              Seg(kind="beat", dur=3.0, seg_id="s0", chapter="open"),
              Seg(kind="bite", dur=6.0, seg_id="b0", chapter="open",
                  source="vid1", t0=42.0, speaker="subject"),
              Seg(kind="card", dur=14.0, seg_id="c0", chapter="protocol"),
              Seg(kind="narr", dur=8.0, seg_id="n1", chapter="protocol",
                  text="Nobody knew."),
              Seg(kind="narr", dur=5.0, seg_id="n2", chapter="protocol",
                  text="Not for eight years.")],
        protocol_chapter="protocol", subject_speaker="subject")


def test_plan_interleaves_silence_at_the_correct_position():
    e = _edl_with_gaps()
    plan = timeline_audio_plan(e, WORK)
    # Must fail if silence were appended at the tail instead of spliced
    # in place: the exact (kind, seg_id) sequence, in timeline order.
    assert [(p["kind"], p["seg_id"]) for p in plan] == [
        ("chunk", "n0"),
        ("silence", "s0"),
        ("chunk", "b0"),
        ("silence", "c0"),
        ("chunk", "n1"),   # run start; n2 folds into this entry
    ]


def test_plan_silence_dur_matches_its_segment():
    e = _edl_with_gaps()
    plan = timeline_audio_plan(e, WORK)
    by_id = {p["seg_id"]: p for p in plan}
    assert by_id["s0"]["dur"] == 3.0
    assert by_id["c0"]["dur"] == 14.0


def test_plan_total_duration_matches_edl_total():
    e = _edl_with_gaps()
    plan = timeline_audio_plan(e, WORK)
    assert round(sum(p["dur"] for p in plan), 6) == e.total()


def test_plan_names_match_audio_chunk_order_naming():
    e = _edl_with_gaps()
    plan = timeline_audio_plan(e, WORK)
    chunks = [p for p in plan if p["kind"] == "chunk"]
    assert [p["path"].name for p in chunks] == ["narr_00.wav", "bite_b0.wav",
                                                 "narr_01.wav"]


def test_plan_with_no_cards_or_beats_matches_audio_chunk_order():
    e = _edl()
    plan = timeline_audio_plan(e, WORK)
    assert all(p["kind"] == "chunk" for p in plan)
    assert [p["path"] for p in plan] == audio_chunk_order(e, WORK)


def test_silence_cmd_is_48k_stereo_for_exact_duration():
    cmd = silence_cmd(3.5, WORK / "sil.wav")
    joined = " ".join(cmd)
    assert "anullsrc=r=48000:cl=stereo" in joined
    assert cmd[cmd.index("-t") + 1] == "3.5"
