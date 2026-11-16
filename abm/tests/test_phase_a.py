from dataclasses import replace
from datetime import date, timedelta
import importlib
import json

import pytest

from rosca_sim.auction import AuctionRoscaModel
from rosca_sim.prices import PricePoint


def study():
    return importlib.import_module("rosca_sim.phase_a")


def year_points():
    return tuple(PricePoint(date(2022, 1, 1) + timedelta(days=i), 2000.0 + i)
                 for i in range(365))


def test_phase_a_has_all_nonempty_prefix_subsets():
    cases = study().phase_a_cases()
    assert len(cases) == len(set(cases)) == 285
    assert {c.annual_rate for c in cases} == {0, 0.05, 0.1, 0.15, 0.2}
    assert {c.default_day for c in cases} == {1, 31, 61, 91, 121}
    assert study().PhaseACase(0.2, 5, (0, 1, 2, 3, 4)) in cases
    for c in cases:
        assert c.default_ids and set(c.default_ids) <= set(range(c.paid_count))
    assert [sum(c.paid_count == k and c.annual_rate == 0 for c in cases)
            for k in range(1, 6)] == [1, 3, 7, 15, 31]


def test_phase_a_uses_all_2022_windows_without_normalizing():
    points = (PricePoint(date(2021, 12, 31), 1), *year_points(), PricePoint(date(2023, 1, 1), 1))
    paths = study().phase_a_paths(points)
    assert len(paths) == 208
    assert paths[0].start_date == "2022-01-01"
    assert paths[-1].start_date == "2022-07-27"
    assert paths[0].prices[0] == 2000
    assert all(len(p.daily_prices) == 158 for p in paths)
    assert len(study().phase_a_paths(year_points()[1:])) == 207
    with pytest.raises(ValueError, match="window"):
        study().phase_a_paths(year_points()[:157])


@pytest.mark.parametrize("k,group", [(1, (0,)), (3, (0, 2)), (5, (0, 1, 2, 3, 4))])
def test_phase_a_scenarios_have_funded_collateral_and_exact_settlement(k, group):
    path = study().phase_a_paths(year_points())[0]
    case = study().PhaseACase(0.2, k, group)
    scenario = study().phase_a_scenario(case, 2.0, path)
    model = AuctionRoscaModel(scenario, "fixed", path)
    result = model.run()
    assert result.stop_reason == "default"
    assert result.payout_order == tuple(range(k))
    assert result.freeze_day == (k - 1) * 30 + 1
    assert result.default_count == len(group)
    assert result.secondary_shortfall_count == 0
    assert scenario.collateral.liquidation_slippage == 0
    assert scenario.collateral.stress_drop is None
    for member in result.agent_results[:k]:
        if member.member_id in group:
            assert member.usdc_settlement_paid == 0
            assert member.eth_sale_day == result.freeze_day
        else:
            assert member.usdc_settlement_paid == 100 * (6 - k)
            assert member.payment_day == result.freeze_day + 7
            assert member.eth_sold == 0
            assert member.eth_returned == pytest.approx(member.eth_locked)
    reverse = replace(scenario, forced_defaults=tuple(reversed(scenario.forced_defaults)))
    assert AuctionRoscaModel(reverse, "fixed", path).run() == result


@pytest.mark.parametrize("k,group", [(0, (0,)), (6, (0,)), (2, (2,)), (2, (0, 0)), (2, ())])
def test_phase_a_rejects_invalid_group_inputs(k, group):
    with pytest.raises(ValueError):
        study().PhaseACase(0.2, k, group)

