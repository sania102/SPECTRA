"""Deterministic signal scoring from normalized evidence.

No LLM is involved. Every score is derived from observable properties of the
evidence and keeps the ids of the items that produced it, so the UI can show
exactly why a signal is high or low.

Signal strength (per information surface)
    quality = mean over items of (0.70 * relevance + 0.30 * freshness)
    volume  = min(1, n / 8) ** 0.8                       # n = relevant items kept
    strength = quality * (0.25 + 0.75 * volume)         # ~5+ relevant items needed to reach "high"

Google Trends is different: it already is a time series, so
    level     = recent average interest index / 100
    momentum  = clamp(0.5 + change_pct / 200)
    strength  = 0.60 * level + 0.40 * momentum

Strength is *evidence strength on that surface*. It is not a probability that any
real-world outcome will happen.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from math import log1p
from typing import Iterable

from backend.models.responses import EvidenceItem, Signal, TrendSeries

ENGINE_TO_SIGNAL = {
    "google": "Public Web Presence",
    "google_news": "News Momentum",
    "google_trends": "Public Attention",
    "google_scholar": "Research Activity",
    "google_jobs": "Hiring Demand",
    "google_shopping": "Commercial Availability",
    "google_patents": "Patent Activity",
    "youtube": "Video Attention",
}
SIGNAL_TO_SURFACE = {
    "Public Web Presence": "web", "News Momentum": "news", "Public Attention": "trends", "Research Activity": "scholar",
    "Hiring Demand": "jobs", "Commercial Availability": "shopping", "Patent Activity": "patents", "Video Attention": "video",
}
SURFACE_ALIASES = {v: k for k, v in SIGNAL_TO_SURFACE.items()}

HIGH, MEDIUM = 0.65, 0.40


def level_for(strength: float) -> str:
    return "high" if strength >= HIGH else "medium" if strength >= MEDIUM else "low"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _freshness(item: EvidenceItem, now: datetime) -> float:
    if item.date_kind == "observed":
        return 1.0                      # live snapshot: observed right now
    if item.published_at is None:
        return 0.5                      # unknown age: neutral, never rewarded
    age_days = max((now - _as_utc(item.published_at)).total_seconds() / 86400.0, 0.0)
    # Scholar/patents are legitimately older; soften their decay.
    half_life = 365.0 if item.engine in {"google_scholar", "google_patents"} else 90.0
    return max(0.05, min(1.0, 1.0 / (1.0 + age_days / half_life)))


def _item_weight(item: EvidenceItem, now: datetime) -> float:
    return 0.70 * item.relevance + 0.30 * _freshness(item, now)


def _strength(weights: list[float]) -> float:
    if not weights:
        return 0.0
    quality = _mean(weights)
    volume = min(1.0, len(weights) / 8.0) ** 0.8
    # One great result is an anecdote, not a signal: quality is scaled by how much evidence backs it.
    return round(quality * (0.25 + 0.75 * volume), 3)


def _confidence(items: list[EvidenceItem]) -> float:
    if not items:
        return 0.0
    sources = len({i.source.strip().lower() for i in items if i.source})
    diversity = min(1.0, sources / 4.0)
    coverage = min(1.0, len(items) / 6.0)
    relevance = _mean([i.relevance for i in items])
    return round(0.35 * diversity + 0.25 * coverage + 0.40 * relevance, 3)


def _trend_signal(items: list[EvidenceItem], series: TrendSeries) -> Signal:
    level = max(0.0, min(1.0, series.recent_avg / 100.0))
    change = series.change_pct if series.change_pct is not None else 0.0
    momentum = max(0.0, min(1.0, 0.5 + change / 200.0))
    points = len(series.values)
    confidence = round(min(0.9, 0.35 + 0.01 * points) if points >= 8 else 0.35, 3)
    change_txt = f"{change:+.0f}%" if series.change_pct is not None else "n/a"
    return Signal(
        name="Public Attention", surface="trends",
        strength=round(0.60 * level + 0.40 * momentum, 3), confidence=confidence,
        level=level_for(0.60 * level + 0.40 * momentum), evidence_count=len(items),
        trend=series.direction, evidence_ids=[i.id for i in items],
        rationale=(f"Google Trends time series ({points} points): recent interest index {series.recent_avg:.0f}/100, "
                   f"{change_txt} vs prior window → {series.direction}."),
    )


def build_signals(evidence: Iterable[EvidenceItem], trend_series: list[TrendSeries] | None = None) -> list[Signal]:
    now = datetime.now(timezone.utc)
    groups: dict[str, list[EvidenceItem]] = defaultdict(list)
    for item in evidence:
        name = ENGINE_TO_SIGNAL.get(item.engine) or SURFACE_ALIASES.get(item.engine)
        if name:
            groups[name].append(item)

    series_list = [s for s in (trend_series or []) if s.values]
    signals: list[Signal] = []
    for name, items in groups.items():
        if name == "Public Attention" and series_list:
            # Prefer the un-regioned series, otherwise the first.
            main = next((s for s in series_list if not s.region), series_list[0])
            signals.append(_trend_signal(items, main))
            continue

        weights = [_item_weight(i, now) for i in items]
        dated = [i for i in items if i.published_at is not None]
        recent = [i for i in dated if (now - _as_utc(i.published_at)).days <= 60]
        if any(i.date_kind == "observed" for i in items) and not dated:
            trend = "snapshot"
        elif recent and len(recent) >= max(1, len(dated) // 2):
            trend = "active"
        elif dated:
            trend = "older"
        else:
            trend = "undated"
        strength = _strength(weights)
        signals.append(Signal(
            name=name, surface=SIGNAL_TO_SURFACE.get(name), strength=strength, confidence=_confidence(items),
            level=level_for(strength), evidence_count=len(items), trend=trend,
            evidence_ids=[i.id for i in items],
            rationale=(f"{len(items)} relevant result(s) from {len({i.source for i in items if i.source})} source(s); "
                       "score blends relevance, freshness and volume."),
        ))
    return sorted(signals, key=lambda s: s.strength, reverse=True)
