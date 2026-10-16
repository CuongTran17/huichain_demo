import importlib
import json


def web():
    return importlib.import_module("rosca_sim.web_phase_a")


def test_chart_units_missing_values_segments_and_fixed_rate_colors():
    rows = tuple(dict(annual_rate=.2, ratio=r, max_individual_loss=loss, loss_count=0 if loss == 0 else None,
                      coverage_complete=loss is not None, completed_runs=1 if loss is not None else 0,
                      expected_runs=1, group_count=1, worst_key=None, worst_start=None)
                 for r, loss in [(.5, 0.), (.75, None), (1., 2.)])
    module = web()
    chart = module.risk_chart(rows, "max_individual_loss").to_dict()
    text = json.dumps(chart)
    assert "USDC" in text and "coverage_complete" in text
    assert chart["layer"][0]["encoding"]["x"]["type"] == "quantitative"
    assert chart["layer"][0]["encoding"]["x"]["axis"]["format"] == ".0%"
    assert chart["layer"][0]["encoding"]["color"]["scale"]["domain"] == [0, .05, .1, .15, .2]
    data = next(iter(chart["datasets"].values()))
    assert data[0]["segment"] != data[2]["segment"]
    assert "loss_count" in json.dumps(module.risk_chart(rows, "loss_count").to_dict())
    heat = module.heatmap_chart(tuple({**r, "k": 1} for r in rows)).to_dict()
    assert "Thiếu dữ liệu" in json.dumps(heat, ensure_ascii=False)
    threshold = module.threshold_chart((dict(scope="rate", annual_rate=.2, candidate_ratio=None,
                                             status="incomplete"),)).to_dict()
    assert "candidate_ratio" in json.dumps(threshold)
    assert "incomplete" in json.dumps(threshold)


def test_replay_renderer_frame_changes_do_not_simulate(phase_a_copy, monkeypatch):
    from streamlit.testing.v1 import AppTest
    from rosca_sim import phase_a_results as results, web_analysis
    replay = results.replay_case(results.load_study(phase_a_copy[0]), (.2, 1., 1, (0,)),
                                 "2022-01-01", phase_a_copy[1])
    def forbidden(*args, **kwargs): raise AssertionError("frame must not simulate")
    monkeypatch.setattr(web_analysis, "AuctionRoscaModel", forbidden)
    at = AppTest.from_string("from rosca_sim.web_phase_a import render_replay\nimport streamlit as st\nrender_replay(st.session_state.replay)")
    at.session_state["replay"] = replay
    at.run(timeout=30)
    assert not at.exception
    assert len(at.get("vega_lite_chart")) >= 1
    at.select_slider(key="pa_frame").set_value(2).run()
    assert not at.exception
    assert any("snapshot" in x.value for x in at.info)
    at.select_slider(key="pa_frame").set_value(3).run()
    assert not at.exception
    assert any("Lãi đã dùng" in x.label for x in at.metric)


def study_app(directory, prices):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "src/rosca_sim/web_app.py"), default_timeout=30)
    at.session_state["view"] = "Kết quả nghiên cứu 2022"
    at.session_state["pa_results_dir"] = str(directory)
    at.session_state["pa_prices_csv"] = str(prices)
    return at.run()


def test_new_mode_filters_only_and_explicit_replay_once(phase_a_copy, monkeypatch):
    from rosca_sim import web_analysis
    original = web_analysis.AuctionRoscaModel
    calls = []
    def counted(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)
    monkeypatch.setattr(web_analysis, "AuctionRoscaModel", counted)
    at = study_app(*phase_a_copy)
    assert not at.exception
    assert len(at.get("vega_lite_chart")) >= 3
    assert any(m.value == "100%" for m in at.metric)
    assert any("2,280" in m.value for m in at.metric)
    assert not calls
    old_cases = at.session_state["cases"]
    at.multiselect(key="pa_rates").set_value([.2]).run()
    at.multiselect(key="pa_paid_counts").set_value([1]).run()
    at.button(key="pa_worst").click().run()
    assert not at.exception and not calls
    assert at.session_state["cases"] == old_cases
    at.button(key="pa_replay").click().run()
    assert not at.exception
    assert len(calls) == 1
    assert any(x.label == "Bảng giá ETH theo ngày và sự kiện" for x in at.expander)
    prices_table = next(x.value for x in at.dataframe if "price" in x.value.columns)
    assert len(prices_table) == 158
    assert prices_table.iloc[0]["price"] == 2000.
    assert prices_table.iloc[1]["events"] == "Đóng băng; Bán ETH Người 1"
    at.select_slider(key="pa_frame").set_value(3).run()
    assert not at.exception and len(calls) == 1
    at.multiselect(key="pa_rates").set_value([]).run()
    assert not at.exception
    assert not any(s.key == "pa_frame" for s in at.select_slider)
    assert len(calls) == 1


