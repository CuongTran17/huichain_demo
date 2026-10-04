"""Thin, deterministic adapters from named web inputs to the auction engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import random
from typing import Literal

from rosca_sim.auction import AuctionPeriodTrace, AuctionRoscaModel, AuctionRunResult
from rosca_sim.prices import PricePath, PricePoint, sample_historical_path
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
