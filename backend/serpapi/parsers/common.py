"""Shared parsing helpers for SerpApi result shapes."""

from __future__ import annotations

import hashlib
import html
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from backend.models.responses import EvidenceItem
from .base import clean_text, first_text

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
_UNIT_DAYS = {"second": 1 / 86400, "sec": 1 / 86400, "minute": 1 / 1440, "min": 1 / 1440, "hour": 1 / 24, "hr": 1 / 24,
              "day": 1, "week": 7, "wk": 7, "month": 30, "mo": 30, "year": 365, "yr": 365}


def evidence_id(engine: str, url: str, title: str) -> str:
    raw = f"{engine}|{url}|{title}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]


def _utc(year: int, month: int, day: int = 1, hour: int = 0, minute: int = 0) -> datetime | None:
    try:
        return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
    except ValueError:
        return None


def parse_datetime(value: Any) -> datetime | None:
    """Parse the many date shapes SerpApi engines return into aware UTC datetimes.

    Handled: ISO strings, Unix timestamps, "3 days ago", "Posted 5 days ago",
    "Yesterday", "Oct 8, 2026", "8 Oct 2026", "10/08/2026, 07:30 AM, +0000 UTC"
    (Google News), "Mar 2024", bare years (Scholar) and dates embedded in longer text.
    Unparseable values return None; a date is never fabricated.
    """
    if value is None or value == "":
        return None

    if isinstance(value, dict):
        for key in ("iso_date", "date", "published_at", "timestamp", "value", "start_date"):
            if value.get(key):
                return parse_datetime(value[key])
        return None

    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) or (isinstance(value, str) and re.fullmatch(r"\d{9,13}", value.strip())):
        try:
            number = float(value)
            if number > 10_000_000_000:
                number /= 1000.0
            if number < 100_000_000:  # not a plausible unix time
                return None
            return datetime.fromtimestamp(number, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    text = html.unescape(str(value)).strip()
    if not text:
        return None
    low = text.lower().strip()
    now = datetime.now(timezone.utc)

    if low in {"today", "just now", "now"}:
        return now
    if low == "yesterday":
        return now - timedelta(days=1)

    rel = re.search(r"(?:^|\b)(?:about\s+|posted\s+|updated\s+|streamed\s+|premiered\s+|published\s+)?"
                    r"(an?|\d+)\s*(second|sec|minute|min|hour|hr|day|week|wk|month|mo|year|yr)s?\.?\s+ago", low)
    if rel:
        amount = 1 if rel.group(1) in ("a", "an") else int(rel.group(1))
        return now - timedelta(days=amount * _UNIT_DAYS[rel.group(2)])
    short = re.fullmatch(r"(\d+)\s*([dhwmy])\s*ago", low)
    if short:
        mult = {"d": 1, "h": 1 / 24, "w": 7, "m": 30, "y": 365}[short.group(2)]
        return now - timedelta(days=int(short.group(1)) * mult)

    # Google News: "10/08/2026, 07:30 AM, +0000 UTC"  (MM/DD/YYYY)
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})(?:,?\s+(\d{1,2}):(\d{2})\s*(AM|PM)?)?", text, re.I)
    if m:
        month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if month > 12 and day <= 12:
            month, day = day, month
        hour = int(m.group(4) or 0)
        if m.group(6):
            hour = hour % 12 + (12 if m.group(6).upper() == "PM" else 0)
        parsed = _utc(year, month, day, hour, int(m.group(5) or 0))
        if parsed:
            return parsed

    # ISO 8601
    iso = re.match(r"(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2}))?", text)
    if iso:
        try:
            full = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return full.replace(tzinfo=timezone.utc) if full.tzinfo is None else full.astimezone(timezone.utc)
        except ValueError:
            parsed = _utc(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)),
                          int(iso.group(4) or 0), int(iso.group(5) or 0))
            if parsed:
                return parsed

    # "Oct 8, 2026" / "October 8 2026" / "Oct. 8, 2026"
    m = re.search(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+((?:19|20)\d{2})\b", text)
    if m and m.group(1)[:3].lower() in _MONTHS:
        parsed = _utc(int(m.group(3)), _MONTHS[m.group(1)[:3].lower()], int(m.group(2)))
        if parsed:
            return parsed

    # "8 Oct 2026"
    m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\.?,?\s+((?:19|20)\d{2})\b", text)
    if m and m.group(2)[:3].lower() in _MONTHS:
        parsed = _utc(int(m.group(3)), _MONTHS[m.group(2)[:3].lower()], int(m.group(1)))
        if parsed:
            return parsed

    # "Mar 2024"
    m = re.search(r"\b([A-Za-z]{3,9})\.?\s+((?:19|20)\d{2})\b", text)
    if m and m.group(1)[:3].lower() in _MONTHS:
        parsed = _utc(int(m.group(2)), _MONTHS[m.group(1)[:3].lower()], 1)
        if parsed:
            return parsed

    # "2026/10/08"
    m = re.search(r"\b((?:19|20)\d{2})/(\d{1,2})/(\d{1,2})\b", text)
    if m:
        parsed = _utc(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if parsed:
            return parsed

    # Bare year, either alone ("2023") or inside Scholar summaries ("A Smith - Nature, 2023 - nature.com")
    years = re.findall(r"\b((?:19|20)\d{2})\b", text)
    if years and (len(text) <= 4 or "-" in text or "," in text):
        year = int(years[-1] if len(text) > 4 else years[0])
        if 1900 <= year <= now.year + 1:
            return _utc(year, 7, 1)  # mid-year: least biased guess for year-only dates
    return None


def date_from_snippet(snippet: str | None) -> datetime | None:
    """Google often prefixes snippets with a date: 'Oct 3, 2026 — Silver prices rose…'."""
    if not snippet:
        return None
    head = snippet[:40]
    m = re.match(r"\s*((?:[A-Za-z]{3,9}\.? \d{1,2}, \d{4})|(?:\d{1,2} [A-Za-z]{3,9}\.? \d{4})|(?:\d+ (?:hour|day|week|month)s? ago))\s*[—\-–·:]", head)
    return parse_datetime(m.group(1)) if m else None


_QUALITY = {
    "google_scholar": 0.85, "google_patents": 0.80, "google_news": 0.70, "google_jobs": 0.65,
    "google_shopping": 0.60, "youtube": 0.55, "google_trends": 0.60, "google": 0.60,
}
_SOURCE_TYPE = {
    "google_scholar": "research", "google_patents": "patent", "google_news": "news", "google_jobs": "jobs",
    "google_shopping": "commercial", "youtube": "video", "google_trends": "attention", "google": "web",
}
SNAPSHOT_ENGINES = {"google_shopping", "google_jobs"}


def make_evidence(
    *,
    engine: str,
    source: str,
    title: str,
    url: str,
    snippet: str | None = None,
    published_at: Any = None,
    entity: str | None = None,
    claim: str | None = None,
    location: str | None = None,
    relevance: float = 0.0,
    retrieval_rank: int | None = None,
    snapshot: bool | None = None,
) -> EvidenceItem:
    title = html.unescape(clean_text(title) or "Untitled result")
    url = clean_text(url) or ""
    snippet = html.unescape(clean_text(snippet) or "") or None

    parsed = parse_datetime(published_at) or date_from_snippet(snippet)
    if snapshot is None:
        snapshot = engine in SNAPSHOT_ENGINES
    if parsed:
        date_kind = "published"
    elif snapshot:
        date_kind = "observed"
    else:
        date_kind = None

    source_domain = None
    if url:
        try:
            source_domain = (urlparse(url).netloc or "").replace("www.", "") or None
        except Exception:
            source_domain = None

    return EvidenceItem(
        id=evidence_id(engine, url, title),
        title=title,
        url=url or None,
        source=source,
        engine=engine,
        snippet=snippet,
        published_at=parsed,
        date_kind=date_kind,
        entity=clean_text(entity),
        claim=clean_text(claim),
        location=clean_text(location),
        relevance=max(0.0, min(1.0, float(relevance))),
        source_type=_SOURCE_TYPE.get(engine, "search"),
        source_domain=source_domain,
        source_quality=_QUALITY.get(engine, 0.5),
        retrieval_rank=retrieval_rank,
    )


def parse_organic_results(payload: dict[str, Any], *, engine: str, source: str) -> list[EvidenceItem]:
    results = payload.get("organic_results", []) or []
    evidence: list[EvidenceItem] = []
    for index, item in enumerate(results):
        if not isinstance(item, dict):
            continue
        title = first_text(item, "title") or f"Result {index + 1}"
        url = first_text(item, "link", "url") or ""
        snippet = first_text(item, "snippet")
        domain_label = first_text(item, "source", "displayed_link")
        date_value = item.get("date") or item.get("iso_date")
        if not date_value:
            rich = item.get("rich_snippet")
            if isinstance(rich, dict):
                ext = (rich.get("top") or {}).get("detected_extensions") or {}
                date_value = ext.get("date") or ext.get("posted_at")
        evidence.append(
            make_evidence(
                engine=engine,
                source=domain_label or source,
                title=title,
                url=url,
                snippet=snippet,
                published_at=date_value,
                relevance=max(0.0, 1.0 - index * 0.08),
                retrieval_rank=index + 1,
            )
        )
    return evidence
