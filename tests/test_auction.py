import math

import pytest

from rosca_sim.auction import AuctionAgentSeed, AuctionBid, AuctionRoscaModel, AuctionScenario
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
