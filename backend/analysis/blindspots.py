"""Potential blind-spot evaluation.

Four kinds of blind spot are produced, all deterministic and all with an explicit
"what could make this wrong":

divergence    one surface is much stronger than another (the classic SPECTRA case)
coverage      a planned surface returned nothing / failed, so that dimension is unobserved
temporal      most evidence is undated, so "current" cannot be verified
disagreement  sources point in opposite directions

    importance (divergence) = 0.55*gap + 0.25*stronger_strength + 0.20*divergence_confidence
    confidence (divergence) = 0.55*divergence_confidence + 0.45*min(signal confidences)

A blind spot is a prompt to look closer, never proof that something is absent.
"""
from __future__ import annotations

from typing import Iterable
from uuid import uuid4

from backend.models.responses import (
    BlindSpot, Disagreement, Divergence, EvidenceItem, InvestigationPlan, Signal, SurfaceStatus, TemporalContext,
)

PHRASE = {
    "Public Attention": "public search interest",
    "News Momentum": "news coverage",
    "Public Web Presence": "general web visibility",
    "Research Activity": "research activity",
    "Patent Activity": "patent activity",
    "Hiring Demand": "hiring demand",
    "Commercial Availability": "observable commercial availability",
    "Video Attention": "video attention",
}
SURFACE_SIGNAL = {
    "web": "Public Web Presence", "news": "News Momentum", "trends": "Public Attention", "scholar": "Research Activity",
    "jobs": "Hiring Demand", "shopping": "Commercial Availability", "patents": "Patent Activity", "video": "Video Attention",
}
SURFACE_WEIGHT = {"shopping": 0.62, "trends": 0.58, "jobs": 0.55, "news": 0.5, "scholar": 0.42, "patents": 0.4, "video": 0.35, "web": 0.45}
DEFAULT_MIN_IMPORTANCE = 0.38


def _wrong_conditions(low_signal: str) -> list[str]:
    base = [
        "Private, offline or poorly indexed activity may not appear in public search results.",
        "Surfaces differ in coverage, latency and ranking bias, so some of the gap may be measurement difference.",
    ]
    if low_signal == "Commercial Availability":
        base.insert(0, "Commercial deployments may exist through enterprise contracts or channels that Google Shopping does not index.")
    if low_signal == "Hiring Demand":
        base.insert(0, "Hiring may happen on private job boards or under different job titles than the ones searched.")
    return base


def _counter_evidence(low: Signal) -> list[str]:
    out = []
    if low.evidence_count:
        out.append(f"{low.name} is not empty: it has {low.evidence_count} supporting item(s), so the gap does not prove absence.")
    return out


def _divergence_blind_spots(divergences, by_signal, min_importance) -> list[BlindSpot]:
    out: list[BlindSpot] = []
    for d in divergences:
        high, low = by_signal.get(d.higher_signal or d.left_signal), by_signal.get(d.lower_signal or d.right_signal)
        if high is None or low is None:
            continue
        importance = round(min(1.0, 0.55 * d.magnitude + 0.25 * high.strength + 0.20 * d.confidence), 3)
        confidence = round(min(1.0, 0.55 * d.confidence + 0.45 * min(high.confidence, low.confidence)), 3)
        if importance < min_importance:
            continue
        early = d.kind == "momentum"
        title = (f"Interest is accelerating faster than {PHRASE.get(low.name, low.name)}" if early else
                 f"{PHRASE.get(high.name, high.name).capitalize()} may be running ahead of {PHRASE.get(low.name, low.name)}")
        out.append(BlindSpot(
            id=f"blind_{uuid4().hex[:12]}", kind="divergence", title=title,
            description=(f"{high.name} is {high.level} ({high.strength:.2f}) while {low.name} is {low.level} ({low.strength:.2f}) — "
                         f"a gap of {d.magnitude:.2f}. The part of the picture that is easiest to see (attention, coverage, research) "
                         f"may overstate what is observable on the other surface. This is a potential blind spot, not proof."),
            importance=importance, confidence=confidence, supporting_signals=[high.name, low.name],
            evidence_ids=list(dict.fromkeys([*high.evidence_ids, *low.evidence_ids])),
            counter_evidence=_counter_evidence(low), what_could_make_this_wrong=_wrong_conditions(low.name),
        ))
    return out


