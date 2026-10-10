"""Plain-language verdict: what SPECTRA found, how far to trust it, what it cannot say."""
from __future__ import annotations

from collections import defaultdict

from backend.analysis.answer import build_answer
from backend.models.responses import (
    BlindSpot, DataQuality, Disagreement, Divergence, EvidenceItem, InvestigationPlan, Signal, SurfaceStatus,
    DirectionSummary, TemporalContext, TrendSeries, Verdict,
)


def build_verdict(
    plan: InvestigationPlan, signals: list[Signal], divergences: list[Divergence], blind_spots: list[BlindSpot],
    disagreements: list[Disagreement], evidence: list[EvidenceItem], trend_series: list[TrendSeries],
    quality: DataQuality, temporal: TemporalContext | None, llm_used: bool,
    direction: DirectionSummary | None = None, regional=None,
) -> Verdict:
    high = [s for s in signals if s.level == "high"]
    low = [s for s in signals if s.level == "low"]
    direction = direction or DirectionSummary()
    source_up, source_down = direction.sources_up, direction.sources_down
    series = next((s for s in trend_series if s.values), None)

    if not signals:
        return Verdict(
            headline="Not enough usable evidence",
            summary=("SPECTRA could not collect enough relevant results to measure any signal. "
                     "Try rephrasing the question with the specific subject (for example “silver price India”)."),
            lean="insufficient", caveats=quality.notes[:4],
            next_steps=["Rephrase with a clearer subject.", "Check the data-quality panel for failed searches."],
        )

    parts = []
    if high:
        parts.append("strongest evidence on " + ", ".join(s.name.lower() for s in high[:3]))
    if low:
        parts.append("weak or thin evidence on " + ", ".join(s.name.lower() for s in low[:3]))
    headline = ("; ".join(parts)).capitalize() + "." if parts else "Evidence is moderate across the surfaces checked."
    if divergences:
        headline += f" {len(divergences)} cross-surface gap(s) found."

    if plan.is_forecast:
        headline = "Not enough directional evidence to read a lean. SPECTRA cannot predict outcomes."
    lean = lean_detail = None
    if plan.is_forecast:
        bits = []
        if direction.unique_sources:
            bits.append(f"{source_up} source(s) lean upward and {source_down} downward among {direction.unique_sources} unique sources "
                        f"({direction.directional_items} directional headline(s) after removing {direction.duplicates_collapsed} duplicate(s)"
                        + (f" and {direction.long_horizon_excluded} long-horizon forecast(s)" if direction.long_horizon_excluded else "") + ")")
        if series and series.change_pct is not None:
            bits.append(f"search interest changed {series.change_pct:+.0f}% (last 30 days vs the 30 days before; {series.window_label or 'requested window'} fetched)")
        lean = direction.lean
        lean_detail = ("; ".join(bits) + ". ") if bits else ""
        lean_detail += (" These are counts of directional coverage, not independent votes or price probabilities. "
                        "Search interest measures attention, not price direction; this is not a reliable price forecast or financial advice.")

    investigation_note = (
        f"SPECTRA planned {quality.surfaces_planned} information surface(s) for “{plan.topic}”; "
        f"{quality.surfaces_completed} returned usable evidence"
        + (f", {quality.surfaces_empty} returned nothing relevant" if quality.surfaces_empty else "")
        + (f", {quality.surfaces_failed} failed" if quality.surfaces_failed else "")
        + f". It kept {quality.kept_results} relevant result(s) from {quality.unique_sources} unique source(s)."
    )
    if blind_spots:
        investigation_note += f" It flagged {len(blind_spots)} potential blind spot(s), led by “{blind_spots[0].title.lower()}”."
    else:
        investigation_note += " It found no material divergence between the surfaces it could observe."

    if plan.is_forecast:
        if lean == "upward":
            answer = f"Current coverage leans upward for {plan.topic}, but the evidence does not establish that the price will rise or that buying now will be profitable."
        elif lean == "downward":
            answer = f"Current coverage leans downward for {plan.topic}, but the evidence does not establish that the price will fall or that waiting will be better."
        elif lean == "mixed":
            answer = f"The evidence is mixed for {plan.topic}; it does not establish whether the price will rise or fall over the requested period, or whether buying now will be profitable."
        else:
            answer = f"There is not enough directional evidence to assess whether {plan.topic} will rise or fall over the requested period."
        summary = answer + " " + investigation_note
    else:
        summary = investigation_note

    if plan.is_forecast and lean in {"upward", "downward", "mixed"}:
        trend_txt = f"; search interest is {series.direction}" if series else ""
        if lean == "mixed":
            headline = f"Evidence is mixed for {plan.topic}{trend_txt}. The forecast direction remains uncertain."
        elif lean == "upward":
            headline = f"Current coverage leans upward for {plan.topic}{trend_txt}, but this does not establish that the price will rise."
        else:
            headline = f"Current coverage leans downward for {plan.topic}{trend_txt}, but this does not establish that the price will fall."

    caveats: list[str] = []
    if plan.is_forecast:
        caveats.append("SPECTRA measures information signals; it cannot predict future prices or outcomes. Strength scores are NOT probabilities.")
        if not plan.geography:
            caveats.append("No market or country was specified; local retail prices, taxes, premiums, currency effects, and resale spreads are not assessed.")
    else:
        caveats.append("Scores describe how strong the evidence is on each surface — not the probability that a claim is true.")
    for st_note in quality.notes[:3]:
        caveats.append(st_note)
    if temporal and temporal.temporal_coverage < 0.45 and (temporal.recent_count + temporal.prior_count + temporal.undated_count) >= 5:
        caveats.append(f"Only {temporal.temporal_coverage * 100:.0f}% of time-bearing evidence has a verified date.")
    if not llm_used:
        caveats.append("AI claim extraction was unavailable; claims come from source titles/snippets and a rule-based direction detector.")

    next_steps = []
    if blind_spots:
        next_steps.append("Open the top blind spot and read its “what could make this wrong” list.")
    if disagreements:
        next_steps.append("Read the conflicting sources side by side in the Disagreements panel.")
    next_steps.append("Verify key claims at the primary sources linked in the evidence list.")

    answer = build_answer(plan, signals, evidence, direction, trend_series, blind_spots, disagreements, quality, regional)
    return Verdict(answer=answer, headline=answer.direct_answer, summary=summary, lean=lean, lean_detail=lean_detail,
                   caveats=caveats[:6], next_steps=next_steps[:3])
