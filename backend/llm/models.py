"""Structured contracts for LLM enrichment (validated after the call, not sent as a strict schema)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class PlanEnrichment(BaseModel):
    refined_topic: str = Field(default="", max_length=300)
    anchor_terms: list[str] = Field(default_factory=list)
    geography: str | None = None
    is_forecast: bool = False
    queries: dict[str, str] = Field(default_factory=dict)


class EvidenceClaimExtraction(BaseModel):
    evidence_id: str
    claim: str = Field(default="", max_length=600)
    entity: str | None = None
    claim_type: str = "general"
    stance: str = "neutral"  # up | down | mixed | neutral


class EvidenceClaimBatch(BaseModel):
    claims: list[EvidenceClaimExtraction] = Field(default_factory=list)


class BlindSpotExplanation(BaseModel):
    title: str = Field(default="", max_length=300)
    description: str = Field(default="", max_length=1500)
    counter_evidence: list[str] = Field(default_factory=list)
    what_could_make_this_wrong: list[str] = Field(default_factory=list)


EXAMPLES = {
    "PlanEnrichment": '{"refined_topic": "silver price", "anchor_terms": ["silver"], "geography": null, "is_forecast": true, '
                      '"queries": {"web": "silver price outlook", "news": "silver price", "trends": "silver price", '
                      '"scholar": "silver market", "jobs": "silver mining", "shopping": "silver coin", '
                      '"patents": "silver", "video": "silver price forecast"}}',
    "EvidenceClaimBatch": '{"claims": [{"evidence_id": "abc123", "claim": "Silver rose 2% after a weaker dollar.", '
                          '"entity": "Silver", "claim_type": "price_movement", "stance": "up"}]}',
    "BlindSpotExplanation": '{"title": "...", "description": "...", "counter_evidence": ["..."], "what_could_make_this_wrong": ["..."]}',
}
