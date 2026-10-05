from dataclasses import replace
from datetime import date, timedelta
import importlib
import json

from rosca_sim.auction import AuctionEvent
from rosca_sim.prices import PricePoint
from rosca_sim.web_analysis import run_named_cases, run_sweep
from rosca_sim.web_cases import example_case


START = date(2022, 1, 1)


def reporting():
    return importlib.import_module("rosca_sim.web_reporting")


def fixture_data():
    case = replace(example_case(), window_start=START)
    points = tuple(PricePoint(START + timedelta(days=i), 1000.0) for i in range(180))
    return case, points


def test_chart_rows_reconcile_to_engine():
    case, points = fixture_data()
    run, = run_named_cases((case,), points, 42, "historical", "USD")
    rows = reporting().member_loss_rows((run,))
    assert sum(row["principal_loss_usdc"] for row in rows) == run.result.principal_loss
    assert reporting().comparison_rows((run,))[0]["principal_loss_usdc"] == run.result.principal_loss
    trace = reporting().trace_rows(run)
    assert next(row for row in trace if row["period"] == 0 and row["member_id"] == 0)["payout_usdc"] == 480.0
    assert trace[0]["retained_interest_usdc"] == 120.0
    assert trace[0]["contribution_usdc"] == 100.0


def test_locked_value_has_quote_proxy_label():
    case, points = fixture_data()
    run, = run_named_cases((case,), points, 42, "ETH daily close", "USD")
    row, = reporting().tradeoff_rows((run,))
    expected = max(member.eth_locked * points[member.payout_day].close
                   for member in run.result.agent_results if member.payout_day is not None)
    assert row["max_member_initial_lock_usdc_proxy"] == expected
    assert row["quote_asset"] == "USD"
    assert "USDC" in row["proxy_assumption"]
    assert row["source_label"] == "ETH daily close"


def test_frontier_counts_changed_winners():
    case, points = fixture_data()
    agents = (replace(case.scenario.agents[0], available_eth=0.3), *case.scenario.agents[1:])
    case = replace(case, scenario=replace(case.scenario, agents=agents))
    runs = run_sweep((case,), points, (0.5, 2.0), (START,), 42, "historical", "USDT")
    rows = reporting().frontier_rows(runs)
    assert rows[0]["changed_order_count"] == 0
    assert rows[1]["changed_order_count"] == 1
    assert rows[1]["runs"] == 1


def test_candidate_none_and_nonmonotonic_warning():
    candidate = reporting().candidate_ratio
    assert candidate(({"case_id": "a", "ratio": 1.0, "loss_run_count": 1},), "a") is None
    assert candidate(({"case_id": "a", "ratio": 1.0, "loss_run_count": 1},
                      {"case_id": "a", "ratio": 1.5, "loss_run_count": 0}), "a") == 1.5
    case, points = fixture_data()
    case = replace(case, scenario=replace(case.scenario,
                                          forced_defaults=(AuctionEvent(0, 1),)))
    runs = run_sweep((case,), points, (0.5, 2.0), (START,), 42, "historical", "USD")
    higher = replace(runs[1], result=replace(runs[1].result,
                     worst_member_loss=runs[0].result.worst_member_loss + 1))
    rows = reporting().frontier_rows((runs[0], higher))
    assert rows[1]["nonmonotonic"] is True


def test_no_eligible_bid_is_not_a_safe_candidate():
    case, points = fixture_data()
    agents = tuple(replace(agent, available_eth=0.0) for agent in case.scenario.agents)
    case = replace(case, scenario=replace(case.scenario, agents=agents))
    runs = run_sweep((case,), points, (0.5,), (START,), 42, "historical", "USD")
    assert runs[0].result.stop_reason == "no_eligible_bid"
    rows = reporting().frontier_rows(runs)
    assert reporting().candidate_ratio(rows, case.case_id) is None


def test_frontier_date_span_covers_all_sampled_windows():
    case, points = fixture_data()
    starts = (START + timedelta(days=1), START)
    runs = run_sweep((case,), points, (0.5,), starts, 42, "historical", "USD")
    row, = reporting().frontier_rows(runs)
    assert row["start_date"] == START.isoformat()
    assert row["end_date"] == (START + timedelta(days=158)).isoformat()
    assert row["window_count"] == 2


def test_nonmonotonic_detects_mean_loss_even_if_worst_member_stays_flat():
    case, points = fixture_data()
    runs = run_sweep((case,), points, (0.5, 1.0), (START,), 42, "historical", "USD")
    low = replace(runs[0], result=replace(runs[0].result,
                  principal_loss=10.0, worst_member_loss=10.0))
    high = replace(runs[1], result=replace(runs[1].result,
                   principal_loss=20.0, worst_member_loss=10.0))
    rows = reporting().frontier_rows((low, high))
    assert rows[1]["nonmonotonic"] is True
    assert "mean_loss_usdc" in rows[1]["nonmonotonic_metrics"]


def test_sweep_raw_rows_include_seed_and_original_scenario_assumptions():
    case, points = fixture_data()
    case = replace(case, scenario=replace(case.scenario,
                   forced_defaults=(AuctionEvent(0, 1),),
                   collateral=replace(case.scenario.collateral, fixed_ratio=0.8)))
    runs = run_sweep((case,), points, (0.5,), (START,), 43, "historical", "USD")
    row, = reporting().sweep_run_rows(runs, (case,))
    assert row["seed"] == 43
    assumptions = json.loads(row["scenario_json"])
    assert assumptions["forced_defaults"] == [{"member_id": 0, "day": 1}]
    assert assumptions["bids"]
    assert assumptions["rosca"]["contribution"] == 100
    assert assumptions["collateral"]["fixed_ratio"] == 0.5
