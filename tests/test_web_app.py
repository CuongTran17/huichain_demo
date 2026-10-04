from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

from streamlit.testing.v1 import AppTest

from rosca_sim.web_cases import dump_cases_json, example_case


APP = Path(__file__).resolve().parents[1] / "src" / "rosca_sim" / "web_app.py"


def app():
    return AppTest.from_file(str(APP), default_timeout=15).run()


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


def test_run_shows_charts_and_discount(tmp_path):
    at = app()
    at.session_state["cases"] = (replace(example_case(), window_start=date(2022, 1, 1)),)
    at.text_input(key="csv_path").set_value(str(price_csv(tmp_path))).run()
    at.button(key="run_cases").click().run()
    assert not at.exception
    assert len(at.get("vega_lite_chart")) >= 3
    assert any("480" in item.value and "120" in item.value for item in at.markdown)
    assert at.session_state["manual_runs"][0].trace[1].contributions_by_member[0] == 100


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
