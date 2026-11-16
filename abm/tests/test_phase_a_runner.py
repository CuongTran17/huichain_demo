from dataclasses import replace
from datetime import date, timedelta
import importlib
import json

import pytest
from rosca_sim.prices import PricePoint


def study():
    return importlib.import_module("rosca_sim.phase_a")


def year_points():
    return tuple(PricePoint(date(2022, 1, 1) + timedelta(days=i), 2000.0 + i) for i in range(365))


def small_study(tmp_path):
    module = study()
    paths = module.phase_a_paths(year_points()[:158])
    provenance = {"source_label": "synthetic test only", "quote_asset": "USDT",
                  "price_csv_sha256": "fixture"}
    fingerprint = module.prepare_phase_a(paths, tmp_path, provenance)
    return module, paths, fingerprint


def test_phase_a_job_is_complete_reusable_and_not_a_global_threshold(tmp_path, monkeypatch):
    module, paths, fingerprint = small_study(tmp_path)
    job = module.run_phase_a_job(paths, 0.2, 1.0, tmp_path, fingerprint)
    saved = json.loads(job.read_text(encoding="utf-8"))
    assert saved["completed_runs"] == 57
    assert len(saved["summaries"]) == 57
    assert len(saved["worst_members"]) == 342
    assert all(row["completed_windows"] == row["expected_windows"] == 1 for row in saved["summaries"])
    def unexpected_model(*args, **kwargs):
        raise AssertionError("a completed matching job should not rerun the model")
    monkeypatch.setattr(module, "AuctionRoscaModel", unexpected_model)
    assert module.run_phase_a_job(paths, 0.2, 1.0, tmp_path, fingerprint) == job
    rows = module.aggregate_phase_a(tmp_path)
    global_row, = [row for row in rows if row["scope"] == "global"]
    assert global_row["status"] == "incomplete"
    assert global_row["candidate_ratio"] is None


def test_phase_a_fingerprint_rejects_changed_data_and_ignores_partial_job(tmp_path):
    module, paths, fingerprint = small_study(tmp_path)
    (tmp_path / "jobs").mkdir(exist_ok=True)
    (tmp_path / "jobs" / "unfinished.tmp").write_text('{"completed_runs":1}', encoding="utf-8")
    module.run_phase_a_job(paths, 0.0, 1.0, tmp_path, fingerprint)
    changed = (replace(paths[0], daily_prices=(1500.0,) + paths[0].daily_prices[1:]),)
    with pytest.raises(ValueError, match="fingerprint|input|path"):
        module.run_phase_a_job(changed, 0.0, 1.0, tmp_path, fingerprint)
    with pytest.raises(ValueError, match="fingerprint|input|conflict"):
        module.prepare_phase_a(paths, tmp_path, {"source_label": "other data"})


def test_phase_a_incomplete_job_not_reused_or_counted(tmp_path):
    module, paths, fingerprint = small_study(tmp_path)
    job = module.run_phase_a_job(paths, 0.0, 1.0, tmp_path, fingerprint)
    data = json.loads(job.read_text(encoding="utf-8"))
    data["completed_runs"] = 1
    job.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="incomplete|corrupt"):
        module.aggregate_phase_a(tmp_path)
    with pytest.raises(ValueError, match="incomplete|corrupt"):
        module.run_phase_a_job(paths, 0.0, 1.0, tmp_path, fingerprint)


