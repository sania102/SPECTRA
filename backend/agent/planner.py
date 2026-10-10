"""Investigation planner: turns a natural-language question into evidence tasks.

The planner is deterministic and authoritative for *which* surfaces are searched.
An optional LLM may only refine wording (a cleaner topic, shorter per-surface queries);
its output is sanitised before use. Every surface gets its own short query — pasting the
whole question into Google Trends is exactly what used to make it return nothing.
"""
from __future__ import annotations

import re
from uuid import uuid4

from backend.analysis.direction import question_horizon
from backend.analysis.topic import QuestionProfile, build_profile
from backend.models.requests import InvestigationDepth
from backend.models.responses import InvestigationPlan
from backend.models.search import EvidenceSurface, InvestigationIntent, SearchTask

SURFACE_ENGINE = {
    EvidenceSurface.WEB: "google",
    EvidenceSurface.NEWS: "google_news",
    EvidenceSurface.TRENDS: "google_trends",
    EvidenceSurface.SCHOLAR: "google_scholar",
    EvidenceSurface.JOBS: "google_jobs",
    EvidenceSurface.SHOPPING: "google_shopping",
    EvidenceSurface.PATENTS: "google_patents",
    EvidenceSurface.VIDEO: "youtube",
}
_SURFACE_ENGINE = SURFACE_ENGINE  # backwards-compatible alias

# Surfaces that are meaningful per-country.
REGIONAL_SURFACES = {EvidenceSurface.WEB, EvidenceSurface.NEWS, EvidenceSurface.TRENDS, EvidenceSurface.SHOPPING,
                     EvidenceSurface.JOBS, EvidenceSurface.VIDEO}


def _intent(question: str, profile: QuestionProfile) -> InvestigationIntent:
    q = question.lower()
    if profile.is_forecast and profile.is_price_question:
        return InvestigationIntent.FORECAST
    if any(x in q for x in ("patent", "innovation", "research", "scientific", "study", "clinical")):
        return InvestigationIntent.SCIENCE
    if any(x in q for x in ("commercially", "commercial maturity", "mature", "revenue", "market size")):
        return InvestigationIntent.COMMERCIAL_MATURITY
    if any(x in q for x in ("jobs", "hiring", "employment", "workforce", "job skill", "career")):
        return InvestigationIntent.MARKET
    if any(x in q for x in ("competitor", "competitive", "companies", "leaders")):
        return InvestigationIntent.COMPETITIVE
    if any(x in q for x in ("risk", "threat", "danger", "downside", "failure")):
        return InvestigationIntent.RISK
    if any(x in q for x in ("sentiment", "opinion", "popular", "public reaction", "people think")):
        return InvestigationIntent.PUBLIC_SENTIMENT
    if profile.is_price_question or "market" in q or "adoption" in q:
        return InvestigationIntent.MARKET
    if any(re.search(rf"\b{x}\b", q) for x in ("technology", "technological", "ai", "robot", "robots", "robotics", "software", "hardware", "ev", "coding")):
        return InvestigationIntent.TECHNOLOGY
    if any(x in q for x in ("now", "today", "current", "latest", "recent", "this year")):
        return InvestigationIntent.STATUS
    return InvestigationIntent.GENERAL


def _time_sensitivity(question: str) -> str:
    q = question.lower()
    if any(x in q for x in ("today", "now", "latest", "current", "recent", "this week", "this month", "next month", "next week")):
        return "high"
    if any(x in q for x in ("2026", "2027", "this year", "last year", "next year", "accelerat")):
        return "medium"
    return "low"


