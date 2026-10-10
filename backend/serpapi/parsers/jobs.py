from __future__ import annotations

from typing import Any

from backend.models.responses import EvidenceItem
from .common import make_evidence
from .base import first_text


def parse(payload: dict[str, Any], *, query: str, engine: str = "google_jobs") -> list[EvidenceItem]:
    items = payload.get("jobs_results", []) or []
    evidence: list[EvidenceItem] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        title = first_text(item, "title") or f"Job result {index + 1}"
        company = first_text(item, "company_name")
        location = first_text(item, "location")
        url = first_text(item, "share_link", "link") or ""
        if not url:
            options = item.get("apply_options") or []
            if options and isinstance(options[0], dict):
                url = first_text(options[0], "link") or ""
        ext = item.get("detected_extensions") or {}
        posted = ext.get("posted_at") if isinstance(ext, dict) else None
        evidence.append(
            make_evidence(
                engine=engine,
                source=first_text(item, "via") or "Google Jobs",
                title=title,
                url=url,
                snippet=first_text(item, "description"),
                published_at=posted,
                entity=company,
                location=location,
                claim=f"{title} at {company}" if company else title,
                relevance=max(0.0, 1.0 - index * 0.06),
                retrieval_rank=index + 1,
            )
        )
    return evidence
