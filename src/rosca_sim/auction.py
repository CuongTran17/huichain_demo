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
    settle_default,
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


@dataclass(frozen=True)
class AuctionAgentResult:
    member_id: int
    payout_day: int | None
    winning_bid: float | None
    net_payout: float
    total_contributed: float
    principal_claim: float
    principal_repaid: float
    principal_loss: float
    interest_received: float
    eth_locked: float
    eth_released: float
    eth_sold: float
    eth_returned: float
    eth_sale_day: int | None
    eth_sale_price: float | None
    usdc_settlement_paid: float
    settlement_mode: str
    payment_day: int | None
    obligation_uncollected: float
    bid_interest_paid: float
    is_trigger_default: bool
    settlement_shortfall: bool


@dataclass(frozen=True)
class AuctionRunResult:
    run_id: int
    policy: str
    seed: int
    price_label: str
    price_window_start: str | None
    stop_reason: str
    freeze_day: int
    settlement_day: int
    default_count: int
    payout_order: tuple[int, ...]
    interest_retained: float
    interest_used: float
    interest_distributed: float
    obligation_uncollected: float
    principal_loss: float
    worst_member_loss: float
    total_collateral_locked: float
    eth_sale_proceeds: float
    ending_cash: float
    agent_results: tuple[AuctionAgentResult, ...]
    interest_used_from_defaulting: float
    interest_used_from_other_members: float
    secondary_shortfall_count: int