def _needs(question: str, intent: InvestigationIntent, profile: QuestionProfile) -> list[EvidenceSurface]:
    """Ordered by importance, so shallower depths keep the most informative surfaces."""
    S = EvidenceSurface
    q = question.lower()
    order: list[EvidenceSurface] = []

    if intent == InvestigationIntent.FORECAST or (profile.is_price_question and profile.is_forecast):
        # Price forecasts need multiple evidence families, not just more headlines.
        order = [S.NEWS, S.TRENDS, S.WEB, S.SHOPPING, S.VIDEO]
        if profile.is_price_question and profile.is_forecast:
            order.append(S.SCHOLAR)  # deeper macro/commodity research cross-check
    elif intent == InvestigationIntent.COMMERCIAL_MATURITY:
        order = [S.WEB, S.NEWS, S.SHOPPING, S.JOBS, S.SCHOLAR, S.PATENTS, S.TRENDS, S.VIDEO]
    elif intent == InvestigationIntent.TECHNOLOGY:
        order = [S.NEWS, S.TRENDS, S.JOBS, S.SCHOLAR, S.WEB, S.PATENTS, S.SHOPPING, S.VIDEO]
    elif intent == InvestigationIntent.SCIENCE:
        order = [S.SCHOLAR, S.PATENTS, S.NEWS, S.WEB, S.TRENDS, S.JOBS]
    elif intent == InvestigationIntent.MARKET:
        order = [S.NEWS, S.TRENDS, S.WEB, S.SHOPPING, S.JOBS, S.VIDEO]
    elif intent == InvestigationIntent.COMPETITIVE:
        order = [S.NEWS, S.WEB, S.JOBS, S.TRENDS, S.PATENTS, S.SHOPPING]
    elif intent == InvestigationIntent.PUBLIC_SENTIMENT:
        order = [S.TRENDS, S.NEWS, S.VIDEO, S.WEB]
    elif intent == InvestigationIntent.RISK:
        order = [S.NEWS, S.WEB, S.SCHOLAR, S.TRENDS]
    else:
        order = [S.WEB, S.NEWS, S.TRENDS, S.SCHOLAR, S.VIDEO]

    if any(x in q for x in ("job", "hiring", "skill", "career", "developer")) and S.JOBS not in order:
        order.append(S.JOBS)
    if profile.is_price_question and S.SHOPPING not in order:
        order.append(S.SHOPPING)
    if any(x in q for x in ("video", "youtube", "demonstration", "demo")) and S.VIDEO not in order:
        order.append(S.VIDEO)
    if S.WEB not in order:
        order.insert(1, S.WEB)
    return list(dict.fromkeys(order))


def _rationale(surface: EvidenceSurface, profile: QuestionProfile) -> str:
    base = {
        EvidenceSurface.WEB: "Establish the broad web baseline: what the open web says.",
        EvidenceSurface.NEWS: "Measure media attention and the direction of recent coverage.",
        EvidenceSurface.TRENDS: "Measure real public search interest over time (not just what media writes).",
        EvidenceSurface.SCHOLAR: "Check research depth: is there serious scientific work behind the topic?",
        EvidenceSurface.JOBS: "Check hiring demand — a real-world adoption signal.",
        EvidenceSurface.SHOPPING: "Check whether the thing is actually for sale — a commercial reality check.",
        EvidenceSurface.PATENTS: "Check invention and IP activity — an innovation signal.",
        EvidenceSurface.VIDEO: "Check public demonstrations and visible real-world activity.",
    }[surface]
    if profile.is_forecast and surface == EvidenceSurface.NEWS:
        base = "Measure the direction of recent coverage (up vs down) — the closest observable proxy to market sentiment."
    return base


def _queries(surface: EvidenceSurface, profile: QuestionProfile) -> tuple[str, list[str]]:
    """Short, surface-appropriate query plus progressively simpler fallbacks."""
    anchors = profile.anchors or profile.key_terms or [profile.topic]
    subject = " ".join(anchors[:3])
    first = anchors[0]
    topic = profile.topic or subject

    if surface == EvidenceSurface.TRENDS:
        primary = topic if len(topic.split()) <= 3 else subject
        fallbacks = [subject, first]
    elif surface == EvidenceSurface.JOBS:
        primary = subject
        fallbacks = [first]
    elif surface == EvidenceSurface.PATENTS:
        primary = subject
        fallbacks = [first]
    elif surface == EvidenceSurface.SCHOLAR:
        primary = topic
        fallbacks = [subject]
    elif surface == EvidenceSurface.SHOPPING:
        primary = topic if profile.is_price_question else subject
        fallbacks = [subject, first]
    elif surface == EvidenceSurface.NEWS:
        primary = topic
        fallbacks = [subject, first]
    else:
        primary = f"{topic} outlook" if (profile.is_forecast and profile.is_price_question and surface == EvidenceSurface.WEB) else topic
        fallbacks = [topic, subject]
    fallbacks = [f for f in dict.fromkeys(fallbacks) if f and f != primary]
    return primary, fallbacks


def _trend_window(depth: InvestigationDepth) -> str:
    return {InvestigationDepth.QUICK: "today 3-m", InvestigationDepth.STANDARD: "today 12-m", InvestigationDepth.DEEP: "today 5-y"}[depth]


