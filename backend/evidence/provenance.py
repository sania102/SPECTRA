"""Evidence provenance and source traceability helpers."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from backend.models.responses import BlindSpot, Divergence, EvidenceItem, Signal


@dataclass(frozen=True)
class EvidenceTrace:
    evidence_id: str
    title: str
    url: str | None
    source: str
    engine: str
    relevance: float


def build_evidence_index(evidence: Iterable[EvidenceItem]) -> dict[str, EvidenceTrace]:
    return {
        item.id: EvidenceTrace(
            evidence_id=item.id,
            title=item.title,
            url=item.url,
            source=item.source,
            engine=item.engine,
            relevance=item.relevance,
        )
        for item in evidence
    }


def evidence_for_signal(signal: Signal, evidence: Iterable[EvidenceItem]) -> list[EvidenceTrace]:
    index = build_evidence_index(evidence)
    return [index[eid] for eid in signal.evidence_ids if eid in index]


def evidence_for_divergence(
    divergence: Divergence,
    signals: Iterable[Signal],
    evidence: Iterable[EvidenceItem],
) -> list[EvidenceTrace]:
    signal_map = {signal.name: signal for signal in signals}
    ids: list[str] = []
    for name in (divergence.left_signal, divergence.right_signal):
        signal = signal_map.get(name)
        if signal:
            ids.extend(signal.evidence_ids)
    index = build_evidence_index(evidence)
    return [index[eid] for eid in dict.fromkeys(ids) if eid in index]


def evidence_for_blind_spot(
    blind_spot: BlindSpot,
    evidence: Iterable[EvidenceItem],
) -> list[EvidenceTrace]:
    index = build_evidence_index(evidence)
    return [index[eid] for eid in blind_spot.evidence_ids if eid in index]


def provenance_summary(
    signals: Iterable[Signal],
    divergences: Iterable[Divergence],
    blind_spots: Iterable[BlindSpot],
) -> dict:
    """Create a compact graph summary suitable for an API response/UI."""
    signal_map = {signal.name: signal for signal in signals}
    divergence_items = list(divergences)
    blind_spot_items = list(blind_spots)

    signal_evidence = {
        signal.name: list(dict.fromkeys(signal.evidence_ids))
        for signal in signal_map.values()
    }
    divergence_evidence = {}
    for item in divergence_items:
        ids: list[str] = []
        for name in (item.left_signal, item.right_signal):
            signal = signal_map.get(name)
            if signal:
                ids.extend(signal.evidence_ids)
        divergence_evidence[item.id] = list(dict.fromkeys(ids))

    return {
        "signals": signal_evidence,
        "divergences": divergence_evidence,
        "blind_spots": {
            item.id: list(dict.fromkeys(item.evidence_ids)) for item in blind_spot_items
        },
    }
