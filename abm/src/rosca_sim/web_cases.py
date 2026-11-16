"""Validated, portable inputs for the local auction explorer."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import date
import json
from math import isfinite
from typing import Any

from rosca_sim.auction import (
    AuctionAgentSeed, AuctionBid, AuctionEvent, AuctionRoscaModel, AuctionScenario,
)
from rosca_sim.model import BehaviorConfig, CollateralConfig, RoscaConfig
from rosca_sim.prices import PricePath


@dataclass(frozen=True)
class NamedCase:
    case_id: str
    name: str
    scenario: AuctionScenario
    window_start: date | None = None


def example_case() -> NamedCase:
    return NamedCase(
        case_id="example-six-member", name="Dây hụi 6 người",
        scenario=AuctionScenario(
            rosca=RoscaConfig(6, 6, 100.0, 30),
            collateral=CollateralConfig(0.5, 0.4, 0.7),
            behavior=BehaviorConfig(10_000.0, 10_000.0),
            agents=tuple(
                AuctionAgentSeed(i, 0.5, 1000.0, "usdc_first", 500.0)
                for i in range(6)
            ),
            bids=tuple(
                AuctionBid(i, i, rate)
                for i, rate in enumerate((0.2, 0.1, 0.08, 0.06, 0.04, 0.0))
            ),
            grace_days=7,
        ),
    )


def _keys(raw: object, expected: set[str], label: str) -> dict[str, Any]:
    if type(raw) is not dict:
        raise ValueError(f"{label} must be an object")
    unknown = set(raw) - expected
    missing = expected - set(raw)
    if unknown or missing:
        raise ValueError(f"{label} has unknown or missing fields: {sorted(unknown | missing)}")
    return raw


def _build(cls: type, raw: object):
    values = _keys(raw, {field.name for field in fields(cls)}, cls.__name__)
    try:
        return cls(**values)
    except TypeError as error:
        raise ValueError(f"invalid {cls.__name__}: {error}") from error


def _reject_nonfinite(value: object) -> None:
    if type(value) is float and not isfinite(value):
        raise ValueError("numbers must be finite")
    if type(value) is dict:
        for item in value.values():
            _reject_nonfinite(item)
    elif type(value) is list:
        for item in value:
            _reject_nonfinite(item)


def _scenario_from_dict(raw: object) -> AuctionScenario:
    expected = {field.name for field in fields(AuctionScenario)}
    values = _keys(raw, expected, "AuctionScenario")
    if values["execution_price_overrides"] != []:
        raise ValueError("execution_price_overrides are unavailable in the historical web app")
    if type(values["agents"]) is not list or type(values["bids"]) is not list:
        raise ValueError("agents and bids must be lists")
    if type(values["forced_defaults"]) is not list or type(values["missed_contributions"]) is not list:
        raise ValueError("events must be lists")
    scenario = AuctionScenario(
        rosca=_build(RoscaConfig, values["rosca"]),
        collateral=_build(CollateralConfig, values["collateral"]),
        behavior=_build(BehaviorConfig, values["behavior"]),
        agents=tuple(_build(AuctionAgentSeed, item) for item in values["agents"]),
        bids=tuple(_build(AuctionBid, item) for item in values["bids"]),
        forced_defaults=tuple(_build(AuctionEvent, item) for item in values["forced_defaults"]),
        missed_contributions=tuple(_build(AuctionEvent, item) for item in values["missed_contributions"]),
        grace_days=values["grace_days"],
    )
    if scenario.collateral.stress_drop is not None:
        raise ValueError("stress_drop is unavailable in the historical web app")
    rosca = scenario.rosca
    if (type(rosca.periods) is not int or type(rosca.period_days) is not int
        or type(scenario.grace_days) is not int or rosca.periods < 6
        or rosca.periods > 100 or rosca.period_days < 1 or rosca.period_days > 365
        or not 0 <= scenario.grace_days <= 365):
        raise ValueError("auction size, period_days, or grace_days is outside web limits")
    days = (rosca.periods - 1) * rosca.period_days + 1 + scenario.grace_days
    path = PricePath((1.0,) * rosca.periods, "validation-only", None, (1.0,) * days)
    AuctionRoscaModel(scenario, "fixed", path)
    return scenario


def dump_cases_json(cases: tuple[NamedCase, ...]) -> str:
    rows = []
    for case in cases:
        rows.append({
            "case_id": case.case_id, "name": case.name,
            "scenario": asdict(case.scenario),
            "window_start": case.window_start.isoformat() if case.window_start else None,
        })
    return json.dumps({"schema_version": 2, "cases": rows}, ensure_ascii=False,
                      allow_nan=False, indent=2, sort_keys=True)


def load_cases_json(payload: str) -> tuple[NamedCase, ...]:
    try:
        raw = json.loads(payload)
    except (json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"invalid JSON or nonfinite number: {error}") from error
    _reject_nonfinite(raw)
    values = _keys(raw, {"schema_version", "cases"}, "case bundle")
    if type(values["schema_version"]) is not int or values["schema_version"] != 2:
        raise ValueError("unsupported case schema_version; schema 2 uses annual_rate, not legacy gross discount")
    if type(values["cases"]) is not list:
        raise ValueError("cases must be a list")
    cases = []
    ids = set()
    for item in values["cases"]:
        data = _keys(item, {"case_id", "name", "scenario", "window_start"}, "NamedCase")
        if (type(data["case_id"]) is not str or not data["case_id"].strip()
            or type(data["name"]) is not str or not data["name"].strip()):
            raise ValueError("case ID and name must be nonempty strings")
        if data["case_id"] in ids:
            raise ValueError(f"duplicate case ID: {data['case_id']}")
        ids.add(data["case_id"])
        start = data["window_start"]
        if start is not None and type(start) is not str:
            raise ValueError("window_start must be an ISO date or null")
        cases.append(NamedCase(
            data["case_id"], data["name"], _scenario_from_dict(data["scenario"]),
            date.fromisoformat(start) if start is not None else None,
        ))
    return tuple(cases)
