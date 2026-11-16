from dataclasses import replace

import pytest

from rosca_sim.auction import AuctionEvent
from rosca_sim.due_date_auction import DueDateAuctionModel, DueDateAuctionScenario
from rosca_sim.prices import PricePath
from test_auction import scenario


def path_with(overrides):
    daily = tuple(overrides.get(day, 1.0) for day in range(158))
    return PricePath(daily[:151:30], "test", None, daily)


def wire(ratio=1.8, **options):
    case = scenario([(period, period, 0.0) for period in range(6)], available_eth=2000)
    case = replace(case, collateral=replace(case.collateral, fixed_ratio=ratio))
    policies = {key: options.pop(key) for key in ("strategic_default_on_due",
                                                  "settlement_capacity_fraction") if key in options}
    return DueDateAuctionScenario(replace(case, **options), **policies)


@pytest.mark.parametrize("ratio,enabled,prices,default", [
    (1.8, True, {30: 0.5}, True),
    (2.0, True, {30: 0.5}, False),
    (1.8, False, {30: 0.5}, False),
    (1.8, True, {15: 0.4}, False),
])
def test_strategic_default_only_at_due_date(ratio, enabled, prices, default):
    model = DueDateAuctionModel(
        wire(ratio, strategic_default_on_due=enabled), "fixed", path_with(prices)
    )
    result = model.run()
    if default:
        assert result.freeze_day == 30
        assert result.payout_order == (0,)
        assert model.strategic_default_gaps == {0: pytest.approx(50)}
        assert all(member.total_contributed == 100 for member in result.agent_results)
        assert result.worst_member_loss == pytest.approx(10)
    else:
        assert result.stop_reason == "completed"
        assert not model.strategic_default_gaps


def test_same_day_triggers_and_scripted_default_are_settled_once():
    case = wire(strategic_default_on_due=True, forced_defaults=(AuctionEvent(0, 60),))
    model = DueDateAuctionModel(case, "fixed", path_with({60: 0.4}))
    result = model.run()
    assert result.freeze_day == 60
    assert result.payout_order == (0, 1)
    assert model.strategic_default_gaps == {0: pytest.approx(40), 1: pytest.approx(112)}
    assert result.default_count == 2
    assert result.eth_sale_proceeds == pytest.approx(648)
    assert all(member.total_contributed == 200 for member in result.agent_results)


@pytest.mark.parametrize("fraction,paid,sold", [(0, 0, 400), (0.5, 200, 200), (1, 400, 0)])
def test_settlement_share_uses_obligation_at_freeze(fraction, paid, sold):
    case = wire(settlement_capacity_fraction=fraction, forced_defaults=(AuctionEvent(0, 60),))
    result = DueDateAuctionModel(case, "fixed", path_with({})).run()
    compliant = result.agent_results[1]
    assert result.agent_results[0].usdc_settlement_paid == 0
    assert compliant.payment_day == 67
    assert compliant.usdc_settlement_paid == pytest.approx(paid)
    assert compliant.eth_sold == pytest.approx(sold)
    assert compliant.eth_sale_day == (67 if sold else None)


@pytest.mark.parametrize("fraction", [-0.1, 1.01, float("nan"), True])
def test_invalid_settlement_share_rejected(fraction):
    with pytest.raises(ValueError, match="settlement capacity fraction"):
        DueDateAuctionModel(wire(settlement_capacity_fraction=fraction), "fixed", path_with({}))
