"""Supported SerpApi engines and how each one wants to be called.

Every engine has different parameter names and limits. Sending the wrong ones
(for example ``q`` to YouTube, or ``num`` to Google Trends) makes SerpApi reject
or silently ignore the request, so the rules live in one place.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EngineSpec:
    name: str
    label: str
    query_param: str
    category: str
    enabled_by_default: bool = False
    num_param: str | None = None      # None => engine does not accept a result-count parameter
    num_min: int = 1
    num_max: int = 100
    supports_gl: bool = True          # country parameter name is always "gl" except Trends (geo)
    timeout: float | None = None      # per-engine override (seconds)
    extra: tuple[tuple[str, Any], ...] = ()


ENGINE_SPECS: dict[str, EngineSpec] = {
    "google": EngineSpec("google", "Google Search", "q", "web", True, num_param="num", num_min=1, num_max=100),
    "google_news": EngineSpec("google_news", "Google News", "q", "news", True),
    "google_trends": EngineSpec("google_trends", "Google Trends", "q", "trends", True, supports_gl=False,
                                extra=(("data_type", "TIMESERIES"),), timeout=40.0),
    "google_scholar": EngineSpec("google_scholar", "Google Scholar", "q", "research", num_param="num", num_min=1, num_max=20),
    "google_jobs": EngineSpec("google_jobs", "Google Jobs", "q", "jobs", timeout=40.0),
    "google_shopping": EngineSpec("google_shopping", "Google Shopping", "q", "commercial", timeout=50.0),
    "google_patents": EngineSpec("google_patents", "Google Patents", "q", "patents", num_param="num", num_min=10, num_max=100),
    "youtube": EngineSpec("youtube", "YouTube", "search_query", "video", supports_gl=True),
}

CORE_ENGINES = tuple(name for name, spec in ENGINE_SPECS.items() if spec.enabled_by_default)
OPTIONAL_ENGINES = tuple(name for name, spec in ENGINE_SPECS.items() if not spec.enabled_by_default)
ALL_ENGINES = tuple(ENGINE_SPECS)


def get_engine_spec(engine: str) -> EngineSpec:
    try:
        return ENGINE_SPECS[engine]
    except KeyError as exc:
        raise ValueError(f"Unsupported SerpApi engine: {engine}") from exc


def build_params(engine: str, *, query: str, max_results: int = 10, gl: str | None = None,
                 extra: dict[str, Any] | None = None, time_window: str | None = None) -> dict[str, Any]:
    """Build a request parameter dict that is valid for the given engine."""
    spec = get_engine_spec(engine)
    params: dict[str, Any] = {spec.query_param: query}
    params.update(dict(spec.extra))

    if spec.num_param:
        params[spec.num_param] = max(spec.num_min, min(spec.num_max, int(max_results)))

    if gl:
        if engine == "google_trends":
            params["geo"] = gl.upper()
        elif spec.supports_gl:
            params["gl"] = gl.lower()
            if engine in {"google", "google_news", "google_shopping", "google_jobs"}:
                params.setdefault("hl", "en")

    if engine == "google_trends":
        params["date"] = time_window or "today 12-m"
    elif engine == "google" and time_window == "recent":
        params["tbs"] = "qdr:y"

    if extra:
        params.update(extra)
    return params
