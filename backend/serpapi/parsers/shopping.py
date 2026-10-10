from __future__ import annotations

from typing import Any

from backend.models.responses import EvidenceItem
from .common import make_evidence
from .base import first_text


def parse(payload: dict[str, Any], *, query: str, engine: str = "google_shopping") -> list[EvidenceItem]:
    items = payload.get("shopping_results", []) or []
    evidence: list[EvidenceItem] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        title = first_text(item, "title") or f"Shopping result {index + 1}"
        url = first_text(item, "product_link", "link") or ""
        seller = first_text(item, "source", "seller")
        price = first_text(item, "price")
        snippet = " — ".join(part for part in (seller, price) if part)
        evidence.append(
            make_evidence(
                engine=engine,
                source=seller or "Google Shopping",
                title=title,
                url=url,
                snippet=snippet,
                entity=seller,
                claim=f"Listed for sale: {title}" + (f" at {price}" if price else ""),
                relevance=max(0.0, 1.0 - index * 0.06),
                retrieval_rank=index + 1,
                snapshot=True,
            )
        )
    return evidence
