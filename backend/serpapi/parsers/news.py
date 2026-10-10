from __future__ import annotations

from typing import Any

from backend.models.responses import EvidenceItem
from .common import make_evidence
from .base import first_text


def _flatten(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Google News returns plain results and also 'stories' bundles of related articles."""
    out: list[dict[str, Any]] = []
    for item in payload.get("news_results", []) or payload.get("organic_results", []) or []:
        if not isinstance(item, dict):
            continue
        stories = item.get("stories")
        if isinstance(stories, list) and stories:
            out.extend(s for s in stories if isinstance(s, dict))
        if item.get("title") and item.get("link"):
            out.append(item)
        elif item.get("highlight") and isinstance(item["highlight"], dict):
            out.append(item["highlight"])
    return out


def parse(payload: dict[str, Any], *, query: str, engine: str = "google_news") -> list[EvidenceItem]:
    evidence: list[EvidenceItem] = []
    for index, item in enumerate(_flatten(payload)):
        title = first_text(item, "title") or f"News result {index + 1}"
        url = first_text(item, "link", "url") or ""
        source_block = item.get("source")
        source_name = source_block.get("name") if isinstance(source_block, dict) else source_block
        evidence.append(
            make_evidence(
                engine=engine,
                source=first_text({"v": source_name}, "v") or "Google News",
                title=title,
                url=url,
                snippet=first_text(item, "snippet", "description"),
                published_at=item.get("iso_date") or item.get("date"),
                relevance=max(0.0, 1.0 - index * 0.05),
                retrieval_rank=index + 1,
            )
        )
    return evidence
