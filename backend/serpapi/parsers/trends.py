"""Google Trends: analyse the time series itself instead of treating points as documents."""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus

from backend.models.responses import EvidenceItem, TrendHorizon, TrendSeries
from .common import make_evidence, parse_datetime


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        text = str(value).replace("<", "").replace(",", "").strip()
        return float(text)
    except ValueError:
        return None


_WINDOW_LABELS = {"today 1-m": "past month", "today 3-m": "past 3 months", "today 12-m": "past 12 months",
                  "today 5-y": "past 5 years", "now 7-d": "past 7 days"}


def _direction(change: float | None, recent: float) -> str:
    if change is None:
        return "rising" if recent > 0 else "flat"
    return "rising" if change >= 12 else "falling" if change <= -12 else "flat"


def _horizon(values: list[float], stamps: list[int], days: int, label: str) -> TrendHorizon | None:
    """Mean interest in the last `days` vs the `days` before it (needs real timestamps)."""
    if len(stamps) != len(values) or len(values) < 6:
        return None
    end = stamps[-1]
    span = days * 86400
    if stamps[0] > end - 2 * span + 3 * 86400:      # series too short for two full periods
        return None
    recent = [v for v, t in zip(values, stamps) if t > end - span]
    prior = [v for v, t in zip(values, stamps) if end - 2 * span < t <= end - span]
    if len(recent) < 2 or len(prior) < 2:
        return None
    r, p = sum(recent) / len(recent), sum(prior) / len(prior)
    change = ((r - p) / p * 100.0) if p > 0 else None
    return TrendHorizon(label=label, days=days, change_pct=round(change, 1) if change is not None else None,
                        direction=_direction(change, r))


def parse_series(payload: dict[str, Any], *, query: str, region: str | None = None, window: str | None = None) -> list[TrendSeries]:
    block = payload.get("interest_over_time") or {}
    timeline = block.get("timeline_data", []) or [] if isinstance(block, dict) else []
    labels: list[str] = []
    values: list[float] = []
    stamps: list[int] = []
    for point in timeline:
        if not isinstance(point, dict):
            continue
        vals = point.get("values") or []
        first = vals[0] if vals and isinstance(vals[0], dict) else {}
        number = _number(first.get("extracted_value", first.get("value")))
        if number is None:
            continue
        labels.append(str(point.get("date") or point.get("timestamp") or len(labels)))
        values.append(number)
        ts = parse_datetime(point.get("timestamp"))
        if ts is not None:
            stamps.append(int(ts.timestamp()))
    if len(values) < 4:
        return []
    if len(stamps) != len(values):
        stamps = []

    # (1) change *inside the requested window*: latest 15% vs the 15% before it.
    w = max(2, math.ceil(len(values) * 0.15))
    recent = values[-w:]
    prior = values[-2 * w:-w] or values[:w]
    recent_avg, prior_avg = sum(recent) / len(recent), sum(prior) / len(prior)
    win_change = ((recent_avg - prior_avg) / prior_avg * 100.0) if prior_avg > 0 else None
    win_dir = _direction(win_change, recent_avg)

    # (2) comparable horizons, identical in every mode (computed from timestamps).
    horizons = [h for h in (
        _horizon(values, stamps, 30, "last 30 days vs the 30 days before"),
        _horizon(values, stamps, 90, "last 90 days vs the 90 days before"),
        _horizon(values, stamps, 365, "last 12 months vs the 12 months before"),
    ) if h]
    primary = horizons[0] if horizons else None
    change = primary.change_pct if primary else win_change
    direction = primary.direction if primary else win_dir

    span = None
    if stamps:
        fmt = lambda t: datetime.fromtimestamp(t, tz=timezone.utc).strftime("%b %d %Y")
        span = f"{fmt(stamps[0])} → {fmt(stamps[-1])}"
    peak = max(range(len(values)), key=values.__getitem__)
    return [TrendSeries(
        query=query, region=region, labels=labels, values=values, timestamps=stamps,
        recent_avg=round(recent_avg, 1), prior_avg=round(prior_avg, 1),
        change_pct=round(change, 1) if change is not None else None, direction=direction, peak_index=peak,
        window=window, window_label=_WINDOW_LABELS.get(window or "", window), points=len(values), span=span,
        window_change_pct=round(win_change, 1) if win_change is not None else None, window_direction=win_dir,
        horizons=horizons,
    )]


def parse(payload: dict[str, Any], *, query: str, engine: str = "google_trends") -> list[EvidenceItem]:
    """One evidence record summarising the series, plus related rising queries when present."""
    evidence: list[EvidenceItem] = []
    trend_url = f"https://trends.google.com/trends/explore?q={quote_plus(query)}"

    series = parse_series(payload, query=query)
    if series:
        s = series[0]
        timeline = (payload.get("interest_over_time") or {}).get("timeline_data", []) or []
        last = timeline[-1] if timeline else {}
        when = parse_datetime(last.get("timestamp")) or parse_datetime(last.get("date")) if isinstance(last, dict) else None
        change_txt = f"{s.change_pct:+.0f}%" if s.change_pct is not None else "n/a"
        snippet = (f"Search-interest index (0–100), {s.window_label or 'requested window'} ({s.span or f'{s.points} points'}). "
                   f"Last 30 days vs the 30 days before: {change_txt} ({s.direction}). "
                   f"Peak was {s.labels[s.peak_index]}. Attention only: not a price signal.")
        evidence.append(make_evidence(
            engine=engine, source="Google Trends",
            title=f"Search interest for “{query}” is {s.direction}",
            url=trend_url, snippet=snippet, published_at=when or None,
            claim=snippet, relevance=0.95, retrieval_rank=1, snapshot=True,
        ))

    for bucket_name, bucket in (("related query", payload.get("related_queries")), ("related topic", payload.get("related_topics"))):
        if not isinstance(bucket, dict):
            continue
        for direction in ("rising", "top"):
            for index, item in enumerate((bucket.get(direction, []) or [])[:5]):
                if not isinstance(item, dict):
                    continue
                label = item.get("query") or item.get("topic") or item.get("value")
                if not label:
                    continue
                evidence.append(make_evidence(
                    engine=engine, source="Google Trends",
                    title=f"{bucket_name.title()}: {label}", url=trend_url,
                    snippet=f"{direction.title()} {bucket_name}: {label}", claim=str(label),
                    relevance=max(0.0, 0.8 - index * 0.05), snapshot=True,
                ))
    return evidence
