"""Routes planner-created search tasks to SerpApi with retry, fallback and progress events."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable

from backend.models.responses import EvidenceItem, TrendSeries
from backend.models.search import SearchTask
from backend.serpapi.client import SerpApiRequestError
from backend.serpapi.engines import ENGINE_SPECS
from backend.serpapi.service import SerpApiService

Emit = Callable[[dict], None]
_FATAL_KINDS = {"auth", "rate_limit"}  # retrying a different query cannot fix these


@dataclass
class TaskExecution:
    task_id: str
    engine: str
    surface: str
    query: str                    # query that produced the final outcome
    status: str                   # completed | empty | failed
    evidence_count: int = 0
    attempts: int = 1
    duration_ms: int = 0
    region: str | None = None
    error: str | None = None
    error_kind: str | None = None
    rationale: str | None = None
    label: str = ""


@dataclass
class InvestigationRouter:
    """Execute a planned investigation without leaking provider details."""

    serpapi_service: SerpApiService
    executions: list[TaskExecution] = field(default_factory=list)
    items_by_task: dict[str, list[EvidenceItem]] = field(default_factory=dict)
    series: list[TrendSeries] = field(default_factory=list)

    def _run_task(self, task: SearchTask, emit: Emit | None) -> tuple[list[EvidenceItem], list[TrendSeries], TaskExecution]:
        label = ENGINE_SPECS[task.engine].label if task.engine in ENGINE_SPECS else task.engine
        started = time.perf_counter()
        if emit:
            emit({"type": "task_start", "task_id": task.id, "engine": task.engine, "surface": task.surface.value,
                  "label": label, "query": task.query, "region": task.region, "rationale": task.rationale})

        queries = list(dict.fromkeys([task.query, *task.fallback_queries]))
        window = task.params.get("date") if task.params else None
        attempts = 0
        last_error: SerpApiRequestError | None = None
        used = task.query

        for q in queries:
            attempts += 1
            used = q
            try:
                outcome = self.serpapi_service.run_query(task, q, window=window)
            except SerpApiRequestError as exc:
                last_error = exc
                attempts += max(0, exc.attempts - 1)
                if exc.kind in _FATAL_KINDS:
                    break
                continue
            last_error = None
            if outcome.items:
                ms = int((time.perf_counter() - started) * 1000)
                ex = TaskExecution(task.id, task.engine, task.surface.value, used, "completed", len(outcome.items), attempts, ms,
                                   task.region, rationale=task.rationale, label=label)
                if emit:
                    emit({"type": "task_done", "task_id": task.id, "engine": task.engine, "surface": task.surface.value,
                          "label": label, "status": "completed", "count": len(outcome.items), "query": used,
                          "attempts": attempts, "duration_ms": ms, "region": task.region})
                return outcome.items, outcome.series, ex
            # empty result: try the next, simpler query

        ms = int((time.perf_counter() - started) * 1000)
        if last_error is not None:
            ex = TaskExecution(task.id, task.engine, task.surface.value, used, "failed", 0, attempts, ms, task.region,
                               error=str(last_error), error_kind=last_error.kind, rationale=task.rationale, label=label)
            status = "failed"
        else:
            ex = TaskExecution(task.id, task.engine, task.surface.value, used, "empty", 0, attempts, ms, task.region,
                               rationale=task.rationale, label=label)
            status = "empty"
        if emit:
            emit({"type": "task_done", "task_id": task.id, "engine": task.engine, "surface": task.surface.value,
                  "label": label, "status": status, "count": 0, "query": used, "attempts": attempts, "duration_ms": ms,
                  "region": task.region, "error": ex.error, "error_kind": ex.error_kind})
        return [], [], ex

    def execute(self, tasks: list[SearchTask], emit: Emit | None = None) -> list[EvidenceItem]:
        """Run independent search surfaces concurrently; output order stays deterministic."""
        ordered = sorted(tasks, key=lambda t: t.priority, reverse=True)
        self.executions, self.items_by_task, self.series = [], {}, []
        results: dict[str, tuple[list[EvidenceItem], list[TrendSeries], TaskExecution]] = {}

        with ThreadPoolExecutor(max_workers=min(5, max(1, len(ordered)))) as pool:
            futures = [pool.submit(self._run_task, task, emit) for task in ordered]
            for future in as_completed(futures):
                items, series, execution = future.result()
                results[execution.task_id] = (items, series, execution)

        evidence: list[EvidenceItem] = []
        for task in ordered:
            items, series, execution = results[task.id]
            self.items_by_task[task.id] = items
            evidence.extend(items)
            self.series.extend(series)
            self.executions.append(execution)
        return evidence
