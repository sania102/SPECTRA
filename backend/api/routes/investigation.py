from __future__ import annotations

import json
import logging
import queue
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from backend.agent.investigator import Investigator
from backend.agent.router import InvestigationRouter
from backend.config.settings import get_settings
from backend.demo import build_demo_result
from backend.llm.client import LLMClient
from backend.llm.service import LLMService
from backend.models.requests import InvestigationRequest
from backend.models.responses import InvestigationResult
from backend.serpapi.client import SerpApiClient, SerpApiConfigurationError, SerpApiRequestError
from backend.serpapi.service import SerpApiService

logger = logging.getLogger("spectra")
router = APIRouter(prefix="/investigations", tags=["investigations"])


def build_llm_client() -> LLMClient:
    s = get_settings()
    return LLMClient(s.llm_api_key, s.llm_model, base_url=s.llm_base_url,
                     fallback_models=[m for m in s.llm_model_chain[1:]], timeout=s.llm_timeout_seconds)


def _build_investigator() -> Investigator:
    return Investigator(InvestigationRouter(SerpApiService(SerpApiClient())), LLMService(build_llm_client()))


def _runs_dir() -> Path:
    path = Path(get_settings().runs_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _save_run(result: InvestigationResult) -> None:
    try:
        (_runs_dir() / f"{result.investigation_id}.json").write_text(result.model_dump_json(), encoding="utf-8")
    except Exception:  # saving is a convenience; never break an investigation over it
        logger.exception("Could not save investigation run")


def _run(request: InvestigationRequest, emit=None) -> InvestigationResult:
    investigator = _build_investigator()
    result = investigator.investigate(request, emit)
    result.metadata["task_executions"] = [
        {"task_id": e.task_id, "engine": e.engine, "status": e.status, "evidence_count": e.evidence_count,
         "attempts": e.attempts, "query": e.query, "error": e.error, "error_kind": e.error_kind}
        for e in investigator.router.executions
    ]
    result.metadata["completed_tasks"] = sum(e.status == "completed" for e in investigator.router.executions)
    result.metadata["failed_tasks"] = sum(e.status == "failed" for e in investigator.router.executions)
    _save_run(result)
    return result


@router.post("", response_model=InvestigationResult, status_code=status.HTTP_200_OK)
def create_investigation(request: InvestigationRequest, http_request: Request) -> InvestigationResult:
    """Run a complete SPECTRA investigation (blocking)."""
    try:
        result = _run(request)
        result.metadata["request_id"] = getattr(http_request.state, "request_id", None)
        return result
    except SerpApiConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SerpApiRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/stream")
def stream_investigation(request: InvestigationRequest) -> StreamingResponse:
    """Server-Sent Events: live progress while SerpApi searches run, then the final result."""
    try:
        _build_investigator()  # fail fast (as JSON) if SERPAPI_API_KEY is missing
    except SerpApiConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    events: queue.Queue = queue.Queue()

    def worker() -> None:
        try:
            result = _run(request, emit=events.put)
            events.put({"type": "result", "result": json.loads(result.model_dump_json())})
        except Exception as exc:  # noqa: BLE001
            logger.exception("Streaming investigation failed")
            events.put({"type": "error", "message": str(exc)[:400]})
        finally:
            events.put(None)

    threading.Thread(target=worker, daemon=True).start()

    def generate():
        while True:
            try:
                event = events.get(timeout=15)
            except queue.Empty:
                yield ": keep-alive\n\n"
                continue
            if event is None:
                break
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/demo", response_model=InvestigationResult, status_code=status.HTTP_200_OK)
def demo_investigation(scenario: str = "humanoid") -> InvestigationResult:
    """Illustrative fixture (clearly labelled as sample data); no external calls."""
    return build_demo_result(scenario)


@router.get("/runs")
def list_runs() -> list[dict]:
    """Previously completed live investigations (replayable without spending SerpApi credits)."""
    out = []
    for path in sorted(_runs_dir().glob("inv_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            out.append({"id": data["investigation_id"], "question": data["plan"]["question"],
                        "generated_at": data["generated_at"], "blind_spots": len(data.get("blind_spots", []))})
        except Exception:
            continue
    return out


@router.get("/runs/{run_id}", response_model=InvestigationResult)
def get_run(run_id: str) -> InvestigationResult:
    if not run_id.startswith("inv_") or not run_id.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid run id.")
    path = _runs_dir() / f"{run_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Run not found.")
    return InvestigationResult.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _valid_run_id(run_id: str) -> bool:
    return run_id.startswith("inv_") and run_id.replace("_", "").isalnum()


@router.delete("/runs/{run_id}")
def delete_run(run_id: str) -> dict:
    """Delete one saved investigation (only files inside the runs directory can be touched)."""
    if not _valid_run_id(run_id):
        raise HTTPException(status_code=400, detail="Invalid run id.")
    path = _runs_dir() / f"{run_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Run not found.")
    path.unlink()
    return {"deleted": run_id}


@router.delete("/runs")
def clear_runs() -> dict:
    """Delete every saved investigation."""
    count = 0
    for path in _runs_dir().glob("inv_*.json"):
        try:
            path.unlink()
            count += 1
        except OSError:
            continue
    return {"deleted": count}
