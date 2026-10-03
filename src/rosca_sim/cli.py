from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, replace
from datetime import date
import hashlib
import json
from math import isfinite
import os
from pathlib import Path
import random
import shutil
from statistics import mean
import tomllib
from typing import Sequence

from rosca_sim.auction import (
    AuctionAgentSeed, AuctionBid, AuctionEvent, AuctionPriceOverride, AuctionScenario,
    AuctionRoscaModel,
)
from rosca_sim.auction_experiment import run_auction_experiment, run_auction_grace_sweep

from rosca_sim.experiment import (
    ExperimentConfig,
    ReputationConfig,
    run_experiment,
)
from rosca_sim.model import EPSILON, BehaviorConfig, CollateralConfig, ForcedDefault, RoscaConfig
from rosca_sim.prices import (
    PricePath,
    fetch_binance_spot_prices,
    fetch_coingecko_prices,
    load_price_csv,
    make_stress_path,
    sample_historical_path,
)


@dataclass(frozen=True)
class LoadedConfig:
    path: Path
    rosca: RoscaConfig
    collateral: CollateralConfig
    reputation: ReputationConfig
    behavior: BehaviorConfig
    prices: dict[str, object]
    experiment: ExperimentConfig
    forced_defaults: tuple[ForcedDefault, ...]


@dataclass(frozen=True)
class LoadedAuctionConfig:
    path: Path
    scenario: AuctionScenario
    prices: dict[str, object]
    runs: int
    seed: int


def load_auction_config(path: Path) -> LoadedAuctionConfig:
    path = Path(path)
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    try:
        rosca = RoscaConfig(**raw["rosca"])
        collateral = CollateralConfig(**raw["collateral"])
        behavior = BehaviorConfig(**raw["behavior"])
        agents = tuple(AuctionAgentSeed(**item) for item in raw["agents"])
        bids = tuple(AuctionBid(**item) for item in raw["bids"])
        events = raw.get("events", {})
        scenario = AuctionScenario(
            rosca, collateral, behavior, agents, bids,
            tuple(AuctionEvent(**item) for item in events.get("forced_defaults", [])),
            tuple(AuctionEvent(**item) for item in events.get("missed_contributions", [])),
            tuple(AuctionPriceOverride(**item) for item in events.get("execution_price_overrides", [])),
            raw["auction"]["grace_days"],
        )
        prices = dict(raw["prices"])
        runs = raw["experiment"]["runs"]
        seed = raw["experiment"]["seed"]
    except (KeyError, TypeError) as error:
        raise ValueError(f"invalid or incomplete auction configuration: {error}") from error
    if type(runs) is not int or runs < 1 or type(seed) is not int:
        raise ValueError("invalid auction experiment runs or seed")
    if type(scenario.grace_days) is not int or scenario.grace_days < 0:
        raise ValueError("grace_days must be a nonnegative integer")
    if rosca.reserve_initial != 0:
        raise ValueError("auction version requires reserve_initial = 0")
    if prices.get("source") == "historical":
        for field in ("file", "start_date", "end_date", "normalize"):
            if field not in prices:
                raise ValueError(f"historical prices require {field}")
        price_file = _resolve_price_file(path, prices["file"])
        if not price_file.is_file():
            raise FileNotFoundError(f"historical price file not found: {price_file}")
        prices.update(file=price_file, start_date=_as_date(prices["start_date"], "prices.start_date"),
                      end_date=_as_date(prices["end_date"], "prices.end_date"),
                      window_start=_as_date(prices["window_start"], "prices.window_start")
                      if "window_start" in prices else None)
        if prices["start_date"] > prices["end_date"]:
            raise ValueError("prices.start_date must not exceed prices.end_date")
        points = load_price_csv(price_file, prices["start_date"], prices["end_date"])
        sample_historical_path(points, rosca.periods, rosca.period_days, random.Random(seed),
                               bool(prices["normalize"]), prices["window_start"], scenario.grace_days)
    elif prices.get("source") == "stress":
        make_stress_path(str(prices["scenario"]), rosca.periods, rosca.period_days, scenario.grace_days)
    else:
        raise ValueError("prices.source must be 'historical' or 'stress'")
    # Model construction validates bids, events, collateral capacity, and daily price shape.
    validation_path = _auction_price_source(LoadedAuctionConfig(path, scenario, prices, runs, seed))
    sample = validation_path(random.Random(seed)) if callable(validation_path) else validation_path
    AuctionRoscaModel(scenario, "fixed", sample)
    AuctionRoscaModel(scenario, "reputation_adjusted", sample)
    return LoadedAuctionConfig(path, scenario, prices, runs, seed)


