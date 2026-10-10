"""Normalize heterogeneous search results into one clean evidence list."""
from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from backend.analysis.stance import detect_stance
from backend.analysis.text import jaccard, stem_set
from backend.models.responses import EvidenceItem

_TRACKING = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid", "ref", "ved", "usg", "oc"}


def canonical_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        p = urlparse(url)
        query = urlencode([(k, v) for k, v in parse_qsl(p.query) if k.lower() not in _TRACKING])
        host = p.netloc.lower().replace("www.", "")
        return urlunparse((p.scheme.lower(), host, p.path.rstrip("/"), "", query, ""))
    except Exception:
        return url


def dedupe(items: Iterable[EvidenceItem]) -> list[EvidenceItem]:
    """Drop repeated URLs and near-identical headlines (wire stories syndicated across outlets)."""
    seen_urls: set[tuple[str, str, str]] = set()
    kept: list[EvidenceItem] = []
    kept_titles: list[tuple[str, set[str], str]] = []
    for item in items:
        cu = canonical_url(item.url)
        scope = item.region or ""  # the same article seen from Global and from India is two observations
        if cu and (item.engine, cu, scope) in seen_urls and item.engine != "google_trends":
            continue
        tokens = stem_set(item.title)
        duplicate = False
        if item.engine in {"google_news", "google"} and len(tokens) >= 5:
            for engine, other, other_scope in kept_titles:
                if engine == item.engine and other_scope == scope and jaccard(tokens, other) >= 0.9:
                    duplicate = True
                    break
        if duplicate:
            continue
        if cu:
            seen_urls.add((item.engine, cu, scope))
        kept_titles.append((item.engine, tokens, scope))
        kept.append(item)
    return kept


def annotate(items: Iterable[EvidenceItem]) -> None:
    """Attach a direction stance and a traceable claim to each item that lacks them."""
    for item in items:
        if item.engine in {"google_trends"}:
            continue
        if not item.stance:
            item.stance = detect_stance(item.title, item.snippet)
        if not item.claim:
            text = (item.snippet or item.title or "").strip()
            item.claim = re.sub(r"\s+", " ", text)[:280] if text else None
