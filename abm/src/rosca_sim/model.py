from dataclasses import dataclass
from typing import Literal

from mesa import Agent, Model


EPSILON = 1e-9


@dataclass(frozen=True)
class RoscaConfig:
    members: int
    periods: int
    contribution: float
    period_days: int
    reserve_initial: float = 0.0


@dataclass(frozen=True)
class CollateralConfig:
    fixed_ratio: float
    alpha_min: float
    alpha_max: float
    require_top_up: bool = False
    stress_drop: float | None = None
    liquidation_slippage: float = 0.0


@dataclass(frozen=True)
class BehaviorConfig:
    reputation_loss: float
    future_access_loss: float
    decision_mode: str = "every_due_date"
    decision_rule: str = "deterministic"


def fixed_collateral_ratio(config: CollateralConfig) -> float:
    return config.fixed_ratio


def reputation_collateral_ratio(
    reputation: float, config: CollateralConfig
) -> float:
    if not 0.0 <= reputation <= 1.0:
        raise ValueError("reputation must be between 0 and 1")
    return config.alpha_max - (config.alpha_max - config.alpha_min) * reputation


def strategic_default_utility(
    remaining_obligation: float,
    collateral_value: float,
    reputation_loss: float,
    future_access_loss: float,
) -> float:
    collateral_loss = min(collateral_value, remaining_obligation)
    return remaining_obligation - collateral_loss - reputation_loss - future_access_loss


@dataclass(frozen=True)
class AgentSeed:
    position: int
    reputation: float


@dataclass(frozen=True)
class RunInputs:
    run_id: int
    seed: int
    agents: tuple[AgentSeed, ...]
    prices: tuple[float, ...]
    price_label: str
    price_window_start: str | None
    daily_prices: tuple[float, ...] = ()
    forced_defaults: tuple["ForcedDefault", ...] = ()


@dataclass(frozen=True)
class ForcedDefault:
    position: int
    day: int


@dataclass(frozen=True)
class PeriodRecord:
    period: int
    opening_pool: float
    contributions: float
    recovered_collateral: float
    reserve_draw: float
    scheduled_payout: float
    actual_payout: float
    payout_shortfall: float
    closing_pool: float
    closing_reserve: float


@dataclass(frozen=True)
class SimulationResult:
    run_id: int
    policy: str
    seed: int
    price_label: str
    price_window_start: str | None
    default_count: int
    default_loss: float
    capital_locked: float
    net_liquidity: float
    completion_rate: float
    recovered_collateral: float
    participant_shortfall: float
    short_payout_count: int
    reserve_initial: float
    reserve_drawn: float
    reserve_remaining: float
    reserve_required_for_full_payouts: float
    margin_breach_agent_days: int
    recipient_payouts: tuple[float, ...]
    recipient_shortfalls: tuple[float, ...]
    recipient_collateral_locked: tuple[float, ...]


@dataclass(frozen=True)
class DefaultSettlement:
    recovered: float
    default_loss: float
    liquidated_eth: float
    returned_eth: float


def settle_default(
    remaining_obligation: float,
    locked_eth: float,
    eth_price: float,
    slippage: float = 0.0,
) -> DefaultSettlement:
    if eth_price <= 0:
        raise ValueError("ETH price must be positive")
    if not 0.0 <= slippage < 1.0:
        raise ValueError("slippage must be between 0 and 1")
    sale_price = eth_price * (1.0 - slippage)
    collateral_value = locked_eth * sale_price
    recovered = min(collateral_value, remaining_obligation)
    liquidated_eth = recovered / sale_price
    return DefaultSettlement(
        recovered=recovered,
        default_loss=max(0.0, remaining_obligation - recovered),
        liquidated_eth=liquidated_eth,
        returned_eth=max(0.0, locked_eth - liquidated_eth),
    )


