from backend.agent.planner import _trend_window, build_plan
from backend.models.requests import InvestigationDepth


def test_trend_window_varies_by_depth():
    assert _trend_window(InvestigationDepth.QUICK) == "today 3-m"
    assert _trend_window(InvestigationDepth.STANDARD) == "today 12-m"
    assert _trend_window(InvestigationDepth.DEEP) == "today 5-y"


def test_quick_is_fast_and_has_no_automatic_regional_expansion():
    plan = build_plan("Will silver prices rise next month?", InvestigationDepth.QUICK)
    assert plan.depth == "quick"
    assert plan.configured_surface_limit == 3
    assert plan.geographic_strategy == "global_overview"
    assert len(plan.search_tasks) == 3
    assert {task.params.get("date") for task in plan.search_tasks if task.surface.value == "trends"} == {"today 3-m"}


def test_standard_price_forecast_compares_global_with_india():
    plan = build_plan("Will silver prices rise next month?", InvestigationDepth.STANDARD)
    assert plan.geographic_strategy == "global_vs_india"
    assert {task.region for task in plan.search_tasks if task.region} == {"Global", "India"}
    trends = [task for task in plan.search_tasks if task.surface.value == "trends"]
    assert {task.region for task in trends} == {"Global", "India"}
    assert all(task.params.get("date") == "today 12-m" for task in trends)


def test_deep_adds_research_cross_check_and_longer_trend_window():
    plan = build_plan("Will silver prices rise next month?", InvestigationDepth.DEEP)
    surfaces = {task.surface.value for task in plan.search_tasks}
    assert "scholar" in surfaces
    assert plan.per_surface_limit == 20
    trends = [task for task in plan.search_tasks if task.surface.value == "trends"]
    assert trends and all(task.params.get("date") == "today 5-y" for task in trends)
    assert {task.region for task in trends} == {"Global", "India"}
