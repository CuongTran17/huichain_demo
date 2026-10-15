"""Bounded, deterministic phase-A study; the Mesa auction engine owns all cash flows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import combinations
from math import isfinite
import random

from rosca_sim.auction import AuctionAgentSeed, AuctionBid, AuctionEvent, AuctionScenario
from rosca_sim.model import BehaviorConfig, CollateralConfig, RoscaConfig
from rosca_sim.prices import PricePath, PricePoint, sample_historical_path, valid_historical_starts


ANNUAL_RATES = (0.0, 0.05, 0.10, 0.15, 0.20)
COARSE_RATIOS = (0.25, 0.50, 0.75, 1.00, 1.25, 1.50, 1.75, 2.00)


@dataclass(frozen=True)
class PhaseACase:
    annual_rate: float
    paid_count: int
    default_ids: tuple[int, ...]

    def __post_init__(self):
        if (type(self.annual_rate) not in (int, float) or self.annual_rate not in ANNUAL_RATES
            or type(self.paid_count) is not int or not 1 <= self.paid_count <= 5
            or type(self.default_ids) is not tuple or not self.default_ids
            or any(type(i) is not int or not 0 <= i < self.paid_count for i in self.default_ids)
            or len(set(self.default_ids)) != len(self.default_ids)):
            raise ValueError("invalid phase A rate, paid count or default group")

    @property
    def default_day(self) -> int:
        return (self.paid_count - 1) * 30 + 1


def phase_a_cases() -> tuple[PhaseACase, ...]:
    return tuple(PhaseACase(rate, k, group) for rate in ANNUAL_RATES
                 for k in range(1, 6) for size in range(1, k + 1)
                 for group in combinations(range(k), size))


def phase_a_paths(points: tuple[PricePoint, ...]) -> tuple[PricePath, ...]:
    selected = tuple(sorted((p for p in points if date(2022, 1, 1) <= p.day <= date(2022, 12, 31)),
                            key=lambda p: p.day))
    if (len({p.day for p in selected}) != len(selected)
        or any(not isfinite(p.close) or p.close <= 0 for p in selected)):
        raise ValueError("invalid or duplicate phase A prices")
    starts = valid_historical_starts(selected, 6, 30, 7)
    if not starts:
        raise ValueError("no complete 2022 window for phase A")
    return tuple(sample_historical_path(selected, 6, 30, random.Random(42),
                                       normalize=False, window_start=start, extra_days=7)
                 for start in starts)


def phase_a_scenario(case: PhaseACase, ratio: float, path: PricePath) -> AuctionScenario:
    if type(ratio) not in (int, float) or not isfinite(ratio) or not 0.25 <= ratio <= 2:
        raise ValueError("phase A ratio must be between 0.25 and 2.00")
    available = 1000 / min(path.prices) + 1
    return AuctionScenario(
        RoscaConfig(6, 6, 100.0, 30), CollateralConfig(ratio, ratio, ratio),
        BehaviorConfig(10000, 10000),
        tuple(AuctionAgentSeed(i, 0.5, available, "usdc_first", 500.0, 7) for i in range(6)),
        tuple(AuctionBid(period, member, case.annual_rate)
              for period in range(6) for member in range(period, 6)),
        forced_defaults=tuple(AuctionEvent(i, case.default_day) for i in case.default_ids),
        grace_days=7,
    )