def describe_mode(depth: InvestigationDepth, regional: bool, per_surface: int, surface_limit: int) -> dict:
    """What each mode is *designed* to do; the audit later shows what was actually executed."""
    base = {
        InvestigationDepth.QUICK: dict(label="Quick", goal="Fast first read", trend_window="past 3 months", scholar_check=False,
                                       regional_comparison=False, summary="Up to 3 surfaces, 6 results each, 3-month trend. Fastest and cheapest."),
        InvestigationDepth.STANDARD: dict(label="Standard", goal="Corroboration", trend_window="past 12 months", scholar_check=False,
                                          regional_comparison=True, summary="Up to 5 surfaces, 10 results each, 12-month trend, Global-vs-India regional cross-check: checks whether independent sources and regions agree."),
        InvestigationDepth.DEEP: dict(label="Deep", goal="Deeper research", trend_window="past 5 years", scholar_check=True,
                                      regional_comparison=True, summary="Up to 8 surfaces, 20 results each, 5-year trend context, research cross-check (Scholar) and regional comparison."),
    }[depth]
    return {**base, "surface_limit": surface_limit, "results_per_surface": per_surface, "regional_applied": bool(regional)}


def _region_lookup() -> dict[str, tuple[str, str]]:
    from backend.analysis.topic import REGIONS
    table = {"global": ("Global", "")}
    for name, gl in REGIONS.values():
        table[name.lower()] = (name, gl)
    return table


def build_plan(question: str, depth: InvestigationDepth = InvestigationDepth.STANDARD,
               regions_override: list[str] | None = None) -> InvestigationPlan:
    profile = build_profile(question)
    intent = _intent(question, profile)
    surfaces = _needs(question, intent, profile)

    configured_surface_limit = {InvestigationDepth.QUICK: 3, InvestigationDepth.STANDARD: 5, InvestigationDepth.DEEP: 8}[depth]
    surfaces = surfaces[:configured_surface_limit]
    per_surface = {InvestigationDepth.QUICK: 6, InvestigationDepth.STANDARD: 10, InvestigationDepth.DEEP: 20}[depth]

    regions = profile.regions[:4]
    comparison = profile.comparison and len(regions) >= 2
    single = regions[0] if (len(regions) == 1) else None

    # Regions chosen explicitly in the UI always win over detection.
    user_selected = False
    if regions_override:
        lookup = _region_lookup()
        picked = list(dict.fromkeys(lookup[r.strip().lower()] for r in regions_override if r.strip().lower() in lookup))[:4]
        if picked:
            user_selected = True
            if len(picked) >= 2:
                regions, comparison, single = picked, True, None
            else:
                regions, comparison = ([] if picked[0][0] == "Global" else picked), False
                single = regions[0] if regions else None
    # For commodity/asset forecasts, Standard and Deep automatically establish a
    # worldwide baseline and compare it with India. Quick stays intentionally fast.
    automatic_global_india = (
        depth != InvestigationDepth.QUICK
        and profile.is_forecast and profile.is_price_question
        and not comparison
        and (not regions or (len(regions) == 1 and regions[0][1] == "in"))
    )
    if automatic_global_india:
        regions = [("Global", ""), ("India", "in")]
        comparison = True

    # Any question about one specific region (Standard/Deep) is compared with the global picture.
    auto_region = (depth != InvestigationDepth.QUICK and not comparison and not automatic_global_india and not user_selected
                   and len(regions) == 1 and regions[0][0] != "Global")
    if auto_region:
        regions = [("Global", ""), regions[0]]
        comparison, single = True, None

    tasks: list[SearchTask] = []

    def add(surface: EvidenceSurface, region: tuple[str, str] | None, idx: int) -> None:
        query, fallbacks = _queries(surface, profile)
        if surface == EvidenceSurface.WEB and profile.is_forecast and profile.is_price_question:
            m = re.search(r"\b(next (?:week|month|quarter|year)|this (?:week|month)|tomorrow)\b", question, re.I)
            if m:  # keep the web query on the same time horizon the user asked about
                query = f"{profile.topic} {m.group(1).lower()}"
        params = {"date": _trend_window(depth)} if surface == EvidenceSurface.TRENDS else {}
        rationale = _rationale(surface, profile)
        if region and comparison:
            rationale = f"[{region[0]}] {rationale}"
        tasks.append(SearchTask(
            id=f"task_{len(tasks) + 1}_{uuid4().hex[:6]}", engine=SURFACE_ENGINE[surface], surface=surface,
            query=query, fallback_queries=fallbacks, rationale=rationale, params=params,
            priority=max(0, 100 - idx * 5), max_results=per_surface,
            region=region[0] if (region and comparison) else None, gl=(region[1] or None) if region else None,
        ))

    if comparison:
        regional = [EvidenceSurface.NEWS, EvidenceSurface.TRENDS]
        if depth != InvestigationDepth.QUICK:
            regional.append(EvidenceSurface.WEB)
        # Shopping provides local price context; Scholar is a deeper independent
        # cross-check, not a replacement for primary market evidence.
        if automatic_global_india and depth == InvestigationDepth.DEEP:
            regional.append(EvidenceSurface.SCHOLAR)
        for i, s in enumerate(regional):
            for r in regions:
                # Global shopping results are less useful than an explicit local
                # market snapshot, so keep shopping on India only if selected.
                if automatic_global_india and s == EvidenceSurface.SHOPPING and r[0] == "Global":
                    continue
                add(s, r, i)
        if automatic_global_india and EvidenceSurface.SHOPPING in surfaces:
            add(EvidenceSurface.SHOPPING, ("India", "in"), len(regional))
        surfaces = list(dict.fromkeys(regional + ([EvidenceSurface.SHOPPING] if automatic_global_india and EvidenceSurface.SHOPPING in surfaces else [])))
        if not automatic_global_india:
            for i, s in enumerate(x for x in _needs(question, intent, profile)[:configured_surface_limit] if x not in regional):
                if len(surfaces) >= configured_surface_limit:
                    break
                add(s, None, len(regional) + i)
                surfaces.append(s)
    else:
        for i, s in enumerate(surfaces):
            region = single if (single and s in REGIONAL_SURFACES) else None
            add(s, region, i)

    mode_profile = describe_mode(depth, comparison, per_surface, configured_surface_limit)
    return InvestigationPlan(
        question=question, intent=intent, topic=profile.topic, depth=depth.value,
        question_horizon=question_horizon(question), mode_profile=mode_profile,
        configured_surface_limit=configured_surface_limit, per_surface_limit=per_surface,
        geographic_strategy=("user_selected_regions" if user_selected and comparison else "global_vs_india" if automatic_global_india else "global_vs_region" if auto_region else "explicit_region_comparison" if comparison else "single_region" if single else "global_overview"),
        geography=(single[0] if single else (", ".join(r[0] for r in regions) if comparison else None)),
        regions=[r[0] for r in regions], is_forecast=profile.is_forecast,
        time_sensitivity=_time_sensitivity(question),
        evidence_requirements=[s.value for s in surfaces],
        selected_engines=list(dict.fromkeys(SURFACE_ENGINE[s] for s in surfaces)),
        search_tasks=tasks, anchor_terms=profile.anchors, key_terms=profile.key_terms,
    )


