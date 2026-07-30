#!/usr/bin/env python3
"""eval_rubric.py - the Incredible rubric as data + the pure scoring math.

This is the single machine-read copy of every weight and anchor. `eval/RUBRIC.md`
is the human source of truth and MUST match this file; `eval.py --calibrate`
fails if the scoring drifts. Everything here is pure (no I/O, no LLM, no ffmpeg)
so the scoring math is trivially testable - run `python eval_rubric.py` for a
self-check.

North star = audience outcome (CTR / retention / watch-time / sub-conversion).
Every dimension is a *predictor* of one of those metrics. The 10 is Gavia's
Khamzat film; the channel's own drafts should land ~4-6 (the gap is the point).

Composite:
    CraftScore = 0.25*A + 0.25*B + 0.20*C + 0.30*D
    TechFactor = 1.0 - sum(failing-gate deductions); a hard fail clamps <= 0.5
    INCREDIBLE = round(CraftScore * TechFactor, 1)        # predictive
    INCREDIBLE = OutcomeScore(F)                           # measured
"""

# --- craft categories A-D (weights sum to 1.0; dim weights sum to 1.0 each) ---

CRAFT = {
    "hook": {
        "name": "Hook / Cold Open", "weight": 0.25, "predicts": "30s retention",
        "dims": {
            "withheld_promise": {"weight": 0.35, "predicts": "30s retention",
                "anchor10": "opens on a concrete unanswered question paid off at the end",
                "anchor0": "states the thesis in sentence three"},
            "first_line_loop": {"weight": 0.25, "predicts": "30s retention",
                "anchor10": "a first line you cannot walk away from",
                "anchor0": "generic date-and-place scene-set"},
            "arresting_first_frame": {"weight": 0.20, "predicts": "production-value snap judgment",
                "anchor10": "a charged, legible image on frame one",
                "anchor0": "logo bug / title card / talking head first"},
            "time_to_hook": {"weight": 0.20, "predicts": "early drop-off",
                "anchor10": "zero throat-clearing; hook is beat zero",
                "anchor0": "branding/intro before any hook"},
        },
    },
    "story": {
        "name": "Story & Stakes", "weight": 0.25, "predicts": "average view duration",
        "dims": {
            "story_not_briefing": {"weight": 0.30, "predicts": "mid-video retention",
                "anchor10": "scene spine; a Wound the body answers",
                "anchor0": "magazine article read aloud, nothing at stake"},
            "escalating_antagonist": {"weight": 0.25, "predicts": "sustained attention",
                "anchor10": "act-1 antagonist replaced by a worse one, resolved act 3",
                "anchor0": "no opposition at all"},
            "payoff_resolves_loop": {"weight": 0.25, "predicts": "completion rate",
                "anchor10": "final chapter explicitly pays off the cold-open promise",
                "anchor0": "cold-open question never answered (or none exists)"},
            "chapters_are_hooks": {"weight": 0.10, "predicts": "mid-video re-hook",
                "anchor10": "every chapter title is itself a hook",
                "anchor0": "table-of-contents labels"},
            "real_voices": {"weight": 0.10, "predicts": "perceived authenticity",
                "anchor10": ">=40% runtime is real archival audio",
                "anchor0": "one synthetic VO for ten unbroken minutes"},
        },
    },
    "pacing": {
        "name": "Pacing & Delivery", "weight": 0.20, "predicts": "mid-video drop-off",
        "dims": {
            "breathing_room": {"weight": 0.30, "predicts": "fatigue drop-off",
                "anchor10": "music-and-picture beats let moments land",
                "anchor0": "zero silence, wall-to-wall VO"},
            "no_sagging_middle": {"weight": 0.25, "predicts": "middle-third retention",
                "anchor10": "momentum sustained across the whole arc",
                "anchor0": "energy flatlines after the setup"},
            "workout_delivers": {"weight": 0.25, "predicts": "sub-conversion",
                "anchor10": "protocol act >=90% training/physique/food; film >=35%",
                "anchor0": "off-topic footage; the promised protocol is thin"},
            "visual_variety": {"weight": 0.20, "predicts": "abandonment",
                "anchor10": "footage-first grammar, no repetition",
                "anchor0": "same treatment / stock footage on repeat"},
        },
    },
    "packaging": {
        "name": "Packaging (click layer)", "weight": 0.30, "predicts": "CTR",
        "dims": {
            "thumbnail_curiosity": {"weight": 0.40, "predicts": "CTR",
                "anchor10": "one legible face + emotion + a transformation tease",
                "anchor0": "cluttered, illegible at phone size, no face-emotion"},
            "title_hook_front": {"weight": 0.35, "predicts": "CTR x impressions",
                "anchor10": "Gavia hook in front, search terms behind",
                "anchor0": "search terms only"},
            "title_thumb_coherence": {"weight": 0.25, "predicts": "CTR-without-retention penalty",
                "anchor10": "one promise, reinforced across both",
                "anchor0": "disconnected or contradictory"},
        },
    },
}

CRAFT_ORDER = ["hook", "story", "pacing", "packaging"]

# --- category E: technical multiplier, folded from qc.py's gates ----------

SOFT_DEDUCTION = 0.06
TECH_GATES = {
    # qc_report.json gate key -> (is_hard, human label)
    "G8_duration":     (True,  "A/V duration sync"),
    "G6_black_freeze": (True,  "black / freeze frames"),
    "G7_loudness":     (False, "loudness -14 LUFS / -1 dBTP"),
    "G1_ocr":          (False, "no stray text / watermark"),
    "G3_shot_len":     (False, "shot length 1.2-6.0s"),
    "G2_reuse":        (False, "no scene reuse <90s"),
    "E_settings":      (False, "delivery settings (>=1080p, 24-30fps, h264/aac)"),
}
HARD_FLOOR = 0.5

