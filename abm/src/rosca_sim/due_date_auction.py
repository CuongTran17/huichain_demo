"""Phase B policies layered on the auction engine used by Phase A."""

from dataclasses import dataclass
from math import isfinite

from rosca_sim.auction import AuctionRoscaModel, AuctionScenario
from rosca_sim.prices import PricePath


@dataclass(frozen=True)
class DueDateAuctionScenario:
    auction: AuctionScenario
    strategic_default_on_due: bool = False
    settlement_capacity_fraction: float | None = None


class DueDateAuctionModel(AuctionRoscaModel):
    def __init__(self, scenario: DueDateAuctionScenario, policy, price_path: PricePath):
        if type(scenario.strategic_default_on_due) is not bool:
            raise ValueError("strategic_default_on_due must be a boolean")
        fraction = scenario.settlement_capacity_fraction
        if fraction is not None and (
            type(fraction) not in (int, float) or not isfinite(fraction) or not 0 <= fraction <= 1
        ):
            raise ValueError("settlement capacity fraction must be between 0 and 1")
        super().__init__(scenario.auction, policy, price_path)
        self.due_date_policy = scenario
        self.strategic_default_gaps: dict[int, float] = {}

    def step(self) -> None:
        if self.stop_reason is None and self.due_date_policy.strategic_default_on_due:
            day = self.period * self.auction.rosca.period_days
            price = self._execution_price(day) * (1 - self.auction.collateral.liquidation_slippage)
            events = self.events_by_day.get(day, [])
            scripted_ids = {member_id for _, member_id in events}
            for agent in self.agents_by_id.values():
                if agent.payout_day is None or agent.remaining_obligation <= 1e-9:
                    continue
                gap = agent.remaining_obligation - agent.locked_eth * price
                if gap > 1e-9:
                    self.strategic_default_gaps[agent.member_id] = gap
                    if agent.member_id not in scripted_ids:
                        self.events_by_day.setdefault(day, []).append(("forced_default", agent.member_id))
        super().step()

    def _settle(self):
        fraction = self.due_date_policy.settlement_capacity_fraction
        if fraction is not None and self.stop_reason != "completed":
            for agent in self.agents_by_id.values():
                agent.usdc_capacity = fraction * agent.remaining_obligation
        return super()._settle()
