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
