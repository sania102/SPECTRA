"""The 'Answer to your question' engine.

Deterministic and traceable: every sentence is built from signals, counts and linked evidence that
SPECTRA already measured. It answers the question the way an evidence analyst would ("Not yet:
attention outruns real-world adoption") while never claiming to predict the future.
"""
from __future__ import annotations

from typing import Iterable

from backend.models.responses import (
    Answer, AnswerLink, AnswerPoint, BlindSpot, DataQuality, Disagreement, DirectionSummary, EvidenceItem,
    InvestigationPlan, RegionalComparison, Signal, TrendSeries,
)

ATTENTION = {"News Momentum", "Public Attention", "Video Attention"}
ADOPTION = {"Commercial Availability", "Hiring Demand"}
BACKING = {"Research Activity", "Patent Activity"}
def _be(noun: str) -> str:
    return "are" if noun.endswith("s") else "is"


def _n(count: int, word: str = "relevant result") -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


PLAIN = {
    "News Momentum": "media coverage", "Public Attention": "public search interest", "Video Attention": "video attention",
    "Public Web Presence": "open-web presence", "Commercial Availability": "products you can actually buy",
    "Hiring Demand": "job postings", "Research Activity": "research papers", "Patent Activity": "patent filings",
}


def _links(ids: Iterable[str], by_id: dict[str, EvidenceItem], n: int = 2) -> list[AnswerLink]:
    items = sorted((by_id[i] for i in ids if i in by_id and by_id[i].url), key=lambda e: -e.relevance)
    out, seen = [], set()
    for e in items:
        key = (e.source_domain or e.source or "").lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(AnswerLink(title=e.title[:140], source=e.source, url=e.url))
        if len(out) >= n:
            break
    return out


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _confidence(quality: DataQuality) -> tuple[str, str]:
    planned = max(1, quality.surfaces_planned)
    score = (0.45 * quality.surfaces_completed / planned + 0.30 * min(1.0, quality.unique_sources / 10)
             + 0.25 * min(1.0, quality.dated_share / 0.6))
    if quality.surfaces_failed:
        score -= 0.1
    level = "high" if score >= 0.75 else "medium" if score >= 0.5 else "low"
    return level, (f"{quality.surfaces_completed} of {quality.surfaces_planned} information surfaces returned evidence, "
                   f"from {quality.unique_sources} unique sources; {round(quality.dated_share * 100)}% of the evidence is dated.")