def test_phase_a_full_small_grid_uses_all_cases_for_global_threshold(tmp_path, monkeypatch):
    module, paths, fingerprint = small_study(tmp_path)
    for rate in module.ANNUAL_RATES:
        for ratio in module.COARSE_RATIOS:
            module.run_phase_a_job(paths, rate, ratio, tmp_path, fingerprint)
    rows = module.aggregate_phase_a(tmp_path)
    assert len(rows) == 291
    global_row, = [row for row in rows if row["scope"] == "global"]
    assert global_row["status"] == "complete"
    assert global_row["candidate_ratio"] == 1.0
    assert global_row["completed_checks"] == global_row["expected_checks"] == 2280
    assert (tmp_path / "phase_a_summary.csv").is_file()
    assert (tmp_path / "phase_a_worst_members.csv").is_file()
    extra = module.plan_phase_a_refinement(tmp_path)
    assert .8 in extra and .95 in extra
    assert json.loads((tmp_path / "phase_a_metadata.json").read_text())["aggregate_status"] == "incomplete"
    import csv
    with (tmp_path / "phase_a_thresholds.csv").open(newline="") as handle:
        global_saved, = [r for r in csv.DictReader(handle) if r["scope"] == "global"]
    assert global_saved["status"] == "incomplete" and global_saved["candidate_ratio"] == ""
    assert global_saved["expected_checks"] == str((8 + len(extra)) * 285)
    assert module.plan_phase_a_refinement(tmp_path) == extra
    assert module.aggregate_phase_a(tmp_path)[-1]["status"] == "incomplete"
    for rate in module.ANNUAL_RATES:
        for ratio in extra:
            module.run_phase_a_job(paths, rate, ratio, tmp_path, fingerprint)
    refined = module.aggregate_phase_a(tmp_path)
    assert refined[-1]["status"] == "complete"
    assert refined[-1]["completed_checks"] == (8 + len(extra)) * 285
    def interrupted(*args, **kwargs):
        raise RuntimeError("interrupted after extending grid")
    monkeypatch.setattr(module, "AuctionRoscaModel", interrupted)
    with pytest.raises(RuntimeError, match="interrupted"):
        module.run_phase_a_job(paths, .2, 1.05, tmp_path, fingerprint)
    assert json.loads((tmp_path / "phase_a_metadata.json").read_text())["aggregate_status"] == "incomplete"
    with (tmp_path / "phase_a_thresholds.csv").open(newline="") as handle:
        global_saved, = [r for r in csv.DictReader(handle) if r["scope"] == "global"]
    assert global_saved["status"] == "incomplete" and global_saved["candidate_ratio"] == ""


def test_refinement_uses_five_point_grid_and_rejects_incomplete():
    module = study()
    row = {"status": "complete", "candidate_ratio": 1.25}
    assert module.refinement_ratios((row,)) == (1.05, 1.1, 1.15, 1.2)
    assert module.refinement_ratios(({"status": "complete", "candidate_ratio": 0.25},)) == ()
    assert module.refinement_ratios(({"status": "not_found", "candidate_ratio": None},)) == ()
    with pytest.raises(ValueError, match="incomplete"):
        module.refinement_ratios(({"status": "incomplete", "candidate_ratio": None},))


def test_thresholds_use_intersection_not_maximum_and_raw_tolerance():
    module = study()
    rows = []
    for case in module.phase_a_cases():
        for ratio in (.25, .5):
            # Every case passes somewhere, but the two sets have no common point.
            passes = ratio == (.25 if case.paid_count == 1 else .5)
            rows.append({"annual_rate": case.annual_rate, "k": case.paid_count,
                         "default_ids": "|".join(map(str, case.default_ids)), "ratio": ratio,
                         "completed_windows": 2, "expected_windows": 2,
                         "max_individual_loss": 1e-10 if passes else .01})
    thresholds = module._threshold_rows(rows, (.25, .5), 2)
    assert all(r["status"] == "complete" for r in thresholds if r["scope"] == "case")
    assert thresholds[-1]["status"] == "not_found"
    assert thresholds[-1]["candidate_ratio"] is None
    assert thresholds[0]["nonmonotonic"] is True
    rows.pop()
    assert module._threshold_rows(rows, (.25, .5), 2)[-1]["status"] == "incomplete"


def test_single_five_point_ratio_can_be_registered_without_full_coarse(tmp_path):
    module, paths, fingerprint = small_study(tmp_path)
    module.run_phase_a_job(paths, .2, .55, tmp_path, fingerprint)
    assert .55 in json.loads((tmp_path / "phase_a_metadata.json").read_text())["planned_ratios"]
    assert module.aggregate_phase_a(tmp_path)[-1]["status"] == "incomplete"


