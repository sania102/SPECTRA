from __future__ import annotations

from typing import Any

from backend.models.responses import EvidenceItem
from .common import make_evidence
from .base import first_text


def parse(payload: dict[str, Any], *, query: str, engine: str = "google_scholar") -> list[EvidenceItem]:
    items = payload.get("organic_results", []) or []
    evidence: list[EvidenceItem] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        title = first_text(item, "title") or f"Scholar result {index + 1}"
        url = first_text(item, "link") or ""
        publication = item.get("publication_info", {})
        summary = publication.get("summary") if isinstance(publication, dict) else None
        # "A Smith, B Jones - Nature, 2023 - nature.com" -> the year is the date signal.
        date_value = item.get("year") or summary
        evidence.append(
            make_evidence(
                engine=engine,
                source="Google Scholar",
                title=title,
                url=url,
                snippet=first_text(item, "snippet"),
                published_at=date_value,
                relevance=max(0.0, 1.0 - index * 0.08),
                retrieval_rank=index + 1,
                snapshot=False,
            )
        )
    return evidence
