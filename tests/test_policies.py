import pytest

from rosca_sim.model import (
    CollateralConfig,
    fixed_collateral_ratio,
    reputation_collateral_ratio,
    strategic_default_utility,
)


def test_reputation_policy_boundaries():
    config = CollateralConfig(fixed_ratio=0.5, alpha_min=0.2, alpha_max=0.8)
    assert reputation_collateral_ratio(0.0, config) == pytest.approx(0.8)
    assert reputation_collateral_ratio(1.0, config) == pytest.approx(0.2)


def test_reputation_policy_rejects_out_of_range_score():
    config = CollateralConfig(fixed_ratio=0.5, alpha_min=0.2, alpha_max=0.8)
    with pytest.raises(ValueError, match="between 0 and 1"):
        reputation_collateral_ratio(1.1, config)


def test_fixed_policy_returns_configured_ratio():
    config = CollateralConfig(fixed_ratio=0.5, alpha_min=0.2, alpha_max=0.8)
    assert fixed_collateral_ratio(config) == pytest.approx(0.5)


def test_default_utility_uses_only_forfeitable_collateral():
    utility = strategic_default_utility(
        remaining_obligation=300.0,
        collateral_value=500.0,
        reputation_loss=25.0,
        future_access_loss=50.0,
    )
    assert utility == pytest.approx(-75.0)
