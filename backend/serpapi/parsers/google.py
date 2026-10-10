from __future__ import annotations

from typing import Any

from backend.models.responses import EvidenceItem
from .common import parse_organic_results


def parse(payload: dict[str, Any], *, query: str, engine: str = "google") -> list[EvidenceItem]:
    items = parse_organic_results(payload, engine=engine, source="Google Search")
    # Answer boxes / knowledge graph carry a direct statement worth keeping as evidence.
    box = payload.get("answer_box")
    if isinstance(box, dict) and (box.get("answer") or box.get("snippet") or box.get("result")):
        from .common import make_evidence
        text = str(box.get("answer") or box.get("snippet") or box.get("result"))
        items.insert(0, make_evidence(
            engine=engine, source=str(box.get("displayed_link") or box.get("title") or "Google answer box"),
            title=str(box.get("title") or text[:90]), url=str(box.get("link") or ""),
            snippet=text, relevance=0.95, retrieval_rank=1,
        ))
    return items
