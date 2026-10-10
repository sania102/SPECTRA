"""Composition root for the investigation pipeline."""
from __future__ import annotations

from backend.agent.investigator import Investigator
from backend.agent.router import InvestigationRouter
from backend.config.settings import get_settings
from backend.llm.client import LLMClient
from backend.llm.service import LLMService
from backend.models.requests import InvestigationRequest
from backend.models.responses import InvestigationResult
from backend.serpapi.client import SerpApiClient
from backend.serpapi.service import SerpApiService


def create_investigator() -> Investigator:
    settings = get_settings()
    client = SerpApiClient()
    service = SerpApiService(client)
    router = InvestigationRouter(service)
    llm = LLMService(LLMClient(settings.llm_api_key, settings.llm_model))
    return Investigator(router, llm)


def run_investigation(request: InvestigationRequest) -> InvestigationResult:
    return create_investigator().investigate(request)