def _auction_price_source(config: LoadedAuctionConfig, extra_days: int | None = None):
    scenario = config.scenario
    tail = scenario.grace_days if extra_days is None else extra_days
    if config.prices["source"] == "stress":
        return make_stress_path(str(config.prices["scenario"]), scenario.rosca.periods,
                                scenario.rosca.period_days, tail)
    points = load_price_csv(Path(config.prices["file"]), config.prices["start_date"], config.prices["end_date"])
    def sample(rng: random.Random) -> PricePath:
        return sample_historical_path(points, scenario.rosca.periods, scenario.rosca.period_days,
                                      rng, bool(config.prices["normalize"]),
                                      config.prices["window_start"], tail)
    return sample


def _augment_auction_metadata(config: LoadedAuctionConfig, output: Path) -> None:
    metadata_path = output / "auction_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["config_sha256"] = hashlib.sha256(config.path.read_bytes()).hexdigest()
    metadata["price_source"] = config.prices["source"]
    if config.prices["source"] == "historical":
        metadata["price_file_sha256"] = hashlib.sha256(Path(config.prices["file"]).read_bytes()).hexdigest()
        metadata["price_start_date"] = config.prices["start_date"].isoformat()
        metadata["price_end_date"] = config.prices["end_date"].isoformat()
    else:
        metadata["price_scenario"] = config.prices["scenario"]
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _as_date(value: object, field: str) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise ValueError(f"{field} must use YYYY-MM-DD") from error
    raise ValueError(f"{field} must use YYYY-MM-DD")


def _resolve_price_file(config_path: Path, raw_path: object) -> Path:
    candidate = Path(str(raw_path))
    if candidate.is_absolute():
        return candidate
    beside_config = config_path.parent / candidate
    return beside_config if beside_config.exists() else candidate


def load_config(path: Path) -> LoadedConfig:
    path = Path(path)
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    try:
        rosca = RoscaConfig(**raw["rosca"])
        collateral = CollateralConfig(**raw["collateral"])
        reputation = ReputationConfig(**raw["reputation"])
        behavior = BehaviorConfig(**raw["behavior"])
        experiment = ExperimentConfig(**raw["experiment"])
        prices = dict(raw["prices"])
        events = tuple(
            ForcedDefault(**item)
            for item in raw.get("events", {}).get("forced_defaults", [])
        )
    except (KeyError, TypeError) as error:
        raise ValueError(f"invalid or incomplete configuration: {error}") from error

    if rosca.members < 1 or rosca.periods < 1:
        raise ValueError("members and periods must be positive")
    if rosca.members != rosca.periods:
        raise ValueError("members must equal periods in version one")
    if rosca.contribution <= 0:
        raise ValueError("contribution must be positive")
    if rosca.reserve_initial < 0:
        raise ValueError("reserve_initial must be nonnegative")
    if rosca.period_days < 1:
        raise ValueError("period_days must be positive")
    ratios = (collateral.fixed_ratio, collateral.alpha_min, collateral.alpha_max)
    if any(not 0.0 <= value <= 1.0 for value in ratios):
        raise ValueError("collateral ratios must be between 0 and 1")
    if collateral.alpha_min > collateral.alpha_max:
        raise ValueError("alpha_min must not exceed alpha_max")
    if collateral.stress_drop is not None and not 0.0 <= collateral.stress_drop < 1.0:
        raise ValueError("stress_drop must be between 0 and 1")
    if not 0.0 <= collateral.liquidation_slippage < 1.0:
        raise ValueError("liquidation_slippage must be between 0 and 1")
    if collateral.require_top_up:
        raise ValueError("version one does not support collateral top-up")
    if reputation.distribution != "beta":
        raise ValueError("version one supports reputation distribution='beta'")
    if reputation.alpha <= 0 or reputation.beta <= 0:
        raise ValueError("reputation alpha and beta must be positive")
    if not 0.0 <= reputation.new_member_share <= 1.0:
        raise ValueError("new_member_share must be between 0 and 1")
    if behavior.decision_mode != "every_due_date":
        raise ValueError("version one supports decision_mode='every_due_date'")
    if behavior.decision_rule != "deterministic":
        raise ValueError("version one supports decision_rule='deterministic'")
    if behavior.reputation_loss < 0 or behavior.future_access_loss < 0:
        raise ValueError("behavioral losses must be nonnegative")
    if experiment.runs < 1:
        raise ValueError("runs must be positive")
    if experiment.risk_tolerance < 0:
        raise ValueError("risk_tolerance must be nonnegative")
    days_needed = (rosca.periods - 1) * rosca.period_days + 1
    if any(
        type(event.position) is not int
        or type(event.day) is not int
        or not 0 <= event.position < rosca.members
        or not event.position * rosca.period_days < event.day < days_needed
        for event in events
    ) or len({(event.position, event.day) for event in events}) != len(events):
        raise ValueError("forced defaults need distinct events after recipient payout")

    source = prices.get("source")
    if source == "historical":
        required = ("file", "start_date", "end_date", "normalize")
        if any(field not in prices for field in required):
            raise ValueError("historical prices require file, start_date, end_date, and normalize")
        price_file = _resolve_price_file(path, prices["file"])
        if not price_file.is_file():
            raise FileNotFoundError(f"historical price file not found: {price_file}")
        start = _as_date(prices["start_date"], "prices.start_date")
        end = _as_date(prices["end_date"], "prices.end_date")
        if start > end:
            raise ValueError("prices.start_date must not exceed prices.end_date")
        window_start = (
            _as_date(prices["window_start"], "prices.window_start")
            if "window_start" in prices
            else None
        )
        prices.update(
            file=price_file,
            start_date=start,
            end_date=end,
            window_start=window_start,
        )
    elif source == "stress":
        scenario = prices.get("scenario")
        if not isinstance(scenario, str):
            raise ValueError("stress prices require a scenario")
        make_stress_path(scenario, rosca.periods, rosca.period_days)
    else:
        raise ValueError("prices.source must be 'historical' or 'stress'")

    return LoadedConfig(path, rosca, collateral, reputation, behavior, prices, experiment, events)


