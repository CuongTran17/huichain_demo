"""Thin, deterministic adapters from named web inputs to the auction engine."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from math import isfinite
import random
from typing import Literal

from rosca_sim.auction import AuctionPeriodTrace, AuctionRoscaModel, AuctionRunResult
from rosca_sim.prices import PricePath, PricePoint, sample_historical_path, valid_historical_starts
from rosca_sim.web_cases import NamedCase


QuoteAsset = Literal["USD", "USDT"]


@dataclass(frozen=True)
class CaseRun:
    case: NamedCase
    result: AuctionRunResult
    trace: tuple[AuctionPeriodTrace, ...]
    price_path: PricePath
    source_label: str
    quote_asset: QuoteAsset


def run_named_cases(
    cases: tuple[NamedCase, ...], points: tuple[PricePoint, ...], seed: int,
    source_label: str, quote_asset: QuoteAsset,
) -> tuple[CaseRun, ...]:
    if quote_asset not in ("USD", "USDT"):
        raise ValueError("quote_asset must be USD or USDT")
    runs = []
    for run_id, case in enumerate(cases):
        try:
            if case.window_start is None:
                raise ValueError("select a historical window_start")
            scenario = case.scenario
            path = sample_historical_path(
                points, scenario.rosca.periods, scenario.rosca.period_days,
                random.Random(seed), normalize=False, window_start=case.window_start,
                extra_days=scenario.grace_days,
            )
            model = AuctionRoscaModel(scenario, "fixed", path, run_id, seed)
            result = model.run()
        except ValueError as error:
            raise ValueError(f"{case.name}: {error}") from error
        runs.append(CaseRun(case, result, model.period_trace, path,
                            source_label, quote_asset))
    return tuple(runs)


@dataclass(frozen=True)
class SweepRun:
    case_id: str
    ratio: float
    start: date
    result: AuctionRunResult
    price_path: PricePath
    source_label: str
    quote_asset: QuoteAsset


def ratio_grid(min_ratio: Decimal, max_ratio: Decimal, step: Decimal) -> tuple[float, ...]:
    if (not all(value.is_finite() for value in (min_ratio, max_ratio, step))
        or min_ratio < 0 or max_ratio < min_ratio or step <= 0):
        raise ValueError("invalid collateral ratio grid")
    count = int((max_ratio - min_ratio) // step) + 1
    if count > 10_000:
        raise ValueError("ratio grid exceeds 10,000 values")
    return tuple(float(min_ratio + step * index) for index in range(count))


def sample_common_starts(
    cases: tuple[NamedCase, ...], points: tuple[PricePoint, ...], count: int, seed: int,
) -> tuple[date, ...]:
    if not cases or type(count) is not int or count < 1:
        raise ValueError("select cases and a positive window count")
    available = set(valid_historical_starts(
        points, cases[0].scenario.rosca.periods,
        cases[0].scenario.rosca.period_days, cases[0].scenario.grace_days,
    ))
    for case in cases[1:]:
        config = case.scenario.rosca
        available.intersection_update(valid_historical_starts(
            points, config.periods, config.period_days, case.scenario.grace_days,
        ))
    if count > len(available):
        raise ValueError(f"requested {count} windows; only {len(available)} available")
    return tuple(sorted(random.Random(seed).sample(sorted(available), count)))


def run_sweep(
    cases: tuple[NamedCase, ...], points: tuple[PricePoint, ...],
    ratios: tuple[float, ...], starts: tuple[date, ...], seed: int,
    source_label: str, quote_asset: QuoteAsset, max_runs: int = 10_000,
) -> tuple[SweepRun, ...]:
    if len(cases) * len(ratios) * len(starts) > max_runs:
        raise ValueError(f"sweep exceeds {max_runs:,} engine runs")
    if not cases or not ratios or not starts or len(set(starts)) != len(starts):
        raise ValueError("select cases, ratios, and distinct starts")
    if any(not isfinite(ratio) or ratio < 0 for ratio in ratios):
        raise ValueError("ratios must be finite nonnegative numbers")
    runs = []
    for case in cases:
        for ratio in ratios:
            scenario = replace(case.scenario, collateral=replace(
                case.scenario.collateral, fixed_ratio=ratio))
            for start in starts:
                selected = replace(case, scenario=scenario, window_start=start)
                run, = run_named_cases((selected,), points, seed, source_label, quote_asset)
                runs.append(SweepRun(case.case_id, ratio, start, run.result,
                                     run.price_path, source_label, quote_asset))
    return tuple(runs)