class RoscaAgent(Agent):
    def __init__(self, model: "RoscaModel", seed: AgentSeed):
        super().__init__(model)
        self.position = seed.position
        self.reputation = seed.reputation
        self.has_received_payout = False
        self.remaining_obligation = 0.0
        self.locked_eth = 0.0
        self.initial_locked_eth = 0.0
        self.collateral_locked_at_payout = 0.0
        self.initial_post_payout_obligation = 0.0
        self.required_ratio = 0.0
        self.active = True
        self.default_period: int | None = None
        self.default_day: int | None = None
        self.total_contributed = 0.0
        self.payout_received = 0.0
        self.payout_shortfall = 0.0
        self.collateral_released = 0.0
        self.returned_eth = 0.0

    def should_default(self, eth_price: float) -> bool:
        utility = strategic_default_utility(
            remaining_obligation=self.remaining_obligation,
            collateral_value=self.locked_eth * eth_price,
            reputation_loss=self.model.behavior.reputation_loss,
            future_access_loss=self.model.behavior.future_access_loss,
        )
        return utility > EPSILON

    def contribute(self) -> float:
        amount = self.model.rosca.contribution
        self.total_contributed += amount
        if self.has_received_payout and self.remaining_obligation > EPSILON:
            self.remaining_obligation = max(0.0, self.remaining_obligation - amount)
            self.release_collateral()
        return amount

    def release_collateral(self) -> None:
        if self.initial_post_payout_obligation <= EPSILON:
            return
        release = min(
            self.locked_eth,
            self.initial_locked_eth
            * self.model.rosca.contribution
            / self.initial_post_payout_obligation,
        )
        self.locked_eth = max(0.0, self.locked_eth - release)
        self.collateral_released += release

    def lock_for_payout(self, period: int, eth_price: float) -> float:
        obligation = self.model.rosca.contribution * (self.model.rosca.periods - period - 1)
        if self.model.policy == "fixed":
            ratio = fixed_collateral_ratio(self.model.collateral)
        else:
            ratio = reputation_collateral_ratio(self.reputation, self.model.collateral)
        if self.model.collateral.stress_drop is not None:
            stressed_ratio = 1.0 / (
                (1.0 - self.model.collateral.stress_drop)
                * (1.0 - self.model.collateral.liquidation_slippage)
            )
            ratio = max(ratio, stressed_ratio)
        required_value = ratio * obligation
        self.collateral_locked_at_payout = required_value
        self.required_ratio = ratio
        self.initial_post_payout_obligation = obligation
        self.remaining_obligation = obligation
        self.initial_locked_eth = required_value / eth_price if required_value > 0 else 0.0
        self.locked_eth = self.initial_locked_eth
        return required_value


