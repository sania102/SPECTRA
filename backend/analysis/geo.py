"""Geographic comparison: the same question searched through different countries."""
from __future__ import annotations

from collections import defaultdict
from math import log1p
from typing import Iterable

from backend.models.responses import EvidenceItem, GeoFinding, RegionSummary, RegionalComparison, TrendSeries


def build_geo_findings(evidence: Iterable[EvidenceItem], trend_series: list[TrendSeries] | None = None) -> list[GeoFinding]:
    groups: dict[tuple[str, str], list[EvidenceItem]] = defaultdict(list)
    for item in evidence:
        if item.region:
            groups[(item.region, item.source_type or item.engine)].append(item)
    out: list[GeoFinding] = []
    for (region, surface), items in groups.items():
        quality = sum(i.relevance for i in items) / len(items)
        strength = round(0.65 * quality + 0.35 * min(1.0, log1p(len(items)) / log1p(8)), 3)
        top = max(items, key=lambda i: i.relevance)
        # Count unique publisher domains, not just returned links, as a simple
        # independence check. Missing domains fall back to the source label.
        independent_sources = {
            (i.source_domain or i.source or i.engine).casefold().strip()
            for i in items if (i.source_domain or i.source or i.engine)
        }
        out.append(GeoFinding(region=region, surface=surface, strength=strength, evidence_count=len(items),
                              source_count=len(independent_sources), top_headline=top.title[:160]))
    for s in trend_series or []:
        if s.region:
            out.append(GeoFinding(
                region=s.region, surface="attention", strength=round(min(1.0, s.recent_avg / 100.0), 3),
                evidence_count=len(s.values), source_count=1, note=f"Search interest {s.direction}"
                + (f" ({s.change_pct:+.0f}%)" if s.change_pct is not None else "")))
    # Annotate how far each region is from the best-covered one on the same surface.
    by_surface: dict[str, list[GeoFinding]] = defaultdict(list)
    for g in out:
        by_surface[g.surface].append(g)
    for surface, gs in by_surface.items():
        if len(gs) < 2:
            continue
        best = max(gs, key=lambda g: g.strength)
        for g in gs:
            if g is best:
                g.note = (g.note + " · " if g.note else "") + "strongest signal on this surface"
            elif best.strength - g.strength >= 0.2:
                g.note = (g.note + " · " if g.note else "") + f"{best.strength - g.strength:.2f} below {best.region}"
    return sorted(out, key=lambda g: (g.surface, -g.strength))


# ── Regional comparison (source-backed, easy to read) ─────────────────────────────────────

def build_regional_comparison(evidence: Iterable[EvidenceItem], trend_series: list[TrendSeries] | None = None,
                              horizon: str = "unspecified", regions: list[str] | None = None) -> RegionalComparison | None:
    from backend.analysis.direction import summarize_direction

    items = [i for i in evidence if i.region]
    names = list(dict.fromkeys(regions or [i.region for i in items if i.region]))
    if len(names) < 2:
        return None
    summaries: list[RegionSummary] = []
    domains: dict[str, set[str]] = {}
    for name in names:
        mine = [i for i in items if i.region == name]
        d = summarize_direction(mine, horizon)
        sources = {(i.source_domain or i.source or "").casefold() for i in mine if i.engine != "google_trends" and (i.source_domain or i.source)}
        domains[name] = sources
        series = next((s for s in (trend_series or []) if s.region == name and s.values), None)
        headlines = [
            {"id": i.id, "title": i.title[:160], "source": i.source, "url": i.url, "stance": i.stance}
            for i in sorted((x for x in mine if x.engine in {"google_news", "google"} and x.stance in {"up", "down"}), key=lambda x: -x.relevance)[:4]
        ]
        summaries.append(RegionSummary(
            region=name, items=len(mine), unique_sources=len(sources), sources_up=d.sources_up, sources_down=d.sources_down,
            lean=d.lean, trend_direction=series.direction if series else None, trend_change_pct=series.change_pct if series else None,
            trend_window=(series.window_label if series else None), top_headlines=headlines, evidence_ids=[i.id for i in mine][:30],
        ))
    leans = {s.lean for s in summaries if s.lean != "insufficient"}
    trends = {s.trend_direction for s in summaries if s.trend_direction}
    agrees = None if not leans and not trends else (len(leans) <= 1 and len(trends) <= 1)

    def phrase(s: RegionSummary) -> str:
        coverage = ("too little directional coverage" if s.lean == "insufficient"
                    else f"coverage leans {s.lean} ({s.sources_up} up vs {s.sources_down} down sources)")
        trend = (f", search interest {s.trend_direction}" + (f" ({s.trend_change_pct:+.0f}% over 30 days)" if s.trend_change_pct is not None else "")) if s.trend_direction else ""
        return f"{s.region}: {coverage}{trend}"

    finding = " | ".join(phrase(s) for s in summaries)
    if agrees is False:
        finding = "Regions disagree. " + finding
    elif agrees:
        finding = "Regions broadly agree. " + finding
    caveats = ["Only the regions listed were searched; this is not a worldwide country-by-country survey."]
    shared = set.intersection(*domains.values()) if domains else set()
    if shared and len(shared) >= 3:
        caveats.append(f"{len(shared)} publishers appear in every region, so regional evidence is not fully independent.")
    return RegionalComparison(regions=summaries, agrees=agrees, finding=finding, caveats=caveats)
