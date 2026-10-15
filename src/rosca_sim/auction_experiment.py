from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, replace
import json
from math import ceil
from pathlib import Path
import random
from statistics import mean
from typing import Callable

from rosca_sim import __version__
from rosca_sim.auction import ANNUAL_BID_METADATA, AuctionRoscaModel, AuctionRunResult, AuctionScenario
from rosca_sim.prices import PricePath


@dataclass(frozen=True)
class AuctionExperimentOutput:
    run_rows: tuple[dict[str, object], ...]
    agent_rows: tuple[dict[str, object], ...]
    pair_rows: tuple[dict[str, object], ...]


def run_auction_pair(
    scenario: AuctionScenario, price_path: PricePath, run_id: int = 0, seed: int = 0
) -> tuple[AuctionRunResult, AuctionRunResult]:
    return (
        AuctionRoscaModel(scenario, "fixed", price_path, run_id, seed).run(),
        AuctionRoscaModel(scenario, "reputation_adjusted", price_path, run_id, seed).run(),
    )


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_auction_experiment(
    scenario: AuctionScenario,
    price_source: PricePath | Callable[[random.Random], PricePath],
    runs: int,
    seed: int,
    output_dir: Path,
) -> AuctionExperimentOutput:
    if type(runs) is not int or runs < 1:
        raise ValueError("runs must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    master = random.Random(seed)
    run_rows: list[dict[str, object]] = []
    agent_rows: list[dict[str, object]] = []
    pair_rows: list[dict[str, object]] = []
    price_labels: set[str] = set()
    windows: set[str | None] = set()
    for run_id in range(runs):
        child_seed = master.getrandbits(63)
        path = price_source(random.Random(child_seed ^ 0x5A5A5A5A)) if callable(price_source) else price_source
        price_labels.add(path.label)
        windows.add(path.start_date)
        fixed, adjusted = run_auction_pair(scenario, path, run_id, child_seed)
        for result in (fixed, adjusted):
            row = asdict(result)
            row.pop("agent_results")
            row["payout_order"] = "|".join(map(str, result.payout_order))
            run_rows.append(row)
            agent_rows.extend({"run_id": run_id, "policy": result.policy, **asdict(agent)}
                              for agent in result.agent_results)
        pair_rows.append({
            "run_id": run_id,
            "fixed_payout_order": "|".join(map(str, fixed.payout_order)),
            "adjusted_payout_order": "|".join(map(str, adjusted.payout_order)),
            "same_payout_order": fixed.payout_order == adjusted.payout_order,
            "delta_principal_loss": adjusted.principal_loss - fixed.principal_loss,
            "delta_worst_member_loss": adjusted.worst_member_loss - fixed.worst_member_loss,
            "delta_collateral_locked": adjusted.total_collateral_locked - fixed.total_collateral_locked,
            "delta_interest_distributed": adjusted.interest_distributed - fixed.interest_distributed,
        })
    _write_csv(output_dir / "auction_run_results.csv", run_rows)
    _write_csv(output_dir / "auction_agent_results.csv", agent_rows)
    _write_csv(output_dir / "auction_pair_results.csv", pair_rows)
    metadata = {
        **ANNUAL_BID_METADATA,
        "model_kind": "auction_stop",
        "program_version": __version__,
        "runs": runs,
        "seed": seed,
        "grace_days": scenario.grace_days,
        "scenario": asdict(scenario),
        "collateral_release_policy": "terminal",
        "price_labels": sorted(price_labels),
        "price_windows": sorted(window for window in windows if window is not None),
        "assumptions": ["exogenous bids and defaults", "daily closes are not intraday execution prices",
                        "no external reserve", "never-paid defaulters retain principal claims"],
    }
    (output_dir / "auction_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return AuctionExperimentOutput(tuple(run_rows), tuple(agent_rows), tuple(pair_rows))


def run_auction_grace_sweep(
    scenario: AuctionScenario,
    price_source: PricePath | Callable[[random.Random], PricePath],
    runs: int,
    seed: int,
    grace_days: tuple[int, ...],
    output_dir: Path,
) -> Path:
    if type(runs) is not int or runs < 1:
        raise ValueError("runs must be positive")
    if (not grace_days or len(set(grace_days)) != len(grace_days)
        or any(type(day) is not int or day < 0 for day in grace_days)):
        raise ValueError("grace days must be unique nonnegative integers")
    if any(agent.payment_day_offset is not None and agent.payment_day_offset > min(grace_days)
           for agent in scenario.agents):
        raise ValueError("payment_day_offset exceeds a requested grace period")
    output_dir.mkdir(parents=True, exist_ok=True)
    observed: dict[tuple[int, str], list[AuctionRunResult]] = {
        (day, policy): [] for day in grace_days for policy in ("fixed", "reputation_adjusted")
    }
    master = random.Random(seed)
    for run_id in range(runs):
        child_seed = master.getrandbits(63)
        path = price_source(random.Random(child_seed ^ 0x5A5A5A5A)) if callable(price_source) else price_source
        for day in grace_days:
            fixed, adjusted = run_auction_pair(replace(scenario, grace_days=day), path, run_id, child_seed)
            observed[(day, "fixed")].append(fixed)
            observed[(day, "reputation_adjusted")].append(adjusted)
    rows: list[dict[str, object]] = []
    for day in grace_days:
        for policy in ("fixed", "reputation_adjusted"):
            results = observed[(day, policy)]
            losses = sorted(result.principal_loss for result in results)
            rows.append({
                "grace_days": day,
                "policy": policy,
                "runs": runs,
                "mean_principal_loss": mean(losses),
                "p95_principal_loss": losses[ceil(0.95 * len(losses)) - 1],
                "worst_member_principal_loss": max(result.worst_member_loss for result in results),
                "mean_interest_used": mean(result.interest_used for result in results),
                "mean_settlement_delay_days": mean(result.settlement_day - result.freeze_day for result in results),
                "mean_forced_eth_sales": mean(sum(agent.eth_sold > 0 for agent in result.agent_results)
                                              for result in results),
            })
    output = output_dir / "auction_grace_frontier.csv"
    _write_csv(output, rows)
    return output
