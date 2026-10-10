"""OpenAI-compatible chat adapter with robust JSON handling and diagnosable errors.

Why this replaced the old Responses-API/strict-schema call: strict ``json_schema`` mode
rejects Pydantic's default schema (it requires ``additionalProperties: false`` and every
property listed in ``required``, and forbids ``default``/``minLength`` keywords). That
produced a generic ``BadRequestError`` for every call. This client asks for plain JSON
(``json_object`` mode, falling back to prompt-only), validates it with Pydantic itself,
tries fallback models, and exposes the provider's real error message.
"""
from __future__ import annotations

import json
import re
from typing import Any, TypeVar

from pydantic import BaseModel

from backend.llm.models import EXAMPLES

T = TypeVar("T", bound=BaseModel)

_KEY_RE = re.compile(r"(sk-[A-Za-z0-9_\-]{8,}|gsk_[A-Za-z0-9]{8,}|AIza[A-Za-z0-9_\-]{10,})")


class LLMError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, code: str | None = None, error_type: str = "LLMError") -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.error_type = error_type


def describe_error(exc: Exception) -> dict[str, Any]:
    """Extract the provider's actual message (status, code, text) with secrets redacted."""
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    body = getattr(exc, "body", None)
    code = param = None
    message = getattr(exc, "message", None) or str(exc)
    if isinstance(body, dict):
        inner = body.get("error", body)
        if isinstance(inner, dict):
            message = inner.get("message") or message
            code = inner.get("code")
            param = inner.get("param")
    message = _KEY_RE.sub("[REDACTED_KEY]", str(message)).replace("\n", " ").strip()
    return {"type": type(exc).__name__, "status": status, "code": code, "param": param, "message": message[:600]}


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise LLMError("Model did not return JSON.", error_type="InvalidJSON")
        value = json.loads(text[start:end + 1])
    if not isinstance(value, dict):
        raise LLMError("Model returned JSON that is not an object.", error_type="InvalidJSON")
    return value


class LLMClient:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", *, base_url: str = "",
                 fallback_models: list[str] | None = None, timeout: float = 45.0) -> None:
        self.api_key = api_key
        self.models = list(dict.fromkeys([model, *(fallback_models or [])]))
        self.active_model: str | None = None
        self.last_error: dict[str, Any] | None = None
        self._client: Any = None
        if api_key:
            try:
                from openai import OpenAI
                kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout, "max_retries": 1}
                if base_url:
                    kwargs["base_url"] = base_url
                self._client = OpenAI(**kwargs)
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError("The openai package is required when LLM_API_KEY is configured.") from exc

    @property
    def enabled(self) -> bool:
        return self._client is not None

    @property
    def model(self) -> str:
        return self.active_model or self.models[0]

    def _chat(self, model: str, messages: list[dict[str, str]], json_mode: bool) -> str:
        kwargs: dict[str, Any] = {"model": model, "messages": messages}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def complete_json(self, *, instructions: str, input_text: str, example: str) -> dict[str, Any]:
        if not self.enabled:
            raise LLMError("LLM is not configured.", error_type="NotConfigured")
        system = (f"{instructions}\n\nRespond with a single valid JSON object only — no prose, no markdown. "
                  f"It must follow this shape exactly:\n{example}")
        messages = [{"role": "system", "content": system}, {"role": "user", "content": f"Input (JSON/text):\n{input_text}"}]

        errors: list[dict[str, Any]] = []
        for model in ([self.active_model] if self.active_model else self.models):
            for json_mode in (True, False):
                try:
                    raw = self._chat(model, messages, json_mode)
                    parsed = _extract_json(raw)
                    self.active_model = model
                    self.last_error = None
                    return parsed
                except LLMError as exc:
                    errors.append({"type": exc.error_type, "message": str(exc), "model": model})
                    continue  # retry without json_mode, then next model
                except Exception as exc:  # provider errors
                    info = describe_error(exc) | {"model": model}
                    errors.append(info)
                    text = info["message"].lower()
                    status = info.get("status")
                    if status in (401, 403):
                        break  # bad key: no model will work
                    if json_mode and ("response_format" in text or "json" in text) and status == 400:
                        continue  # same model without response_format
                    break  # model-level problem (404/400 invalid model, etc.): next model
        self.last_error = errors[-1] if errors else None
        detail = errors[-1] if errors else {"message": "unknown"}
        raise LLMError(
            f"{detail.get('type', 'Error')} (status {detail.get('status')}, model {detail.get('model')}): {detail.get('message')}",
            status=detail.get("status"), code=detail.get("code"), error_type=str(detail.get("type", "LLMError")),
        )

    def structured(self, *, instructions: str, input_text: str, schema: type[T], name: str) -> T:
        example = EXAMPLES.get(schema.__name__, "{}")
        data = self.complete_json(instructions=instructions, input_text=input_text, example=example)
        try:
            return schema.model_validate(data)
        except Exception as exc:
            raise LLMError(f"Model JSON did not match {schema.__name__}: {str(exc)[:300]}", error_type="SchemaMismatch") from exc

    def ping(self) -> dict[str, Any]:
        """Tiny call used by /api/diagnostics/llm so the real provider error is visible."""
        if not self.enabled:
            return {"ok": False, "configured": False, "message": "LLM_API_KEY is not set."}
        try:
            data = self.complete_json(instructions="Return the JSON object {\"ok\": true}.", input_text="ping", example='{"ok": true}')
            return {"ok": bool(data.get("ok", True)), "configured": True, "model": self.active_model, "tried": self.models}
        except LLMError as exc:
            return {"ok": False, "configured": True, "tried": self.models, "status": exc.status, "code": exc.code,
                    "error_type": exc.error_type, "message": str(exc)[:600]}
