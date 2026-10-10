"""Common parser protocol for converting SerpApi payloads into SPECTRA evidence."""

from __future__ import annotations

from typing import Any, Protocol

from backend.models.responses import EvidenceItem


class EngineParser(Protocol):
    def parse(self, payload: dict[str, Any], *, query: str, engine: str) -> list[EvidenceItem]: ...


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def first_text(item: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = clean_text(item.get(key))
        if value:
            return value
    return None