def _price_source(config: LoadedConfig):
    if config.prices["source"] == "stress":
        return make_stress_path(
            str(config.prices["scenario"]),
            config.rosca.periods,
            config.rosca.period_days,
        )
    price_file = Path(config.prices["file"])
    points = load_price_csv(
        price_file,
        config.prices["start_date"],
        config.prices["end_date"],
    )

    def sample(rng: random.Random) -> PricePath:
        return sample_historical_path(
            points,
            config.rosca.periods,
            config.rosca.period_days,
            rng,
            bool(config.prices["normalize"]),
            config.prices["window_start"],
        )

    return sample


def _augment_metadata(config: LoadedConfig, output: Path) -> None:
    metadata_path = output / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["price_source"] = config.prices["source"]
    if config.prices["source"] == "historical":
        price_file = Path(config.prices["file"])
        metadata.update(
            price_file=str(price_file),
            price_file_sha256=hashlib.sha256(price_file.read_bytes()).hexdigest(),
            price_start_date=config.prices["start_date"].isoformat(),
            price_end_date=config.prices["end_date"].isoformat(),
            price_window_start=(
                config.prices["window_start"].isoformat()
                if config.prices["window_start"] is not None
                else None
            ),
        )
    else:
        metadata["price_scenario"] = config.prices["scenario"]
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rosca-sim")
    commands = parser.add_subparsers(dest="command", required=True)
    auction = commands.add_parser("auction-run", help="run paired auction ROSCA scenarios")
    auction.add_argument("--config", type=Path, required=True)
    auction.add_argument("--output", type=Path, required=True)
    auction_sweep = commands.add_parser("auction-grace-sweep", help="compare auction settlement deadlines")
    auction_sweep.add_argument("--config", type=Path, required=True)
    auction_sweep.add_argument("--output", type=Path, required=True)
    auction_sweep.add_argument("--days", type=int, nargs="+", required=True)
    run = commands.add_parser("run", help="run a paired ROSCA experiment")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    sweep = commands.add_parser("sweep", help="compare capped fixed collateral ratios")
    sweep.add_argument("--config", type=Path, required=True)
    sweep.add_argument("--output", type=Path, required=True)
    sweep.add_argument("--ratios", type=float, nargs="+", required=True)
    fetch = commands.add_parser("fetch-prices", help="download daily ETH/USD prices")
    fetch.add_argument("--start", type=date.fromisoformat, required=True)
    fetch.add_argument("--end", type=date.fromisoformat, required=True)
    fetch.add_argument("--output", type=Path, required=True)
    binance = commands.add_parser(
        "fetch-binance-prices", help="download daily ETH/USDT spot prices"
    )
    binance.add_argument("--start", type=date.fromisoformat, required=True)
    binance.add_argument("--end", type=date.fromisoformat, required=True)
    binance.add_argument("--output", type=Path, required=True)
    return parser