_SAFE_QUERY = re.compile(r"^[\w\s\-\+&'’\.,/₹$%]{2,80}$", re.UNICODE)


def apply_llm_queries(plan: InvestigationPlan, queries: dict[str, str] | None, refined_topic: str | None = None,
                      anchors: list[str] | None = None) -> bool:
    """Merge sanitised LLM wording into the plan. The engine selection never changes."""
    changed = False
    if anchors:
        clean = [a.lower().strip() for a in anchors if isinstance(a, str) and re.fullmatch(r"[\w\-\+\. ]{2,30}", a.strip())]
        clean = list(dict.fromkeys(clean))[:4]
        if clean:
            plan.anchor_terms = clean
            changed = True
    if refined_topic and 2 <= len(refined_topic) <= 60 and len(refined_topic.split()) <= 6 and _SAFE_QUERY.match(refined_topic):
        plan.topic = refined_topic.strip()
        changed = True
    for task in plan.search_tasks:
        suggestion = (queries or {}).get(task.surface.value)
        if not suggestion or not isinstance(suggestion, str):
            continue
        suggestion = suggestion.strip()
        if task.surface == EvidenceSurface.TRENDS:  # Trends wants a stable short topic, never time words
            suggestion = re.sub(r"\b(today|now|tomorrow|next|this|week|month|year|latest|current|forecast|prediction)\b", "", suggestion, flags=re.I)
            suggestion = re.sub(r"\s+", " ", suggestion).strip()
        limit = 4 if task.surface == EvidenceSurface.TRENDS else 7
        if not _SAFE_QUERY.match(suggestion) or len(suggestion.split()) > limit or suggestion == task.query:
            continue
        task.fallback_queries = [q for q in dict.fromkeys([task.query, *task.fallback_queries]) if q != suggestion]
        task.query = suggestion
        changed = True
    return changed
