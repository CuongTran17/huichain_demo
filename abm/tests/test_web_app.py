from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
import pytest

from streamlit.testing.v1 import AppTest

from rosca_sim.auction import AuctionEvent
from rosca_sim.web_cases import dump_cases_json, example_case, load_cases_json


APP = Path(__file__).resolve().parents[1] / "src" / "rosca_sim" / "web_app.py"


def app():
    view = AppTest.from_file(str(APP), default_timeout=15).run()
    return view.radio(key="view").set_value("So sánh kịch bản").run()


def price_csv(tmp_path):
    start = date(2022, 1, 1)
    path = tmp_path / "eth.csv"
    path.write_text("date,close\n" + "".join(
        f"{start + timedelta(days=i)},{1000 + i}\n" for i in range(190)
    ), encoding="utf-8")
    return path


def test_app_starts_with_example():
    at = app()
    assert not at.exception
    assert len(at.session_state["cases"][0].scenario.agents) == 6
    assert any("6 người" in item.value for item in at.markdown)
    assert any("20%/năm" in item.value for item in at.caption)


def test_case_editor_clone_import_and_remove():
    at = app()
    at.button(key="clone_case").click().run()
    assert len(at.session_state["cases"]) == 2
    assert at.session_state["cases"][0].case_id != at.session_state["cases"][1].case_id
    original = at.session_state["cases"][0]
    at.text_area(key="import_json").set_value(dump_cases_json((original,))).run()
    at.button(key="import_cases").click().run()
    assert len(at.session_state["cases"]) == 1
    at.button(key="remove_case").click().run()
    assert len(at.session_state["cases"]) == 0


def test_case_form_saves_name_and_can_be_run(tmp_path):
    at = app()
    at.text_input[0].set_value("Dây thử đã sửa")
    next(button for button in at.button if button.label == "Lưu điều kiện dây").click().run()
    assert not at.exception
    assert at.session_state["cases"][0].name == "Dây thử đã sửa", [item.value for item in at.error]


def test_run_shows_charts_and_discount(tmp_path):
    at = app()
    at.session_state["cases"] = (replace(example_case(), window_start=date(2022, 1, 1)),)
    at.text_input(key="csv_path").set_value(str(price_csv(tmp_path))).run()
    at.button(key="run_cases").click().run()
    assert not at.exception
    assert len(at.get("vega_lite_chart")) >= 3
    assert any("559" in item.value and "41" in item.value for item in at.markdown)
    assert at.session_state["manual_runs"][0].trace[1].contributions_by_member[0] == 100


def test_day_zero_freeze_shows_empty_period_ledger(tmp_path):
    at = app()
    original = example_case()
    scenario = replace(original.scenario, missed_contributions=(AuctionEvent(0, 0),))
    at.session_state["cases"] = (replace(original, scenario=scenario,
                                          window_start=date(2022, 1, 1)),)
    at.text_input(key="csv_path").set_value(str(price_csv(tmp_path))).run()
    at.button(key="run_cases").click().run()
    assert not at.exception
    assert at.session_state["manual_runs"][0].trace == ()
    assert any("chưa có kỳ" in item.value.casefold() for item in at.markdown)


def test_interest_caption_distinguishes_retained_from_remaining(tmp_path):
    at = app()
    original = example_case()
    scenario = replace(original.scenario, forced_defaults=(AuctionEvent(0, 1),))
    at.session_state["cases"] = (replace(original, scenario=scenario,
                                          window_start=date(2022, 1, 1)),)
    at.text_input(key="csv_path").set_value(str(price_csv(tmp_path))).run()
    at.button(key="run_cases").click().run()
    result = at.session_state["manual_runs"][0].result
    assert result.interest_retained == pytest.approx(41.0958904109589)
    assert result.interest_used == pytest.approx(41.0958904109589)
    assert any("đã giữ từ lúc lĩnh" in item.value.casefold() for item in at.caption)
    assert not any("lãi còn quỹ 120" in item.value.casefold() for item in at.caption)


