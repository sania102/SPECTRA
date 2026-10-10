"""Provider-neutral search task contracts."""
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class EvidenceSurface(str, Enum):
    WEB = "web"
    NEWS = "news"
    TRENDS = "trends"
    SCHOLAR = "scholar"
    JOBS = "jobs"
    SHOPPING = "shopping"
    PATENTS = "patents"
    VIDEO = "video"


class SearchTask(BaseModel):
    """A single search operation selected by the investigation planner."""
    id: str
    engine: str
    surface: EvidenceSurface
    query: str
    rationale: str
    params: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=50, ge=0, le=100)
    max_results: int = Field(default=10, ge=1, le=100)
    # Shorter / simpler queries tried automatically when this one errors or is empty.
    fallback_queries: list[str] = Field(default_factory=list)
    # Region label (e.g. "India") when the task is part of a geographic comparison.
    region: str | None = None
    gl: str | None = None


class InvestigationIntent(str, Enum):
    STATUS = "status"
    MARKET = "market"
    TECHNOLOGY = "technology"
    SCIENCE = "science"
    PUBLIC_SENTIMENT = "public_sentiment"
    COMMERCIAL_MATURITY = "commercial_maturity"
    COMPETITIVE = "competitive"
    RISK = "risk"
    FORECAST = "forecast"
    GENERAL = "general"
