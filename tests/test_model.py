import pytest

from rosca_sim.model import (
    EPSILON,
    AgentSeed,
    BehaviorConfig,
    CollateralConfig,
    ForcedDefault,
    RoscaConfig,
    RoscaModel,
    RunInputs,
    settle_default,
)


def make_inputs(members, prices, reputations=None):
    reputations = reputations or [0.5] * members
    return RunInputs(
        run_id=0,
        seed=7,
        agents=tuple(AgentSeed(position=i, reputation=reputations[i]) for i in range(members)),
        prices=tuple(prices),
        price_label="test",
        price_window_start=None,
    )


def safe_model():
    return RoscaModel(
        rosca=RoscaConfig(3, 3, 100.0, 30),
        collateral=CollateralConfig(0.5, 0.2, 0.8),
        behavior=BehaviorConfig(10_000.0, 10_000.0),
        policy="fixed",
        inputs=make_inputs(3, (1.0, 1.0, 1.0)),
    )


def test_no_default_round_funds_every_payout():
    result = safe_model().run()
    assert result.default_count == 0
    assert result.completion_rate == 1.0
    assert result.default_loss == 0.0
    assert result.capital_locked == pytest.approx(150.0)
    assert result.net_liquidity == pytest.approx(750.0)


def test_pool_identity_holds_after_every_period():
    model = safe_model()
    model.run()
    for row in model.period_records:
        assert row.opening_pool + row.contributions + row.recovered_collateral + row.reserve_draw == pytest.approx(
            row.actual_payout + row.closing_pool
        )
        assert row.payout_shortfall == pytest.approx(
            row.scheduled_payout - row.actual_payout
        )


def test_last_position_recipient_locks_no_collateral():
    model = safe_model()
    model.run()
    assert model.members[-1].initial_locked_eth == 0.0
    assert model.members[-1].locked_eth == 0.0


def test_fully_covering_collateral_produces_zero_default_loss():
    settlement = settle_default(300.0, locked_eth=3.0, eth_price=100.0)
    assert settlement.recovered == pytest.approx(300.0)
    assert settlement.default_loss == pytest.approx(0.0)


def test_insufficient_collateral_records_exact_shortfall():
    settlement = settle_default(300.0, locked_eth=2.0, eth_price=100.0)
    assert settlement.recovered == pytest.approx(200.0)
    assert settlement.default_loss == pytest.approx(100.0)


def test_excess_collateral_is_returned_not_forfeited():
    settlement = settle_default(300.0, locked_eth=5.0, eth_price=100.0)
    assert settlement.liquidated_eth == pytest.approx(3.0)
    assert settlement.returned_eth == pytest.approx(2.0)


def defaulting_model():
    return RoscaModel(
        rosca=RoscaConfig(2, 2, 100.0, 30),
        collateral=CollateralConfig(0.2, 0.2, 0.8),
        behavior=BehaviorConfig(0.0, 0.0),
        policy="fixed",
        inputs=make_inputs(2, (1.0, 1.0)),
    )


def test_default_happens_before_current_contribution_and_release():
    model = defaulting_model()
    model.run()
    agent = model.members[0]
    assert agent.default_period == 1
    assert agent.total_contributed == pytest.approx(100.0)
    assert agent.collateral_released == pytest.approx(0.0)
    assert model.period_records[1].contributions == pytest.approx(100.0)


def test_defaulted_agent_never_contributes_again():
    model = defaulting_model()
    model.run()
    assert model.members[0].active is False
    assert model.members[0].total_contributed == pytest.approx(100.0)


@pytest.mark.parametrize(
    ("reserve", "shortfall", "draw"),
    [(0.0, 80.0, 0.0), (80.0, 0.0, 80.0), (79.0, 1.0, 79.0)],
)
def test_funded_reserve_covers_only_available_shortfall(reserve, shortfall, draw):
    model = RoscaModel(
        rosca=RoscaConfig(2, 2, 100.0, 30, reserve),
        collateral=CollateralConfig(0.2, 0.2, 0.8),
        behavior=BehaviorConfig(0.0, 0.0),
        policy="fixed",
        inputs=make_inputs(2, (1.0, 1.0)),
    )
    result = model.run()
    assert result.participant_shortfall == pytest.approx(shortfall)
    assert result.reserve_drawn == pytest.approx(draw)
    assert result.reserve_remaining == pytest.approx(reserve - draw)
    assert result.reserve_required_for_full_payouts == pytest.approx(80.0)
    assert model.members[1].payout_shortfall == pytest.approx(shortfall)
    for row in model.period_records:
        assert row.opening_pool + row.contributions + row.recovered_collateral + row.reserve_draw == pytest.approx(
            row.actual_payout + row.closing_pool
        )


@pytest.mark.parametrize(
    ("reserve", "shortfall"),
    [(0.0, 360.0), (360.0, 0.0), (359.0, 1.0)],
)
def test_eth_halves_then_early_recipient_defaults(reserve, shortfall):
    daily = (1.0,) + (0.5,) * 180
    inputs = RunInputs(
        run_id=0,
        seed=7,
        agents=tuple(AgentSeed(position=i, reputation=0.5) for i in range(7)),
        prices=(1.0,) + (0.5,) * 6,
        price_label="half_then_default",
        price_window_start=None,
        daily_prices=daily,
        forced_defaults=(ForcedDefault(position=0, day=1),),
    )
    model = RoscaModel(
        rosca=RoscaConfig(7, 7, 100.0, 30, reserve),
        collateral=CollateralConfig(0.8, 0.8, 0.8),
        behavior=BehaviorConfig(10_000.0, 10_000.0),
        policy="fixed",
        inputs=inputs,
    )
    result = model.run()
    assert model.members[0].initial_post_payout_obligation == pytest.approx(600.0)
    assert result.recovered_collateral == pytest.approx(240.0)
    assert result.default_loss == pytest.approx(360.0)
    assert result.default_count == 1
    assert model.members[0].default_day == 1
    assert result.participant_shortfall == pytest.approx(shortfall)
    assert result.reserve_drawn == pytest.approx(min(360.0, reserve))
    assert result.reserve_required_for_full_payouts == pytest.approx(360.0)
    assert result.margin_breach_agent_days >= 1