def test_code_change_rejected_and_failed_model_does_not_publish(tmp_path, monkeypatch):
    module, paths, fingerprint = small_study(tmp_path)
    original = module._code_hashes()
    monkeypatch.setattr(module, "_code_hashes", lambda: {**original, "auction.py": "changed"})
    with pytest.raises(ValueError, match="fingerprint|code"):
        module.run_phase_a_job(paths, .2, 1, tmp_path, fingerprint)
    monkeypatch.setattr(module, "_code_hashes", lambda: original)
    def failed(*args, **kwargs):
        raise RuntimeError("interrupted")
    monkeypatch.setattr(module, "AuctionRoscaModel", failed)
    with pytest.raises(RuntimeError, match="interrupted"):
        module.run_phase_a_job(paths, .2, 1, tmp_path, fingerprint)
    assert not list((tmp_path / "jobs").glob("*.json"))


def test_edited_summary_payload_not_reused(tmp_path):
    module, paths, fingerprint = small_study(tmp_path)
    target = module.run_phase_a_job(paths, .2, 1, tmp_path, fingerprint)
    data = json.loads(target.read_text())
    data["summaries"][0]["max_individual_loss"] = 0
    data["summaries"][0]["max_total_loss"] = 123
    target.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="corrupt"):
        module.aggregate_phase_a(tmp_path)


def test_manifest_cannot_shrink_expected_grid_or_window_coverage(tmp_path):
    module, paths, fingerprint = small_study(tmp_path)
    target = tmp_path / "phase_a_metadata.json"
    original = json.loads(target.read_text())
    for changed in ({**original, "planned_ratios": [1.0]}, {**original, "windows": 99}):
        target.write_text(json.dumps(changed))
        with pytest.raises(ValueError, match="manifest|corrupt|coverage"):
            module.aggregate_phase_a(tmp_path)


def test_worst_total_and_individual_keep_separate_dates_and_ties(tmp_path, monkeypatch):
    module = study()
    paths = module.phase_a_paths(year_points()[:159])
    fingerprint = module.prepare_phase_a(paths, tmp_path, {"source_label": "synthetic only"})
    original_model = module.AuctionRoscaModel
    class ReportedResults:
        def __init__(self, scenario, **kwargs):
            self.result = original_model(scenario, **kwargs).run()
            self.first = kwargs["price_path"].start_date == "2022-01-01"

        def run(self):
            # Exercise independent maxima and tie dates without changing the engine.
            return replace(self.result, principal_loss=10 if self.first else 20,
                           worst_member_loss=5, interest_used=1 if self.first else 2,
                           obligation_uncollected=3 if self.first else 4)
    monkeypatch.setattr(module, "AuctionRoscaModel", ReportedResults)
    target = module.run_phase_a_job(paths, .2, 1, tmp_path, fingerprint)
    job = json.loads(target.read_text())
    assert all(r["worst_total_start"] == "2022-01-02" and r["max_total_loss"] == 20
               and r["worst_individual_start"] == "2022-01-01"
               and r["interest_used_at_worst_individual"] == 1
               and r["uncollected_at_worst_individual"] == 3 for r in job["summaries"])
    assert all(r["window_start"] == "2022-01-01" for r in job["worst_members"])


def test_cli_single_job_and_aggregate_only_share_completed_checkpoint(tmp_path, capsys):
    from rosca_sim.cli import main
    prices = tmp_path / "synthetic.csv"
    prices.write_text("date,close\n" + "".join(f"{p.day},{p.close}\n" for p in year_points()[:158]))
    output = tmp_path / "study"
    args = ["auction-phase-a", "--prices", str(prices), "--output", str(output),
            "--source-label", "synthetic integration only", "--quote-asset", "USDT"]
    assert main([*args, "--annual-rate", ".2", "--ratio", "1"]) == 0
    target, = list((output / "jobs").glob("*.json"))
    before = target.read_bytes()
    assert main([*args, "--aggregate-only"]) == 0
    assert target.read_bytes() == before
    assert '"status": "incomplete"' in capsys.readouterr().out
