"""Directional evidence, counted without double-counting.

Three different things are easy to confuse:
  * evidence items   – individual search results (one publisher can contribute many)
  * claims           – statements extracted from those items (several items may repeat one claim)
  * unique sources   – independent publishers / domains

The lean SPECTRA reports is therefore computed from *sources*, after (1) collapsing
near-identical headlines (syndicated wire stories) and (2) excluding items that talk about
a different time horizon than the question (a "by 2030" forecast says nothing about next month).
Search interest (Google Trends) is attention, never a price direction, and is not used here.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable

from backend.analysis.text import jaccard, stem_set
from backend.models.responses import DirectionSummary, EvidenceItem

DIRECTIONAL_ENGINES = {"google", "google_news", "youtube"}
_NEAR_QUESTION = re.compile(r"\b(today|tomorrow|tonight|this week|next week|this month|next month|next few (days|weeks)|short[- ]term|"
                            r"coming (days|weeks)|right now|this quarter|next quarter)\b", re.I)
_LONG_ITEM = re.compile(r"\b(long[- ]term|decade|by 20(?:2[7-9]|[3-9]\d)|20(?:2[7-9]|[3-9]\d)|next year|five[- ]year|5[- ]year|"
                        r"through 20\d\d|until 20\d\d)\b", re.I)
_NEAR_ITEM = re.compile(r"\b(today|tonight|this week|this month|next week|next month|tomorrow|week|intraday|session|"
                        r"october|november|december|q4|oct\b)\b", re.I)


def question_horizon(question: str) -> str:
    return "near" if _NEAR_QUESTION.search(question or "") else "unspecified"


def tag_horizons(items: Iterable[EvidenceItem]) -> None:
    year = datetime.now(timezone.utc).year
    for item in items:
        text = f"{item.title} {item.snippet or ''}"
        long_years = [int(y) for y in re.findall(r"\b(20\d\d)\b", text) if int(y) > year]
        if _LONG_ITEM.search(text) and (long_years or re.search(r"long[- ]term|decade|next year|five|5[- ]year", text, re.I)):
            item.horizon = "long"
        elif _NEAR_ITEM.search(text):
            item.horizon = "near"


def _source_key(item: EvidenceItem) -> str:
    return (item.source_domain or item.source or "").strip().casefold().removeprefix("www.")


def effective_directional(evidence: Iterable[EvidenceItem], horizon: str = "unspecified") -> tuple[list[EvidenceItem], int, int]:
    """Directional items after removing near-duplicate headlines and off-horizon forecasts.

    Returns (items, duplicates_collapsed, long_horizon_excluded).
    """
    pool = [i for i in evidence if i.engine in DIRECTIONAL_ENGINES and i.stance in {"up", "down"}]
    pool.sort(key=lambda i: -i.relevance)
    kept: list[EvidenceItem] = []
    reps: list[set[str]] = []
    collapsed = excluded = 0
    for item in pool:
        if horizon == "near" and item.horizon == "long":
            excluded += 1
            continue
        tokens = stem_set(item.title)
        if len(tokens) >= 4 and any(jaccard(tokens, r) >= 0.7 for r in reps):
            collapsed += 1
            continue
        reps.append(tokens)
        kept.append(item)
    return kept, collapsed, excluded


def summarize_direction(evidence: Iterable[EvidenceItem], horizon: str = "unspecified") -> DirectionSummary:
    items = list(evidence)
    kept, collapsed, excluded = effective_directional(items, horizon)
    votes: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    surfaces_up: set[str] = set()
    surfaces_down: set[str] = set()
    for it in kept:
        key = _source_key(it)
        if not key:
            continue
        votes[key][0 if it.stance == "up" else 1] += 1
        (surfaces_up if it.stance == "up" else surfaces_down).add(it.source_type or it.engine)
    s_up = sum(1 for u, d in votes.values() if u > d)
    s_down = sum(1 for u, d in votes.values() if d > u)
    s_mixed = sum(1 for u, d in votes.values() if u == d)
    decided = s_up + s_down
    share = round(s_up / decided, 3) if decided else None
    lean = "insufficient" if decided < 4 else "upward" if share >= 0.65 else "downward" if share <= 0.35 else "mixed"
    neutral = sum(1 for i in items if i.engine in DIRECTIONAL_ENGINES and i.stance in {"neutral", "mixed", None})
    note = (f"{len(kept)} directional item(s) from {len(votes)} unique source(s): {s_up} lean up, {s_down} lean down"
            + (f", {s_mixed} split" if s_mixed else "") + "."
            + (f" {collapsed} near-duplicate headline(s) were counted once." if collapsed else "")
            + (f" {excluded} long-horizon forecast(s) were excluded because the question is about the near term." if excluded else ""))
    return DirectionSummary(
        items_up=sum(1 for i in kept if i.stance == "up"), items_down=sum(1 for i in kept if i.stance == "down"),
        items_neutral=neutral, directional_items=len(kept), duplicates_collapsed=collapsed, long_horizon_excluded=excluded,
        unique_sources=len(votes), sources_up=s_up, sources_down=s_down, sources_mixed=s_mixed,
        surfaces_up=sorted(surfaces_up), surfaces_down=sorted(surfaces_down), share_up=share, lean=lean, note=note,
    )
