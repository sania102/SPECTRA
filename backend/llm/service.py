"""LLM-powered enrichment with safe deterministic fallbacks."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable

from backend.llm.client import LLMClient, LLMError
from backend.llm.models import BlindSpotExplanation, EvidenceClaimBatch, EvidenceClaimExtraction, PlanEnrichment
from backend.models.responses import BlindSpot, EvidenceItem, InvestigationPlan

CHUNK = 18
MAX_CHUNKS = 3


@dataclass
class ClaimExtractionOutcome:
    claims: list[EvidenceClaimExtraction] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    chunks_attempted: int = 0
    chunks_failed: int = 0


@dataclass
class LLMService:
    client: LLMClient

    @property
    def enabled(self) -> bool:
        return self.client.enabled

    def enrich_plan(self, plan: InvestigationPlan) -> PlanEnrichment | None:
        if not self.enabled:
            return None
        instructions = (
            "You help plan web-search queries for an investigation tool. Given a user question, return: "
            "refined_topic (2-4 words naming the SUBJECT, e.g. 'silver price'), anchor_terms (1-3 lowercase words that any "
            "relevant result MUST mention, e.g. ['silver']), geography (country name or null), is_forecast (true if the user "
            "asks about future movement), and queries: ONE short search query (max 4 words for trends, max 7 otherwise) for each "
            "of web, news, trends, scholar, jobs, shopping, patents, video. Never paste the whole question. Never invent facts."
        )
        prompt = f"Question: {plan.question}\nSurfaces to be searched: {', '.join(plan.evidence_requirements)}"
        return self.client.structured(instructions=instructions, input_text=prompt, schema=PlanEnrichment, name="plan")

    def extract_claims(self, evidence: Iterable[EvidenceItem]) -> ClaimExtractionOutcome:
        outcome = ClaimExtractionOutcome()
        if not self.enabled:
            return outcome
        compact = [
            {"evidence_id": i.id, "title": i.title, "snippet": (i.snippet or "")[:240], "source": i.source}
            for i in evidence if (i.title or i.snippet) and i.engine != "google_trends"
        ]
        instructions = (
            "For each item extract ONE factual claim directly supported by its title/snippet — never invent anything. "
            "Return claims with: evidence_id (copied exactly), claim (<=25 words), entity (main company/asset/place or null), "
            "claim_type (price_movement, adoption, research, hiring, product, regulation, forecast, other), and stance: "
            "'up' if the item says the subject is rising/strengthening/accelerating, 'down' if falling/weakening/delayed, "
            "'mixed' if both, otherwise 'neutral'."
        )
        for start in range(0, min(len(compact), CHUNK * MAX_CHUNKS), CHUNK):
            chunk = compact[start:start + CHUNK]
            outcome.chunks_attempted += 1
            try:
                batch = self.client.structured(instructions=instructions,
                                               input_text=json.dumps(chunk, ensure_ascii=False),
                                               schema=EvidenceClaimBatch, name="claims")
                outcome.claims.extend(batch.claims)
            except (LLMError, Exception) as exc:  # keep going with other chunks
                outcome.chunks_failed += 1
                outcome.errors.append(str(exc)[:400])
                if isinstance(exc, LLMError) and exc.status in (401, 403, 404):
                    break
        return outcome

    def explain_blind_spot(self, blind_spot: BlindSpot, signals_text: str) -> BlindSpotExplanation | None:
        if not self.enabled:
            return None
        instructions = (
            "Rewrite a SPECTRA potential blind spot clearly for a non-expert in 2-3 sentences. Be conservative: separate "
            "observed evidence from inference, never raise confidence, never claim certainty, and list plausible alternative "
            "explanations (counter_evidence) and what evidence could falsify the finding (what_could_make_this_wrong)."
        )
        prompt = f"Blind spot: {blind_spot.model_dump_json()}\nSignals: {signals_text}"
        return self.client.structured(instructions=instructions, input_text=prompt, schema=BlindSpotExplanation, name="explain")
