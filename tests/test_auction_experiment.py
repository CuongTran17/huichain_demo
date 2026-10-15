import csv
import json
from dataclasses import replace
from rosca_sim.auction import AuctionAgentSeed, AuctionBid, AuctionEvent, AuctionRoscaModel, AuctionScenario
from rosca_sim.auction_experiment import run_auction_experiment, run_auction_grace_sweep, run_auction_pair
from rosca_sim.model import BehaviorConfig, CollateralConfig, RoscaConfig
from rosca_sim.prices import PricePath, make_stress_path


def case():
    return AuctionScenario(
        RoscaConfig(6, 6, 100, 30),
        CollateralConfig(1, 0.5, 2),
        BehaviorConfig(10000, 10000),
        tuple(AuctionAgentSeed(i, 0 if i == 0 else 1, 500, "usdc_first", 500) for i in range(6)),
        (AuctionBid(0, 0, 0.2), AuctionBid(0, 1, 0.1)),
        grace_days=7,
    )


def test_paired_policies_can_have_distinct_realized_order():
    path = make_stress_path("constant", 6, 30, extra_days=7)
    fixed, adjusted = run_auction_pair(case(), path)
    assert fixed.payout_order == (0,)
    assert adjusted.payout_order == (1,)
    assert fixed.price_label == adjusted.price_label == "constant"


def test_experiment_outputs_are_distinct_and_reproducible(tmp_path):
    path = make_stress_path("constant", 6, 30, extra_days=7)
    a = tmp_path / "a"
    b = tmp_path / "b"
    run_auction_experiment(case(), path, 2, 42, a)
    run_auction_experiment(case(), path, 2, 42, b)
    names = {"auction_run_results.csv", "auction_agent_results.csv", "auction_pair_results.csv", "auction_metadata.json"}
    assert {p.name for p in a.iterdir()} == names
    assert all((a / name).read_bytes() == (b / name).read_bytes() for name in names)
    with (a / "auction_agent_results.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert {"net_payout", "winning_bid", "eth_sold", "eth_returned", "principal_claim", "principal_loss", "interest_received"} <= set(rows[0])
    assert not (a / "run_results.csv").exists()
    assert {"bid_interest_paid", "is_trigger_default", "settlement_shortfall"} <= set(rows[0])
    metadata = json.loads((a / "auction_metadata.json").read_text(encoding="utf-8"))
    assert metadata["collateral_release_policy"] == "terminal"
    assert metadata["scenario"]["collateral"]["liquidation_slippage"] == 0
    assert metadata["scenario"]["agents"][0]["usdc_capacity"] == 500
    with (a / "auction_run_results.csv").open(newline="", encoding="utf-8") as handle:
        run_rows = list(csv.DictReader(handle))
    for row in run_rows:
        assert float(row["interest_used_from_defaulting"]) + float(
            row["interest_used_from_other_members"]) == float(row["interest_used"])
        assert "secondary_shortfall_count" in row


def test_grace_sweep_reuses_path_and_records_worst_loss(tmp_path):
    original = case()
    agents = list(original.agents)
    agents[0] = replace(agents[0], available_eth=1000)
    agents[1] = replace(agents[1], available_eth=1000, usdc_capacity=0)
    scenario = replace(original, collateral=replace(original.collateral, fixed_ratio=0.5),
                       agents=tuple(agents), bids=(AuctionBid(0, 0, 0.2),
                                  AuctionBid(1, 1, 0.0)), forced_defaults=(AuctionEvent(0, 31),))
    daily = [1.0] * 165
    daily[38] = 0.5
    path = PricePath((1.0,) * 6, "drop", None, tuple(daily))
    output = run_auction_grace_sweep(scenario, path, 1, 42, (0, 1, 3, 7, 14), tmp_path)
    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert {int(row["grace_days"]) for row in rows} == {0, 1, 3, 7, 14}
    assert "worst_member_principal_loss" in rows[0]
    zero = next(row for row in rows if row["policy"] == "fixed" and row["grace_days"] == "0")
    seven = next(row for row in rows if row["policy"] == "fixed" and row["grace_days"] == "7")
    assert float(seven["mean_principal_loss"]) > float(zero["mean_principal_loss"])


def test_four_correlated_defaults_are_one_order_independent_freeze():
    original = case()
    agents = tuple(replace(agent, available_eth=1000) for agent in original.agents)
    bids = tuple(AuctionBid(i, i, 0.0) for i in range(6))
    events = tuple(AuctionEvent(i, 91) for i in range(4))
    a = replace(original, agents=agents, bids=bids, forced_defaults=events)
    b = replace(a, forced_defaults=tuple(reversed(events)))
    path = make_stress_path("constant", 6, 30, extra_days=7)
    result_a = AuctionRoscaModel(a, "fixed", path).run()
    result_b = AuctionRoscaModel(b, "fixed", path).run()
    assert result_a == result_b
    assert result_a.default_count == 4
    assert result_a.freeze_day == 91
    assert result_a.payout_order == (0, 1, 2, 3)
