from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routes.investigation import router as investigation_router
from backend.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger("spectra")

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="SPECTRA — Information Blind-Spot Intelligence API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST","DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex[:16]}"
    started = time.perf_counter()
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled request failure request_id=%s path=%s", request_id, request.url.path)
        raise
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = str(duration_ms)
    logger.info("request_id=%s method=%s path=%s status=%s duration_ms=%s", request_id, request.method, request.url.path, response.status_code, duration_ms)
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "detail": "The investigation request is invalid.",
            "request_id": getattr(request.state, "request_id", None),
            "fields": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled application error request_id=%s", getattr(request.state, "request_id", None))
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "detail": "SPECTRA could not complete the request.",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


app.include_router(investigation_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "spectra-backend", "version": app.version}


@app.get("/api/status", tags=["system"])
def api_status() -> dict[str, object]:
    current = get_settings()
    return {
        "service": current.app_name,
        "environment": current.app_env,
        "version": app.version,
        "serpapi_configured": bool(current.serpapi_api_key),
        "llm_configured": bool(current.llm_api_key),
        "llm_model": current.llm_model,
    }


@app.get("/api/diagnostics/llm", tags=["system"])
def diagnose_llm() -> dict[str, object]:
    """Makes one tiny LLM call and returns the provider's real error message (key redacted)."""
    from backend.api.routes.investigation import build_llm_client
    return build_llm_client().ping()


@app.get("/api/readiness", tags=["system"])
def readiness() -> JSONResponse:
    current = get_settings()
    serpapi_ready = bool(current.serpapi_api_key)
    ready = serpapi_ready
    payload = {
        "status": "ready" if ready else "not_ready",
        "checks": {"serpapi": serpapi_ready, "llm_optional": bool(current.llm_api_key)},
        "version": app.version,
    }
    return JSONResponse(status_code=200 if ready else 503, content=payload)
