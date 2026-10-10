"""Offline sample investigations for judges and first-time visitors (zero SerpApi credits).

These run the REAL SPECTRA pipeline (planner -> router -> parsers -> relevance -> signals ->
divergence -> blind spots -> direction/regional analysis) over canned SerpApi-shaped payloads, so
every panel in the UI is exercised by the same code that handles live data. The API marks the result
``metadata.demo_mode = true`` and the UI shows a "Sample data" banner: nothing here is live evidence.
"""
from __future__ import annotations

from backend.agent.investigator import Investigator
from backend.agent.router import InvestigationRouter
from backend.models.requests import InvestigationDepth, InvestigationRequest
from backend.models.responses import InvestigationResult
from backend.serpapi.service import SerpApiService

NOW = 1_760_000_000

HUMANOID_NEWS = [
    ("Humanoid robotics startups raise record funding as investors pile in", "TechCrunch", 1),
    ("Humanoid robots enter factory pilots at major automakers", "Reuters", 2),
    ("Humanoid robotics hype surges after viral demo video", "The Verge", 2),
    ("Humanoid robotics revenue slumps below forecasts as analysts warn", "Bloomberg", 3),
    ("Humanoid robot makers delay mass production targets", "Financial Times", 4),
    ("Humanoid robotics market forecast to expand sharply", "Forbes", 5),
    ("Humanoid robotics pilots rise, but few paying customers yet", "WSJ", 6),
    ("Humanoid robotics rollout stalls, still far from mainstream deployment", "MIT Tech Review", 8),
]
SILVER = {
    "": [("Silver surges to record high on safe-haven demand", "Reuters", 1), ("Silver climbs as dollar weakens, rally extends", "Bloomberg", 1),
         ("Silver prices rally on strong industrial demand", "Kitco", 2), ("Silver slips as profit-taking hits metals", "MarketWatch", 3),
         ("Silver falls on firmer dollar and rate fears", "CNBC", 3), ("Silver jumps after Fed signals cuts", "Mint", 4),
         ("Silver could hit $100 by 2030, analysts say", "Forbes", 5), ("Silver tumbles as correction deepens", "FXStreet", 6)],
    "in": [("Silver price in India rises, MCX futures climb", "Economic Times", 1), ("Silver rate today: prices surge on festive demand", "Business Standard", 1),
           ("Silver jumps in Indian markets as rupee weakens", "Moneycontrol", 2), ("Silver slips in India as import duty worries weigh", "Mint", 3),
           ("Silver price rally gains pace on MCX", "Hindustan Times", 3), ("Silver falls on MCX after sharp rise", "Zee Business", 5),
           ("Silver price in India: outlook stays bullish", "NDTV Profit", 6)],
}


def _news(rows, extra=None):
    return {"news_results": [{"title": t, "link": f"https://{s.lower().replace(' ', '')}.com/{abs(hash(t)) % 99999}",
                              "source": {"name": s}, "snippet": f"{t}.", "date": f"{d} days ago"} for t, s, d in rows]}


def _trend(window, base, drift):
    n, step = {"today 3-m": (90, 86400), "today 12-m": (52, 7 * 86400), "today 5-y": (260, 7 * 86400)}.get(window, (52, 7 * 86400))
    pts = [{"date": f"p{i}", "timestamp": str(NOW - (n - i) * step), "values": [{"extracted_value": max(2, int(base + drift * (i - n / 2) / n * 40 + (6 if i % 7 == 0 else 0)))}]} for i in range(n)]
    return {"interest_over_time": {"timeline_data": pts},
            "related_queries": {"rising": [{"query": "price today", "value": "+250%"}], "top": [{"query": "live rate", "value": 100}]}}


