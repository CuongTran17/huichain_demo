import math

import pytest

from dataclasses import replace

from rosca_sim.auction import AuctionAgentSeed, AuctionBid, AuctionEvent, AuctionPriceOverride, AuctionRoscaModel, AuctionScenario
from rosca_sim.model import BehaviorConfig, CollateralConfig, RoscaConfig
from rosca_sim.prices import PricePath


def scenario(bids, available_eth=1000.0):
    return AuctionScenario(
        rosca=RoscaConfig(6, 6, 100.0, 30),
        collateral=CollateralConfig(1.0, 1.0, 1.0),
        behavior=BehaviorConfig(10_000.0, 10_000.0),
        agents=tuple(
            AuctionAgentSeed(i, 0.5, available_eth, "usdc_first", 500.0)
            for i in range(6)
        ),
        bids=tuple(AuctionBid(*bid) for bid in bids),
    )


def constant_prices():
    return PricePath((1.0,) * 6, "constant", None, (1.0,) * 158)


def test_six_member_winning_discount_and_lock():
    model = AuctionRoscaModel(
        scenario([(0, 0, 0.20), (0, 1, 0.10)]), "fixed", constant_prices()
    )
    model.step()
    winner = model.agents_by_id[0]
    assert winner.net_payout == pytest.approx(480.0)
    assert model.interest_balance == pytest.approx(120.0)
    assert winner.remaining_obligation == pytest.approx(500.0)
    assert winner.locked_eth == pytest.approx(500.0)
    assert model.cash_balance == pytest.approx(120.0)
    assert all(model.agents_by_id[i].locked_eth == 0 for i in range(1, 6))


def test_trace_matches_first_auction():
    model = AuctionRoscaModel(scenario([(0, 0, 0.20)]), "fixed", constant_prices())
    model.step()
    trace = model.period_trace
    assert len(trace) == 1
    assert trace[0].period == 0
    assert trace[0].day == 0
    assert trace[0].winner_id == 0
    assert trace[0].contributions_by_member == (100.0,) * 6
    assert trace[0].gross_pot == 600.0
    assert trace[0].bid_interest == 120.0
    assert trace[0].net_payout == 480.0
    assert trace[0].eth_locked_by_member == (500.0,) + (0.0,) * 5
    assert trace[0].pool_cash == 120.0


def test_trace_keeps_eth_after_fixed_contribution():
    model = AuctionRoscaModel(
        scenario([(0, 0, 0.20), (1, 1, 0.10)]), "fixed", constant_prices()
    )
    model.step()
    model.step()
    assert model.period_trace[1].contributions_by_member[0] == 100.0
    assert model.period_trace[1].eth_released_by_member[0] == 0.0
    assert model.agents_by_id[0].remaining_obligation == 400.0
    assert model.agents_by_id[0].locked_eth == 500.0
    assert model.period_trace[1].winner_id == 1


def test_freeze_trace_omits_next_round():
    original = scenario([(0, 0, 0.20), (1, 1, 0.10)])
    case = replace(original, forced_defaults=(AuctionEvent(0, 30),))
    model = AuctionRoscaModel(case, "fixed", constant_prices())
    result = model.run()
    assert result.freeze_day == 30
    assert len(model.period_trace) == 1
    assert model.period_trace[0].winner_id == 0


def test_same_day_default_trace_order_independent():
    original = scenario([(0, 0, 0.20), (1, 1, 0.10)])
    events = (AuctionEvent(0, 31), AuctionEvent(1, 31))
    first = AuctionRoscaModel(replace(original, forced_defaults=events), "fixed", constant_prices())
    second = AuctionRoscaModel(
        replace(original, forced_defaults=tuple(reversed(events)) + (AuctionEvent(0, 60),)),
        "fixed", constant_prices(),
    )
    first_result = first.run()
    second_result = second.run()
    assert first_result == second_result
    assert first.period_trace == second.period_trace


def test_paid_member_cannot_bid_again_or_pay_extra_interest():
    model = AuctionRoscaModel(
        scenario([(0, 0, 0.20), (1, 0, 0.90), (1, 1, 0.10)]),
        "fixed",
        constant_prices(),
    )
    model.step()
    model.step()
    assert model.payout_order == [0, 1]
    assert model.agents_by_id[0].total_contributed == pytest.approx(200.0)
    assert model.agents_by_id[0].remaining_obligation == pytest.approx(400.0)


def test_equal_bids_choose_lowest_member_id():
    model = AuctionRoscaModel(
        scenario([(0, 2, 0.10), (0, 1, 0.10)]), "fixed", constant_prices()
    )
    model.step()
    assert model.payout_order == [1]


