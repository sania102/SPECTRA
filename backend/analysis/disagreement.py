"""Claim grouping and disagreement detection.

Claim groups answer "which statements are repeated across independent sources?".
Disagreements answer "where do sources point in opposite directions?".

Both are deterministic. Direction comes from item.stance, which is either the LLM's
label (when available) or the lexicon in analysis.stance.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable
from uuid import uuid4

from backend.analysis.direction import effective_directional
from backend.analysis.text import jaccard, stem_set
from backend.models.responses import ClaimGroup, Disagreement, EvidenceItem, TrendSeries

DIRECTIONAL_ENGINES = {"google", "google_news", "youtube"}
STANCE_NAMES = {"up": "upward / strengthening", "down": "downward / weakening"}


def _sources(items: Iterable[EvidenceItem]) -> set[str]:
    return {(i.source_domain or i.source or "").lower() for i in items if (i.source_domain or i.source)}


def build_claim_groups(evidence: Iterable[EvidenceItem]) -> list[ClaimGroup]:
    items = [i for i in evidence if i.engine not in {"google_trends", "google_shopping", "google_jobs"} and (i.claim or i.title)]
    clusters: list[tuple[set[str], list[EvidenceItem]]] = []
    for item in sorted(items, key=lambda i: -i.relevance):
        tokens = stem_set(item.title + " " + (item.claim or ""))
        placed = False
        for rep, members in clusters:
            overlap = len(tokens & rep)
            if jaccard(tokens, rep) >= 0.45 or (overlap >= 4 and jaccard(tokens, rep) >= 0.33):
                members.append(item)
                rep |= set()  # representative stays that of the most relevant member
                placed = True
                break
        if not placed:
            clusters.append((tokens, [item]))

    groups: list[ClaimGroup] = []
    for _, members in clusters:
        if len(members) < 2:
            continue
        src = _sources(members)
        stances = [m.stance for m in members if m.stance in {"up", "down"}]
        stance = max(set(stances), key=stances.count) if stances else None
        groups.append(ClaimGroup(
            id=f"claim_{uuid4().hex[:10]}", label=members[0].title[:160], stance=stance,
            claim_count=len(members), source_count=len(src),
            surfaces=sorted({m.source_type or m.engine for m in members}),
            evidence_ids=[m.id for m in members], corroborated=len(src) >= 2,
        ))

    # Theme groups: how many independent sources point the same direction.
    by_stance: dict[str, list[EvidenceItem]] = defaultdict(list)
    for item in items:
        if item.engine in DIRECTIONAL_ENGINES and item.stance in {"up", "down"}:
            by_stance[item.stance].append(item)
    for stance, members in by_stance.items():
        if len(members) >= 2:
            src = _sources(members)
            groups.append(ClaimGroup(
                id=f"theme_{stance}_{uuid4().hex[:6]}",
                label=f"{len(members)} sources point {STANCE_NAMES[stance]}", stance=stance,
                claim_count=len(members), source_count=len(src),
                surfaces=sorted({m.source_type or m.engine for m in members}),
                evidence_ids=[m.id for m in members], corroborated=len(src) >= 2,
            ))
    return sorted(groups, key=lambda g: (g.corroborated, g.source_count, g.claim_count), reverse=True)


def directional_counts(evidence: Iterable[EvidenceItem], horizon: str = "unspecified") -> tuple[list[EvidenceItem], list[EvidenceItem], int]:
    """Up / down items after duplicate collapsing and horizon filtering (see analysis.direction)."""
    kept, _, _ = effective_directional(evidence, horizon)
    ups = [i for i in kept if i.stance == "up"]
    downs = [i for i in kept if i.stance == "down"]
    return ups, downs, len(kept)


def detect_disagreements(evidence: Iterable[EvidenceItem], trend_series: list[TrendSeries] | None = None,
                         horizon: str = "unspecified") -> list[Disagreement]:
    items = list(evidence)
    ups, downs, _ = directional_counts(items, horizon)
    out: list[Disagreement] = []

    up_src, down_src = _sources(ups), _sources(downs)
    if len(up_src) >= 2 and len(down_src) >= 2:  # independence: two *sources* on each side, not two headlines
        total = len(up_src) + len(down_src)
        minority = min(len(up_src), len(down_src)) / total
        if minority >= 0.25:
            engines = {i.engine for i in ups + downs}
            conf = min(0.9, 0.30 + 0.10 * min(len(up_src), len(down_src)) + 0.60 * minority)
            out.append(Disagreement(
                id=f"dis_{uuid4().hex[:10]}", topic="Direction of travel",
                kind="within_surface" if len(engines) == 1 else "across_surfaces",
                side_a_label=f"{len(up_src)} source(s) ({len(ups)} item(s)) point upward / strengthening",
                side_b_label=f"{len(down_src)} source(s) ({len(downs)} item(s)) point downward / weakening",
                side_a_evidence_ids=[i.id for i in ups], side_b_evidence_ids=[i.id for i in downs],
                side_a_sources=len(up_src), side_b_sources=len(down_src), confidence=round(conf, 3),
                explanation=(f"Independent sources split roughly {len(up_src)}:{len(down_src)} on direction. A headline summary would hide that "
                             "a substantial minority of coverage says the opposite."),
            ))

    series = next((s for s in (trend_series or []) if s.values), None)
    if series and series.direction in {"rising", "falling"}:
        trend_ids = [i.id for i in items if i.engine == "google_trends"]
        news_ups = [i for i in ups if i.engine == "google_news"]
        news_downs = [i for i in downs if i.engine == "google_news"]
        if series.direction == "rising" and len(news_downs) >= 2 and len(news_downs) >= 2 * max(1, len(news_ups)):
            out.append(Disagreement(
                id=f"dis_{uuid4().hex[:10]}", topic="Public interest vs news tone", kind="across_surfaces",
                side_a_label=f"Search interest is rising ({series.change_pct:+.0f}%)" if series.change_pct is not None else "Search interest is rising",
                side_b_label=f"{len(news_downs)} news item(s) lean negative",
                side_a_evidence_ids=trend_ids, side_b_evidence_ids=[i.id for i in news_downs],
                side_a_sources=1, side_b_sources=len(_sources(news_downs)), confidence=0.55,
                explanation="People are searching more while recent coverage leans the other way — attention is not the same as good news.",
            ))
        elif series.direction == "falling" and len(news_ups) >= 2 and len(news_ups) >= 2 * max(1, len(news_downs)):
            out.append(Disagreement(
                id=f"dis_{uuid4().hex[:10]}", topic="Public interest vs news tone", kind="across_surfaces",
                side_a_label=f"Search interest is falling ({series.change_pct:+.0f}%)" if series.change_pct is not None else "Search interest is falling",
                side_b_label=f"{len(news_ups)} news item(s) lean positive",
                side_a_evidence_ids=trend_ids, side_b_evidence_ids=[i.id for i in news_ups],
                side_a_sources=1, side_b_sources=len(_sources(news_ups)), confidence=0.55,
                explanation="Coverage sounds optimistic while public search interest is fading.",
            ))
    return out
