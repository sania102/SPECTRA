"""Small, dependency-free text utilities shared by planner and analysis."""
from __future__ import annotations

import re

STOPWORDS = frozenset("""
a an the and or but if then else so of to in on at by for from with without into onto over under about as is are was were be been being am
do does did done doing have has had having will would shall should can could may might must
i me my mine we our ours you your yours he she it its they them their theirs this that these those there here
what which who whom whose when where why how whether
not no yes than too very just also only even still yet already again more most much many some any each every all both few
up down out off per via vs versus
get gets got go goes going gone make makes made take takes took buy buys bought sell sells sold
today tomorrow tonight now currently current latest recent recently soon later
next last this week weeks month months year years day days time
actually really truly becoming become becomes became commercially mature
tell show give find know think say says said want need like
one two three first second 1 2 3
gm gms gram grams kg kgs oz ounce ounces litre liter litres liters tola tolas unit units piece pieces
""".split())

# Words that describe *what kind of thing we measure* rather than the subject itself.
GENERIC_TERMS = frozenset("""
price prices pricing cost costs rate rates value market markets trend trends trending adoption demand supply growth
outlook forecast prediction news update updates report reports industry sector stock stocks share shares
commercial commercially mature maturity importance important mainstream skill skills job jobs
accelerating faster slower infrastructure evolving evolve changing change mainstream rising falling increase decrease
""".split())

MEASURE_TERMS = frozenset("price prices cost costs rate rates adoption demand supply market growth stock stocks".split())

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9\-\+\.]*[a-z0-9]|[a-z0-9]", re.I)


def tokenize(text: str | None) -> list[str]:
    if not text:
        return []
    cleaned = text.lower().replace("’", "'")
    cleaned = re.sub(r"'s\b", "", cleaned)
    return [t.strip(".-") for t in _TOKEN_RE.findall(cleaned) if t.strip(".-")]


def stem(token: str) -> str:
    """Very light stemmer: good enough to match robot/robots/robotics, EV/EVs."""
    t = token.lower()
    for suffix in ("ics", "ing", "ies", "ed", "es", "s"):
        if len(t) > len(suffix) + 3 and t.endswith(suffix):
            t = t[: -len(suffix)]
            break
    return t[:6]


def content_terms(text: str | None) -> list[str]:
    """Tokens that carry meaning (stopwords and bare numbers removed), order preserved."""
    out: list[str] = []
    for tok in tokenize(text):
        if tok in STOPWORDS:
            continue
        if tok.isdigit():
            continue
        out.append(tok)
    return list(dict.fromkeys(out))


def stem_set(text: str | None) -> set[str]:
    return {stem(t) for t in content_terms(text)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
