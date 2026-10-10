"""Query-aware relevance scoring and filtering.

The old pipeline scored relevance purely from rank (position 1 => 1.0, position 2 =>
0.92 ...), so an unrelated Tesla article at rank 1 looked perfectly relevant. Here the
score depends on whether the result actually talks about the investigated subject.
"""
from __future__ import annotations

from typing import Iterable

from backend.analysis.text import content_terms, stem
from backend.models.responses import EvidenceItem

# Engines whose results ARE the topic by construction (the query is the topic itself).
SKIP_FILTER_ENGINES = {"google_trends"}
MIN_ANCHOR_COVERAGE = 0.5


def _stems(text: str | None) -> set[str]:
    return {stem(t) for t in content_terms(text)}


def score_item(item: EvidenceItem, anchors: list[str], key_terms: list[str]) -> tuple[float, list[str], float]:
    """Return (relevance 0-1, matched terms, anchor coverage 0-1)."""
    title_stems = _stems(item.title)
    body_stems = _stems(" ".join(filter(None, [item.snippet, item.claim])))
    anchor_stems = [(a, stem(a)) for a in anchors]

    if not anchor_stems:
        return item.relevance, [], 1.0

    matched: list[str] = []
    weight = 0.0
    for raw, st in anchor_stems:
        in_title, in_body = st in title_stems, st in body_stems
        if in_title or in_body:
            matched.append(raw)
            weight += 1.0 if in_title else 0.7
    coverage = weight / len(anchor_stems)

    others = [stem(t) for t in key_terms if t not in anchors]
    other_cov = (sum(1 for s in others if s in title_stems or s in body_stems) / len(others)) if others else 0.0

    rank = item.retrieval_rank or 10
    rank_prior = 1.0 / (1.0 + 0.12 * (rank - 1))

    title_bonus = 1.0 if matched and all(stem(m) in title_stems for m in matched) else 0.0
    relevance = 0.55 * min(1.0, coverage) + 0.20 * other_cov + 0.15 * rank_prior + 0.10 * title_bonus
    return round(max(0.0, min(1.0, relevance)), 3), matched, min(1.0, coverage)


def apply_relevance(
    items: Iterable[EvidenceItem], anchors: list[str], key_terms: list[str],
) -> tuple[list[EvidenceItem], list[EvidenceItem]]:
    """Rescore every item; drop those that do not mention the investigated subject."""
    kept: list[EvidenceItem] = []
    dropped: list[EvidenceItem] = []
    for item in items:
        if item.engine in SKIP_FILTER_ENGINES:
            item.matched_terms = list(anchors)
            kept.append(item)
            continue
        relevance, matched, coverage = score_item(item, anchors, key_terms)
        item.relevance = relevance
        item.matched_terms = matched
        (kept if coverage >= MIN_ANCHOR_COVERAGE else dropped).append(item)
    return kept, dropped
