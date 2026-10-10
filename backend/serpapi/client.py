"""Single boundary for all SerpApi access: retries, per-engine timeouts, caching."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any

import httpx

from backend.config.settings import get_settings
from backend.serpapi.engines import ENGINE_SPECS


class SerpApiConfigurationError(RuntimeError):
    """Raised when SPECTRA cannot call SerpApi because configuration is missing."""


class SerpApiRequestError(RuntimeError):
    """Raised when SerpApi rejects or cannot complete a request.

    ``kind`` is one of: timeout, rate_limit, auth, bad_request, empty, server, network, unknown.
    """

    def __init__(self, message: str, kind: str = "unknown", attempts: int = 1) -> None:
        super().__init__(message)
        self.kind = kind
        self.attempts = attempts


_EMPTY_MARKERS = ("hasn't returned any results", "no results", "returned any results")


class _TTLCache:
    def __init__(self, ttl: float) -> None:
        self.ttl = ttl
        self._data: dict[str, tuple[float, dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> dict[str, Any] | None:
        if self.ttl <= 0:
            return None
        with self._lock:
            hit = self._data.get(key)
            if not hit:
                return None
            if time.time() - hit[0] > self.ttl:
                self._data.pop(key, None)
                return None
            return hit[1]

    def set(self, key: str, value: dict[str, Any]) -> None:
        if self.ttl <= 0:
            return
        with self._lock:
            self._data[key] = (time.time(), value)


# Shared across requests so repeated demo questions do not burn SerpApi credits.
_CACHE: _TTLCache | None = None


def _cache(ttl: float) -> _TTLCache:
    global _CACHE
    if _CACHE is None or _CACHE.ttl != ttl:
        _CACHE = _TTLCache(ttl)
    return _CACHE


class SerpApiClient:
    BASE_URL = "https://serpapi.com/search.json"

    def __init__(self, api_key: str | None = None, timeout: float | None = None, max_retries: int | None = None) -> None:
        settings = get_settings()
        key = api_key or settings.serpapi_api_key
        if not key:
            raise SerpApiConfigurationError(
                "SERPAPI_API_KEY is not configured. Add it to backend/.env or the environment."
            )
        self.api_key = key
        self.timeout = timeout if timeout is not None else settings.serpapi_timeout_seconds
        self.max_retries = max_retries if max_retries is not None else settings.serpapi_max_retries
        self.cache = _cache(settings.serpapi_cache_ttl_seconds)

    def _timeout_for(self, engine: str) -> float:
        spec = ENGINE_SPECS.get(engine)
        override = spec.timeout if spec else None
        return max(self.timeout, override) if override else self.timeout

    @staticmethod
    def _cache_key(engine: str, params: dict[str, Any]) -> str:
        blob = json.dumps({"e": engine, "p": params}, sort_keys=True, default=str)
        return hashlib.sha1(blob.encode()).hexdigest()

    def search(self, *, engine: str, params: dict[str, Any]) -> dict[str, Any]:
        request_params = dict(params)
        request_params["engine"] = engine

        key = self._cache_key(engine, request_params)
        cached = self.cache.get(key)
        if cached is not None:
            return cached

        request_params["api_key"] = self.api_key
        timeout = self._timeout_for(engine)
        attempts = self.max_retries + 1
        last: SerpApiRequestError | None = None

        for attempt in range(attempts):
            try:
                response = httpx.get(self.BASE_URL, params=request_params, timeout=timeout)
                if response.status_code == 429:
                    raise SerpApiRequestError(f"SerpApi rate limit / out of credits for '{engine}'.", "rate_limit")
                if response.status_code in (401, 403):
                    raise SerpApiRequestError("SerpApi rejected the API key (check SERPAPI_API_KEY).", "auth")
                if response.status_code >= 500:
                    raise SerpApiRequestError(f"SerpApi server error {response.status_code} for '{engine}'.", "server")
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise SerpApiRequestError(f"SerpApi returned non-JSON for '{engine}'.", "server") from exc
                if not isinstance(payload, dict):
                    raise SerpApiRequestError(f"SerpApi returned an unexpected payload for '{engine}'.", "server")

                error_text = str(payload.get("error") or "")
                if error_text:
                    lowered = error_text.lower()
                    if any(marker in lowered for marker in _EMPTY_MARKERS):
                        # Not a failure: the engine simply had nothing for that query.
                        payload.setdefault("_spectra_empty", True)
                        self.cache.set(key, payload)
                        return payload
                    kind = "bad_request" if response.status_code == 400 else "unknown"
                    if "timed out" in lowered or "timeout" in lowered:
                        kind = "timeout"
                    raise SerpApiRequestError(f"SerpApi: {error_text}", kind)
                if response.status_code >= 400:
                    raise SerpApiRequestError(
                        f"SerpApi HTTP {response.status_code} for '{engine}': {response.text[:300]}", "bad_request")

                self.cache.set(key, payload)
                return payload
            except SerpApiRequestError as exc:
                exc.attempts = attempt + 1
                last = exc
                # Retry only transient problems.
                if exc.kind in {"timeout", "server", "network"} and attempt < attempts - 1:
                    time.sleep(0.6 * (2 ** attempt))
                    continue
                raise
            except httpx.TimeoutException as exc:
                last = SerpApiRequestError(
                    f"SerpApi request for '{engine}' timed out after {timeout:.0f}s.", "timeout", attempt + 1)
                if attempt < attempts - 1:
                    time.sleep(0.6 * (2 ** attempt))
                    continue
                raise last from exc
            except httpx.HTTPError as exc:
                last = SerpApiRequestError(f"Network error calling SerpApi for '{engine}': {exc}", "network", attempt + 1)
                if attempt < attempts - 1:
                    time.sleep(0.6 * (2 ** attempt))
                    continue
                raise last from exc

        raise last or SerpApiRequestError(f"SerpApi request failed for '{engine}'.")