def test_cache_not_false_complete_and_missing_csv_allows_overview(phase_a_copy):
    from rosca_sim import phase_a
    directory, prices = phase_a_copy
    at = study_app(directory, prices.with_name("missing.csv"))
    assert not at.exception
    assert any(m.value == "100%" for m in at.metric)
    phase_a._job_path(directory, 0., .25).unlink()
    at.run()
    assert not at.exception
    assert not any(m.value == "100%" for m in at.metric)
    assert any("Chưa đủ" in m.value for m in at.metric)
    at.button(key="pa_replay").click().run()
    assert at.error and not at.exception


def test_csv_export_compound_values_and_empty_header():
    from rosca_sim.phase_a_results import csv_bytes
    import csv
    import io
    exported = csv_bytes(({"loss": 0.0000000001, "key": (.2, 1., 1, (0,))},), {"scope": "filtered"})
    row, = list(csv.DictReader(io.StringIO(exported.decode("utf-8-sig"))))
    assert row["scope"] == "filtered" and row["loss"] == "1e-10"
    assert json.loads(row["key"]) == [.2, 1., 1, [0]]
    assert csv_bytes((), {"scope": "empty"}).decode("utf-8-sig").strip() == "scope"


def test_cached_hit_changed_between_signature_and_lookup_is_rejected(phase_a_copy, monkeypatch):
    from rosca_sim import phase_a
    module = web()
    directory, prices = phase_a_copy
    at = study_app(directory, prices)
    assert not at.exception
    original = module._cached_study
    def change_before_cached_lookup(path, signature):
        phase_a._job_path(directory, 0., .25).unlink()
        return original(path, signature)
    monkeypatch.setattr(module, "_cached_study", change_before_cached_lookup)
    at.run()
    assert not at.exception
    assert at.error
    assert not at.metric


def test_old_source_settings_survive_round_trip_to_new_mode(phase_a_copy):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "src/rosca_sim/web_app.py"), default_timeout=30).run()
    at.text_input(key="csv_path").set_value(str(phase_a_copy[1]))
    at.text_input(key="source_label").set_value("my retained local source")
    at.selectbox(key="quote_asset").set_value("USDT").run()
    at.session_state["pa_results_dir"] = str(phase_a_copy[0])
    at.radio(key="view").set_value("Kết quả nghiên cứu 2022").run()
    assert not at.exception
    at.radio(key="view").set_value("So sánh kịch bản").run()
    assert not at.exception
    assert at.text_input(key="csv_path").value == str(phase_a_copy[1])
    assert at.text_input(key="source_label").value == "my retained local source"
    assert at.selectbox(key="quote_asset").value == "USDT"


def test_heatmap_labels_do_not_hide_cent_loss():
    chart = web().heatmap_chart((dict(annual_rate=.2, ratio=1., k=1, max_individual_loss=.01,
        coverage_complete=True, worst_key=None, worst_start=None, completed_runs=1, expected_runs=1),)).to_dict()
    assert chart["layer"][1]["encoding"]["text"]["format"] == ".2f"


def test_dense_heatmap_does_not_overlay_unreadable_currency_labels():
    rows = tuple(dict(annual_rate=.2, ratio=i/20, k=1, max_individual_loss=123.45,
        coverage_complete=True, worst_key=None, worst_start=None, completed_runs=1, expected_runs=1)
        for i in range(5, 41))
    chart = web().heatmap_chart(rows).to_dict()
    assert chart["layer"][1].get("transform") == [{"filter": "false"}]
