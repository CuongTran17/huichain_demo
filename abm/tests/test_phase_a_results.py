import importlib
import json
from dataclasses import replace

import pytest

from rosca_sim import phase_a


def reader():
    return importlib.import_module("rosca_sim.phase_a_results")


def files(directory):
    return {str(p): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in directory.rglob("*") if p.is_file()}


def test_reader_validates_full_snapshot_without_writes_or_runner(phase_a_copy, monkeypatch):
    directory, _ = phase_a_copy
    before = files(directory)
    def forbidden(*args, **kwargs):
        raise AssertionError("reader must not write or simulate")
    for name in ("prepare_phase_a", "aggregate_phase_a", "run_phase_a_job", "plan_phase_a_refinement"):
        monkeypatch.setattr(phase_a, name, forbidden)
    snapshot = reader().load_study(directory)
    assert (snapshot.completed_jobs, snapshot.expected_jobs) == (40, 40)
    assert snapshot.completed_runs == snapshot.expected_runs == 2280
    assert len(snapshot.summaries) == 2280
    assert len(snapshot.thresholds) == 291
    assert snapshot.thresholds[-1]["candidate_ratio"] == 1.0
    rows = reader().member_rows(snapshot, (.2, 1., 1, (0,)))
    assert sorted(r["member_id"] for r in rows) == list(range(6))
    assert {r["window_start"] for r in rows} == {"2022-01-01"}
    assert files(directory) == before


def test_missing_job_invalidates_old_complete_claim(phase_a_copy):
    directory, _ = phase_a_copy
    module = reader()
    signature = module.study_signature(directory)
    phase_a._job_path(directory, 0, .25).unlink()
    assert module.study_signature(directory) != signature
    snapshot = module.load_study(directory)
    assert (snapshot.completed_jobs, snapshot.completed_runs, snapshot.expected_runs) == (39, 2223, 2280)
    assert snapshot.thresholds[-1]["status"] == "incomplete"
    assert snapshot.thresholds[-1]["candidate_ratio"] is None


@pytest.mark.parametrize("damage", ["json", "count", "payload", "duplicate", "schema", "basis", "code"])
def test_corrupt_source_is_error_not_partial_success(phase_a_copy, damage):
    directory, _ = phase_a_copy
    path = phase_a._job_path(directory, 0, .25)
    if damage in ("schema", "basis", "code"):
        path = directory / "phase_a_metadata.json"
    data = json.loads(path.read_text())
    if damage == "json":
        path.write_text("{")
    else:
        if damage == "count": data["completed_runs"] = 1
        if damage == "payload": data["payload_sha256"] = "bad"
        if damage == "duplicate": data["summaries"][1] = data["summaries"][0]
        if damage == "schema": data["identity"]["result_schema_version"] = 1
        if damage == "basis": data["identity"]["bid_rate_basis"] = "gross"
        if damage == "code": data["identity"]["code_hashes"] = {}
        if "identity" in data: data["fingerprint"] = phase_a._hash(data["identity"])
        path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        reader().load_study(directory)


def test_change_during_read_and_stale_member_read_are_rejected(phase_a_copy, monkeypatch):
    directory, _ = phase_a_copy
    module = reader()
    snapshot = module.load_study(directory)
    original = phase_a._read_job
    changed = False
    def changing(*args):
        nonlocal changed
        result = original(*args)
        if not changed:
            changed = True
            path = directory / "phase_a_metadata.json"
            path.write_text(path.read_text() + " ")
        return result
    monkeypatch.setattr(phase_a, "_read_job", changing)
    with pytest.raises(ValueError, match="changed|reload"):
        module.load_study(directory)
    with pytest.raises(ValueError, match="changed|reload"):
        module.member_rows(snapshot, (.2, 1., 1, (0,)))