class RoscaModel(Model):
    def __init__(
        self,
        rosca: RoscaConfig,
        collateral: CollateralConfig,
        behavior: BehaviorConfig,
        policy: Literal["fixed", "reputation_adjusted"],
        inputs: RunInputs,
    ):
        super().__init__(rng=inputs.seed)
        if rosca.members != rosca.periods:
            raise ValueError("members must equal periods in version one")
        if len(inputs.agents) != rosca.members or len(inputs.prices) != rosca.periods:
            raise ValueError("run inputs do not match ROSCA dimensions")
        days_needed = (rosca.periods - 1) * rosca.period_days + 1
        if inputs.daily_prices and len(inputs.daily_prices) != days_needed:
            raise ValueError("daily price path does not match ROSCA duration")
        if inputs.daily_prices and any(
            inputs.daily_prices[period * rosca.period_days] != inputs.prices[period]
            for period in range(rosca.periods)
        ):
            raise ValueError("due-date and daily ETH prices disagree")
        if policy not in {"fixed", "reputation_adjusted"}:
            raise ValueError(f"unknown policy: {policy}")
        if rosca.reserve_initial < 0:
            raise ValueError("reserve_initial must be nonnegative")
        self.rosca = rosca
        self.collateral = collateral
        self.behavior = behavior
        self.policy = policy
        self.inputs = inputs
        self.members = sorted(
            (RoscaAgent(self, seed) for seed in inputs.agents), key=lambda agent: agent.position
        )
        self.pool_balance = 0.0
        self.reserve_balance = rosca.reserve_initial
        self.period_records: list[PeriodRecord] = []
        self.total_default_loss = 0.0
        self.total_recovered_collateral = 0.0
        self.total_capital_locked = 0.0
        self.fully_funded_payouts = 0
        self.margin_breach_agent_days = 0
        self.forced_defaults: dict[int, set[int]] = {}
        for event in inputs.forced_defaults:
            self.forced_defaults.setdefault(event.day, set()).add(event.position)
        if sum(map(len, self.forced_defaults.values())) != len(inputs.forced_defaults):
            raise ValueError("duplicate forced default event")
        if any(
            not 0 <= event.position < rosca.members
            or not event.position * rosca.period_days < event.day < days_needed
            for event in inputs.forced_defaults
        ):
            raise ValueError("forced default must follow the recipient's payout")

    def _observe_margin(self, eth_price: float) -> None:
        self.margin_breach_agent_days += sum(
            agent.active
            and agent.has_received_payout
            and agent.remaining_obligation > EPSILON
            and agent.locked_eth * eth_price + EPSILON
            < agent.required_ratio * agent.remaining_obligation
            for agent in self.members
        )

    def _process_defaults(self, day: int, eth_price: float, strategic: bool) -> float:
        recovered_this_period = 0.0
        for agent in self.members:
            if (
                agent.active
                and agent.has_received_payout
                and agent.remaining_obligation > EPSILON
                and (
                    agent.position in self.forced_defaults.get(day, ())
                    or (strategic and agent.should_default(eth_price))
                )
            ):
                settlement = settle_default(
                    agent.remaining_obligation,
                    agent.locked_eth,
                    eth_price,
                    self.collateral.liquidation_slippage,
                )
                agent.active = False
                agent.default_day = day
                agent.default_period = (day + self.rosca.period_days - 1) // self.rosca.period_days
                agent.locked_eth = 0.0
                agent.returned_eth += settlement.returned_eth
                self.total_default_loss += settlement.default_loss
                self.total_recovered_collateral += settlement.recovered
                recovered_this_period += settlement.recovered
        self.pool_balance += recovered_this_period
        return recovered_this_period

    def step(self) -> None:
        period = len(self.period_records)
        due_day = period * self.rosca.period_days
        eth_price = self.inputs.prices[period]
        opening_pool = self.pool_balance
        recovered = 0.0
        if self.inputs.daily_prices and period:
            for day in range((period - 1) * self.rosca.period_days + 1, due_day):
                daily_price = self.inputs.daily_prices[day]
                self._observe_margin(daily_price)
                recovered += self._process_defaults(day, daily_price, strategic=False)
        self._observe_margin(eth_price)
        recovered += self._process_defaults(due_day, eth_price, strategic=True)

        contributions = 0.0
        for agent in self.members:
            if agent.active:
                contributions += agent.contribute()
        self.pool_balance += contributions

        recipient = self.members[period]
        locked_value = recipient.lock_for_payout(period, eth_price)
        self.total_capital_locked += locked_value

        scheduled_payout = self.rosca.members * self.rosca.contribution
        reserve_draw = min(
            max(0.0, scheduled_payout - self.pool_balance), self.reserve_balance
        )
        self.reserve_balance -= reserve_draw
        self.pool_balance += reserve_draw
        actual_payout = min(self.pool_balance, scheduled_payout)
        self.pool_balance = max(0.0, self.pool_balance - actual_payout)
        recipient.payout_received += actual_payout
        payout_shortfall = max(0.0, scheduled_payout - actual_payout)
        recipient.payout_shortfall += payout_shortfall
        recipient.has_received_payout = True
        if abs(actual_payout - scheduled_payout) <= EPSILON:
            self.fully_funded_payouts += 1

        self.period_records.append(
            PeriodRecord(
                period=period,
                opening_pool=opening_pool,
                contributions=contributions,
                recovered_collateral=recovered,
                reserve_draw=reserve_draw,
                scheduled_payout=scheduled_payout,
                actual_payout=actual_payout,
                payout_shortfall=payout_shortfall,
                closing_pool=self.pool_balance,
                closing_reserve=self.reserve_balance,
            )
        )

    def run(self) -> SimulationResult:
        while len(self.period_records) < self.rosca.periods:
            self.step()
        payouts = sum(agent.payout_received for agent in self.members)
        return SimulationResult(
            run_id=self.inputs.run_id,
            policy=self.policy,
            seed=self.inputs.seed,
            price_label=self.inputs.price_label,
            price_window_start=self.inputs.price_window_start,
            default_count=sum(agent.default_period is not None for agent in self.members),
            default_loss=self.total_default_loss,
            capital_locked=self.total_capital_locked,
            net_liquidity=payouts - self.total_capital_locked,
            completion_rate=self.fully_funded_payouts / self.rosca.periods,
            recovered_collateral=self.total_recovered_collateral,
            participant_shortfall=sum(agent.payout_shortfall for agent in self.members),
            short_payout_count=sum(
                record.payout_shortfall > EPSILON for record in self.period_records
            ),
            reserve_initial=self.rosca.reserve_initial,
            reserve_drawn=self.rosca.reserve_initial - self.reserve_balance,
            reserve_remaining=self.reserve_balance,
            reserve_required_for_full_payouts=(
                self.rosca.reserve_initial - self.reserve_balance
                + sum(agent.payout_shortfall for agent in self.members)
            ),
            margin_breach_agent_days=self.margin_breach_agent_days,
            recipient_payouts=tuple(agent.payout_received for agent in self.members),
            recipient_shortfalls=tuple(agent.payout_shortfall for agent in self.members),
            recipient_collateral_locked=tuple(
                agent.collateral_locked_at_payout for agent in self.members
            ),
        )
