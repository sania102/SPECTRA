"""Entity extraction and normalization (OpenAI == OpenAI Inc. == OpenAI company)."""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable

from backend.models.responses import EvidenceItem

_CORP_SUFFIX = re.compile(
    r"\b(inc|incorporated|corp|corporation|co|company|ltd|limited|llc|llp|plc|gmbh|ag|sa|nv|pvt|private|motors|holdings|group|labs)\b\.?",
    re.IGNORECASE,
)
# Small explicit alias table for well-known renames; everything else is rule-based.
ALIASES = {
    "tesla motors": "tesla", "alphabet": "google", "google llc": "google", "meta platforms": "meta", "facebook": "meta",
    "x corp": "x", "twitter": "x", "nvidia corporation": "nvidia", "boston dynamics inc": "boston dynamics",
}
_CAP_PHRASE = re.compile(r"\b([A-Z][A-Za-z0-9&\-]{1,}(?:\s+(?:of\s+|&\s+)?[A-Z][A-Za-z0-9&\-]{1,}){0,2}|[A-Z]{2,6})\b")
_NOT_ENTITIES = frozenset("""
The This That These Those How What Why When Where Who Which Is Are Will Can Could Should Would And But For With From Into
New Latest Today Yesterday Report Reports Price Prices Market Markets News Update Updates Video Watch Read More Here Best Top
Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec January February March April June July August September October November December
Monday Tuesday Wednesday Thursday Friday Saturday Sunday Why Does Did Has Have Had Was Were After Before Over Under Amid
Google Search News Trends Scholar Jobs Shopping Patents YouTube
""".split())


def canonical_entity(value: str | None) -> str | None:
    """Casefolded, suffix-stripped key used to decide that two names are the same entity."""
    if not value:
        return None
    text = re.sub(r"\s+", " ", value).strip(" .,:;|-_()[]\"'")
    if not text:
        return None
    low = text.casefold()
    low = ALIASES.get(low, low)
    stripped = _CORP_SUFFIX.sub(" ", low)
    stripped = re.sub(r"[^\w\s&\-]", " ", stripped)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    stripped = ALIASES.get(stripped, stripped)
    return stripped or low


def extract_entities(text: str | None, exclude: set[str] | None = None) -> list[str]:
    """Pull capitalised proper-noun phrases out of a headline or snippet."""
    if not text:
        return []
    exclude = {e.casefold() for e in (exclude or set())}
    found: list[str] = []
    for match in _CAP_PHRASE.finditer(text):
        phrase = match.group(1).strip()
        words = phrase.split()
        while words and words[0] in _NOT_ENTITIES:
            words = words[1:]
        while words and words[-1] in _NOT_ENTITIES:
            words = words[:-1]
        if not words:
            continue
        phrase = " ".join(words)
        if len(phrase) < 3 or phrase.casefold() in exclude or phrase in _NOT_ENTITIES:
            continue
        found.append(phrase)
    return list(dict.fromkeys(found))


@dataclass
class EntityGroup:
    canonical: str
    display: str
    aliases: set[str] = field(default_factory=set)
    evidence_ids: list[str] = field(default_factory=list)
    source_types: set[str] = field(default_factory=set)


def group_entities(evidence: Iterable[EvidenceItem], exclude: set[str] | None = None, min_mentions: int = 2) -> list[EntityGroup]:
    groups: dict[str, EntityGroup] = {}
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for item in evidence:
        names: list[str] = []
        if item.entity:
            names.append(item.entity)
        names.extend(extract_entities(item.title, exclude))
        for name in dict.fromkeys(names):
            key = canonical_entity(name)
            if not key or (exclude and key in {e.casefold() for e in exclude}):
                continue
            g = groups.setdefault(key, EntityGroup(canonical=key, display=name))
            g.aliases.add(name)
            counts[key][name] += 1
            if item.id not in g.evidence_ids:
                g.evidence_ids.append(item.id)
            g.source_types.add(item.source_type or item.engine)
    for key, g in groups.items():
        g.display = max(counts[key], key=lambda n: (counts[key][n], len(n)))
    out = [g for g in groups.values() if len(g.evidence_ids) >= min_mentions]
    return sorted(out, key=lambda g: len(g.evidence_ids), reverse=True)[:12]