def test_eth_drop_without_default_does_not_draw_reserve():
    inputs = RunInputs(
        run_id=0,
        seed=7,
        agents=tuple(AgentSeed(position=i, reputation=0.5) for i in range(2)),
        prices=(1.0, 1.0),
        price_label="dip_and_recover",
        price_window_start=None,
        daily_prices=(1.0,) + (0.5,) * 29 + (1.0,),
    )
    model = RoscaModel(
        rosca=RoscaConfig(2, 2, 100.0, 30, 80.0),
        collateral=CollateralConfig(0.8, 0.8, 0.8),
        behavior=BehaviorConfig(10_000.0, 10_000.0),
        policy="fixed",
        inputs=inputs,
    )
    result = model.run()
    assert result.margin_breach_agent_days == 29
    assert result.default_count == 0
    assert result.participant_shortfall == 0.0
    assert result.reserve_drawn == 0.0


def test_two_recipients_can_default_on_same_day():
    model = RoscaModel(
        rosca=RoscaConfig(3, 3, 100.0, 30),
        collateral=CollateralConfig(0.0, 0.0, 0.0),
        behavior=BehaviorConfig(10_000.0, 10_000.0),
        policy="fixed",
        inputs=RunInputs(
            run_id=0,
            seed=7,
            agents=tuple(AgentSeed(position=i, reputation=0.5) for i in range(3)),
            prices=(1.0, 1.0, 1.0),
            price_label="joint_default",
            price_window_start=None,
            daily_prices=(1.0,) * 61,
            forced_defaults=(ForcedDefault(0, 31), ForcedDefault(1, 31)),
        ),
    )
    result = model.run()
    assert result.default_count == 2
    assert result.participant_shortfall == pytest.approx(200.0)


def test_completed_agent_has_zero_locked_eth():
    model = safe_model()
    model.run()
    assert model.members[0].locked_eth == pytest.approx(0.0, abs=EPSILON)


def test_released_eth_never_exceeds_initial_lock():
    model = safe_model()
    model.run()
    for agent in model.members:
        assert agent.collateral_released <= agent.initial_locked_eth + EPSILON


def test_agent_rechecks_default_after_eth_price_falls():
    model = RoscaModel(
        rosca=RoscaConfig(3, 3, 100.0, 30),
        collateral=CollateralConfig(0.8, 0.2, 0.8),
        behavior=BehaviorConfig(25.0, 25.0),
        policy="fixed",
        inputs=make_inputs(3, (1.0, 1.0, 0.5)),
    )
    model.run()
    assert model.members[0].default_period == 2


def test_six_member_stress_cover_locks_by_remaining_dues_and_releases_after_payment():
    model = RoscaModel(
        rosca=RoscaConfig(6, 6, 100.0, 30),
        collateral=CollateralConfig(
            0.5, 0.2, 0.8, stress_drop=0.4, liquidation_slippage=0.1
        ),
        behavior=BehaviorConfig(10_000.0, 10_000.0),
        policy="fixed",
        inputs=make_inputs(6, (1.0,) * 6),
    )
    model.step()
    assert model.members[0].collateral_locked_at_payout == pytest.approx(500 / 0.54)
    model.step()
    assert model.members[0].remaining_obligation == pytest.approx(400.0)
    assert model.members[0].locked_eth == pytest.approx(400 / 0.54)
    model.run()
    assert [agent.collateral_locked_at_payout for agent in model.members] == pytest.approx(
        [500 / 0.54, 400 / 0.54, 300 / 0.54, 200 / 0.54, 100 / 0.54, 0.0]
    )
    assert model.members[0].locked_eth == pytest.approx(0.0)


def test_stress_cover_pays_full_after_early_default_and_eth_drop():
    model = RoscaModel(
        rosca=RoscaConfig(6, 6, 100.0, 30),
        collateral=CollateralConfig(
            0.5, 0.2, 0.8, stress_drop=0.4, liquidation_slippage=0.1
        ),
        behavior=BehaviorConfig(10_000.0, 10_000.0),
        policy="fixed",
        inputs=RunInputs(
            run_id=0,
            seed=7,
            agents=tuple(AgentSeed(i, 0.5) for i in range(6)),
            prices=(1.0,) + (0.6,) * 5,
            price_label="forty_percent_drop",
            price_window_start=None,
            daily_prices=(1.0,) + (0.6,) * 150,
            forced_defaults=(ForcedDefault(0, 1),),
        ),
    )
    result = model.run()
    assert result.recovered_collateral == pytest.approx(500.0)
    assert result.default_loss == pytest.approx(0.0)
    assert result.participant_shortfall == pytest.approx(0.0)
    assert result.reserve_drawn == pytest.approx(0.0)


def test_default_settlement_accounts_for_slippage_and_returns_excess_eth():
    settlement = settle_default(100.0, locked_eth=2.0, eth_price=100.0, slippage=0.1)
    assert settlement.recovered == pytest.approx(100.0)
    assert settlement.liquidated_eth == pytest.approx(100 / 90)
    assert settlement.returned_eth == pytest.approx(2 - 100 / 90)