def test_last_recipient_locks_no_eth():
    model = AuctionRoscaModel(
        scenario([(period, period, 0.0) for period in range(6)]),
        "fixed",
        constant_prices(),
    )
    for _ in range(6):
        model.step()
    assert model.payout_order == list(range(6))
    assert model.agents_by_id[5].locked_eth == 0.0


def test_unfunded_high_bid_is_skipped():
    original = scenario([(0, 0, 0.20), (0, 1, 0.10)])
    agents = list(original.agents)
    agents[0] = AuctionAgentSeed(0, 0.5, 0.0, "usdc_first", 500.0)
    model = AuctionRoscaModel(
        AuctionScenario(original.rosca, original.collateral, original.behavior, tuple(agents), original.bids),
        "fixed", constant_prices(),
    )
    model.step()
    assert model.payout_order == [1]
    assert model.agents_by_id[0].locked_eth == 0.0


def test_no_eligible_bid_freezes_without_payout():
    model = AuctionRoscaModel(
        scenario([(0, 0, 0.20)], available_eth=0.0), "fixed", constant_prices()
    )
    model.step()
    assert model.stop_reason == "no_eligible_bid"
    assert model.payout_order == []
    assert model.cash_balance == pytest.approx(600.0)


@pytest.mark.parametrize("rate", [True, -0.1, 1.0, math.nan, math.inf])
def test_invalid_bid_rate_is_rejected(rate):
    with pytest.raises(ValueError, match="bid rate"):
        AuctionRoscaModel(scenario([(0, 0, rate)]), "fixed", constant_prices())


def test_duplicate_bid_is_rejected():
    with pytest.raises(ValueError, match="duplicate bid"):
        AuctionRoscaModel(scenario([(0, 0, 0.1), (0, 0, 0.2)]), "fixed", constant_prices())


@pytest.mark.parametrize("sale_price,used,loss", [(0.8, 100.0, 0.0), (0.6, 120.0, 80.0)])
def test_first_recipient_default_consumes_interest_before_principal(sale_price, used, loss):
    original = scenario([(0, 0, 0.2)])
    shocked = PricePath((1.0,) * 6, "shock", None, (1.0, sale_price) + (1.0,) * 156)
    case = replace(original, forced_defaults=(AuctionEvent(0, 1),), grace_days=0)
    result = AuctionRoscaModel(case, "fixed", shocked).run()
    assert result.default_count == 1
    assert result.freeze_day == 1
    assert result.interest_used == pytest.approx(used)
    assert result.principal_loss == pytest.approx(loss)
    if loss:
        assert [r.principal_loss for r in result.agent_results[1:]] == pytest.approx([16.0] * 5)


def test_normal_completion_distributes_interest_by_wait():
    bids = [(period, period, 0.2 if period == 0 else 0.0) for period in range(6)]
    result = AuctionRoscaModel(scenario(bids), "fixed", constant_prices()).run()
    assert result.stop_reason == "completed"
    assert result.interest_retained == pytest.approx(120.0)
    assert result.interest_distributed == pytest.approx(120.0)
    interests = [r.interest_received for r in result.agent_results]
    assert interests[0] == 0.0
    assert interests == sorted(interests)


def test_completion_returns_full_initial_eth():
    bids = [(period, period, 0.2 if period == 0 else 0.0) for period in range(6)]
    prices = PricePath((2000.0,) * 6, "constant", None, (2000.0,) * 158)
    result = AuctionRoscaModel(scenario(bids), "fixed", prices).run()
    assert result.agent_results[0].eth_locked == pytest.approx(0.25)
    for member in result.agent_results:
        assert member.eth_released == 0
        assert member.eth_sold == 0
        assert member.eth_returned == pytest.approx(member.eth_locked)


def test_sale_slippage_does_not_reduce_initial_bid_collateral():
    original = scenario([(0, 0, 0.2)])
    case = replace(original, collateral=replace(original.collateral, liquidation_slippage=0.1),
                   forced_defaults=(AuctionEvent(0, 1),), grace_days=0)
    prices = PricePath((2000.0,) * 6, "constant", None, (2000.0,) * 158)
    result = AuctionRoscaModel(case, "fixed", prices).run()
    assert result.agent_results[0].eth_locked == pytest.approx(0.25)
    assert result.eth_sale_proceeds == pytest.approx(450)
    assert result.obligation_uncollected == pytest.approx(50)
    assert result.interest_used == pytest.approx(50)
    assert result.principal_loss == 0
    assert result.interest_distributed == pytest.approx(70)


