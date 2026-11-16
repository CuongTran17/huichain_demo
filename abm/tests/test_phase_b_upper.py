from pathlib import Path
import csv
import json

import pytest

from rosca_sim import phase_b, phase_b_upper as upper
from rosca_sim.due_date_auction import DueDateAuctionModel
from rosca_sim.prices import PricePath


def price_path(overrides=None, base=2000, start="2022-01-01"):
    values = [base] * 158
    for day, price in (overrides or {}).items():
        values[day] = price
    return PricePath(tuple(values[:151:30]), "test", start, tuple(values))


def test_upper_scenario_matches_phase_b_at_200():
    path = price_path({60: 1000, 67: 700})
    args = dict(strategic=False, paid_count=2, forced_ids=(4,))
    before = phase_b.phase_b_scenario(path, 2, "mixed_rotating", 0.5, **args)
    after = upper.build_scenario(path, 200, "mixed_rotating", 0.5, **args)
    assert DueDateAuctionModel(after, "fixed", path).run() == DueDateAuctionModel(before, "fixed", path).run()


def test_upper_ratio_locks_full_eth_at_low_prices():
    path = price_path(base=100)
    scenario = upper.build_scenario(path, 300, "all_zero", 0, strategic=False)
    result = DueDateAuctionModel(scenario, "fixed", path).run()
    assert result.stop_reason == "completed"
    assert result.agent_results[0].eth_locked == 15
    with pytest.raises(ValueError):
        upper.build_scenario(path, 301, "all_zero", 0, strategic=False)


def test_screen_candidates_consider_due_and_grace_prices():
    due = price_path({60: 1000})
    grace = price_path({67: 100}, start="2022-01-02")
    irrelevant = price_path({37: 100})
    assert upper.stress_score(grace) > upper.stress_score(due)
    assert upper.stress_score(irrelevant) == upper.stress_score(price_path())


def test_screen_survivor_is_not_pass():
    path = price_path()
    row = upper.screen_ratio((path,), 205)
    assert row["status"] == "needs_full"
    assert row["runs"] == 58
    failed = upper.screen_ratio((price_path({30: 500}),), 205)
    assert failed["status"] == "fail_witness"
    assert failed["witness"]["freeze_day"] == 30
    assert failed["witness"]["worst_member_loss"] > 0


def test_first_pass_requires_evidence_for_all_lower_grid_points():
    grid = (205, 210, 215)
    assert upper.select_threshold(grid, {205: "fail_witness", 210: "full_fail", 215: "full_pass"}) == (215, "found")
    assert upper.select_threshold(grid, {205: "fail_witness", 215: "full_pass"}) == (None, "incomplete")
    assert upper.select_threshold(grid, dict.fromkeys(grid, "full_fail")) == (None, "not_found")


def test_missing_or_foreign_checkpoint_cannot_certify_threshold(tmp_path: Path):
    paths = (price_path(),)
    identity = {"scope": "full", "study": "test"}
    job = ("all_zero", 0.0, 205, "strategic")
    assert upper.checkpoint(tmp_path, identity, paths, job, run=False) is None
    data = upper.checkpoint(tmp_path, identity, paths, job, run=True)
    assert data["summary"]["completed_runs"] == 1
    assert phase_b._digest(upper.checkpoint(tmp_path, identity, paths, job, run=False)) == phase_b._digest(data)
    with pytest.raises(ValueError, match="checkpoint"):
        upper.checkpoint(tmp_path, dict(identity, study="other"), paths, job, run=False)


def test_aggregate_needs_every_profile_capacity_and_mode(tmp_path: Path):
    paths = (price_path(),)
    identity = {"scope": "full", "study": "test"}
    screening = [dict(ratio_pct=ratio, status="needs_full", runs=58, witness=None) for ratio in upper.GRID]
    jobs = phase_b._jobs("full", 205)
    for job in jobs[:-1]:
        upper.checkpoint(tmp_path, identity, paths, job, run=True)
    assert upper._aggregate(tmp_path, identity, paths, screening) == 1
    threshold = tmp_path / "threshold.json"
    assert json.loads(threshold.read_text())["min_passing_ratio_pct"] is None
    upper.checkpoint(tmp_path, identity, paths, jobs[-1], run=True)
    assert upper._aggregate(tmp_path, identity, paths, screening) == 0
    result = json.loads(threshold.read_text())
    assert (result["min_passing_ratio_pct"], result["full_runs"]) == (205, 522)
    assert upper._aggregate(tmp_path, identity, paths, []) == 1
    for table in ("screening.csv", "phase_b_upper_ratios.csv", "phase_b_upper_jobs.csv"):
        with (tmp_path / table).open(newline="") as handle:
            assert list(csv.DictReader(handle)) == []


def test_full_scan_witness_is_not_exported_as_screening_witness(tmp_path: Path):
    paths = (price_path({30: 500}),)
    identity = {"scope": "full", "study": "test"}
    for job in phase_b._jobs("full", 205):
        upper.checkpoint(tmp_path, identity, paths, job, run=True)
    screened = [dict(ratio_pct=205, status="needs_full", runs=58, witness=None)]
    assert upper._aggregate(tmp_path, identity, paths, screened) == 1
    with (tmp_path / "screening.csv").open(newline="") as handle:
        assert next(csv.DictReader(handle))["witness_member_loss_usdc"] == ""
    with (tmp_path / "phase_b_upper_ratios.csv").open(newline="") as handle:
        assert float(next(csv.DictReader(handle))["witness_member_loss_usdc"]) > 0
