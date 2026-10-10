"""Deterministic direction ("up" / "down") detection for claims.

Used when no LLM is available (or as a cross-check). It is intentionally simple and
transparent: a lexicon of rise/fall words, light negation handling, headline weighting.
"""
from __future__ import annotations

import re

from backend.analysis.text import tokenize

UP = {
    "rise", "rises", "rising", "rose", "risen", "surge", "surges", "surged", "surging", "rally", "rallies", "rallied",
    "jump", "jumps", "jumped", "gain", "gains", "gained", "soar", "soars", "soared", "soaring", "climb", "climbs", "climbed",
    "hike", "hikes", "hiked", "higher", "increase", "increases", "increased", "increasing", "boost", "boosts", "boosted",
    "spike", "spikes", "spiked", "bullish", "upside", "upswing", "upward", "record-high", "outperform", "accelerate",
    "accelerates", "accelerating", "growth", "growing", "grows", "grew", "expands", "expanding", "booming", "boom", "strengthens",
    "up", "advance", "advances", "advanced", "rebound", "rebounds", "recovers", "recovery",
}
DOWN = {
    "fall", "falls", "fell", "falling", "fallen", "drop", "drops", "dropped", "dropping", "slump", "slumps", "slumped",
    "decline", "declines", "declined", "declining", "plunge", "plunges", "plunged", "tumble", "tumbles", "tumbled", "slide",
    "slides", "slid", "bearish", "lower", "decrease", "decreases", "decreased", "dip", "dips", "dipped", "crash", "crashes",
    "crashed", "slip", "slips", "slipped", "retreat", "retreats", "weaken", "weakens", "weakened", "downside", "downturn",
    "downward", "correction", "sell-off", "selloff", "slowdown", "slows", "slowing", "stall", "stalls", "stalled", "shrink",
    "shrinks", "shrinking", "delay", "delays", "delayed", "cuts", "cut", "loses", "lost", "losses", "down", "struggle", "struggles",
    "struggling", "cools", "cooling", "hurdle", "hurdles",
}
NEGATORS = {"not", "no", "never", "without", "unlikely", "fails", "fail", "won't", "wont", "isn't", "isnt", "doesn't", "doesnt", "hardly"}


def _score(text: str) -> tuple[float, float]:
    tokens = tokenize(text)
    up = down = 0.0
    for i, tok in enumerate(tokens):
        window = tokens[max(0, i - 3):i]
        negated = any(w in NEGATORS for w in window)
        if tok in UP:
            if negated:
                down += 0.8
            else:
                up += 1.0
        elif tok in DOWN:
            if negated:
                up += 0.8
            else:
                down += 1.0
    return up, down


def detect_stance(title: str | None, snippet: str | None = None) -> str:
    """Return 'up', 'down', 'mixed' or 'neutral' for a piece of evidence."""
    tu, td = _score(title or "")
    su, sd = _score(snippet or "")
    up, down = 2 * tu + su, 2 * td + sd  # headlines weigh double
    if up == 0 and down == 0:
        return "neutral"
    if up >= 2 * down and up >= 1.5:
        return "up"
    if down >= 2 * up and down >= 1.5:
        return "down"
    if up >= 1.5 and down >= 1.5:
        return "mixed"
    return "neutral"


STANCE_LABELS = {"up": "points upward / strengthening", "down": "points downward / weakening", "mixed": "mixed", "neutral": "neutral"}