@pytest.mark.parametrize("first_bid,sale_price,from_default,from_others,used", [
    (0.2, 0.5, 120, 30, 150),
    (0.2, 0.7, 50, 0, 50),
    (0.0, 0.5, 0, 40, 40),
])
def test_interest_sources_follow_freeze_group_not_event_order(
    first_bid, sale_price, from_default, from_others, used,
):
    original = scenario([(0, 0, first_bid), (1, 1, 40 / 600)])
    case = replace(original, forced_defaults=(AuctionEvent(0, 60),),
                   missed_contributions=(AuctionEvent(2, 60), AuctionEvent(3, 60)))
    daily = (1.0,) * 60 + (sale_price,) * 98
    prices = PricePath((1.0, 1.0) + (sale_price,) * 4, "sources", None, daily)
    result = AuctionRoscaModel(case, "fixed", prices).run()
    reversed_result = AuctionRoscaModel(replace(case,
        missed_contributions=tuple(reversed(case.missed_contributions))), "fixed", prices).run()
    assert result == reversed_result
    assert result.interest_used == pytest.approx(used)
    assert result.interest_used_from_defaulting == pytest.approx(from_default)
    assert result.interest_used_from_other_members == pytest.approx(from_others)
    assert result.agent_results[0].bid_interest_paid == pytest.approx(600 * first_bid)
    assert result.agent_results[1].bid_interest_paid == pytest.approx(40)
    assert result.agent_results[2].bid_interest_paid == 0
    assert result.agent_results[2].is_trigger_default
    assert not result.agent_results[2].settlement_shortfall
    assert result.obligation_uncollected == pytest.approx(max(0, 400 - 500 * sale_price))
    if first_bid == 0.2 and sale_price == 0.5:
        assert result.interest_distributed == pytest.approx(10)
        assert result.principal_loss == 0


def test_secondary_settlement_shortfall_is_not_a_trigger_default():
    original = scenario([(0, 0, 0.2), (1, 1, 0.0)])
    agents = tuple(replace(a, usdc_capacity=0) for a in original.agents)
    case = replace(original, agents=agents, forced_defaults=(AuctionEvent(0, 31),))
    daily = [1.0] * 158
    daily[0], daily[30] = 0.5, 2.0
    prices = PricePath((0.5, 2.0) + (1.0,) * 4, "secondary", None, tuple(daily))
    result = AuctionRoscaModel(case, "fixed", prices).run()
    first, second, *savers = result.agent_results
    assert first.is_trigger_default and not first.settlement_shortfall
    assert not second.is_trigger_default and second.settlement_shortfall
    assert second.obligation_uncollected == pytest.approx(200)
    assert result.default_count == 1
    assert result.secondary_shortfall_count == 1
    assert not any(a.settlement_shortfall for a in savers)


def test_completion_has_no_interest_buffer_usage_or_shortfalls():
    result = AuctionRoscaModel(scenario([(i, i, 0.1) for i in range(6)]),
                              "fixed", constant_prices()).run()
    assert result.interest_used_from_defaulting == 0
    assert result.interest_used_from_other_members == 0
    assert result.secondary_shortfall_count == 0
    assert not any(a.is_trigger_default or a.settlement_shortfall for a in result.agent_results)


def test_due_date_default_freezes_before_new_contributions():
    original = scenario([(0, 0, 0.2), (1, 1, 0.1)])
    case = replace(original, forced_defaults=(AuctionEvent(0, 30),))
    result = AuctionRoscaModel(case, "fixed", constant_prices()).run()
    assert result.payout_order == (0,)
    assert all(r.total_contributed == 100 for r in result.agent_results)


def test_reversed_same_day_defaults_have_identical_result():
    original = scenario([(0, 0, 0.2), (1, 1, 0.1)])
    events = (AuctionEvent(0, 31), AuctionEvent(1, 31))
    case = replace(original, forced_defaults=events, grace_days=0)
    reverse = replace(case, forced_defaults=tuple(reversed(events)))
    a = AuctionRoscaModel(case, "fixed", constant_prices()).run()
    b = AuctionRoscaModel(reverse, "fixed", constant_prices()).run()
    assert a == b
    assert a.default_count == 2


def test_missed_pre_payout_contribution_freezes_without_penalty():
    original = scenario([(0, 0, 0.2)])
    case = replace(original, missed_contributions=(AuctionEvent(1, 30),))
    result = AuctionRoscaModel(case, "fixed", constant_prices()).run()
    assert result.default_count == 1
    assert result.agent_results[1].principal_repaid == pytest.approx(100)


def test_eth_first_sells_only_debt_and_returns_surplus_eth():
    original = scenario([(0, 0, 0.2), (1, 1, 0.0)])
    agents = list(original.agents)
    agents[1] = AuctionAgentSeed(1, 0.5, 1000, "eth_first", 0)
    case = replace(original, agents=tuple(agents), forced_defaults=(AuctionEvent(0, 31),), grace_days=0)
    result = AuctionRoscaModel(case, "fixed", constant_prices()).run()
    recipient = result.agent_results[1]
    assert recipient.eth_sold == pytest.approx(400)
    assert recipient.eth_returned == pytest.approx(0)
    assert recipient.usdc_settlement_paid == 0
    assert recipient.obligation_uncollected == 0


