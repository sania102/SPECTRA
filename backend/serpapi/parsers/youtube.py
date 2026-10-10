from __future__ import annotations

from typing import Any

from backend.models.responses import EvidenceItem
from .common import make_evidence
from .base import first_text


def parse(payload: dict[str, Any], *, query: str, engine: str = "youtube") -> list[EvidenceItem]:
    items = payload.get("video_results", []) or payload.get("organic_results", []) or []
    evidence: list[EvidenceItem] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        title = first_text(item, "title") or f"YouTube result {index + 1}"
        url = first_text(item, "link") or ""
        channel = item.get("channel")
        channel_name = channel.get("name") if isinstance(channel, dict) else channel
        views = item.get("views")
        snippet = first_text(item, "description", "snippet")
        if views:
            snippet = f"{snippet + ' · ' if snippet else ''}{int(views):,} views" if isinstance(views, (int, float)) else f"{snippet + ' · ' if snippet else ''}{views} views"
        evidence.append(
            make_evidence(
                engine=engine,
                source=first_text({"v": channel_name}, "v") or "YouTube",
                title=title,
                url=url,
                snippet=snippet,
                published_at=item.get("published_date") or item.get("published"),
                relevance=max(0.0, 1.0 - index * 0.06),
                retrieval_rank=index + 1,
            )
        )
    return evidence
