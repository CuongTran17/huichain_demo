import csv
import json
import random

from rosca_sim.experiment import (
    ExperimentConfig,
    ReputationConfig,
    build_run_inputs,
    run_experiment,
    run_pair,
)
from rosca_sim.model import BehaviorConfig, CollateralConfig, RoscaConfig
from rosca_sim.prices import make_stress_path


def settings():
    return (
        RoscaConfig(3, 3, 100.0, 30),
        CollateralConfig(0.5, 0.2, 0.8),
        BehaviorConfig(50.0, 100.0),
        ReputationConfig("beta", 2.0, 2.0, 1 / 3),
    )


def test_build_run_inputs_is_reproducible_and_marks_cold_start():
    rosca, _, _, reputation = settings()
    path = make_stress_path("drop_40", rosca.periods, rosca.period_days)
    first = build_run_inputs(4, 19, rosca, reputation, path)
    second = build_run_inputs(4, 19, rosca, reputation, path)
    assert first == second
    assert sum(agent.reputation == 0.0 for agent in first.agents) == 1
    assert all(0.0 <= agent.reputation <= 1.0 for agent in first.agents)


def test_run_pair_uses_identical_run_identity():
    rosca, collateral, behavior, reputation = settings()
    inputs = build_run_inputs(
        4, 19, rosca, reputation, make_stress_path("drop_40", rosca.periods, rosca.period_days)
    )
    fixed, adjusted, paired = run_pair(
        rosca, collateral, behavior, inputs, risk_tolerance=0.0
    )
    assert fixed.run_id == adjusted.run_id == inputs.run_id
    assert fixed.seed == adjusted.seed == inputs.seed
    assert fixed.price_label == adjusted.price_label == inputs.price_label
    assert paired["run_id"] == inputs.run_id
    assert paired["delta_default_loss"] == adjusted.default_loss - fixed.default_loss


def test_run_experiment_writes_reproducible_csv_and_metadata(tmp_path):
    rosca, collateral, behavior, reputation = settings()
    experiment = ExperimentConfig(runs=4, seed=42, risk_tolerance=0.0)
    path = make_stress_path("drop_40", rosca.periods, rosca.period_days)
    first = run_experiment(
        rosca, collateral, behavior, reputation, experiment, path, tmp_path / "first"
    )
    second = run_experiment(
        rosca, collateral, behavior, reputation, experiment, path, tmp_path / "second"
    )
    assert first.paired_rows == second.paired_rows
    assert (tmp_path / "first" / "run_results.csv").exists()
    assert (tmp_path / "first" / "paired_results.csv").exists()
    assert (tmp_path / "first" / "recipient_results.csv").exists()
    summary = json.loads((tmp_path / "first" / "summary.json").read_text(encoding="utf-8"))
    assert summary["fixed"]["runs"] == 4
    assert 0.0 <= summary["fixed"]["shortfall_run_rate"] <= 1.0
    with (tmp_path / "first" / "run_results.csv").open(newline="", encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == 8
    with (tmp_path / "first" / "recipient_results.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        recipients = list(csv.DictReader(handle))
    assert len(recipients) == 24
    assert all("net_liquidity_at_payout" in row for row in recipients)
    for run in first.run_rows:
        shortfalls = sum(
            float(row["payout_shortfall"])
            for row in recipients
            if int(row["run_id"]) == run["run_id"]
            and row["policy"] == run["policy"]
        )
        assert shortfalls == run["participant_shortfall"]
    metadata = json.loads((tmp_path / "first" / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["runs"] == 4
    assert metadata["seed"] == 42
    assert metadata["price_label"] == "drop_40"
    assert metadata["mesa_version"] == "3.5.1"
