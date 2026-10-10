"""Run one question in Quick, Standard and Deep (live SerpApi) and print a side-by-side audit.

Usage:  python scripts/compare_modes.py "Will silver prices rise next month?"
Costs roughly 8 + 20 + 30 SerpApi credits on a cold cache (identical queries are cached for the TTL).
Writes docs/mode-comparison.md so the differences are documented with real data.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.models.requests import InvestigationDepth, InvestigationRequest  # noqa: E402
from backend.services.investigation import create_investigator  # noqa: E402

question = " ".join(sys.argv[1:]) or "Will silver prices rise next month?"
rows = []
for depth in InvestigationDepth:
    r = create_investigator().investigate(InvestigationRequest(question=question, depth=depth))
    q, d, v = r.data_quality, r.direction, r.verdict
    trend = r.trend_series[0] if r.trend_series else None
    rows.append({
        "mode": depth.value, "surfaces": f"{q.surfaces_completed}/{q.surfaces_planned} (empty {q.surfaces_empty}, failed {q.surfaces_failed})",
        "tasks": f"{q.tasks_completed}/{q.tasks_planned}", "kept": f"{q.kept_results}/{q.raw_results}", "sources": q.unique_sources,
        "trend": f"{trend.window_label} · {trend.points} pts · 30d {trend.change_pct}% ({trend.direction})" if trend else "none",
        "lean": f"{d.lean} ({d.sources_up}↑ / {d.sources_down}↓ of {d.unique_sources} sources)" if d else "n/a",
        "regional": ("agree" if r.regional and r.regional.agrees else "disagree" if r.regional else "n/a"),
        "blind_spots": len(r.blind_spots), "reconciled": q.reconciled,
    })
cols = list(rows[0])
md = [f"# Mode comparison\n\nQuestion: *{question}*\n", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
md += ["| " + " | ".join(str(r[c]) for c in cols) + " |" for r in rows]
out = "\n".join(md)
print(out)
Path(__file__).resolve().parents[1].joinpath("docs/mode-comparison.md").write_text(out + "\n", encoding="utf-8")
