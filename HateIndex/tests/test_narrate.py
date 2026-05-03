"""Table-driven tests for narration band helpers. Pure functions, no I/O."""
from __future__ import annotations

import pytest

from scripts.narrate import (
    drawdown_phrase,
    momentum_phrase,
    positioning_phrase,
    headline_phrase,
    rotation_phrase,
    build_commentary,
)


@pytest.mark.parametrize("z, dd, expect_substr", [
    (2.5, -0.42, "deeper drawdown than 95%"),
    (1.4, -0.28, "more depressed than two-thirds"),
    (0.1, -0.05, "normal historical range"),
    (-1.5, 0.10, "no drawdown signal"),
    (None, -0.20, None),
])
def test_drawdown_phrase_bands(z, dd, expect_substr):
    out = drawdown_phrase(z, dd)
    if expect_substr is None:
        assert out is None
    else:
        assert expect_substr in out


@pytest.mark.parametrize("z, expect_substr", [
    (2.0, "underperforming the benchmark"),
    (0.0, "tracking the benchmark"),
    (-1.5, "outperforming the benchmark"),
    (None, None),
])
def test_momentum_phrase_bands(z, expect_substr):
    out = momentum_phrase(z)
    if expect_substr is None:
        assert out is None
    else:
        assert expect_substr in out.lower()


def test_positioning_phrase_null_returns_none():
    assert positioning_phrase(None) is None


def test_positioning_phrase_negative_z_means_long():
    assert "long" in positioning_phrase(-1.5).lower()


def test_positioning_phrase_positive_z_means_short():
    assert "short" in positioning_phrase(1.5).lower()


def test_headline_phrase_includes_score_and_rank():
    out = headline_phrase("Lithium", -1.0, universe_scores=[1.9, 0.8, -1.0, -1.2])
    assert "Lithium" in out
    assert "-1.0" in out


def test_headline_phrase_top_score_lands_in_top_third():
    """The maximum score should rank top third, even when score is rounded
    relative to the unrounded universe (regression for the float-equality
    `in` bug that silently collapsed all ranks to the bottom)."""
    out = headline_phrase("Nat Gas", 1.92, universe_scores=[
        1.9213, 1.25, 0.6, 0.5, 0.0, -0.5, -0.6, -0.85, -1.0, -1.18, -1.26, -1.39
    ])
    assert "top third" in out


def test_headline_phrase_bottom_score_lands_in_bottom_third():
    out = headline_phrase("Copper", -1.39, universe_scores=[
        1.92, 1.25, 0.6, 0.5, 0.0, -0.5, -0.6, -0.85, -1.0, -1.18, -1.26, -1.39
    ])
    assert "bottom third" in out


def test_rotation_phrase_unchanged_status():
    assert "Lagging" in rotation_phrase("Lagging", just_entered=False)


def test_rotation_phrase_just_entered_leading_is_flagged():
    out = rotation_phrase("Lagging→Leading", just_entered=True)
    assert "fresh" in out.lower() or "rotated" in out.lower()


def test_build_commentary_returns_three_keys():
    out = build_commentary(
        name="Lithium",
        score=-1.0,
        universe_scores=[1.9, 0.8, -1.0, -1.2],
        components={"drawdown": 1.4, "momentum": 0.6, "positioning": None,
                    "flows": None, "valuation": None, "sentiment": None},
        drawdown_pct=-0.28,
        status="Lagging→Leading",
        just_entered=True,
    )
    assert set(out.keys()) == {"headline", "components", "rotation"}
    assert isinstance(out["components"], list)
    # null components produce explicit "not available" notes
    assert any("not available" in s.lower() for s in out["components"])