@dataclass(frozen=True)
class AuctionPeriodTrace:
    period: int
    day: int
    contributions_by_member: tuple[float, ...]
    winner_id: int | None
    gross_pot: float
    bid_interest: float
    net_payout: float
    eth_locked_by_member: tuple[float, ...]
    eth_released_by_member: tuple[float, ...]
    pool_cash: float
    retained_interest: float
    remaining_obligation_by_member: tuple[float, ...]
    retained_eth_by_member: tuple[float, ...]
    insufficient_eth_bidder_ids: tuple[int, ...]


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
        self.bid_interest_paid = 0.0
        self.remaining_obligation = 0.0
        self.initial_obligation = 0.0
        self.initial_locked_eth = 0.0
        self.locked_eth = 0.0
        self.eth_released = 0.0
        self.eth_sold = 0.0
        self.eth_returned = 0.0
        self.eth_sale_day: int | None = None
        self.eth_sale_price: float | None = None
        self.usdc_settlement_paid = 0.0
        self.payment_day: int | None = None
        self.obligation_uncollected = 0.0
        self.principal_repaid = 0.0
        self.interest_received = 0.0

    def contribute(self, day: int) -> float:
        amount = self.model.auction.rosca.contribution
        self.total_contributed += amount
        if self.payout_day is None:
            self.pre_payout_contributions.append((day, amount))
        else:
            self.remaining_obligation = max(0.0, self.remaining_obligation - amount)
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
        if type(rosca.members) is not int or type(rosca.periods) is not int or rosca.members < 6 or rosca.members != rosca.periods:
            raise ValueError("auction mode requires members == periods >= 6")
        if (type(rosca.contribution) not in (int, float) or not isfinite(rosca.contribution)
            or rosca.contribution <= 0 or type(rosca.period_days) is not int
            or rosca.period_days < 1 or rosca.reserve_initial != 0):
            raise ValueError("invalid auction ROSCA configuration")
        if policy not in ("fixed", "reputation_adjusted"):
            raise ValueError("unknown auction collateral policy")
        if type(scenario.grace_days) is not int or scenario.grace_days < 0:
            raise ValueError("grace_days must be a nonnegative integer")
        collateral_values = (scenario.collateral.fixed_ratio, scenario.collateral.alpha_min,
                             scenario.collateral.alpha_max, scenario.collateral.liquidation_slippage)
        if any(type(value) not in (int, float) or not isfinite(value) for value in collateral_values):
            raise ValueError("invalid auction collateral ratios")
        if (min(collateral_values[:3]) < 0 or scenario.collateral.alpha_min > scenario.collateral.alpha_max
            or not 0 <= scenario.collateral.liquidation_slippage < 1):
            raise ValueError("invalid liquidation slippage")
        if scenario.collateral.require_top_up:
            raise ValueError("auction mode does not support automatic top-up")
        if scenario.collateral.stress_drop is not None and (
            type(scenario.collateral.stress_drop) not in (int, float)
            or not isfinite(scenario.collateral.stress_drop)
            or not 0 <= scenario.collateral.stress_drop < 1
        ):
            raise ValueError("invalid auction stress_drop")
        if len(price_path.prices) != rosca.periods or any(
            type(price) not in (int, float) or not isfinite(price) or price <= 0
            for price in price_path.prices
        ):
            raise ValueError("invalid due-date ETH prices")
        required_days = (rosca.periods - 1) * rosca.period_days + 1 + scenario.grace_days
        if len(price_path.daily_prices) < required_days:
            raise ValueError("daily ETH price path lacks settlement tail")
        if any(type(price) not in (int, float) or not isfinite(price) or price <= 0
               for price in price_path.daily_prices):
            raise ValueError("invalid daily ETH execution price")
        ids = [agent.member_id for agent in scenario.agents]
        if sorted(ids) != list(range(rosca.members)):
            raise ValueError("auction agents need unique contiguous member IDs")
        for agent in scenario.agents:
            if (
                type(agent.reputation) not in (int, float)
                or not isfinite(agent.reputation)
                or not 0 <= agent.reputation <= 1
                or type(agent.available_eth) not in (int, float)
                or not isfinite(agent.available_eth)
                or agent.available_eth < 0
                or type(agent.usdc_capacity) not in (int, float)
                or not isfinite(agent.usdc_capacity)
                or agent.usdc_capacity < 0
                or agent.settlement_mode not in ("eth_first", "usdc_first")
                or (agent.payment_day_offset is not None and (
                    type(agent.payment_day_offset) is not int
                    or not 0 <= agent.payment_day_offset <= scenario.grace_days
                ))
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
        seen_events: set[tuple[int, int]] = set()
        self.events_by_day: dict[int, list[tuple[str, int]]] = {}
        for kind, events in (("forced_default", scenario.forced_defaults),
                             ("missed_contribution", scenario.missed_contributions)):
            for event in events:
                if (type(event.day) is not int or event.day < 0
                    or event.day > (rosca.periods - 1) * rosca.period_days
                    or type(event.member_id) is not int or event.member_id not in ids):
                    raise ValueError("invalid auction event")
                if kind == "missed_contribution" and event.day % rosca.period_days:
                    raise ValueError("missed contribution must occur on a due date")
                key = (event.day, event.member_id)
                if key in seen_events:
                    raise ValueError("duplicate or conflicting auction event")
                seen_events.add(key)
                self.events_by_day.setdefault(event.day, []).append((kind, event.member_id))
        self.overrides_by_day: dict[int, float] = {}
        for override in scenario.execution_price_overrides:
            if (type(override.day) is not int or not 0 <= override.day < required_days
                or type(override.price) not in (int, float)
                or not isfinite(override.price) or override.price <= 0):
                raise ValueError("invalid execution price override")
            if override.day in self.overrides_by_day:
                raise ValueError("duplicate execution price override")
            self.overrides_by_day[override.day] = override.price
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
        self.default_ids: set[int] = set()
        self.total_collateral_locked = 0.0
        self.eth_sale_proceeds = 0.0
        self._period_trace: list[AuctionPeriodTrace] = []

    @property
    def period_trace(self) -> tuple[AuctionPeriodTrace, ...]:
        return tuple(self._period_trace)

    def _record_period(
        self, period: int, day: int, before: tuple[tuple[float, float, float], ...],
        winner_id: int | None, bid_interest: float, net_payout: float,
        insufficient_eth_bidder_ids: tuple[int, ...],
    ) -> None:
        agents = tuple(self.agents_by_id[i] for i in range(self.auction.rosca.members))
        self._period_trace.append(AuctionPeriodTrace(
            period=period, day=day,
            contributions_by_member=tuple(a.total_contributed - old[0] for a, old in zip(agents, before)),
            winner_id=winner_id,
            gross_pot=self.auction.rosca.members * self.auction.rosca.contribution,
            bid_interest=bid_interest,
            net_payout=net_payout,
            eth_locked_by_member=tuple(a.initial_locked_eth - old[1] for a, old in zip(agents, before)),
            eth_released_by_member=tuple(a.eth_released - old[2] for a, old in zip(agents, before)),
            pool_cash=self.cash_balance,
            retained_interest=self.interest_balance,
            remaining_obligation_by_member=tuple(a.remaining_obligation for a in agents),
            retained_eth_by_member=tuple(a.locked_eth for a in agents),
            insufficient_eth_bidder_ids=insufficient_eth_bidder_ids,
        ))

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
        if day in self.events_by_day:
            self._freeze_events(day)
            return
        period = self.period
        before = tuple(
            (a.total_contributed, a.initial_locked_eth, a.eth_released)
            for a in (self.agents_by_id[i] for i in range(rosca.members))
        )
        price = self.price_path.prices[self.period]
        self.cash_balance += sum(agent.contribute(day) for agent in self.agents_by_id.values())
        candidates = sorted(
            self.bids_by_period.get(self.period, ()),
            key=lambda bid: (-bid.rate, bid.member_id),
        )
        winner: AuctionAgent | None = None
        winning_bid: AuctionBid | None = None
        required_eth = 0.0
        insufficient_eth_ids: list[int] = []
        for bid in candidates:
            agent = self.agents_by_id[bid.member_id]
            if agent.payout_day is not None:
                continue
            needed = self._required_eth(agent, self.period, price)
            if agent.available_eth + 1e-9 >= needed:
                winner, winning_bid, required_eth = agent, bid, needed
                break
            insufficient_eth_ids.append(agent.member_id)
        if winner is None or winning_bid is None:
            self.stop_reason = "no_eligible_bid"
            self.freeze_day = day
            self._record_period(period, day, before, None, 0.0, 0.0, tuple(insufficient_eth_ids))
            return
        winner.available_eth -= required_eth
        winner.locked_eth = required_eth
        winner.initial_locked_eth = required_eth
        winner.initial_obligation = rosca.contribution * (rosca.periods - self.period - 1)
        self.total_collateral_locked += required_eth
        winner.remaining_obligation = winner.initial_obligation
        winner.payout_day = day
        winner.winning_bid = winning_bid.rate
        gross = rosca.members * rosca.contribution
        discount = gross * winning_bid.rate
        winner.bid_interest_paid = discount
        winner.net_payout = gross - discount
        self.cash_balance -= winner.net_payout
        self.interest_balance += discount
        self.payout_order.append(winner.member_id)
        self._record_period(period, day, before, winner.member_id, discount, winner.net_payout,
                            tuple(insufficient_eth_ids))
        self.period += 1
        if self.period == rosca.periods:
            self.stop_reason = "completed"
            self.freeze_day = day

    def _freeze_events(self, day: int) -> None:
        batch = self.events_by_day[day]
        for kind, member_id in batch:
            paid = self.agents_by_id[member_id].payout_day is not None
            if (kind == "forced_default" and not paid) or (kind == "missed_contribution" and paid):
                raise ValueError("auction event conflicts with realized payout timing")
        self.default_ids = {member_id for _, member_id in batch}
        self.stop_reason = "default"
        self.freeze_day = day

    def _execution_price(self, day: int) -> float:
        prices = self.price_path.daily_prices
        if day >= len(prices):
            raise ValueError("daily ETH price path lacks settlement tail")
        price = self.overrides_by_day.get(day, prices[day])
        if not isfinite(price) or price <= 0:
            raise ValueError("invalid daily ETH execution price")
        return price

    def _sell(self, agent: AuctionAgent, obligation: float, day: int) -> float:
        price = self._execution_price(day)
        sale = settle_default(obligation, agent.locked_eth,
                              price,
                              self.auction.collateral.liquidation_slippage)
        if sale.liquidated_eth > 0:
            agent.eth_sale_day = day
            agent.eth_sale_price = price * (1 - self.auction.collateral.liquidation_slippage)
        agent.eth_sold += sale.liquidated_eth
        agent.eth_returned += sale.returned_eth
        agent.locked_eth = 0.0
        self.eth_sale_proceeds += sale.recovered
        self.cash_balance += sale.recovered
        return sale.recovered

    def _settle(self) -> AuctionRunResult:
        assert self.stop_reason is not None and self.freeze_day is not None
        freeze = self.freeze_day
        deadline = freeze + self.auction.grace_days
        if self.stop_reason != "completed":
            for agent in self.agents_by_id.values():
                if agent.payout_day is None:
                    continue
                obligation = agent.remaining_obligation
                if obligation <= 1e-9:
                    agent.eth_returned += agent.locked_eth
                    agent.locked_eth = 0.0
                    continue
                if agent.member_id in self.default_ids:
                    recovered = self._sell(agent, obligation, freeze)
                    agent.obligation_uncollected = max(0.0, obligation - recovered)
                    continue
                payment_day = freeze + (agent.payment_day_offset if agent.payment_day_offset is not None else self.auction.grace_days)
                agent.payment_day = payment_day
                if agent.settlement_mode == "eth_first":
                    obligation -= self._sell(agent, obligation, freeze)
                    payment = min(obligation, agent.usdc_capacity)
                else:
                    payment = min(obligation, agent.usdc_capacity)
                agent.usdc_settlement_paid = payment
                self.cash_balance += payment
                obligation -= payment
                if agent.settlement_mode == "usdc_first":
                    obligation -= self._sell(agent, obligation, deadline) if obligation > 1e-9 else 0.0
                    if agent.locked_eth:
                        agent.eth_returned += agent.locked_eth
                        agent.locked_eth = 0.0
                agent.obligation_uncollected = max(0.0, obligation)
        else:
            for agent in self.agents_by_id.values():
                agent.eth_returned += agent.locked_eth
                agent.locked_eth = 0.0

        claims = {a.member_id: a.total_contributed for a in self.agents_by_id.values() if a.payout_day is None}
        total_claim = sum(claims.values())
        cash_before_waterfall = self.cash_balance
        repaid = min(total_claim, self.cash_balance)
        non_interest_cash = max(0.0, self.cash_balance - self.interest_balance)
        interest_used = min(self.interest_balance, max(0.0, repaid - non_interest_cash))
        default_interest = sum(a.bid_interest_paid for a in self.agents_by_id.values()
                               if a.member_id in self.default_ids)
        interest_from_defaulting = min(interest_used, default_interest)
        for member_id, claim in claims.items():
            self.agents_by_id[member_id].principal_repaid = repaid * claim / total_claim if total_claim else 0.0
        self.cash_balance -= repaid
        interest_distributed = 0.0
        eligible = [a for a in self.agents_by_id.values() if a.member_id not in self.default_ids]
        weights = {a.member_id: sum(amount * max(0, min(a.payout_day if a.payout_day is not None else freeze, freeze) - day)
                                     for day, amount in a.pre_payout_contributions) for a in eligible}
        if sum(weights.values()) <= 1e-9:
            weights = {a.member_id: sum(amount for _, amount in a.pre_payout_contributions) for a in eligible}
        total_weight = sum(weights.values())
        if total_weight > 0:
            distributable = self.cash_balance
            for agent in eligible:
                amount = distributable * weights[agent.member_id] / total_weight
                agent.interest_received = amount
                interest_distributed += amount
            self.cash_balance -= interest_distributed
        results = tuple(
            AuctionAgentResult(
                member_id=a.member_id, payout_day=a.payout_day, winning_bid=a.winning_bid,
                net_payout=a.net_payout, total_contributed=a.total_contributed,
                principal_claim=claims.get(a.member_id, 0.0), principal_repaid=a.principal_repaid,
                principal_loss=max(0.0, claims.get(a.member_id, 0.0) - a.principal_repaid),
                interest_received=a.interest_received, eth_locked=a.initial_locked_eth,
                eth_released=a.eth_released, eth_sold=a.eth_sold, eth_returned=a.eth_returned,
                eth_sale_day=a.eth_sale_day, eth_sale_price=a.eth_sale_price,
                usdc_settlement_paid=a.usdc_settlement_paid, settlement_mode=a.settlement_mode,
                payment_day=a.payment_day, obligation_uncollected=a.obligation_uncollected,
                bid_interest_paid=a.bid_interest_paid,
                is_trigger_default=a.member_id in self.default_ids,
                settlement_shortfall=a.payout_day is not None and a.obligation_uncollected > 1e-9,
            ) for a in (self.agents_by_id[i] for i in sorted(self.agents_by_id))
        )
        assert abs(cash_before_waterfall - repaid - interest_distributed - self.cash_balance) < 1e-6
        total_inflow = (sum(a.total_contributed + a.usdc_settlement_paid for a in self.agents_by_id.values())
                        + self.eth_sale_proceeds)
        total_outflow = (sum(a.net_payout for a in self.agents_by_id.values())
                         + repaid + interest_distributed + self.cash_balance)
        assert abs(total_inflow - total_outflow) < 1e-6
        assert all(abs(r.eth_locked - r.eth_released - r.eth_sold - r.eth_returned) < 1e-6 for r in results)
        assert self.cash_balance >= -1e-6
        return AuctionRunResult(
            run_id=self.run_id, policy=self.policy, seed=self.seed,
            price_label=self.price_path.label, price_window_start=self.price_path.start_date,
            stop_reason=self.stop_reason, freeze_day=freeze,
            settlement_day=deadline if self.stop_reason != "completed" else freeze,
            default_count=len(self.default_ids), payout_order=tuple(self.payout_order),
            interest_retained=self.interest_balance, interest_used=interest_used,
            interest_distributed=interest_distributed,
            obligation_uncollected=sum(r.obligation_uncollected for r in results),
            principal_loss=sum(r.principal_loss for r in results),
            worst_member_loss=max(r.principal_loss for r in results),
            total_collateral_locked=self.total_collateral_locked,
            eth_sale_proceeds=self.eth_sale_proceeds, ending_cash=self.cash_balance,
            agent_results=results,
            interest_used_from_defaulting=interest_from_defaulting,
            interest_used_from_other_members=interest_used - interest_from_defaulting,
            secondary_shortfall_count=sum(r.settlement_shortfall and not r.is_trigger_default
                                          for r in results),
        )

    def run(self) -> AuctionRunResult:
        while self.stop_reason is None:
            due = self.period * self.auction.rosca.period_days
            prior_events = [day for day in self.events_by_day if (self.period == 0 or day > (self.period - 1) * self.auction.rosca.period_days) and day < due]
            if prior_events:
                self._freeze_events(min(prior_events))
                break
            self.step()
            if self.stop_reason is None:
                next_due = self.period * self.auction.rosca.period_days
                between = [day for day in self.events_by_day if due < day < next_due]
                if between:
                    self._freeze_events(min(between))
        return self._settle()