def test_missing_csv_is_inline_error():
    at = app()
    at.text_input(key="csv_path").set_value("C:/no-such-eth.csv").run()
    at.button(key="run_cases").click().run()
    assert at.error
    assert not at.get("vega_lite_chart")


def test_edit_marks_result_stale(tmp_path):
    at = app()
    at.session_state["cases"] = (replace(example_case(), window_start=date(2022, 1, 1)),)
    at.text_input(key="csv_path").set_value(str(price_csv(tmp_path))).run()
    at.button(key="run_cases").click().run()
    assert not at.warning
    at.text_input(key="source_label").set_value("nguồn khác").run()
    assert any("cũ" in warning.value for warning in at.warning)


def sweep_app(tmp_path, cases=None):
    at = app()
    at.session_state["cases"] = cases or (replace(example_case(), window_start=date(2022, 1, 1)),)
    at.text_input(key="csv_path").set_value(str(price_csv(tmp_path))).run()
    at.radio(key="view").set_value("Quét tự động và tìm ngưỡng").run()
    return at


def test_sweep_requires_submit(tmp_path):
    at = sweep_app(tmp_path)
    assert not at.session_state.get("sweep_runs")
    at.number_input(key="ratio_max").set_value(2.0).run()
    assert not at.session_state.get("sweep_runs")
    at.button(key="run_sweep").click().run()
    assert at.session_state["sweep_runs"]
    previous = at.session_state["sweep_runs"]
    at.number_input(key="ratio_max").set_value(2.5).run()
    assert at.session_state["sweep_runs"] == previous
    assert at.warning


def test_sweep_guard_is_visible(tmp_path):
    at = sweep_app(tmp_path)
    at.number_input(key="ratio_min").set_value(0.0).run()
    at.number_input(key="ratio_max").set_value(10000.0).run()
    at.number_input(key="ratio_step").set_value(1.0).run()
    at.button(key="run_sweep").click().run()
    assert at.error
    assert not at.session_state.get("sweep_runs")


def test_sweep_result_explains_candidate_or_none(tmp_path):
    case = example_case()
    agents = (replace(case.scenario.agents[0], available_eth=0.3), *case.scenario.agents[1:])
    case = replace(case, scenario=replace(case.scenario, agents=agents))
    at = sweep_app(tmp_path, (case,))
    at.number_input(key="ratio_min").set_value(0.5).run()
    at.number_input(key="ratio_max").set_value(2.0).run()
    at.number_input(key="ratio_step").set_value(1.5).run()
    at.button(key="run_sweep").click().run()
    assert not at.exception
    assert len(at.session_state["sweep_runs"]) == 2
    assert any("ngưỡng" in item.value.casefold() for item in at.markdown)
    assert any("thứ tự lĩnh" in item.value.casefold() for item in at.markdown)


def test_different_horizon_labels_own_end_date(tmp_path):
    first = replace(example_case(), case_id="a")
    second = replace(first, case_id="b", scenario=replace(first.scenario, grace_days=14))
    at = sweep_app(tmp_path, (first, second))
    at.button(key="run_sweep").click().run()
    rows = at.session_state["frontier"]
    assert next(row["end_date"] for row in rows if row["case_id"] == "a") != next(
        row["end_date"] for row in rows if row["case_id"] == "b")


def test_stale_sweep_does_not_relabel_old_candidate(tmp_path):
    at = sweep_app(tmp_path)
    at.button(key="run_sweep").click().run()
    old = at.session_state["cases"][0]
    at.session_state["cases"] = (replace(old, name="Tên dây mới"),)
    at.run()
    assert at.warning
    assert not any("Tên dây mới:" in item.value for item in at.markdown)


