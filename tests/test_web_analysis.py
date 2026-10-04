from dataclasses import replace
from datetime import date, timedelta
import importlib
import random

import pytest

from rosca_sim.auction import AuctionEvent, AuctionRoscaModel
from rosca_sim.prices import PricePoint, sample_historical_path
from rosca_sim.web_cases import example_case


START = date(2022, 1, 1)


def points(days=180):
    return tuple(PricePoint(START + timedelta(days=i), 1000.0) for i in range(days))


def analysis():
    return importlib.import_module("rosca_sim.web_analysis")


def case_with_start(**changes):
    return replace(example_case(), window_start=START, **changes)


def test_named_run_matches_engine():
    case = case_with_start()
    run, = analysis().run_named_cases((case,), points(), 42, "ETH close", "USD")
    path = sample_historical_path(points(), 6, 30, random.Random(42),
                                  normalize=False, window_start=START, extra_days=7)
    direct = AuctionRoscaModel(case.scenario, "fixed", path, 0, 42)
    assert run.result == direct.run()
    assert run.trace == direct.period_trace
    assert run.price_path == path
    assert run.source_label == "ETH close"
    assert run.quote_asset == "USD"


def test_two_cases_keep_distinct_freeze_days():
    first = case_with_start(case_id="first", name="Bùng sau kỳ đầu",
                            scenario=replace(example_case().scenario,
                                             forced_defaults=(AuctionEvent(0, 1),)))
    second = case_with_start(case_id="second", name="Bùng sau kỳ hai",
                             scenario=replace(example_case().scenario,
                                              forced_defaults=(AuctionEvent(0, 31),)))
    runs = analysis().run_named_cases((first, second), points(), 42, "close", "USDT")
    assert runs[0].case.case_id != runs[1].case.case_id
    assert runs[0].result.freeze_day != runs[1].result.freeze_day
    assert runs[0].result.freeze_day == 1
    assert runs[1].result.freeze_day == 31


@pytest.mark.parametrize("bad", ["missing", "tail", "event"])
def test_bad_case_does_not_become_zero_loss(bad):
    case = case_with_start(case_id="bad", name="Trường hợp lỗi")
    data = points()
    if bad == "missing":
        case = replace(case, window_start=None)
    elif bad == "tail":
        data = points(151)
    else:
        case = replace(case, scenario=replace(case.scenario,
                            forced_defaults=(AuctionEvent(1, 1),)))
    with pytest.raises(ValueError, match=case.name):
        analysis().run_named_cases((case,), data, 42, "close", "USD")
