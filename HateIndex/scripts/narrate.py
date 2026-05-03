"""
Pure-function narration helpers.

Each component has a band-based template that turns a z-score into a sentence
in the project voice (numbers + comparison + caveat; no exclamation marks).
build_commentary() composes the three blocks the dashboard reads.
"""
from __future__ import annotations

from typing import Optional


def drawdown_phrase(z: Optional[float], drawdown_pct: float) -> Optional[str]:
    if z is None:
        return None
    abs_dd = abs(drawdown_pct) * 100
    if z >= 2:
        return f"Trading {abs_dd:.0f}% below 5-year max — deeper drawdown than 95% of historical weeks."
    if z >= 1:
        return f"Trading {abs_dd:.0f}% below 5-year max — more depressed than two-thirds of weeks."
    if z >= -1:
        return "Drawdown is in the normal historical range."
    return "Above its 5-year average — no drawdown signal."


def momentum_phrase(z: Optional[float]) -> Optional[str]:
    if z is None:
        return None
    if z >= 1:
        return "Underperforming the benchmark — relative momentum negative."
    if z <= -1:
        return "Outperforming the benchmark — relative momentum positive."
    return "Tracking the benchmark — no momentum signal."


def positioning_phrase(z: Optional[float]) -> Optional[str]:
    if z is None:
        return None
    if z >= 1:
        return "Managed money is short — extreme bearish positioning."
    if z <= -1:
        return "Managed money is long — extreme bullish positioning."
    return "Managed money positioning is neutral."


def headline_phrase(name: str, score: float, universe_scores: list[float]) -> str:
    sorted_desc = sorted(universe_scores, reverse=True)
    n = len(sorted_desc) or 1
    # Use nearest-index match instead of float-equality `in`, since `score` may be
    # rounded while universe_scores are not (silent rank-collapse to the bottom otherwise).
    rank = min(range(len(sorted_desc)), key=lambda i: abs(sorted_desc[i] - score)) + 1 if sorted_desc else 1
    if rank <= n / 3:
        rank_label = "top third — the market hates this"
    elif rank <= 2 * n / 3:
        rank_label = "middle of the pack"
    else:
        rank_label = "bottom third — not yet hated"
    return f"{name} at {score:+.1f} sits in the {rank_label}."


def rotation_phrase(status: str, just_entered: bool) -> str:
    if just_entered and "Leading" in status:
        return f"{status}: rotated into Leading — fresh momentum, signal active."
    if just_entered and "Improving" in status:
        return f"{status}: rotated into Improving — early-stage rotation."
    if "→" in status:
        return f"{status}: rotation in progress."
    return f"{status}: unchanged this week."


def build_commentary(
    name: str,
    score: float,
    universe_scores: list[float],
    components: dict,
    drawdown_pct: float,
    status: str,
    just_entered: bool,
) -> dict:
    parts: list[str] = []
    dd = drawdown_phrase(components.get("drawdown"), drawdown_pct)
    mo = momentum_phrase(components.get("momentum"))
    po = positioning_phrase(components.get("positioning"))
    if dd: parts.append(dd)
    if mo: parts.append(mo)
    if po: parts.append(po)
    else:  parts.append("Positioning data not available — CFTC does not publish a managed-money series for this contract.")
    for k in ("flows", "valuation", "sentiment"):
        if components.get(k) is None:
            parts.append(f"{k.title()} component not yet implemented (Phase 7).")

    return {
        "headline":   headline_phrase(name, score, universe_scores),
        "components": parts,
        "rotation":   rotation_phrase(status, just_entered),
    }
