from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from importlib.metadata import version
from math import ceil
from pathlib import Path
import random
from statistics import mean
from typing import Callable

from rosca_sim import __version__
from rosca_sim.model import (
    EPSILON,
    AgentSeed,
    BehaviorConfig,
    CollateralConfig,
    ForcedDefault,
    RoscaConfig,
    RoscaModel,
    RunInputs,
    SimulationResult,
)
from rosca_sim.prices import PricePath


@dataclass(frozen=True)
class ReputationConfig:
    distribution: str
    alpha: float
    beta: float
    new_member_share: float


@dataclass(frozen=True)
class ExperimentConfig:
    runs: int
    seed: int
    risk_tolerance: float


@dataclass(frozen=True)
class ExperimentOutput:
    run_rows: tuple[dict[str, object], ...]
    paired_rows: tuple[dict[str, object], ...]
    recipient_rows: tuple[dict[str, object], ...]


def build_run_inputs(
    run_id: int,
    seed: int,
    rosca: RoscaConfig,
    reputation: ReputationConfig,
    price_path: PricePath,
    forced_defaults: tuple[ForcedDefault, ...] = (),
) -> RunInputs:
    if reputation.distribution != "beta":
        raise ValueError("version one supports reputation distribution='beta'")
    rng = random.Random(seed)
    cold_count = round(rosca.members * reputation.new_member_share)
    cold_indices = set(rng.sample(range(rosca.members), cold_count))
    agents = tuple(
        AgentSeed(
            position=position,
            reputation=(
                0.0
                if position in cold_indices
                else rng.betavariate(reputation.alpha, reputation.beta)
            ),
        )
        for position in range(rosca.members)
    )
    return RunInputs(
        run_id=run_id,
        seed=seed,
        agents=agents,
        prices=price_path.prices,
        price_label=price_path.label,
        price_window_start=price_path.start_date,
        daily_prices=price_path.daily_prices,
        forced_defaults=forced_defaults,
    )


def run_pair(
    rosca: RoscaConfig,
    collateral: CollateralConfig,
    behavior: BehaviorConfig,
    inputs: RunInputs,
    risk_tolerance: float,
) -> tuple[SimulationResult, SimulationResult, dict[str, object]]:
    fixed = RoscaModel(rosca, collateral, behavior, "fixed", inputs).run()
    adjusted = RoscaModel(
        rosca, collateral, behavior, "reputation_adjusted", inputs
    ).run()
    paired: dict[str, object] = {
        "run_id": inputs.run_id,
        "delta_default_loss": adjusted.default_loss - fixed.default_loss,
        "delta_participant_shortfall": (
            adjusted.participant_shortfall - fixed.participant_shortfall
        ),
        "delta_reserve_drawn": adjusted.reserve_drawn - fixed.reserve_drawn,
        "delta_reserve_required": (
            adjusted.reserve_required_for_full_payouts
            - fixed.reserve_required_for_full_payouts
        ),
        "delta_capital_locked": adjusted.capital_locked - fixed.capital_locked,
        "delta_net_liquidity": adjusted.net_liquidity - fixed.net_liquidity,
        "delta_completion_rate": adjusted.completion_rate - fixed.completion_rate,
        "risk_equivalent": adjusted.default_loss
        <= fixed.default_loss + risk_tolerance + EPSILON,
        "participant_risk_equivalent": adjusted.participant_shortfall
        <= fixed.participant_shortfall + risk_tolerance + EPSILON,
    }
    return fixed, adjusted, paired


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("cannot write an empty result table")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_experiment(
    rosca: RoscaConfig,
    collateral: CollateralConfig,
    behavior: BehaviorConfig,
    reputation: ReputationConfig,
    experiment: ExperimentConfig,
    price_source: PricePath | Callable[[random.Random], PricePath],
    output_dir: Path,
    forced_defaults: tuple[ForcedDefault, ...] = (),
) -> ExperimentOutput:
    if experiment.runs < 1:
        raise ValueError("runs must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    master = random.Random(experiment.seed)
    run_rows: list[dict[str, object]] = []
    paired_rows: list[dict[str, object]] = []
    recipient_rows: list[dict[str, object]] = []
    labels: set[str] = set()
    for run_id in range(experiment.runs):
        child_seed = master.getrandbits(63)
        path_rng = random.Random(child_seed ^ 0x5A5A5A5A)
        price_path = price_source(path_rng) if callable(price_source) else price_source
        labels.add(price_path.label)
        inputs = build_run_inputs(
            run_id, child_seed, rosca, reputation, price_path, forced_defaults
        )
        fixed, adjusted, paired = run_pair(
            rosca, collateral, behavior, inputs, experiment.risk_tolerance
        )
        for result in (fixed, adjusted):
            row = asdict(result)
            payouts = row.pop("recipient_payouts")
            shortfalls = row.pop("recipient_shortfalls")
            locked_values = row.pop("recipient_collateral_locked")
            run_rows.append(row)
            recipient_rows.extend(
                {
                    "run_id": run_id,
                    "policy": result.policy,
                    "position": position,
                    "scheduled_payout": rosca.members * rosca.contribution,
                    "actual_payout": payout,
                    "payout_shortfall": shortfall,
                    "collateral_locked_at_payout": locked,
                    "net_liquidity_at_payout": payout - locked,
                }
                for position, (payout, shortfall, locked) in enumerate(
                    zip(payouts, shortfalls, locked_values)
                )
            )
        paired_rows.append(paired)

    _write_csv(output_dir / "run_results.csv", run_rows)
    _write_csv(output_dir / "paired_results.csv", paired_rows)
    _write_csv(output_dir / "recipient_results.csv", recipient_rows)
    summary = {}
    for policy in ("fixed", "reputation_adjusted"):
        policy_runs = [row for row in run_rows if row["policy"] == policy]
        policy_recipients = [row for row in recipient_rows if row["policy"] == policy]
        reserve_needs = sorted(
            float(row["reserve_required_for_full_payouts"])
            for row in policy_runs
        )
        summary[policy] = {
            "runs": len(policy_runs),
            "reserve_initial": rosca.reserve_initial,
            "mean_reserve_drawn": mean(
                float(row["reserve_drawn"]) for row in policy_runs
            ),
            "shortfall_run_rate": mean(
                float(row["participant_shortfall"]) > EPSILON
                for row in policy_runs
            ),
            "shortfall_recipient_rate": mean(
                float(row["payout_shortfall"]) > EPSILON
                for row in policy_recipients
            ),
            "mean_participant_shortfall": mean(
                float(row["participant_shortfall"]) for row in policy_runs
            ),
            "max_participant_shortfall": max(
                float(row["participant_shortfall"]) for row in policy_runs
            ),
            "reserve_required_p95": reserve_needs[ceil(0.95 * len(reserve_needs)) - 1],
            "reserve_required_max": reserve_needs[-1],
            "mean_capital_locked": mean(
                float(row["capital_locked"]) for row in policy_runs
            ),
            "mean_net_liquidity": mean(
                float(row["net_liquidity"]) for row in policy_runs
            ),
        }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    metadata = {
        "program_version": __version__,
        "mesa_version": version("mesa"),
        "runs": experiment.runs,
        "seed": experiment.seed,
        "price_label": next(iter(labels)) if len(labels) == 1 else "mixed_historical",
        "forced_defaults": [asdict(event) for event in forced_defaults],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )
    return ExperimentOutput(tuple(run_rows), tuple(paired_rows), tuple(recipient_rows))
