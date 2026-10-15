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