def test_same_name_cases_remain_distinct_and_drill_down_is_selectable(tmp_path):
    first = replace(example_case(), case_id="case-a", name="Cùng tên", window_start=date(2022, 1, 1))
    second = replace(first, case_id="case-b", scenario=replace(first.scenario,
                    missed_contributions=(AuctionEvent(0, 0),)))
    at = app()
    at.session_state["cases"] = (first, second)
    at.text_input(key="csv_path").set_value(str(price_csv(tmp_path))).run()
    at.button(key="run_cases").click().run()
    assert not at.exception
    options = next(item.options for item in at.selectbox if item.label == "Mở chi tiết dây")
    assert len(set(options)) == 2
    detail = next(item for item in at.selectbox if item.label == "Mở chi tiết dây")
    detail.set_value(options[1]).run()
    assert "case-b" in next(item.value for item in at.selectbox if item.label == "Mở chi tiết dây")
    assert any("Chưa có kỳ" in item.value for item in at.markdown)


def test_sweep_shows_loss_frequency_and_collateral_tradeoff_charts(tmp_path):
    at = sweep_app(tmp_path)
    at.button(key="run_sweep").click().run()
    assert not at.exception
    assert len(at.get("vega_lite_chart")) >= 4


@pytest.mark.parametrize("percent", [0.0, 5.0, 10.0, 99.999])
def test_slippage_editor_preserves_percent_units_and_roundtrip(percent):
    at = app()
    control = next(item for item in at.number_input if item.label == "Trượt giá khi bán ETH (%)")
    control.set_value(percent)
    next(button for button in at.button if button.label == "Lưu điều kiện dây").click().run()
    assert not at.exception
    case = at.session_state["cases"][0]
    assert case.scenario.collateral.liquidation_slippage == pytest.approx(percent / 100)
    assert load_cases_json(dump_cases_json((case,))) == (case,)


def test_slippage_edit_marks_manual_and_sweep_results_stale(tmp_path):
    at = app()
    at.session_state["cases"] = (replace(example_case(), window_start=date(2022, 1, 1)),)
    at.text_input(key="csv_path").set_value(str(price_csv(tmp_path))).run()
    at.button(key="run_cases").click().run()
    at.radio(key="view").set_value("Quét tự động và tìm ngưỡng").run()
    at.button(key="run_sweep").click().run()
    at.radio(key="view").set_value("So sánh kịch bản").run()
    next(item for item in at.number_input if item.label == "Trượt giá khi bán ETH (%)").set_value(10.0)
    next(button for button in at.button if button.label == "Lưu điều kiện dây").click().run()
    assert any("cũ" in item.value for item in at.warning)
    at.radio(key="view").set_value("Quét tự động và tìm ngưỡng").run()
    assert any("cũ" in item.value for item in at.warning)
    assert any("ẩn" in item.value for item in at.info)


def test_slippage_100_percent_is_inline_error_without_overwriting_case():
    at = app()
    next(item for item in at.number_input if item.label == "Trượt giá khi bán ETH (%)").set_value(100.0)
    next(button for button in at.button if button.label == "Lưu điều kiện dây").click().run()
    assert at.error and not at.exception
    assert at.session_state["cases"][0].scenario.collateral.liquidation_slippage == 0


def test_settlement_and_coverage_are_visible_without_margin_calls(tmp_path):
    at = app()
    at.session_state["cases"] = (replace(example_case(), window_start=date(2022, 1, 1)),)
    at.text_input(key="csv_path").set_value(str(price_csv(tmp_path))).run()
    at.button(key="run_cases").click().run()
    assert not at.exception
    tables = [item.value for item in at.dataframe]
    assert any("bid_interest_paid_usdc" in table.columns for table in tables)
    assert any("interest_used_from_defaulting_usdc" in table.columns for table in tables)
    assert any("coverage_ratio" in table.columns for table in tables)
    assert any("chỉ báo" in item.value.casefold() for item in at.caption)
    assert any("Hoàn thành" in item.value for item in at.markdown)
    assert not any("Nạp thêm" in item.label for item in at.button)
