"""Top-level investigation orchestration: plan -> search -> clean -> analyse -> explain."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from backend.agent.planner import apply_llm_queries, build_plan
from backend.agent.router import InvestigationRouter
from backend.analysis.advanced import (
    build_entity_profiles, cross_surface_findings, summarize_context, summarize_temporal_context,
)
from backend.analysis.blindspots import evaluate_blind_spots
from backend.analysis.disagreement import build_claim_groups, detect_disagreements
from backend.analysis.direction import summarize_direction, tag_horizons
from backend.analysis.divergence import detect_divergences
from backend.analysis.geo import build_geo_findings, build_regional_comparison
from backend.analysis.normalization import annotate, dedupe
from backend.analysis.relevance import apply_relevance
from backend.analysis.signals import build_signals
from backend.analysis.verdict import build_verdict
from backend.evidence.provenance import provenance_summary
from backend.llm.service import LLMService
from backend.models.requests import InvestigationRequest
from backend.models.responses import (
    ContextCoverage, CrossSurfaceFinding as ResponseCrossSurfaceFinding, DataQuality, EntityProfile as ResponseEntityProfile,
    EvidenceItem, InvestigationResult, SurfaceStatus, TemporalContext,
)

Emit = Callable[[dict], None]
_KEY_RE = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|gsk_[A-Za-z0-9]{8,}|AIza[A-Za-z0-9_\-]{10,})")


def _safe_error_message(exc: Exception) -> str:
    return _KEY_RE.sub("[REDACTED_KEY]", str(exc).replace("\n", " ").strip())[:500]


class Investigator:
    """Coordinates planning, retrieval, deterministic analysis and optional LLM enrichment."""

    def __init__(self, router: InvestigationRouter, llm: LLMService | None = None):
        self.router = router
        self.llm = llm

    def investigate(self, request: InvestigationRequest, emit: Emit | None = None) -> InvestigationResult:
        def say(event: dict) -> None:
            if emit:
                emit(event)

        llm_on = bool(self.llm and self.llm.enabled)

        # ── 1. Understand + plan ─────────────────────────────────────────────
        say({"type": "stage", "stage": "understanding", "message": "Understanding the question…"})
        plan = build_plan(request.question, request.depth, request.regions)

        llm_used = False
        enrichment_status, enrichment_error = "not_attempted", None
        if llm_on:
            enrichment_status = "attempted"
            try:
                enrichment = self.llm.enrich_plan(plan)
                if enrichment:
                    llm_used = apply_llm_queries(plan, enrichment.queries, enrichment.refined_topic, enrichment.anchor_terms)
                    plan.llm_refined = llm_used
                    if enrichment.geography and not plan.geography:
                        plan.geography = enrichment.geography
                    enrichment_status = "completed"
            except Exception as exc:
                enrichment_status, enrichment_error = "failed", _safe_error_message(exc)

        say({"type": "plan", "plan": plan.model_dump(mode="json") if hasattr(plan, "model_dump") else {}})

        # ── 2. Search (SerpApi) ──────────────────────────────────────────────
        planned_unique_surfaces = len({task.surface.value for task in plan.search_tasks})
        say({"type": "stage", "stage": "searching", "message": f"Executing {len(plan.search_tasks)} search tasks across {planned_unique_surfaces} unique information surfaces…"})
        raw_evidence = self.router.execute(plan.search_tasks, emit)

        # ── 3. Clean: dedupe, relevance filter ───────────────────────────────
        say({"type": "stage", "stage": "filtering", "message": "Removing duplicates and off-topic results…"})
        deduped = dedupe(raw_evidence)
        kept, dropped = apply_relevance(deduped, plan.anchor_terms, plan.key_terms)
        unique: dict[str, EvidenceItem] = {}
        for item in kept:
            unique.setdefault(item.id, item)
        kept_ids = set(unique)

        # ── 4. Claims + direction ────────────────────────────────────────────
        annotate(unique.values())
        tag_horizons(unique.values())
        claims_added = 0
        claim_status, claim_error, claim_errors = "not_attempted", None, []
        if llm_on and unique:
            say({"type": "stage", "stage": "claims", "message": "Extracting claims with AI…"})
            claim_status = "completed_no_claims"
            outcome = self.llm.extract_claims(unique.values())
            for ex in outcome.claims:
                item = unique.get(ex.evidence_id)
                if not item:
                    continue
                if ex.claim.strip():
                    item.claim = ex.claim.strip()
                    claims_added += 1
                if ex.entity and not item.entity:
                    item.entity = ex.entity
                if ex.claim_type:
                    item.claim_type = ex.claim_type
                if ex.stance in {"up", "down", "mixed", "neutral"} and item.engine != "google_trends":
                    item.stance = ex.stance
            claim_errors = outcome.errors
            if claims_added:
                claim_status = "completed_with_claims" if not outcome.chunks_failed else "partial"
            elif outcome.chunks_failed:
                claim_status = "failed"
            claim_error = outcome.errors[0] if outcome.errors else None

        # ── 5. Deterministic analysis ────────────────────────────────────────
        say({"type": "stage", "stage": "signals", "message": "Measuring signal strength on every surface…"})
        evidence_list = sorted(unique.values(), key=lambda e: -e.relevance)
        trend_series = list(self.router.series)
        signals = build_signals(evidence_list, trend_series)

        say({"type": "stage", "stage": "divergence", "message": "Comparing surfaces and looking for disagreement…"})
        divergences = detect_divergences(signals, trend_series)
        disagreements = detect_disagreements(evidence_list, trend_series, plan.question_horizon)
        direction = summarize_direction(evidence_list, plan.question_horizon)
        regional = build_regional_comparison(evidence_list, trend_series, plan.question_horizon, plan.regions) if len(plan.regions) >= 2 else None
        claim_groups = build_claim_groups(evidence_list)

        temporal = summarize_temporal_context(evidence_list)
        temporal_model = TemporalContext(
            recent_count=temporal.recent_count, prior_count=temporal.prior_count, undated_count=temporal.undated_count,
            snapshot_count=temporal.snapshot_count, recent_share=temporal.recent_share,
            temporal_coverage=temporal.temporal_coverage, direction=temporal.direction,
        )

        # Per-surface status (what the user sees in the live view and data-quality panel)
        surface_status: list[SurfaceStatus] = []
        for ex in self.router.executions:
            task_items = self.router.items_by_task.get(ex.task_id, [])
            kept_count = sum(1 for i in task_items if i.id in kept_ids)
            status = ex.status
            if status == "completed" and kept_count == 0:
                status = "empty"
            surface_status.append(SurfaceStatus(
                task_id=ex.task_id, engine=ex.engine, surface=ex.surface, label=ex.label, query=ex.query, status=status,
                evidence_count=ex.evidence_count, kept_count=kept_count, attempts=ex.attempts, duration_ms=ex.duration_ms,
                region=ex.region, error=ex.error, error_kind=ex.error_kind, rationale=ex.rationale,
            ))

        say({"type": "stage", "stage": "blindspots", "message": "Hunting for blind spots…"})
        blind_spots = evaluate_blind_spots(
            divergences, signals, evidence_list, plan=plan, surface_status=surface_status,
            disagreements=disagreements, temporal=temporal_model,
        )

        geo_findings = build_geo_findings(evidence_list, trend_series)
        exclude = {t.casefold() for t in [*plan.anchor_terms, plan.topic, *plan.regions]}
        entity_profiles = build_entity_profiles(evidence_list, exclude=exclude)
        context = summarize_context(evidence_list, plan.geography if len(plan.regions) <= 1 else None)
        # advanced.cross_surface_findings returns dataclass instances, while the
        # API response schema requires Pydantic CrossSurfaceFinding models.
        # Convert at this boundary so InvestigationResult can validate reliably.
        cross_surface = [
            ResponseCrossSurfaceFinding(
                id=finding.id,
                finding_type=finding.finding_type,
                title=finding.title,
                description=finding.description,
                signal_names=list(finding.signal_names),
                evidence_ids=list(finding.evidence_ids),
                confidence=finding.confidence,
            )
            for finding in cross_surface_findings(signals, evidence_list)
        ]
        if len(plan.regions) >= 2 and geo_findings:
            cross_surface.append(ResponseCrossSurfaceFinding(
                id="cross_geo", finding_type="geographic", title="Geographic comparison",
                description=f"The same question was searched in {', '.join(plan.regions)}; see the regional signal table.",
                signal_names=[], evidence_ids=[e.id for e in evidence_list if e.region][:24], confidence=0.6))

        # ── 6. Data quality + verdict ────────────────────────────────────────
        notes: list[str] = []
        for st in surface_status:
            where = f" ({st.region})" if st.region else ""
            if st.status == "failed":
                notes.append(f"{st.label}{where} failed after {st.attempts} attempt(s): {st.error_kind or 'error'} — that surface is unobserved, not “low”.")
            elif st.status == "empty" and st.evidence_count == 0:
                notes.append(f"{st.label}{where} returned no results, even after simpler fallback queries.")
            elif st.status == "empty":
                notes.append(f"{st.label}{where}: all {st.evidence_count} results were off-topic and filtered out.")
        if dropped:
            notes.append(f"Filtered out {len(dropped)} result(s) that did not mention “{', '.join(plan.anchor_terms)}”.")
        # A surface is an information channel (News, Trends, Web, etc.); a task
        # is one execution of that channel for a specific region/query. Keep both
        # counts so regional comparisons don't misleadingly inflate surface totals.
        # Canonical, reconciled surface accounting. Every planned surface lands in exactly ONE bucket:
        #   completed = at least one of its tasks returned usable (kept) evidence
        #   failed    = no task returned evidence and at least one task errored (unobserved, not "low")
        #   empty     = searches ran but nothing relevant came back
        by_surface: dict[str, list[SurfaceStatus]] = {}
        for st in surface_status:
            by_surface.setdefault(st.surface, []).append(st)
        completed_surface_names = {n for n, sts in by_surface.items() if any(s.status == "completed" for s in sts)}
        failed_surface_names = {n for n, sts in by_surface.items() if n not in completed_surface_names and any(s.status == "failed" for s in sts)}
        empty_surface_names = set(by_surface) - completed_surface_names - failed_surface_names
        planned_surfaces = {task.surface.value for task in plan.search_tasks}
        unique_source_names = {(e.source_domain or e.source or "").casefold() for e in evidence_list
                               if e.engine != "google_trends" and (e.source_domain or e.source)}
        quality = DataQuality(
            surfaces_planned=len(planned_surfaces),
            surfaces_completed=len(completed_surface_names),
            surfaces_with_evidence=len(completed_surface_names),
            surfaces_failed=len(failed_surface_names),
            surfaces_empty=len(empty_surface_names),
            tasks_planned=len(plan.search_tasks),
            tasks_attempted=sum(1 for s in surface_status if s.attempts > 0),
            tasks_completed=sum(1 for s in surface_status if s.status == "completed"),
            tasks_failed=sum(1 for s in surface_status if s.status == "failed"),
            tasks_empty=sum(1 for s in surface_status if s.status == "empty"),
            raw_results=len(raw_evidence), kept_results=len(evidence_list), dropped_irrelevant=len(dropped),
            unique_sources=len(unique_source_names),
            trend_windows=sorted({s.window_label or s.window or "" for s in trend_series if (s.window_label or s.window)}),
            dated_share=temporal.temporal_coverage, notes=notes,
        )
        quality.reconciled = (quality.surfaces_completed + quality.surfaces_failed + quality.surfaces_empty == quality.surfaces_planned
                              and quality.tasks_completed + quality.tasks_failed + quality.tasks_empty == quality.tasks_planned)
        verdict = build_verdict(plan, signals, divergences, blind_spots, disagreements, evidence_list, trend_series,
                                quality, temporal_model, llm_used=llm_on and claim_status in {"completed_with_claims", "partial"},
                                direction=direction, regional=regional)

        # ── 7. Optional AI polish of the top blind spots ─────────────────────
        llm_explanations = 0
        if llm_on and blind_spots:
            say({"type": "stage", "stage": "explaining", "message": "Writing plain-language explanations…"})
            signals_text = "; ".join(f"{s.name}={s.strength:.2f} ({s.level}, confidence {s.confidence:.2f})" for s in signals)
            for bs in blind_spots[:3]:
                try:
                    explanation = self.llm.explain_blind_spot(bs, signals_text)
                except Exception:
                    break
                if explanation and explanation.description:
                    bs.title = explanation.title or bs.title
                    bs.description = explanation.description
                    if explanation.counter_evidence:
                        bs.counter_evidence = explanation.counter_evidence[:5]
                    if explanation.what_could_make_this_wrong:
                        bs.what_could_make_this_wrong = explanation.what_could_make_this_wrong[:5]
                    llm_explanations += 1

        result = InvestigationResult(
            investigation_id=f"inv_{uuid4().hex}", plan=plan, signals=signals, divergences=divergences,
            blind_spots=blind_spots, disagreements=disagreements, claim_groups=claim_groups, geo_findings=geo_findings,
            trend_series=trend_series, surface_status=surface_status, verdict=verdict, data_quality=quality, direction=direction, regional=regional,
            evidence=evidence_list,
            entity_profiles=[ResponseEntityProfile(canonical=p.canonical, mentions=p.mentions, evidence_ids=p.evidence_ids,
                                                   source_types=p.source_types, aliases=p.aliases) for p in entity_profiles],
            temporal_context=temporal_model,
            context_coverage=ContextCoverage(geography=context.geography, matched_count=context.matched_count,
                                             unspecified_count=context.unspecified_count, mismatch_count=context.mismatch_count,
                                             context_coverage=context.context_coverage),
            cross_surface_findings=cross_surface,
            claim_clusters=[{"claim_key": g.label, "claim_count": g.claim_count, "evidence_ids": g.evidence_ids,
                             "source_types": g.surfaces} for g in claim_groups],
            generated_at=datetime.now(timezone.utc),
            provenance=provenance_summary(signals, divergences, blind_spots),
            metadata={
                "stage": "full_pipeline_v2",
                "signal_count": len(signals), "divergence_count": len(divergences), "blind_spot_count": len(blind_spots),
                "disagreement_count": len(disagreements), "claim_group_count": len(claim_groups),
                "task_count": len(plan.search_tasks), "evidence_count": len(evidence_list),
                "depth_audit": {
                    "requested_depth": plan.depth,
                    "configured_surface_limit": plan.configured_surface_limit,
                    "configured_per_surface_limit": plan.per_surface_limit,
                    "unique_surfaces_planned": len({t.surface.value for t in plan.search_tasks}),
                    "tasks_planned": len(plan.search_tasks),
                    "tasks_attempted": quality.tasks_attempted,
                    "tasks_completed": quality.tasks_completed,
                    "tasks_empty": quality.tasks_empty,
                    "tasks_failed": quality.tasks_failed,
                    "geographic_strategy": plan.geographic_strategy,
                    "trend_windows_requested": sorted({str(t.params.get("date")) for t in plan.search_tasks if t.surface.value == "trends" and t.params.get("date")}),
                    "trend_windows_returned": [{"region": s.region, "window": s.window, "points": s.points, "span": s.span} for s in trend_series],
                    "mode_profile": plan.mode_profile,
                },
                "llm_enabled": llm_on, "llm_used_for_enrichment": llm_used,
                "llm_model": (self.llm.client.active_model if llm_on else None),
                "llm_enrichment_status": enrichment_status, "llm_enrichment_error_message": enrichment_error,
                "claims_added_by_llm": claims_added, "claim_extraction_status": claim_status,
                "claim_extraction_error_message": claim_error, "claim_extraction_errors": claim_errors[:3],
                "llm_blindspot_explanations": llm_explanations,
                "entity_profile_count": len(entity_profiles), "cross_surface_finding_count": len(cross_surface),
                "dropped_irrelevant": len(dropped),
            },
        )
        say({"type": "stage", "stage": "done", "message": "Investigation complete."})
        return result
