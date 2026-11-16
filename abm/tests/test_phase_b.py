from datetime import date, timedelta
import csv
import json

import pytest

from rosca_sim.due_date_auction import DueDateAuctionModel
from rosca_sim.cli import main
from rosca_sim.prices import PricePoint
from rosca_sim import phase_b


def points(count):
    return tuple(PricePoint(date(2022, 1, 1) + timedelta(days=i), 2000 + i)
                 for i in range(count))


def test_phase_b_paths_keep_real_prices_and_skip_gaps():
    year = points(365)
    paths = phase_b.phase_b_paths(year)
    assert len(paths) == 208
    assert paths[0].prices[0] == 2000
    assert len(paths[-1].daily_prices) == 158
    assert phase_b.phase_b_paths(year[:158])[-1].daily_prices[-1] == 2157
    assert len(phase_b.phase_b_paths(year[:160] + year[161:])) == 50
    with pytest.raises(ValueError, match="158"):
        phase_b.phase_b_paths(year[:157])


@pytest.mark.parametrize("profile,first", [("all_zero", 0), ("all_twenty", 0), ("mixed_rotating", 4)])
def test_phase_b_bids_and_forced_events_follow_actual_winners(profile, first):
    path, = phase_b.phase_b_paths(points(158))
    case = phase_b.phase_b_scenario(path, 1.8, profile, 0.5, strategic=False)
    result = DueDateAuctionModel(case, "fixed", path).run()
    assert result.stop_reason == "completed"
    assert result.payout_order[0] == first
    assert len(set(result.payout_order)) == 6
    groups = phase_b.forced_groups(result.payout_order)
    assert len(groups) == 57
    assert groups[0] == (1, (first,))
    forced = phase_b.phase_b_scenario(path, 1.8, profile, 0.5, strategic=False,
                                      paid_count=1, forced_ids=(first,))
    stopped = DueDateAuctionModel(forced, "fixed", path).run()
    assert stopped.freeze_day == 30
    assert stopped.agent_results[first].is_trigger_default


def test_cli_pilot_resume_and_missing_or_changed_inputs(tmp_path, capsys):
    prices = tmp_path / "prices.csv"
    prices.write_text("date,close\n" + "".join(f"{p.day},{p.close}\n" for p in points(158)),
                      encoding="utf-8")
    out = tmp_path / "out"
    args = ["auction-phase-b", "--prices", str(prices), "--output", str(out),
            "--source-label", "fixture", "--end", "2022-06-07"]
    assert main(args + ["--dry-run"]) == 0
    assert not out.exists()
    assert json.loads(capsys.readouterr().out)["windows"] == 1
    assert main(args + ["--pilot"]) == 0
    job = next((out / "jobs").glob("*.json"))
    before = job.stat().st_mtime_ns
    assert main(args + ["--pilot"]) == 0
    assert job.stat().st_mtime_ns == before
    job.unlink()
    assert main(args + ["--aggregate-only"]) == 1
    assert json.loads((out / "phase_b_metadata.json").read_text())["status"] == "incomplete"
    prices.write_text(prices.read_text().replace("2000", "2100"), encoding="utf-8")
    with pytest.raises(ValueError, match="fingerprint"):
        main(args + ["--pilot"])


def test_full_study_counts_groups_and_brackets_demo_ratio(tmp_path):
    prices = tmp_path / "prices.csv"
    prices.write_text("date,close\n" + "".join(
        f"{point.day},{2000 if index < 30 else 1100}\n"
        for index, point in enumerate(points(158))), encoding="utf-8")
    out = tmp_path / "full"
    args = ["auction-phase-b", "--prices", str(prices), "--output", str(out),
            "--source-label", "fixture", "--end", "2022-06-07"]
    assert main(args + ["--full"]) == 0
    with (out / "phase_b_thresholds.csv").open(newline="") as handle:
        global_result = next(row for row in csv.DictReader(handle) if row["profile"] == "all")
    assert global_result["min_passing_ratio_pct"] == "185"
    assert global_result["adjacent_lower_fails_pct"] == "180"
    assert global_result["result_at_180"] == "FAIL"
    with (out / "phase_b_summary.csv").open(newline="") as handle:
        jobs = list(csv.DictReader(handle))
    assert sum(int(row["completed_runs"]) for row in jobs) == 2 * 3 * 3 * 58
    with (out / "phase_b_payouts.csv").open(newline="") as handle:
        payouts = list(csv.DictReader(handle))
    slot = next(row for row in payouts if row["profile"] == "all_twenty"
                and row["ratio_pct"] == "180" and row["payout_number"] == "1")
    assert float(slot["max_locked_usdc"]) == pytest.approx(900)
    assert float(slot["max_locked_to_extra_cash"]) == pytest.approx(900 / (558.904109589 - 100))
    assert main(args + ["--aggregate-only"]) == 0
    metadata_path = out / "phase_b_metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["tested_ratios_pct"] = [185]
    metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="coverage"):
        main(args + ["--aggregate-only"])


def test_corrupt_checkpoint_invalidates_previous_report(tmp_path):
    prices = tmp_path / "prices.csv"
    prices.write_text("date,close\n" + "".join(f"{p.day},{p.close}\n" for p in points(158)),
                      encoding="utf-8")
    out = tmp_path / "pilot"
    args = ["auction-phase-b", "--prices", str(prices), "--output", str(out),
            "--source-label", "fixture", "--end", "2022-06-07"]
    assert main(args + ["--pilot"]) == 0
    next((out / "jobs").glob("*.json")).write_text("{}")
    with pytest.raises(ValueError, match="checkpoint"):
        main(args + ["--aggregate-only"])
    assert json.loads((out / "phase_b_metadata.json").read_text())["status"] == "incomplete"
    with (out / "phase_b_thresholds.csv").open(newline="") as handle:
        assert {row["status"] for row in csv.DictReader(handle)} == {"incomplete"}