class _Humanoid:
    def search(self, *, engine, params):
        t = "humanoid robotics"
        if engine == "google_news":
            return _news(HUMANOID_NEWS)
        if engine == "google":
            return {"organic_results": [{"position": i + 1, "title": f"{t.title()}: market, players and outlook #{i + 1}", "link": f"https://web{i}.example.com/{i}",
                                         "snippet": f"{t.title()} overview with pilots, funding and production plans.", "source": f"Site {i}"} for i in range(10)]}
        if engine == "google_trends":
            return _trend(params.get("date", "today 12-m"), 40, 1.0)
        if engine == "google_scholar":
            return {"organic_results": [{"title": f"Dexterous manipulation for {t} {i}", "link": f"https://scholar.example.com/{i}", "snippet": f"Research on {t} control.",
                                         "publication_info": {"summary": f"A Researcher - Robotics Journal, {2024 + i % 3}"}} for i in range(12)]}
        if engine == "google_patents":
            return {"organic_results": [{"title": f"{t.title()} actuator system {i}", "patent_link": f"https://patents.example.com/{i}", "publication_number": f"US{i}A1",
                                         "assignee": "Acme Robotics", "publication_date": f"2026-0{i % 8 + 1}-10"} for i in range(12)]}
        if engine == "google_jobs":
            return {"jobs_results": [{"title": "Controls Engineer", "company_name": "Acme Robotics", "location": "Remote", "share_link": "https://jobs.example.com/1",
                                      "detected_extensions": {"posted_at": "3 days ago"}, "description": f"Work on {t}."}]}
        if engine == "youtube":
            return {"video_results": [{"title": f"{t.title()} demo goes viral #{i}", "link": f"https://youtube.com/watch?v={i}", "channel": {"name": "TechChannel"},
                                       "published_date": f"{i + 1} days ago", "views": 500000 // (i + 1)} for i in range(10)]}
        return {"shopping_results": []}


class _Silver:
    def search(self, *, engine, params):
        gl = params.get("gl") or params.get("geo", "").lower()
        if engine == "google_news":
            return _news(SILVER["in" if gl == "in" else ""])
        if engine == "google":
            return {"organic_results": [{"position": i + 1, "title": f"Silver price today{' in India' if gl == 'in' else ''}: live rate #{i + 1}", "link": f"https://silver{i}.example.com/{gl}",
                                         "snippet": ("Oct %d, 2026 — " % (i + 1)) + "Track the silver price with live charts.", "source": f"Site {i}"} for i in range(8)]}
        if engine == "google_trends":
            return _trend(params.get("date", "today 12-m"), 55, -0.6 if gl == "in" else 0.5)
        if engine == "google_shopping":
            return {"shopping_results": [{"title": f"Silver coin {g} g 999", "product_link": f"https://shop{i}.example.com/a", "source": f"BullionShop {i}", "price": f"₹{g * 105}"}
                                         for i, g in enumerate((10, 20, 50, 100))]}
        if engine == "google_scholar":
            return {"organic_results": [{"title": f"Industrial demand and silver price dynamics {i}", "link": f"https://s.example.com/{i}", "snippet": "Silver demand and prices study.",
                                         "publication_info": {"summary": "J Econ, 2025"}} for i in range(6)]}
        if engine == "youtube":
            return {"video_results": [{"title": f"Silver price prediction {i}", "link": f"https://youtube.com/watch?v=s{i}", "channel": {"name": f"Chan{i}"}, "published_date": "2 days ago"} for i in range(5)]}
        return {}


SCENARIOS = {
    "humanoid": (_Humanoid, "Is humanoid robotics actually commercially mature?", InvestigationDepth.DEEP),
    "silver": (_Silver, "If I buy silver 1 gm today, will the price go up by next month?", InvestigationDepth.STANDARD),
}


def build_demo_result(scenario: str = "humanoid") -> InvestigationResult:
    client_cls, question, depth = SCENARIOS.get(scenario, SCENARIOS["humanoid"])
    result = Investigator(InvestigationRouter(SerpApiService(client_cls())), None).investigate(InvestigationRequest(question=question, depth=depth))
    result.investigation_id = f"demo_{scenario}"
    result.metadata.update({"demo_mode": True, "demo_scenario": scenario,
                            "demo_note": "Sample data: the real SPECTRA pipeline run over canned SerpApi-shaped responses. No live searches were used."})
    return result