def _coverage_blind_spots(surface_status: list[SurfaceStatus], by_signal: dict[str, Signal]) -> list[BlindSpot]:
    """A planned surface that produced nothing usable is itself information."""
    best: dict[str, SurfaceStatus] = {}
    for st in surface_status:
        cur = best.get(st.surface)
        if cur is None or (cur.kept_count == 0 and st.kept_count > 0):
            best[st.surface] = st
    out: list[BlindSpot] = []
    for surface, st in best.items():
        signal_name = SURFACE_SIGNAL.get(surface)
        if st.kept_count > 0 or signal_name in by_signal and by_signal[signal_name].evidence_count > 0:
            continue
        importance = SURFACE_WEIGHT.get(surface, 0.4)
        if importance < 0.4:
            continue  # a missing video search is not worth a blind-spot card
        if st.status == "failed":
            reason = f"the request failed ({st.error_kind or 'error'}): {st.error or 'unknown error'}"
            confidence = 0.35
        elif st.evidence_count > 0:
            reason = f"all {st.evidence_count} result(s) were filtered out as not relevant to the subject"
            confidence = 0.5
        else:
            reason = "the search returned no results"
            confidence = 0.5
        label = PHRASE.get(signal_name or "", surface)
        out.append(BlindSpot(
            id=f"blind_{uuid4().hex[:12]}", kind="coverage",
            title=f"Could not observe {label}",
            description=(f"SPECTRA planned to check {label} ({st.label}) but {reason}. "
                         "That dimension is therefore unobserved — which is different from being low."),
            importance=round(importance, 3), confidence=confidence, supporting_signals=[signal_name] if signal_name else [],
            evidence_ids=[], counter_evidence=[],
            what_could_make_this_wrong=["A retry or a differently-worded query may return data.",
                                         "The activity may exist but not be exposed through this Google surface."],
        ))
    return sorted(out, key=lambda b: b.importance, reverse=True)[:2]


def _temporal_blind_spot(temporal: TemporalContext | None, evidence: list[EvidenceItem]) -> BlindSpot | None:
    if temporal is None:
        return None
    time_bearing = temporal.recent_count + temporal.prior_count + temporal.undated_count
    if time_bearing < 5 or temporal.temporal_coverage >= 0.45:
        return None
    ids = [i.id for i in evidence if i.published_at is None and i.date_kind is None][:20]
    return BlindSpot(
        id=f"blind_{uuid4().hex[:12]}", kind="temporal", title="Most evidence cannot be placed in time",
        description=(f"Only {temporal.temporal_coverage * 100:.0f}% of time-bearing results carried a usable publication date "
                     f"({temporal.undated_count} undated). Without dates SPECTRA cannot tell whether the evidence is current."),
        importance=0.52, confidence=0.7, supporting_signals=[], evidence_ids=ids, counter_evidence=[],
        what_could_make_this_wrong=["Undated pages may well be recent; Google simply did not expose a date.",
                                     "Open the linked sources to check publication dates directly."],
    )


def _disagreement_blind_spots(disagreements: list[Disagreement]) -> list[BlindSpot]:
    out = []
    for d in disagreements:
        if d.confidence < 0.4:
            continue
        out.append(BlindSpot(
            id=f"blind_{uuid4().hex[:12]}", kind="disagreement",
            title="A one-sided summary would hide a real split in the evidence",
            description=f"{d.topic}: {d.side_a_label} versus {d.side_b_label}. {d.explanation}",
            importance=round(min(1.0, 0.45 + 0.35 * d.confidence), 3), confidence=d.confidence,
            supporting_signals=[], evidence_ids=list(dict.fromkeys([*d.side_a_evidence_ids, *d.side_b_evidence_ids])),
            counter_evidence=[], what_could_make_this_wrong=[
                "Headline wording can look directional without describing the topic itself.",
                "One side may rely on older coverage; compare dates in the evidence list.",
            ],
        ))
    return out


def evaluate_blind_spots(
    divergences: Iterable[Divergence],
    signals: Iterable[Signal],
    evidence: Iterable[EvidenceItem],
    *,
    plan: InvestigationPlan | None = None,
    surface_status: list[SurfaceStatus] | None = None,
    disagreements: list[Disagreement] | None = None,
    temporal: TemporalContext | None = None,
    min_importance: float = DEFAULT_MIN_IMPORTANCE,
) -> list[BlindSpot]:
    signal_list = list(signals)
    evidence_list = list(evidence)
    by_signal = {s.name: s for s in signal_list}

    results = _divergence_blind_spots(divergences, by_signal, min_importance)
    results += _coverage_blind_spots(surface_status or [], by_signal)
    results += _disagreement_blind_spots(disagreements or [])
    temporal_spot = _temporal_blind_spot(temporal, evidence_list)
    if temporal_spot:
        results.append(temporal_spot)

    # De-duplicate identical titles, rank by importance x confidence.
    seen: set[str] = set()
    unique: list[BlindSpot] = []
    for b in sorted(results, key=lambda b: b.importance * b.confidence, reverse=True):
        if b.title in seen:
            continue
        seen.add(b.title)
        unique.append(b)
    return unique[:6]