# --- category F: measured-outcome anchors (10 == Gavia-tier target) --------

OUTCOME = {
    "ctr":               {"target": 0.06,  "predicts": "reach",        "unit": "fraction"},
    "retention_30s":     {"target": 0.70,  "predicts": "hook worked",  "unit": "fraction"},
    "avg_pct_viewed":    {"target": 0.45,  "predicts": "story held",   "unit": "fraction"},
    "avg_view_minutes":  {"target": 10.0,  "predicts": "watch-time",   "unit": "minutes"},
    "sub_conversion":    {"target": 0.010, "predicts": "payoff landed","unit": "fraction"},
    "like_ratio":        {"target": 0.04,  "predicts": "satisfaction", "unit": "fraction"},
}

# Calibration expectations
GAVIA_TOL = 1.2          # |composite - 10| must be <= this
DIM_TOL = 1.0            # each judged dim within +/- this of the golden scorecard
DRAFT_BAND = (3.0, 6.5)  # channel drafts must land inside this band


# ----------------------------- pure scoring -------------------------------

def _wmean(pairs):
    """Weighted mean over (weight, score) pairs, skipping None scores and
    re-normalizing over the present weights. Returns None if nothing present."""
    num = den = 0.0
    for w, s in pairs:
        if s is None:
            continue
        num += w * float(s)
        den += w
    return None if den == 0 else num / den


def category_score(cat_key, dim_scores):
    """Weighted mean of a category's dimensions. dim_scores maps dim-id -> 0-10
    or None (absent input). Returns None if every dim is absent."""
    dims = CRAFT[cat_key]["dims"]
    return _wmean([(d["weight"], dim_scores.get(k)) for k, d in dims.items()])


def craft_score(cat_scores):
    """Weighted mean of A-D. cat_scores maps category-key -> 0-10 or None."""
    return _wmean([(CRAFT[k]["weight"], cat_scores.get(k)) for k in CRAFT_ORDER])


def tech_factor(failing_gate_keys):
    """Fold qc.py's failing gates into a [HARD_FLOOR, 1.0] multiplier."""
    factor = 1.0
    hard = False
    for g in failing_gate_keys:
        is_hard, _ = TECH_GATES.get(g, (False, g))
        if is_hard:
            hard = True
        else:
            factor -= SOFT_DEDUCTION
    factor = max(0.0, factor)
    if hard:
        factor = min(factor, HARD_FLOOR)
    return round(factor, 3)


def outcome_metric_score(key, value):
    """Normalize one analytics metric to 0-10 against its Gavia-tier target."""
    if value is None:
        return None
    target = OUTCOME[key]["target"]
    if target <= 0:
        return None
    return round(max(0.0, min(10.0, 10.0 * float(value) / target)), 2)


def outcome_score(metrics):
    """Mean of the measured-outcome metrics (equal weight). metrics maps
    metric-key -> raw value or None."""
    scores = [outcome_metric_score(k, metrics.get(k)) for k in OUTCOME]
    present = [s for s in scores if s is not None]
    return None if not present else round(sum(present) / len(present), 2)


def composite_predictive(cat_scores, failing_gate_keys):
    craft = craft_score(cat_scores)
    tf = tech_factor(failing_gate_keys)
    inc = None if craft is None else round(craft * tf, 1)
    return {"incredible_score": inc, "craft_score": None if craft is None else round(craft, 2),
            "tech_factor": tf}


def _selftest():
    # a perfect craft film with clean tech -> ~10
    perfect = {k: 10 for k in CRAFT_ORDER}
    r = composite_predictive(perfect, [])
    assert r["tech_factor"] == 1.0, r
    assert r["incredible_score"] == 10.0, r

    # a soft gate deducts, a hard gate clamps
    assert tech_factor(["G7_loudness"]) == 0.94
    assert tech_factor(["G8_duration"]) == 0.5
    assert tech_factor(["G8_duration", "G7_loudness"]) == 0.5  # hard wins

    # category weighted mean respects dim weights & skips absent dims
    cs = category_score("packaging", {"thumbnail_curiosity": 10,
                                      "title_hook_front": 0,
                                      "title_thumb_coherence": None})
    # (0.40*10 + 0.35*0) / (0.40+0.35) = 5.333...
    assert abs(cs - 5.3333) < 1e-3, cs

    # craft weights sum to 1.0; dim weights sum to 1.0 per category
    assert abs(sum(CRAFT[k]["weight"] for k in CRAFT_ORDER) - 1.0) < 1e-9
    for k in CRAFT_ORDER:
        assert abs(sum(d["weight"] for d in CRAFT[k]["dims"].values()) - 1.0) < 1e-9, k

    # outcome normalization: hitting target == 10, half target == 5
    assert outcome_metric_score("ctr", 0.06) == 10.0
    assert outcome_metric_score("ctr", 0.03) == 5.0
    assert outcome_score({"ctr": 0.06, "retention_30s": 0.35}) == 7.5

    # a mid draft lands mid
    mid = {"hook": 4, "story": 5, "pacing": 6, "packaging": 4}
    inc = composite_predictive(mid, [])["incredible_score"]
    assert DRAFT_BAND[0] <= inc <= DRAFT_BAND[1], inc
    print("[OK] eval_rubric self-test passed; example mid-draft ->", inc)


if __name__ == "__main__":
    _selftest()
