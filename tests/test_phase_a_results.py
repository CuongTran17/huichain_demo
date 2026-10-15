import importlib
import json

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
