"""Claim extraction and evidence-to-claim traceability.

Claims are grounded in text already present in a search result. When a dedicated
claim field is absent, the snippet (or, if absent, the title) is retained as a
source statement; this is not a prediction or an independently verified fact.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from backend.models.responses import EvidenceItem


@dataclass(frozen=True)
class EvidenceClaim:
    evidence_id: str
    claim: str
    source: str
    url: str | None


def extract_claims(evidence: Iterable[EvidenceItem]) -> list[EvidenceClaim]:
    """Extract traceable source statements without inventing missing facts."""
    extracted: list[EvidenceClaim] = []
    for item in evidence:
        claim = (item.claim or item.snippet or item.title or "").strip()
        if not claim:
            continue
        extracted.append(
            EvidenceClaim(
                evidence_id=item.id,
                claim=" ".join(claim.split()),
                source=item.source,
                url=item.url,
            )
        )
    return extracted
