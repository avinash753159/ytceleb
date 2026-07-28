import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from edl import EDL, Seg  # noqa: E402


@pytest.fixture
def good_edl():
    """A tiny EDL that passes every format gate. 100s total.

    50s bite (50%), 30s narr, 15s card in the protocol chapter, 5s beat.
    """
    segs = [
        Seg(kind="bite", dur=25.0, seg_id="b0", chapter="open",
            speaker="subject", promise="the_photo", fitness=False),
        Seg(kind="narr", dur=15.0, seg_id="n0", chapter="open"),
        Seg(kind="beat", dur=5.0, seg_id="s0", chapter="open", fitness=True),
        Seg(kind="card", dur=15.0, seg_id="c0", chapter="protocol",
            fitness=True),
        Seg(kind="narr", dur=15.0, seg_id="n1", chapter="protocol",
            fitness=True),
        Seg(kind="bite", dur=25.0, seg_id="b1", chapter="payoff",
            speaker="subject", resolves="the_photo", fitness=True),
    ]
    return EDL(segs=segs, protocol_chapter="protocol",
               subject_speaker="subject")
