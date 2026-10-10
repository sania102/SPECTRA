"""Cross-surface divergence detection.

A divergence is a *meaningful* gap between two information surfaces: one is strong,
the other clearly weaker, and both are backed by actual observations.

    gap        = |strength_a - strength_b|
    confidence = 0.70 * min(conf_a, conf_b) + 0.30 * min(1, gap / 0.5)

Pairs with a known interpretation get tailored wording; any other pair that clears
the thresholds is reported with a generic (but still evidence-linked) explanation.
"""
from __future__ import annotations

from itertools import combinations
from typing import Iterable
from uuid import uuid4

from backend.models.responses import Divergence, Signal, TrendSeries

PAIR_EXPLANATIONS: dict[frozenset[str], str] = {
    frozenset(("Public Attention", "Commercial Availability")): "Search interest and observable commercial availability are at different levels.",
    frozenset(("News Momentum", "Commercial Availability")): "Media coverage and observable commercial availability are not aligned.",
    frozenset(("Research Activity", "Commercial Availability")): "Research activity and observable commercial availability show a meaningful gap.",
    frozenset(("Patent Activity", "Commercial Availability")): "Patent activity and observable commercial availability are not aligned.",
    frozenset(("Hiring Demand", "Commercial Availability")): "Hiring demand and observable commercial availability are at different levels.",
    frozenset(("Public Attention", "Research Activity")): "Public interest and research activity are not moving together.",
    frozenset(("News Momentum", "Research Activity")): "Media coverage and research activity show a meaningful gap.",
    frozenset(("Public Attention", "Hiring Demand")): "Public interest and hiring demand are not aligned.",
    frozenset(("News Momentum", "Hiring Demand")): "Media coverage and hiring demand are not aligned.",
    frozenset(("News Momentum", "Public Attention")): "What the media covers and what people actually search for are different.",
    frozenset(("Public Web Presence", "Commercial Availability")): "Web visibility and commercial listings tell different stories.",
    frozenset(("Video Attention", "Commercial Availability")): "Video attention and commercial availability are at different levels.",
    frozenset(("Research Activity", "Hiring Demand")): "Research activity is not matched by hiring activity.",
    frozenset(("Video Attention", "Research Activity")): "Video attention and research activity differ.",
}

DEFAULT_MIN_GAP = 0.22
DEFAULT_MIN_CONFIDENCE = 0.40
DEFAULT_MIN_STRONGER = 0.45
MIN_WEAKER_CONFIDENCE = 0.25


def _confidence(left: Signal, right: Signal, gap: float) -> float:
    support = min(left.confidence, right.confidence)
    return round(0.70 * support + 0.30 * min(1.0, gap / 0.50), 3)


def detect_divergences(
    signals: Iterable[Signal],
    trend_series: list[TrendSeries] | None = None,
    *,
    min_gap: float = DEFAULT_MIN_GAP,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    min_stronger: float = DEFAULT_MIN_STRONGER,
) -> list[Divergence]:
    sig = list(signals)
    results: list[Divergence] = []

    for a, b in combinations(sig, 2):
        gap = round(abs(a.strength - b.strength), 3)
        high, low = (a, b) if a.strength >= b.strength else (b, a)
        if gap < min_gap or high.strength < min_stronger or low.confidence < MIN_WEAKER_CONFIDENCE:
            continue
        confidence = _confidence(a, b, gap)
        if confidence < min_confidence:
            continue
        key = frozenset((a.name, b.name))
        if key not in PAIR_EXPLANATIONS and (low.level != "low" or gap < 0.30):
            continue  # unfamiliar pairs only count when one side is clearly weak
        base = PAIR_EXPLANATIONS.get(key, f"{high.name} and {low.name} are at clearly different levels.")
        results.append(Divergence(
            id=f"div_{uuid4().hex[:12]}", left_signal=high.name, right_signal=low.name,
            magnitude=gap, confidence=confidence, higher_signal=high.name, lower_signal=low.name, kind="level",
            explanation=f"{base} {high.name} is {high.level} ({high.strength:.2f}) while {low.name} is {low.level} ({low.strength:.2f}).",
        ))

    # Early-signal divergence: attention is moving fast but adoption surfaces are not.
    by_name = {s.name: s for s in sig}
    attention = by_name.get("Public Attention")
    series = next((s for s in (trend_series or []) if s.values), None)
    if attention and series and series.direction == "rising" and (series.change_pct or 0) >= 25:
        for adoption_name in ("Hiring Demand", "Commercial Availability"):
            adoption = by_name.get(adoption_name)
            if adoption and adoption.level == "low" and adoption.confidence >= MIN_WEAKER_CONFIDENCE:
                results.append(Divergence(
                    id=f"div_{uuid4().hex[:12]}", left_signal="Public Attention", right_signal=adoption_name,
                    magnitude=round(min(1.0, (series.change_pct or 0) / 100.0), 3),
                    confidence=round(min(attention.confidence, adoption.confidence) * 0.9, 3),
                    higher_signal="Public Attention", lower_signal=adoption_name, kind="momentum",
                    explanation=(f"Early-signal divergence: search interest is up {series.change_pct:.0f}% versus the prior window, "
                                 f"but {adoption_name} remains low ({adoption.strength:.2f})."),
                ))

    return sorted(results, key=lambda d: d.magnitude * d.confidence, reverse=True)
