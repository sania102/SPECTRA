from __future__ import annotations

from typing import Any

from backend.models.responses import EvidenceItem
from .common import make_evidence
from .base import first_text


def parse(payload: dict[str, Any], *, query: str, engine: str = "google_patents") -> list[EvidenceItem]:
    items = payload.get("organic_results", []) or []
    evidence: list[EvidenceItem] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        title = first_text(item, "title") or f"Patent result {index + 1}"
        url = first_text(item, "patent_link", "link", "pdf") or ""
        publication = first_text(item, "publication_number", "patent_id")
        assignee = first_text(item, "assignee", "company")
        date_value = (item.get("publication_date") or item.get("filing_date")
                      or item.get("grant_date") or item.get("priority_date"))
        evidence.append(
            make_evidence(
                engine=engine,
                source="Google Patents",
                title=title,
                url=url or (f"https://patents.google.com/patent/{publication}" if publication else ""),
                snippet=first_text(item, "snippet", "description"),
                published_at=date_value,
                entity=assignee,
                claim=f"Patent {publication}: {title}" if publication else title,
                relevance=max(0.0, 1.0 - index * 0.07),
                retrieval_rank=index + 1,
                snapshot=False,
            )
        )
    return evidence
