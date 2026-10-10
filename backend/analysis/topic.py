"""Deterministic question understanding: topic, anchors, forecast and geography."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.analysis.text import GENERIC_TERMS, MEASURE_TERMS, content_terms, stem

# Country / region name -> (display name, SerpApi country code)
REGIONS: dict[str, tuple[str, str]] = {
    "india": ("India", "in"), "indian": ("India", "in"), "indians": ("India", "in"), "inr": ("India", "in"), "rupee": ("India", "in"), "rupees": ("India", "in"), "₹": ("India", "in"),
    "mumbai": ("India", "in"), "delhi": ("India", "in"), "bengaluru": ("India", "in"), "bangalore": ("India", "in"),
    "usa": ("United States", "us"), "us": ("United States", "us"), "u.s.": ("United States", "us"), "america": ("United States", "us"),
    "american": ("United States", "us"), "united states": ("United States", "us"),
    "uk": ("United Kingdom", "gb"), "britain": ("United Kingdom", "gb"), "british": ("United Kingdom", "gb"), "united kingdom": ("United Kingdom", "gb"),
    "europe": ("European Union", "de"), "european": ("European Union", "de"), "eu": ("European Union", "de"), "germany": ("Germany", "de"), "german": ("Germany", "de"),
    "france": ("France", "fr"), "french": ("France", "fr"),
    "japan": ("Japan", "jp"), "japanese": ("Japan", "jp"),
    "china": ("China", "cn"), "chinese": ("China", "cn"),
    "korea": ("South Korea", "kr"), "korean": ("South Korea", "kr"),
    "brazil": ("Brazil", "br"), "canada": ("Canada", "ca"), "australia": ("Australia", "au"),
    "singapore": ("Singapore", "sg"), "uae": ("United Arab Emirates", "ae"), "dubai": ("United Arab Emirates", "ae"),
}

FORECAST_PATTERNS = (
    r"\bwill\b", r"\bgoing to\b", r"\bgo up\b", r"\bgo down\b", r"\bnext (week|month|quarter|year)\b",
    r"\bby (next|the end|2027|2028|2030)\b", r"\bforecast\b", r"\bpredict", r"\bin the future\b", r"\bexpected to\b",
    r"\bshould i (buy|invest|sell)\b", r"\bworth (buying|investing)\b", r"\bbull(ish)?\b", r"\bbear(ish)?\b",
)

PRICE_WORDS = ("price", "prices", "cost", "costs", "rate", "rates", "worth", "cheaper", "expensive", "gold", "silver", "bitcoin",
               "crypto", "stock", "shares", "petrol", "diesel", "oil")

COMMODITIES = {"gold", "silver", "platinum", "copper", "oil", "crude", "petrol", "diesel", "bitcoin", "ethereum", "gas", "lithium"}


@dataclass
class QuestionProfile:
    topic: str
    anchors: list[str]
    key_terms: list[str]
    is_forecast: bool
    is_price_question: bool
    regions: list[tuple[str, str]] = field(default_factory=list)  # (name, gl)
    comparison: bool = False


def detect_regions(question: str) -> list[tuple[str, str]]:
    q = " " + question.lower() + " "
    found: dict[str, str] = {}
    # multi-word first
    for key, (name, gl) in sorted(REGIONS.items(), key=lambda kv: -len(kv[0])):
        if key == "us":
            if re.search(r"\b(the )?us\b(?! (to|and me))", q) and re.search(r"\b(in|from|across|vs|versus|and|with)\s+(the\s+)?us\b|\bus\s+(market|economy|policy|regulation)", q):
                found.setdefault(name, gl)
            continue
        if re.search(rf"(?<![a-z]){re.escape(key)}(?![a-z])", q):
            found.setdefault(name, gl)
    return list(found.items())


def build_profile(question: str) -> QuestionProfile:
    q = re.sub(r"\s+", " ", question.strip())
    ql = q.lower()

    is_forecast = any(re.search(p, ql) for p in FORECAST_PATTERNS)
    is_price = any(re.search(rf"\b{w}\b", ql) for w in PRICE_WORDS)
    regions = detect_regions(q)
    comparison = bool(re.search(r"\b(vs|versus|compared? (with|to)|differ|difference|between)\b", ql)) and len(regions) >= 2

    region_words = {k for k in REGIONS}
    terms = [t for t in content_terms(q) if t not in region_words]

    # Anchors: the specific subject words. Generic measurement words (price, market…) are not anchors.
    anchors = [t for t in terms if t not in GENERIC_TERMS and len(t) >= 2]
    if not anchors:
        anchors = terms[:2]
    anchors = anchors[:4]

    # Topic: anchors plus the single most informative generic word (usually "price"), in original order.
    generic = [t for t in terms if t in MEASURE_TERMS]
    keep: list[str] = []
    for t in terms:
        if t in anchors or (generic and t == generic[0]):
            keep.append(t)
    if is_price and "price" not in keep and not any(w in keep for w in ("cost", "rate", "rates")) and any(a in COMMODITIES for a in anchors):
        keep.append("price")
    topic = " ".join(keep[:5]) or q.rstrip("?.!")

    key_terms = list(dict.fromkeys([*anchors, *[t for t in terms if t not in anchors]]))[:8]
    return QuestionProfile(topic=topic, anchors=anchors, key_terms=key_terms, is_forecast=is_forecast,
                           is_price_question=is_price, regions=regions, comparison=comparison)


def anchor_stems(anchors: list[str]) -> set[str]:
    return {stem(a) for a in anchors}