def test_usdc_first_full_payment_returns_all_eth():
    original = scenario([(0, 0, 0.2), (1, 1, 0.0)])
    case = replace(original, forced_defaults=(AuctionEvent(0, 31),), grace_days=7)
    result = AuctionRoscaModel(case, "fixed", constant_prices()).run()
    recipient = result.agent_results[1]
    assert recipient.usdc_settlement_paid == pytest.approx(400)
    assert recipient.eth_sold == 0
    assert recipient.eth_returned == pytest.approx(400)
    assert recipient.payment_day == 38


def test_partial_usdc_and_eth_never_overcollect():
    original = scenario([(0, 0, 0.2), (1, 1, 0.0)])
    agents = list(original.agents)
    agents[1] = AuctionAgentSeed(1, 0.5, 1000, "usdc_first", 150)
    case = replace(original, agents=tuple(agents), forced_defaults=(AuctionEvent(0, 31),), grace_days=7)
    recipient = AuctionRoscaModel(case, "fixed", constant_prices()).run().agent_results[1]
    assert recipient.usdc_settlement_paid == pytest.approx(150)
    assert recipient.eth_sold == pytest.approx(250)
    assert recipient.eth_returned == pytest.approx(150)
    assert recipient.obligation_uncollected == 0


def test_event_conflicts_and_invalid_capacity_rejected():
    original = scenario([(0, 0, 0.2)])
    with pytest.raises(ValueError, match="duplicate or conflicting"):
        AuctionRoscaModel(replace(original, forced_defaults=(AuctionEvent(0, 30),),
                                  missed_contributions=(AuctionEvent(0, 30),)), "fixed", constant_prices())
    agents = list(original.agents)
    agents[0] = replace(agents[0], usdc_capacity=-1)
    with pytest.raises(ValueError, match="invalid auction agent"):
        AuctionRoscaModel(replace(original, agents=tuple(agents)), "fixed", constant_prices())
    with pytest.raises(ValueError, match="realized payout"):
        AuctionRoscaModel(replace(original, forced_defaults=(AuctionEvent(1, 1),)), "fixed", constant_prices()).run()


def test_intraday_wick_changes_executable_sale_not_due_price():
    original = scenario([(0, 0, 0.2)])
    case = replace(original, forced_defaults=(AuctionEvent(0, 1),), grace_days=0)
    baseline = AuctionRoscaModel(case, "fixed", constant_prices()).run()
    shocked = AuctionRoscaModel(replace(case, execution_price_overrides=(AuctionPriceOverride(1, 0.6),)),
                                "fixed", constant_prices()).run()
    assert baseline.eth_sale_proceeds == pytest.approx(500)
    assert shocked.eth_sale_proceeds == pytest.approx(300)
    assert shocked.agent_results[0].eth_locked == pytest.approx(500)


def test_usdc_first_nopayer_sells_at_deadline_price():
    original = scenario([(0, 0, 0.2), (1, 1, 0)])
    agents = list(original.agents)
    agents[1] = replace(agents[1], usdc_capacity=0)
    daily = list((1.0,) * 158)
    daily[38] = 0.5
    case = replace(original, agents=tuple(agents), forced_defaults=(AuctionEvent(0, 31),), grace_days=7)
    result = AuctionRoscaModel(case, "fixed", PricePath((1.0,) * 6, "shock", None, tuple(daily))).run()
    assert result.agent_results[1].eth_sold == pytest.approx(400)
    assert result.agent_results[1].obligation_uncollected == pytest.approx(200)
    assert result.agent_results[1].eth_sale_day == 38
    assert result.agent_results[1].eth_sale_price == pytest.approx(0.5)


@pytest.mark.parametrize("invalid", [True, math.nan, math.inf, 0.0, -1.0])
def test_invalid_due_price_is_rejected_before_any_payout(invalid):
    prices = PricePath((invalid,) + (1.0,) * 5, "invalid", None, (1.0,) * 158)
    with pytest.raises(ValueError, match="due-date ETH prices"):
        AuctionRoscaModel(scenario([(0, 0, 0.2)]), "fixed", prices)


def test_invalid_sale_override_is_rejected_before_any_eth_sale():
    original = scenario([(0, 0, 0.2)])
    case = replace(original, execution_price_overrides=(AuctionPriceOverride(1, math.nan),))
    with pytest.raises(ValueError, match="execution price override"):
        AuctionRoscaModel(case, "fixed", constant_prices())
