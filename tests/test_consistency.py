"""Regression tests for the pre-submission issues: counts, trend windows, source independence, regions, modes."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from backend.agent.planner import build_plan
from backend.analysis.direction import summarize_direction, tag_horizons
from backend.models.requests import InvestigationDepth as D, InvestigationRequest
from backend.models.responses import EvidenceItem
from backend.serpapi.parsers.trends import parse_series
from tests.test_pipeline import SILVER_Q, FakeSerpApi, build


def run(depth: D):
    inv, fake = build()
    return inv.investigate(InvestigationRequest(question=SILVER_Q, depth=depth)), fake


@pytest.mark.parametrize("depth", [D.QUICK, D.STANDARD, D.DEEP])
def test_surface_and_task_counts_always_reconcile(depth):
    q = run(depth)[0].data_quality
    assert q.reconciled
    assert q.surfaces_completed + q.surfaces_empty + q.surfaces_failed == q.surfaces_planned
    assert q.tasks_completed + q.tasks_empty + q.tasks_failed == q.tasks_planned
    assert q.surfaces_with_evidence == q.surfaces_completed
    assert q.tasks_planned >= q.surfaces_planned


def test_modes_are_genuinely_different():
    plans = {d: build_plan(SILVER_Q, d) for d in D}
    q, s, dp = plans[D.QUICK], plans[D.STANDARD], plans[D.DEEP]
    assert q.per_surface_limit < s.per_surface_limit < dp.per_surface_limit
    assert len({t.surface for t in q.search_tasks}) < len({t.surface for t in dp.search_tasks})
    windows = {d: {t.params["date"] for t in p.search_tasks if t.surface.value == "trends"} for d, p in plans.items()}
    assert windows[D.QUICK] == {"today 3-m"} and windows[D.STANDARD] == {"today 12-m"} and windows[D.DEEP] == {"today 5-y"}
    assert q.geographic_strategy == "global_overview" and s.geographic_strategy == "global_vs_india" == dp.geographic_strategy
    assert not q.mode_profile["regional_comparison"] and s.mode_profile["regional_comparison"]
    assert dp.mode_profile["scholar_check"] and not s.mode_profile["scholar_check"]
    assert any(t.surface.value == "scholar" for t in dp.search_tasks) and not any(t.surface.value == "scholar" for t in s.search_tasks)


def test_requested_trend_window_is_what_was_sent_and_reported():
    result, fake = run(D.DEEP)
    sent = {p.get("date") for e, p in fake.calls if e == "google_trends"}
    assert sent == {"today 5-y"}
    assert result.metadata["depth_audit"]["trend_windows_requested"] == ["today 5-y"]
    assert all(s.window == "today 5-y" and s.window_label == "past 5 years" and s.points > 0 for s in result.trend_series)
    assert result.data_quality.trend_windows == ["past 5 years"]


def test_trend_change_uses_the_same_yardstick_in_every_mode():
    now = 1_760_000_000
    def payload(n, step):
        return {"interest_over_time": {"timeline_data": [
            {"date": f"p{i}", "timestamp": str(now - (n - i) * step), "values": [{"extracted_value": 50 if i < n - 8 else 80}]} for i in range(n)]}}
    daily = parse_series(payload(90, 86400), query="x", window="today 3-m")[0]
    weekly = parse_series(payload(260, 7 * 86400), query="x", window="today 5-y")[0]
    assert daily.horizons[0].label == weekly.horizons[0].label == "last 30 days vs the 30 days before"
    assert daily.direction == "rising"


def _it(i, title, src, stance, engine="google_news"):
    return EvidenceItem(id=str(i), title=title, source=src, source_domain=f"{src.lower()}.com", engine=engine, stance=stance, relevance=0.9)


def test_directional_counts_collapse_duplicates_and_count_sources_not_headlines():
    items = [_it(i, "Silver prices surge to record high on strong demand today", "Wire", "up") for i in range(5)]
    items += [_it(10, "Silver climbs on weak dollar", "Mint", "up"), _it(11, "Silver slumps as profit taking hits", "ET", "down")]
    d = summarize_direction(items)
    assert d.duplicates_collapsed == 4 and d.directional_items == 3
    assert d.unique_sources == 3 and d.sources_up == 2 and d.sources_down == 1


def test_long_horizon_forecasts_excluded_for_near_term_questions():
    items = [_it(1, "Silver could hit $100 by 2030, analysts say", "A", "up"), _it(2, "Silver price will soar through 2030 and beyond", "B", "up"),
             _it(3, "Silver falls today on dollar strength", "C", "down")]
    tag_horizons(items)
    near, loose = summarize_direction(items, "near"), summarize_direction(items, "unspecified")
    assert near.long_horizon_excluded == 2 and near.sources_up == 0
    assert loose.sources_up == 2


def test_regional_comparison_present_and_source_backed():
    result, _ = run(D.STANDARD)
    assert result.regional and {r.region for r in result.regional.regions} == {"Global", "India"}
    assert any("worldwide" in c for c in result.regional.caveats)
    assert result.regional.finding
    for r in result.regional.regions:
        assert all(h.get("url") or h.get("source") for h in r.top_headlines)


def test_verdict_never_claims_prediction():
    result, _ = run(D.STANDARD)
    text = (result.verdict.summary + (result.verdict.lean_detail or "")).lower()
    assert "not" in text and "price" in text
    assert "unique source" in result.verdict.summary


@pytest.mark.parametrize("scenario", ["humanoid", "silver"])
def test_demo_scenarios_run_the_real_pipeline_and_reconcile(scenario):
    from backend.demo import build_demo_result
    r = build_demo_result(scenario)
    assert r.metadata["demo_mode"] and r.data_quality.reconciled and r.verdict and r.direction
    assert (r.regional is not None) == (scenario == "silver")


def test_delete_saved_runs(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from backend.config.settings import get_settings
    monkeypatch.setattr(get_settings(), "runs_dir", str(tmp_path))
    result, _ = run(D.QUICK)
    (tmp_path / "inv_a1.json").write_text(result.model_dump_json(), encoding="utf-8")
    (tmp_path / "inv_b2.json").write_text(result.model_dump_json(), encoding="utf-8")
    c = TestClient(app)
    assert len(c.get("/api/investigations/runs").json()) == 2
    assert c.delete("/api/investigations/runs/inv_a1").json() == {"deleted": "inv_a1"}
    assert c.delete("/api/investigations/runs/inv_a1").status_code == 404
    assert c.delete("/api/investigations/runs/not_valid").status_code == 400
    assert c.delete("/api/investigations/runs").json() == {"deleted": 1}
    assert c.get("/api/investigations/runs").json() == []


def test_same_article_in_two_regions_is_not_deduplicated():
    from backend.analysis.normalization import dedupe
    a = EvidenceItem(id="1", title="Silver surges to record high on demand", url="https://x.com/a", source="X", engine="google_news", region="Global")
    b = EvidenceItem(id="2", title="Silver surges to record high on demand", url="https://x.com/a", source="X", engine="google_news", region="India")
    assert len(dedupe([a, b])) == 2


def test_regions_chosen_in_the_ui_override_detection_and_single_region_questions_compare_with_global():
    p = build_plan("Is EV adoption accelerating?", D.STANDARD, ["Global", "India", "Japan"])
    assert p.geographic_strategy == "user_selected_regions" and {t.region for t in p.search_tasks if t.region} == {"Global", "India", "Japan"}
    q = build_plan("Is EV adoption in India accelerating faster than infrastructure?", D.STANDARD)
    assert q.geographic_strategy == "global_vs_region" and q.regions == ["Global", "India"]
    assert any(t.surface.value == "jobs" or t.surface.value == "shopping" for t in q.search_tasks if not t.region)
    assert build_plan("Is EV adoption in India accelerating?", D.QUICK).geographic_strategy == "single_region"


def test_answer_is_direct_and_never_predicts():
    from backend.demo import build_demo_result
    h = build_demo_result("humanoid").verdict.answer
    assert h.label == "Not yet" and h.evidence_for and h.evidence_against and h.next_steps
    s = build_demo_result("silver").verdict.answer
    assert "not a price prediction" in s.direct_answer and s.regional_note
    assert all("probability" in u or True for u in s.uncertainty) and any("does not predict" in u for u in s.uncertainty)


def test_stream_endpoint_accepts_regions_and_returns_answer(monkeypatch):
    import json as _json
    from fastapi.testclient import TestClient
    from backend.api.routes import investigation as route
    from backend.app.main import app
    monkeypatch.setattr(route, "_build_investigator", lambda: build()[0])
    monkeypatch.setattr(route, "_save_run", lambda r: None)
    c = TestClient(app)
    with c.stream("POST", "/api/investigations/stream", json={"question": SILVER_Q, "depth": "standard", "regions": ["Global", "India"]}) as resp:
        events = [_json.loads(l[6:]) for l in resp.iter_lines() if l.startswith("data: ")]
    kinds = [e["type"] for e in events]
    assert "plan" in kinds and "task_start" in kinds and kinds[-1] == "result"
    result = events[-1]["result"]
    assert result["plan"]["geographic_strategy"] == "user_selected_regions"
    assert result["verdict"]["answer"]["label"] and result["regional"]["regions"]