def test_filters_aggregate_raw_max_and_counts_with_expected_groups(phase_a_copy):
    module = reader()
    study = module.load_study(phase_a_copy[0])
    rows = tuple(dict(annual_rate=.2, ratio=1., k=k, default_ids=ids,
                      max_individual_loss=loss, loss_window_count=count,
                      completed_windows=3, expected_windows=3,
                      worst_individual_start="2022-01-01")
                 for k, ids, loss, count in [(1, "0", 5, 2), (2, "0", 7, 1), (2, "1", 1, 0)])
    study = replace(study, summaries=rows, manifest={**study.manifest, "windows": 3, "planned_ratios": [1.]})
    filters = module.StudyFilters((.2,), 1., 1., (1, 2), ((1, (0,)), (2, (0,)), (2, (1,))))
    risk, = module.risk_rows(study, filters)
    assert (risk["max_individual_loss"], risk["loss_count"]) == (7, 3)
    assert risk["completed_runs"] == risk["expected_runs"] == 9
    assert risk["coverage_complete"]
    assert [r["max_individual_loss"] for r in module.heatmap_rows(study, filters, .2)] == [5, 7]
    assert module.select_worst(rows) == (.2, 1., 2, (0,))
    assert module.member_label(0) == "Người 1"
    assert module.member_label(5) == "Người 6"
    assert not module.filter_summaries(study, replace(filters, annual_rates=()))
    assert not module.risk_rows(study, replace(filters, groups=()))
    missing = replace(study, summaries=())
    point, = module.risk_rows(missing, filters)
    assert point["max_individual_loss"] is None and point["loss_count"] is None
    assert point["completed_runs"] == 0 and point["expected_runs"] == 9
    assert not point["coverage_complete"]
    for bad in (replace(filters, min_ratio=float("nan")), replace(filters, max_ratio=.5),
                replace(filters, groups=((1, (2,)),))):
        with pytest.raises(ValueError): module.filter_summaries(study, bad)


def test_replay_single_real_run_matches_saved_members_and_frames(phase_a_copy, monkeypatch):
    from rosca_sim import web_analysis
    module = reader()
    directory, prices = phase_a_copy
    study = module.load_study(directory)
    before = files(directory)
    original = web_analysis.AuctionRoscaModel
    calls = []
    def counted(*args, **kwargs):
        calls.append((args, kwargs))
        return original(*args, **kwargs)
    monkeypatch.setattr(web_analysis, "AuctionRoscaModel", counted)
    replay = module.replay_case(study, (.2, 1., 1, (0,)), "2022-01-01", prices)
    assert len(calls) == 1
    assert replay.run.result.freeze_day == 1
    assert replay.run.result.settlement_day == 8
    assert replay.run.result.agent_results[0].net_payout == pytest.approx(558.9041095890411)
    assert replay.run.result.worst_member_loss == 0.
    assert not replay.mismatches
    assert len(replay.checks) > 6
    assert [(f["kind"], f["day"]) for f in module.replay_frames(replay)] == [
        ("initial", 0), ("period", 0), ("freeze", 1), ("settlement", 8)]
    assert files(directory) == before
    prices.write_text(prices.read_text() + "\n")
    with pytest.raises(ValueError, match="SHA|hash"):
        module.replay_case(study, (.2, 1., 1, (0,)), "2022-01-01", prices)
    assert len(calls) == 1


def test_replay_checks_only_corresponding_saved_window(phase_a_copy):
    module = reader()
    study = module.load_study(phase_a_copy[0])
    key = (.2, 1., 1, (0,))
    summary = next(r for r in study.summaries if module.case_key(r) == key)
    changed = {**summary, "worst_total_start": "2022-01-02", "max_total_loss": 999.}
    altered = replace(study, summaries=tuple(changed if r is summary else r for r in study.summaries))
    replay = module.replay_case(altered, key, "2022-01-01", phase_a_copy[1])
    assert "principal_loss" not in replay.checks
    assert not replay.mismatches
    changed["interest_used_at_worst_individual"] = 999.
    replay = module.replay_case(altered, key, "2022-01-01", phase_a_copy[1])
    assert "interest_used" in replay.mismatches
