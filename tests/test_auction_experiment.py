import csv
from rosca_sim.auction import AuctionAgentSeed, AuctionBid, AuctionScenario
from rosca_sim.auction_experiment import run_auction_experiment, run_auction_pair
from rosca_sim.model import BehaviorConfig, CollateralConfig, RoscaConfig
from rosca_sim.prices import make_stress_path


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
