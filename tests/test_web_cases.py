from dataclasses import replace
from datetime import date
import importlib
import json

import pytest


def cases_module():
    return importlib.import_module("rosca_sim.web_cases")


def test_example_has_first_bid():
    case = cases_module().example_case()
    assert case.scenario.rosca.members == 6
    assert case.scenario.rosca.periods == 6
    assert case.scenario.bids[0].annual_rate == 0.2
    assert case.scenario.agents[0].settlement_mode == "usdc_first"
    assert json.loads(cases_module().dump_cases_json((case,)))["schema_version"] == 2


def test_named_case_roundtrip():
    module = cases_module()
    first = replace(module.example_case(), case_id="first", name="Không bùng", window_start=date(2022, 5, 1))
    second = replace(first, case_id="second", name="Bùng kỳ hai")
    restored = module.load_cases_json(module.dump_cases_json((first, second)))
    assert restored == (first, second)


def test_case_import_rejects_unsafe_data():
    module = cases_module()
    original = json.loads(module.dump_cases_json((module.example_case(),)))

    bad = json.loads(json.dumps(original))
    bad["cases"].append(bad["cases"][0])
    with pytest.raises(ValueError, match="duplicate"):
        module.load_cases_json(json.dumps(bad))

    bad = json.loads(json.dumps(original))
    bad["schema_version"] = 1
    with pytest.raises(ValueError, match="schema"):
        module.load_cases_json(json.dumps(bad))

    bad = json.loads(json.dumps(original))
    bad["cases"][0]["scenario"]["execution_price_overrides"] = [{"day": 1, "price": 0.1}]
    with pytest.raises(ValueError, match="execution_price_overrides"):
        module.load_cases_json(json.dumps(bad))

    bad = json.loads(json.dumps(original))
    bad["cases"][0]["scenario"]["bids"][0]["annual_rate"] = 1.0
    with pytest.raises(ValueError, match="bid rate"):
        module.load_cases_json(json.dumps(bad))

    bad = json.loads(json.dumps(original))
    bad["cases"][0]["scenario"]["rosca"]["members"] = 5
    with pytest.raises(ValueError, match="members == periods"):
        module.load_cases_json(json.dumps(bad))

    bad = json.loads(json.dumps(original))
    bad["cases"][0]["scenario"]["forced_defaults"] = [{"member_id": 7, "day": 1}]
    with pytest.raises(ValueError, match="invalid auction event"):
        module.load_cases_json(json.dumps(bad))


def test_case_import_rejects_nonfinite_and_unknown_fields():
    module = cases_module()
    original = json.loads(module.dump_cases_json((module.example_case(),)))
    bad = json.loads(json.dumps(original))
    bad["cases"][0]["scenario"]["agents"][0]["available_eth"] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        module.load_cases_json(json.dumps(bad))
    bad = json.loads(json.dumps(original))
    bad["cases"][0]["secret_override"] = True
    with pytest.raises(ValueError, match="unknown"):
        module.load_cases_json(json.dumps(bad))


@pytest.mark.parametrize("value", [True, -0.01, 1.0, float("nan"), float("inf")])
def test_import_rejects_invalid_sale_slippage(value):
    module = cases_module()
    raw = json.loads(module.dump_cases_json((module.example_case(),)))
    raw["cases"][0]["scenario"]["collateral"]["liquidation_slippage"] = value
    with pytest.raises(ValueError):
        module.load_cases_json(json.dumps(raw))


def test_historical_web_keeps_rejecting_stress_floor():
    module = cases_module()
    raw = json.loads(module.dump_cases_json((module.example_case(),)))
    raw["cases"][0]["scenario"]["collateral"]["stress_drop"] = 0.4
    with pytest.raises(ValueError, match="stress_drop"):
        module.load_cases_json(json.dumps(raw))
