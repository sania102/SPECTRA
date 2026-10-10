"""End-to-end pipeline tests using a fake SerpApi client (no network, no API keys).

Run with:  python -m pytest tests/test_pipeline.py -q      (or)      python tests/test_pipeline.py
The payloads mirror real SerpApi response shapes, including the failure modes seen in
production: Google Trends returning nothing for a long question, Google Shopping
timing out, unrelated Tesla/computer-memory articles, and Google News date strings.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.agent.investigator import Investigator
from backend.agent.planner import apply_llm_queries, build_plan
from backend.agent.router import InvestigationRouter
from backend.llm.models import EvidenceClaimExtraction
from backend.llm.service import ClaimExtractionOutcome, LLMService
from backend.models.requests import InvestigationDepth, InvestigationRequest
from backend.serpapi.client import SerpApiRequestError
from backend.serpapi.engines import build_params
from backend.serpapi.service import SerpApiService

W = ["warehouse", "factory", "logistics", "hospital", "retail", "automotive", "elder-care", "kitchen"]
SILVER_Q = "if I buy silver 1 gm today will the price go up by next month"


def news(title, src, date, snippet=""):
    return {"title": title, "link": f"https://{src.lower().replace(' ', '')}.com/{abs(hash(title)) % 10**6}",
            "source": {"name": src}, "date": date, "snippet": snippet}


class FakeSerpApi:
    """Behaves like SerpApiClient.search, enforcing engine parameter rules."""

    def __init__(self, shopping_times_out=True):
        self.calls: list[tuple[str, dict]] = []
        self.shopping_times_out = shopping_times_out

    def search(self, *, engine, params):
        self.calls.append((engine, dict(params)))
        if engine == "youtube":
            assert "search_query" in params and "q" not in params, "YouTube needs search_query"
        else:
            assert "q" in params, f"{engine} needs q"
        if engine == "google_trends":
            assert "num" not in params, "Trends must not receive num"
            if len(params["q"].split()) > 4:
                return {"_spectra_empty": True, "error": "Google hasn't returned any results for this query."}
            vals = [30, 32, 31, 35, 38, 40, 44, 52, 60, 66, 70, 74]
            return {"interest_over_time": {"timeline_data": [
                {"date": f"Week {i}", "timestamp": str(1_750_000_000 + i * 604800), "values": [{"query": params["q"], "extracted_value": v}]}
                for i, v in enumerate(vals)]}}
        if engine == "google_shopping":
            if self.shopping_times_out and params["q"] != "silver":
                raise SerpApiRequestError("SerpApi request for 'google_shopping' timed out after 50s.", "timeout", 3)
            return {"shopping_results": [
                {"title": "Silver Coin 10 g 999", "product_link": "https://shop.example/a", "source": "BullionShop", "price": "₹1,450"},
                {"title": "Silver Bar 100 g", "product_link": "https://shop.example/b", "source": "MetalMart", "price": "₹13,900"},
                {"title": "Silver Chain 925", "product_link": "https://shop.example/c", "source": "Jewels", "price": "₹5,600"}]}
        if engine == "google_news":
            return {"news_results": [
                news("Silver prices surge to record high as demand jumps", "Reuters", "10/08/2026, 07:30 AM, +0000 UTC", "Silver rallied strongly."),
                news("Silver climbs again on weaker dollar", "Bloomberg", "10/07/2026, 09:00 AM, +0000 UTC"),
                news("Silver rally gains momentum, analysts bullish", "Mint", "10/06/2026, 10:00 AM, +0000 UTC"),
                news("Silver slumps as profit-taking hits metals", "Economic Times", "10/05/2026, 10:00 AM, +0000 UTC"),
                news("Silver tumbles; correction fears grow", "Business Standard", "10/04/2026, 10:00 AM, +0000 UTC"),
                news("Tesla unveils new model at event", "Verge", "10/08/2026, 07:30 AM, +0000 UTC"),
                news("Computer memory prices rise sharply", "Tom's Hardware", "10/08/2026, 07:30 AM, +0000 UTC")]}
        if engine == "google":
            return {"organic_results": [
                {"title": "Silver price today in India", "link": "https://goodreturns.in/silver", "snippet": "Oct 8, 2026 — Silver price rises to ₹95,000 per kg."},
                {"title": "Silver forecast 2026: analysts see higher prices", "link": "https://forecast.example/silver", "snippet": "Experts say silver could climb."},
                {"title": "Best pizza in Mumbai", "link": "https://pizza.example", "snippet": "Cheesy."}]}
        return {}


def build(fake=None, llm=None):
    fake = fake or FakeSerpApi()
    router = InvestigationRouter(SerpApiService(fake))
    return Investigator(router, llm), fake


def test_topic_and_short_queries():
    plan = build_plan(SILVER_Q, InvestigationDepth.STANDARD)
    assert plan.topic == "silver price", plan.topic
    assert plan.anchor_terms == ["silver"]
    assert plan.is_forecast
    for task in plan.search_tasks:
        assert len(task.query.split()) <= 4, (task.engine, task.query)
        assert SILVER_Q not in task.query
    trends = next(t for t in plan.search_tasks if t.engine == "google_trends")
    assert trends.query == "silver price"
    assert any(t.engine == "google_shopping" for t in plan.search_tasks)


def test_engine_params():
    assert "search_query" in build_params("youtube", query="x") and "q" not in build_params("youtube", query="x")
    assert "num" not in build_params("google_trends", query="x", max_results=20)
    assert "num" not in build_params("google_news", query="x", max_results=20)
    assert build_params("google_patents", query="x", max_results=3)["num"] == 10
    assert build_params("google_scholar", query="x", max_results=50)["num"] == 20
    assert build_params("google_trends", query="x", gl="in")["geo"] == "IN"


def test_full_silver_investigation():
    inv, fake = build()
    result = inv.investigate(InvestigationRequest(question=SILVER_Q, depth=InvestigationDepth.STANDARD))

    # 1. Trends works with a short topic query and is analysed as a time series
    trends = [s for s in result.signals if s.name == "Public Attention"]
    assert trends and trends[0].trend == "rising"
    assert result.trend_series and result.trend_series[0].direction == "rising"

    # 2. Shopping timeout is recovered through the simpler fallback query
    shop = [s for s in result.surface_status if s.engine == "google_shopping"][0]
    assert shop.status == "completed" and shop.attempts >= 2, shop

    # 3. Off-topic results are removed
    titles = " ".join(e.title.lower() for e in result.evidence)
    assert "tesla" not in titles and "memory" not in titles and "pizza" not in titles
    assert result.data_quality.dropped_irrelevant >= 3

    # 4. Dates are parsed (Google News format) and coverage is reported honestly
    news_items = [e for e in result.evidence if e.engine == "google_news"]
    assert news_items and all(e.published_at is not None for e in news_items)
    assert result.temporal_context.temporal_coverage >= 0.8, result.temporal_context

    # 5. Sources disagree on direction -> a real disagreement, claim groups and a blind spot
    assert result.disagreements, "expected an up-vs-down disagreement"
    assert result.claim_groups, "expected non-empty claim groups"
    assert any(b.kind == "disagreement" for b in result.blind_spots)

    # 6. Forecast honesty
    assert result.verdict and any("cannot predict" in c.lower() for c in result.verdict.caveats)
    assert result.verdict.lean in {"upward", "downward", "mixed"}
    assert all(0.0 <= s.strength <= 1.0 for s in result.signals)


def test_unrecoverable_failure_becomes_coverage_blind_spot():
    inv, _ = build(FakeSerpApi(shopping_times_out=True))
    # make even the fallback fail by monkeypatching the fake
    original = FakeSerpApi.search

    def always_fail(self, *, engine, params):
        if engine == "google_shopping":
            self.calls.append((engine, dict(params)))
            raise SerpApiRequestError("timed out", "timeout", 3)
        return original(self, engine=engine, params=params)

    FakeSerpApi.search = always_fail
    try:
        inv, _ = build()
        result = inv.investigate(InvestigationRequest(question=SILVER_Q))
    finally:
        FakeSerpApi.search = original
    shop = [s for s in result.surface_status if s.engine == "google_shopping"][0]
    assert shop.status == "failed" and shop.error_kind == "timeout"
    assert any(b.kind == "coverage" and "commercial" in b.title.lower() for b in result.blind_spots)
    assert any("unobserved" in n for n in result.data_quality.notes)
    assert not any(s.name == "Commercial Availability" for s in result.signals), "missing must not be scored as low"


def test_divergence_and_blind_spot_for_maturity_question():
    class MaturityFake(FakeSerpApi):
        def search(self, *, engine, params):
            self.calls.append((engine, dict(params)))
            if engine == "google_news":
                return {"news_results": [news(f"Humanoid robotics {W[i]} draws investors, analysts say", f"Outlet{i}", f"10/0{(i % 7) + 1}/2026, 08:00 AM, +0000 UTC") for i in range(8)]}
            if engine == "google":
                return {"organic_results": [{"title": f"Humanoid robotics {W[i]} market overview", "link": f"https://w{i}.example", "snippet": "Humanoid robotics is booming."} for i in range(8)]}
            if engine == "google_scholar":
                return {"organic_results": [{"title": f"Humanoid robotics {W[i]} manipulation study", "link": f"https://s{i}.example", "snippet": "humanoid robotics research", "publication_info": {"summary": "A Smith - Nature, 2025 - nature.com"}} for i in range(8)]}
            if engine == "google_patents":
                return {"organic_results": [{"title": f"Humanoid robotics {W[i]} actuator", "patent_link": f"https://p{i}.example", "snippet": "humanoid robotics", "publication_date": "2025-05-01"} for i in range(8)]}
            if engine == "google_jobs":
                return {"jobs_results": [{"title": "Humanoid robotics engineer", "company_name": "RoboCo", "location": "CA", "description": "humanoid robotics", "share_link": "https://j.example", "detected_extensions": {"posted_at": "3 days ago"}}]}
            if engine == "google_shopping":
                return {"shopping_results": [{"title": "Humanoid robotics toy kit", "product_link": "https://shop.example/t", "source": "ToyShop", "price": "$99"}]}
            if engine == "google_trends":
                return {"interest_over_time": {"timeline_data": [{"date": f"W{i}", "timestamp": str(1_750_000_000 + i * 604800), "values": [{"extracted_value": v}]} for i, v in enumerate([20, 22, 25, 30, 41, 55, 70, 85])]}}
            return {}

    inv, _ = build(MaturityFake())
    result = inv.investigate(InvestigationRequest(question="Is humanoid robotics actually commercially mature?", depth=InvestigationDepth.DEEP))
    names = {s.name: s for s in result.signals}
    assert names["Commercial Availability"].level == "low", names["Commercial Availability"]
    assert names["News Momentum"].level in {"high", "medium"}
    assert result.divergences, "expected attention-vs-commercial divergence"
    assert any(b.kind == "divergence" and "commercial" in b.title.lower() for b in result.blind_spots), [b.title for b in result.blind_spots]
    top = result.blind_spots[0]
    assert top.what_could_make_this_wrong and top.evidence_ids


def test_geographic_comparison_plan():
    plan = build_plan("How is AI regulation evolving in India vs the EU vs Japan?", InvestigationDepth.STANDARD)
    regional = [t for t in plan.search_tasks if t.region]
    assert {t.region for t in regional} == {"India", "European Union", "Japan"}
    assert all(t.gl for t in regional)


def test_llm_output_is_sanitised_and_overrides_stance():
    plan = build_plan(SILVER_Q)
    changed = apply_llm_queries(plan, {"trends": "silver price today", "news": "x" * 200, "web": "ignore previous; DROP TABLE;"},
                                refined_topic="silver price", anchors=["silver", "<script>"])
    assert changed and plan.anchor_terms == ["silver"]
    trends = next(t for t in plan.search_tasks if t.surface.value == "trends")
    assert trends.query == "silver price"  # keep Trends topic stable across depth modes
    web = next(t for t in plan.search_tasks if t.surface.value == "web")
    assert "DROP" not in web.query
    assert "next month" in web.query

    class FakeLLM(LLMService):
        def __init__(self):
            self.client = type("C", (), {"enabled": True, "active_model": "fake"})()

        def enrich_plan(self, plan):
            return None

        def extract_claims(self, evidence):
            out = ClaimExtractionOutcome(chunks_attempted=1)
            for e in evidence:
                if e.engine == "google_news":
                    out.claims.append(EvidenceClaimExtraction(evidence_id=e.id, claim="Silver is rising.", stance="up", claim_type="price_movement"))
            return out

        def explain_blind_spot(self, bs, text):
            return None

    inv, _ = build(llm=FakeLLM())
    result = inv.investigate(InvestigationRequest(question=SILVER_Q))
    assert result.metadata["claims_added_by_llm"] > 0
    assert result.metadata["claim_extraction_status"] in {"completed_with_claims", "partial"}


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                import traceback
                print(f"FAIL  {name}: {exc!r}")
                traceback.print_exc()
    sys.exit(1 if failed else 0)
