"""Application-facing SerpApi orchestration service."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.models.responses import EvidenceItem, TrendSeries
from backend.models.search import SearchTask
from backend.serpapi.client import SerpApiClient
from backend.serpapi.engines import build_params
from backend.serpapi.parsers import PARSERS
from backend.serpapi.parsers.common import evidence_id
from backend.serpapi.parsers.trends import parse_series


@dataclass
class SearchOutcome:
    items: list[EvidenceItem] = field(default_factory=list)
    series: list[TrendSeries] = field(default_factory=list)
    raw_empty: bool = False


class SerpApiService:
    """Execute provider-neutral search tasks and return normalized evidence."""

    def __init__(self, client: SerpApiClient):
        self.client = client

    def search(self, *, engine: str, query: str, params: dict | None = None) -> list[EvidenceItem]:
        """Compatibility helper for direct service-level searches."""
        merged = build_params(engine, query=query, extra=params)
        raw = self.client.search(engine=engine, params=merged)
        return PARSERS[engine](raw, query=query, engine=engine)

    def run_query(self, task: SearchTask, query: str, window: str | None = None) -> SearchOutcome:
        params = build_params(
            task.engine, query=query, max_results=task.max_results, gl=task.gl,
            extra=task.params or None, time_window=window,
        )
        raw: dict[str, Any] = self.client.search(engine=task.engine, params=params)
        items = PARSERS[task.engine](raw, query=query, engine=task.engine)
        for item in items:
            if task.region:
                item.region = task.region
                # Same headline/URL searched in two countries are different observations.
                item.id = evidence_id(item.engine, item.url or "", f"{item.title}|{task.region}")
        series: list[TrendSeries] = []
        if task.engine == "google_trends":
            series = parse_series(raw, query=query, region=task.region, window=window or (task.params or {}).get("date"))
        return SearchOutcome(items=items, series=series, raw_empty=bool(raw.get("_spectra_empty")) or not items)

    def search_task(self, task: SearchTask) -> list[EvidenceItem]:
        return self.run_query(task, task.query).items