def _dotenv_value(name: str, path: Path = Path(".env")) -> str | None:
    if not path.is_file():
        return None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = raw_line.partition("=")
        if separator and key.strip() == name:
            return value.strip().strip("'\"") or None
    return None


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in ("auction-run", "auction-grace-sweep"):
        auction_config = load_auction_config(args.config)
        output = Path(args.output)
        if args.command == "auction-run":
            run_auction_experiment(auction_config.scenario, _auction_price_source(auction_config),
                                   auction_config.runs, auction_config.seed, output)
            _augment_auction_metadata(auction_config, output)
        else:
            run_auction_grace_sweep(auction_config.scenario,
                                    _auction_price_source(auction_config, max(args.days)),
                                    auction_config.runs, auction_config.seed,
                                    tuple(args.days), output)
        shutil.copyfile(auction_config.path, output / "config.toml")
        print(output)
        print(f"runs: {auction_config.runs}")
        return 0
    if args.command == "fetch-binance-prices":
        fetch_binance_spot_prices(args.start, args.end, args.output)
        print(args.output)
        return 0
    if args.command == "fetch-prices":
        api_key = os.environ.get("COINGECKO_API_KEY") or _dotenv_value(
            "COINGECKO_API_KEY"
        )
        if not api_key:
            raise ValueError("COINGECKO_API_KEY is required")
        if args.start > args.end:
            raise ValueError("start date must not exceed end date")
        fetch_coingecko_prices(args.start, args.end, api_key, args.output)
        print(args.output)
        return 0

    config = load_config(args.config)
    output = Path(args.output)
    if args.command == "sweep":
        ratios = args.ratios
        if any(not isfinite(ratio) or not 0.0 <= ratio <= 1.0 for ratio in ratios) or len(set(ratios)) != len(ratios):
            raise ValueError("sweep ratios must be unique and between 0 and 1")
        if config.collateral.stress_drop is not None:
            raise ValueError("sweep requires stress_drop to be unset")
        source = _price_source(config)
        frontier = []
        for ratio in ratios:
            child = output / f"ratio-{ratio}"
            result = run_experiment(
                config.rosca,
                replace(config.collateral, fixed_ratio=ratio),
                config.behavior,
                config.reputation,
                config.experiment,
                source,
                child,
                config.forced_defaults,
            )
            _augment_metadata(config, child)
            fixed_runs = [row for row in result.run_rows if row["policy"] == "fixed"]
            first_recipients = [
                row for row in result.recipient_rows
                if row["policy"] == "fixed" and row["position"] == 0
            ]
            frontier.append({
                "ratio": ratio,
                "mean_first_recipient_collateral_locked": mean(row["collateral_locked_at_payout"] for row in first_recipients),
                "mean_first_recipient_net_liquidity": mean(row["net_liquidity_at_payout"] for row in first_recipients),
                "mean_participant_shortfall": mean(row["participant_shortfall"] for row in fixed_runs),
                "shortfall_run_rate": mean(row["participant_shortfall"] > EPSILON for row in fixed_runs),
                "max_reserve_required": max(row["reserve_required_for_full_payouts"] for row in fixed_runs),
            })
        with (output / "frontier.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(frontier[0]))
            writer.writeheader()
            writer.writerows(frontier)
        shutil.copyfile(config.path, output / "base-config.toml")
        print(output)
        print(f"ratios: {len(ratios)}")
        return 0
    run_experiment(
        config.rosca,
        config.collateral,
        config.behavior,
        config.reputation,
        config.experiment,
        _price_source(config),
        output,
        config.forced_defaults,
    )
    shutil.copyfile(config.path, output / "config.toml")
    _augment_metadata(config, output)
    print(output)
    print(f"runs: {config.experiment.runs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
