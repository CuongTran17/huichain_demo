from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal

from mesa import Agent, Model

from rosca_sim.model import (
    BehaviorConfig,
    CollateralConfig,
    RoscaConfig,
    fixed_collateral_ratio,
    reputation_collateral_ratio,
)
from rosca_sim.prices import PricePath


@dataclass(frozen=True)
class AuctionAgentSeed:
    member_id: int
    reputation: float
    available_eth: float
    settlement_mode: Literal["eth_first", "usdc_first"]
    usdc_capacity: float
    payment_day_offset: int | None = None


@dataclass(frozen=True)
class AuctionBid:
    period: int
    member_id: int
    rate: float


@dataclass(frozen=True)
class AuctionEvent:
    member_id: int
    day: int


@dataclass(frozen=True)
class AuctionPriceOverride:
    day: int
    price: float


@dataclass(frozen=True)
class AuctionScenario:
    rosca: RoscaConfig
    collateral: CollateralConfig
    behavior: BehaviorConfig
    agents: tuple[AuctionAgentSeed, ...]
    bids: tuple[AuctionBid, ...]
    forced_defaults: tuple[AuctionEvent, ...] = ()
    missed_contributions: tuple[AuctionEvent, ...] = ()
    execution_price_overrides: tuple[AuctionPriceOverride, ...] = ()
    grace_days: int = 7


class AuctionAgent(Agent):
    def __init__(self, model: AuctionRoscaModel, seed: AuctionAgentSeed):
        super().__init__(model)
        self.member_id = seed.member_id
        self.reputation = seed.reputation
        self.available_eth = seed.available_eth
        self.settlement_mode = seed.settlement_mode
        self.usdc_capacity = seed.usdc_capacity
        self.payment_day_offset = seed.payment_day_offset
        self.total_contributed = 0.0
        self.pre_payout_contributions: list[tuple[int, float]] = []
        self.net_payout = 0.0
        self.payout_day: int | None = None
        self.winning_bid: float | None = None
        self.remaining_obligation = 0.0
        self.initial_obligation = 0.0
        self.initial_locked_eth = 0.0
        self.locked_eth = 0.0
        self.eth_released = 0.0

    def contribute(self, day: int) -> float:
        amount = self.model.auction.rosca.contribution
        self.total_contributed += amount
        if self.payout_day is None:
            self.pre_payout_contributions.append((day, amount))
        else:
            self.remaining_obligation = max(0.0, self.remaining_obligation - amount)
            if self.initial_obligation > 0:
                release = min(
                    self.locked_eth,
                    self.initial_locked_eth * amount / self.initial_obligation,
                )
                self.locked_eth -= release
                self.eth_released += release
        return amount


class AuctionRoscaModel(Model):
    def __init__(
        self,
        scenario: AuctionScenario,
        policy: Literal["fixed", "reputation_adjusted"],
        price_path: PricePath,
        run_id: int = 0,
        seed: int = 0,
    ):
        super().__init__(rng=seed)
        rosca = scenario.rosca
        if rosca.members < 6 or rosca.members != rosca.periods:
            raise ValueError("auction mode requires members == periods >= 6")
        if rosca.contribution <= 0 or rosca.period_days < 1 or rosca.reserve_initial != 0:
            raise ValueError("invalid auction ROSCA configuration")
        if policy not in ("fixed", "reputation_adjusted"):
            raise ValueError("unknown auction collateral policy")
        if len(price_path.prices) != rosca.periods or any(
            not isfinite(price) or price <= 0 for price in price_path.prices
        ):
            raise ValueError("invalid due-date ETH prices")
        ids = [agent.member_id for agent in scenario.agents]
        if sorted(ids) != list(range(rosca.members)):
            raise ValueError("auction agents need unique contiguous member IDs")
        for agent in scenario.agents:
            if (
                not 0 <= agent.reputation <= 1
                or not isfinite(agent.available_eth)
                or agent.available_eth < 0
                or not isfinite(agent.usdc_capacity)
                or agent.usdc_capacity < 0
                or agent.settlement_mode not in ("eth_first", "usdc_first")
            ):
                raise ValueError("invalid auction agent")
        seen_bids: set[tuple[int, int]] = set()
        self.bids_by_period: dict[int, list[AuctionBid]] = {}
        for bid in scenario.bids:
            if type(bid.rate) not in (int, float) or not isfinite(bid.rate) or not 0 <= bid.rate < 1:
                raise ValueError("bid rate must be finite and in [0, 1)")
            if type(bid.period) is not int or type(bid.member_id) is not int or not 0 <= bid.period < rosca.periods or bid.member_id not in ids:
                raise ValueError("invalid auction bid target")
            key = (bid.period, bid.member_id)
            if key in seen_bids:
                raise ValueError("duplicate bid")
            seen_bids.add(key)
            self.bids_by_period.setdefault(bid.period, []).append(bid)
        self.auction = scenario
        self.policy = policy
        self.price_path = price_path
        self.run_id = run_id
        self.seed = seed
        self.agents_by_id = {
            agent.member_id: AuctionAgent(self, agent) for agent in scenario.agents
        }
        self.period = 0
        self.cash_balance = 0.0
        self.interest_balance = 0.0
        self.payout_order: list[int] = []
        self.stop_reason: str | None = None
        self.freeze_day: int | None = None

    def _required_eth(self, agent: AuctionAgent, period: int, price: float) -> float:
        obligation = self.auction.rosca.contribution * (self.auction.rosca.periods - period - 1)
        collateral = self.auction.collateral
        ratio = (
            fixed_collateral_ratio(collateral)
            if self.policy == "fixed"
            else reputation_collateral_ratio(agent.reputation, collateral)
        )
        if collateral.stress_drop is not None:
            ratio = max(
                ratio,
                1 / ((1 - collateral.stress_drop) * (1 - collateral.liquidation_slippage)),
            )
        return ratio * obligation / price

    def step(self) -> None:
        if self.stop_reason is not None or self.period >= self.auction.rosca.periods:
            raise RuntimeError("auction circle is no longer active")
        rosca = self.auction.rosca
        day = self.period * rosca.period_days
        price = self.price_path.prices[self.period]
        self.cash_balance += sum(agent.contribute(day) for agent in self.agents_by_id.values())
        candidates = sorted(
            self.bids_by_period.get(self.period, ()),
            key=lambda bid: (-bid.rate, bid.member_id),
        )
        winner: AuctionAgent | None = None
        winning_bid: AuctionBid | None = None
        required_eth = 0.0
        for bid in candidates:
            agent = self.agents_by_id[bid.member_id]
            if agent.payout_day is not None:
                continue
            needed = self._required_eth(agent, self.period, price)
            if agent.available_eth + 1e-9 >= needed:
                winner, winning_bid, required_eth = agent, bid, needed
                break
        if winner is None or winning_bid is None:
            self.stop_reason = "no_eligible_bid"
            self.freeze_day = day
            return
        winner.available_eth -= required_eth
        winner.locked_eth = required_eth
        winner.initial_locked_eth = required_eth
        winner.initial_obligation = rosca.contribution * (rosca.periods - self.period - 1)
        winner.remaining_obligation = winner.initial_obligation
        winner.payout_day = day
        winner.winning_bid = winning_bid.rate
        gross = rosca.members * rosca.contribution
        discount = gross * winning_bid.rate
        winner.net_payout = gross - discount
        self.cash_balance -= winner.net_payout
        self.interest_balance += discount
        self.payout_order.append(winner.member_id)
        self.period += 1
        if self.period == rosca.periods:
            self.stop_reason = "completed"