def build_answer(
    plan: InvestigationPlan, signals: list[Signal], evidence: list[EvidenceItem], direction: DirectionSummary,
    trend_series: list[TrendSeries], blind_spots: list[BlindSpot], disagreements: list[Disagreement],
    quality: DataQuality, regional: RegionalComparison | None,
) -> Answer:
    by_id = {e.id: e for e in evidence}
    sig = {s.name: s for s in signals}
    topic = plan.topic or "this topic"
    confidence, reason = _confidence(quality)
    series = next((s for s in trend_series if s.values and not s.region), None) or next((s for s in trend_series if s.values), None)
    uncertainty = ["SPECTRA measures what public information shows; it does not predict the future. Scores describe evidence strength, not probability."]
    for note in quality.notes[:2]:
        uncertainty.append(note)
    if quality.dated_share < 0.4:
        uncertainty.append(f"Only {round(quality.dated_share * 100)}% of the evidence carries a date, so 'what is changing' is harder to judge.")
    pros: list[AnswerPoint] = []
    cons: list[AnswerPoint] = []

    if not signals:
        return Answer(label="Can't tell yet", tone="unknown", confidence="low", confidence_reason=reason,
                      direct_answer=f"SPECTRA could not collect enough relevant evidence about {topic}. Try rephrasing with the specific subject.",
                      uncertainty=uncertainty, next_steps=["Rephrase the question with a clearer subject.", "Check the Audit tab for failed or empty searches."])

    # ── Forecast-style questions: direction of coverage, never a prediction ───────────────────────
    if plan.is_forecast:
        ups = [e for e in evidence if e.stance == "up" and e.engine in {"google", "google_news", "youtube"} and e.horizon != "long"]
        downs = [e for e in evidence if e.stance == "down" and e.engine in {"google", "google_news", "youtube"} and e.horizon != "long"]
        lean = direction.lean
        label, tone = {"upward": ("Leans up", "positive"), "downward": ("Leans down", "negative"),
                       "mixed": ("Evidence is split", "mixed")}.get(lean, ("Not enough to tell", "unknown"))
        who = f"{direction.sources_up} sources lean up and {direction.sources_down} lean down (of {direction.unique_sources} unique sources)"
        if lean == "insufficient":
            direct = f"There is not enough directional coverage to say which way {topic} is likely to move. SPECTRA cannot predict it either way."
        else:
            word = {"upward": "upward", "downward": "downward", "mixed": "in both directions"}[lean]
            direct = f"Current coverage points {word} for {topic}: {who}. That describes what sources say, not what will happen: this is not a price prediction."
        if direction.sources_up:
            pros.append(AnswerPoint(text=f"{direction.sources_up} unique source(s) describe {topic} rising or strengthening.",
                                    evidence_ids=[e.id for e in ups][:6], links=_links([e.id for e in ups], by_id, 3)))
        if direction.sources_down:
            cons.append(AnswerPoint(text=f"{direction.sources_down} unique source(s) describe {topic} falling or weakening.",
                                    evidence_ids=[e.id for e in downs][:6], links=_links([e.id for e in downs], by_id, 3)))
        if series and series.change_pct is not None:
            uncertainty.append(f"Search interest is {series.direction} ({series.change_pct:+.0f}% over the last 30 days, {series.window_label or 'requested window'}). "
                               "That is attention, not price direction.")
        if direction.long_horizon_excluded:
            uncertainty.append(f"{direction.long_horizon_excluded} long-term forecast(s) were excluded because you asked about the near term.")
        uncertainty.append("Local prices, taxes, currency effects and retail premiums are not assessed." if not plan.geography else
                           "Coverage is not financial advice; prices can move on events no headline anticipates.")
    # ── Assessment questions: is attention matched by real-world activity? ────────────────────────
    else:
        att = [s for s in signals if s.name in ATTENTION and s.evidence_count]
        adopt_all = [s for s in signals if s.name in ADOPTION]
        back = [s for s in signals if s.name in BACKING and s.evidence_count]
        a = _mean([s.strength for s in att])
        adopt_obs = [s for s in adopt_all if s.evidence_count]
        sub_scores = [s.strength for s in adopt_obs] or [s.strength for s in back]
        b = _mean(sub_scores)
        a_txt = "high" if (a or 0) >= 0.55 else "moderate" if (a or 0) >= 0.38 else "low"
        if a is None:
            label, tone, direct = "Partly answered", "mixed", f"SPECTRA could not measure public attention for {topic}, so it can only describe real-world activity."
        elif b is None:
            label, tone = "Partly answered", "mixed"
            direct = (f"Public attention for {topic} is {a_txt}, but SPECTRA found no jobs, product or research signals to show whether real-world adoption has followed.")
        elif a >= 0.50 and b < 0.35:
            label, tone = "Not yet", "negative"
            direct = f"Probably not yet. Attention to {topic} is {a_txt}, but real-world signals (jobs, products, research) are weak: public attention is running ahead of adoption."
        elif a >= 0.50 and b >= 0.50:
            label, tone = "Yes, evidence supports it", "positive"
            direct = f"The evidence supports it. Attention to {topic} is {a_txt} and it is matched by real-world activity (jobs, products, research)."
        elif a < 0.38 and b >= 0.50:
            label, tone = "Quietly yes", "positive"
            direct = f"Real-world activity around {topic} is solid, but it gets little public attention: progress may be happening off the radar."
        elif a < 0.38 and b < 0.38:
            label, tone = "Little evidence", "negative"
            direct = f"There is little evidence of either attention or real-world activity around {topic}."
        else:
            label, tone = "Partly", "mixed"
            direct = f"Mixed picture for {topic}: attention is {a_txt} and real-world signals are moderate. Some evidence supports it, some does not."
        for s in sorted(signals, key=lambda x: -x.strength):
            if s.evidence_count and s.level == "high":
                pros.append(AnswerPoint(text=f"{PLAIN.get(s.name, s.name).capitalize()} {_be(PLAIN.get(s.name, s.name))} strong ({s.strength:.0%}, {_n(s.evidence_count)}).",
                                        evidence_ids=s.evidence_ids[:6], links=_links(s.evidence_ids, by_id)))
        gaps = {st for st in ADOPTION | BACKING if st not in sig}
        for s in sorted(signals, key=lambda x: x.strength):
            if s.level == "low":
                cons.append(AnswerPoint(text=f"{PLAIN.get(s.name, s.name).capitalize()} {_be(PLAIN.get(s.name, s.name))} weak ({s.strength:.0%}, {_n(s.evidence_count)}).",
                                        evidence_ids=s.evidence_ids[:6], links=_links(s.evidence_ids, by_id, 1)))
        for name in sorted(gaps & ADOPTION):
            cons.append(AnswerPoint(text=f"No {PLAIN[name]} were found in public search."))
        if series and series.change_pct is not None:
            uncertainty.append(f"Search interest is {series.direction} ({series.change_pct:+.0f}% over the last 30 days).")
        uncertainty.append("A quiet surface can mean the activity is private or poorly indexed, not that it does not exist.")

    for d in disagreements[:1]:
        cons.append(AnswerPoint(text=f"Sources disagree: {d.side_a_label} vs {d.side_b_label}.",
                                evidence_ids=(d.side_a_evidence_ids[:3] + d.side_b_evidence_ids[:3]),
                                links=_links(d.side_a_evidence_ids[:4] + d.side_b_evidence_ids[:4], by_id, 2)))
    regional_note = None
    if regional and regional.finding:
        regional_note = regional.finding
        if regional.agrees is False:
            uncertainty.append("Regions disagree: the answer may differ depending on where you are.")

    steps: list[str] = []
    if blind_spots:
        steps.append(f"Read the top blind spot: “{blind_spots[0].title}”.")
    if disagreements:
        steps.append("Open the conflicting sources side by side (Evidence tab).")
    if regional and regional.agrees is False:
        steps.append("Compare the regional headlines in the Regions tab before deciding.")
    steps.append("Verify the key claims at the linked primary sources.")
    return Answer(label=label, tone=tone, direct_answer=direct, confidence=confidence, confidence_reason=reason,
                  evidence_for=pros[:4], evidence_against=cons[:4], uncertainty=uncertainty[:5], next_steps=steps[:4], regional_note=regional_note)
