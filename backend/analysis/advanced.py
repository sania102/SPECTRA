"""Entity, temporal, geographic-context and cross-surface summaries (all deterministic)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from backend.analysis.entities import group_entities
from backend.models.responses import EvidenceItem, Signal


@dataclass(frozen=True)
class EntityProfile:
    canonical: str
    mentions: int
    evidence_ids: list[str]
    source_types: list[str]
    aliases: list[str]


@dataclass(frozen=True)
class TemporalSummary:
    recent_count: int
    prior_count: int
    undated_count: int
    snapshot_count: int
    recent_share: float
    temporal_coverage: float
    direction: str


@dataclass(frozen=True)
class ContextSummary:
    geography: str | None
    matched_count: int
    unspecified_count: int
    mismatch_count: int
    context_coverage: float


@dataclass(frozen=True)
class CrossSurfaceFinding:
    id: str
    finding_type: str
    title: str
    description: str
    signal_names: list[str]
    evidence_ids: list[str]
    confidence: float


def _clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value).strip() if value else ""


def build_entity_profiles(evidence: Iterable[EvidenceItem], exclude: set[str] | None = None) -> list[EntityProfile]:
    return [
        EntityProfile(canonical=g.display, mentions=len(g.evidence_ids), evidence_ids=g.evidence_ids,
                      source_types=sorted(g.source_types), aliases=sorted(g.aliases))
        for g in group_entities(evidence, exclude=exclude)
    ]


def _days_old(item: EvidenceItem, now: datetime) -> float | None:
    if item.published_at is None:
        return None
    published = item.published_at
    published = published.replace(tzinfo=timezone.utc) if published.tzinfo is None else published.astimezone(timezone.utc)
    return max(0.0, (now - published).total_seconds() / 86400.0)


def summarize_temporal_context(evidence: Iterable[EvidenceItem], *, recent_days: int = 90) -> TemporalSummary:
    """Dating quality and direction.

    Coverage is measured over *time-bearing* evidence only. Live snapshots (shopping
    listings, trend summaries) are counted separately instead of being wrongly
    treated as "undated".
    """
    now = datetime.now(timezone.utc)
    recent = older = undated = snapshots = 0
    rate_recent = rate_prior = 0
    for item in evidence:
        age = _days_old(item, now)
        if age is None:
            if item.date_kind == "observed":
                snapshots += 1
            else:
                undated += 1
            continue
        if age <= recent_days:
            recent += 1
        else:
            older += 1
        if item.engine in {"google_news", "google", "youtube"}:
            if age <= 14:
                rate_recent += 1
            elif age <= 60:
                rate_prior += 1

    dated = recent + older
    directional_dated = rate_recent + rate_prior
    if directional_dated < 3:
        direction = "unknown"
    else:
        per_day_recent, per_day_prior = rate_recent / 14.0, rate_prior / 46.0
        if per_day_recent > 1.5 * per_day_prior and rate_recent >= 2:
            direction = "accelerating"
        elif per_day_recent < 0.5 * per_day_prior and rate_prior >= 3:
            direction = "cooling"
        else:
            direction = "steady"
    total = dated + undated
    return TemporalSummary(
        recent_count=recent, prior_count=older, undated_count=undated, snapshot_count=snapshots,
        recent_share=round(recent / dated, 3) if dated else 0.0,
        temporal_coverage=round(dated / total, 3) if total else 0.0, direction=direction,
    )


def summarize_context(evidence: Iterable[EvidenceItem], geography: str | None) -> ContextSummary:
    items = list(evidence)
    target = _clean(geography).casefold()
    if not target:
        return ContextSummary(None, 0, len(items), 0, 0.0)
    matched = unspecified = mismatch = 0
    for item in items:
        location = _clean(item.location or item.region).casefold()
        if not location:
            unspecified += 1
        elif target in location or location in target:
            matched += 1
        else:
            mismatch += 1
    specified = matched + mismatch
    return ContextSummary(geography, matched, unspecified, mismatch, round(matched / specified, 3) if specified else 0.0)


def cross_surface_findings(signals: Iterable[Signal], evidence: Iterable[EvidenceItem]) -> list[CrossSurfaceFinding]:
    by_name = {s.name: s for s in signals}
    evidence_list = list(evidence)
    findings: list[CrossSurfaceFinding] = []

    source_types = sorted({i.source_type or i.engine for i in evidence_list})
    if len(source_types) >= 3:
        findings.append(CrossSurfaceFinding(
            id="cross_broad_coverage", finding_type="coverage", title="Multi-surface evidence",
            description=(f"The investigation draws on {len(source_types)} distinct surfaces ({', '.join(source_types)}), "
                         "so conclusions depend less on any single search channel."),
            signal_names=[s.name for s in by_name.values()], evidence_ids=[i.id for i in evidence_list[:24]],
            confidence=round(min(1.0, 0.40 + 0.10 * len(source_types)), 3),
        ))

    pairs = [
        ("Research Activity", "Patent Activity", "Research and patent activity both show technical momentum."),
        ("Hiring Demand", "Research Activity", "Hiring and research activity are both observable — a talent-to-research cross-check."),
        ("Public Attention", "News Momentum", "Search interest and news momentum reinforce each other."),
        ("News Momentum", "Commercial Availability", "Media coverage is matched by visible commercial listings."),
    ]
    for left_name, right_name, description in pairs:
        left, right = by_name.get(left_name), by_name.get(right_name)
        if not left or not right or min(left.strength, right.strength) < 0.50:
            continue
        findings.append(CrossSurfaceFinding(
            id=f"cross_{left_name[:3].lower()}_{right_name[:3].lower()}", finding_type="reinforcement",
            title=f"{left_name} ↔ {right_name} agree", description=description,
            signal_names=[left_name, right_name],
            evidence_ids=list(dict.fromkeys([*left.evidence_ids[:10], *right.evidence_ids[:10]])),
            confidence=round(min(left.confidence, right.confidence) * 0.9, 3),
        ))
    return findings
