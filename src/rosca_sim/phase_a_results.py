"""Read-only adapter for the fixed annual-interest phase-A study."""

from dataclasses import dataclass
from pathlib import Path

from rosca_sim import phase_a as pa

CaseKey = tuple[float, float, int, tuple[int, ...]]
GroupKey = tuple[int, tuple[int, ...]]


@dataclass(frozen=True)
class StudySnapshot:
    directory: Path
    manifest: dict[str, object]
    summaries: tuple[dict[str, object], ...]
    thresholds: tuple[dict[str, object], ...]
    signature: tuple
    completed_jobs: int
    expected_jobs: int
    completed_runs: int
    expected_runs: int


def _manifest(directory):
    try:
        manifest = pa._manifest(directory)
        fixed = {"study_version": 1, "result_schema_version": 2,
                 "bid_rate_basis": "annual_simple_act365", "members": 6,
                 "contribution": 100, "period_days": 30, "grace_days": 7,
                 "slippage": 0, "collateral_release_policy": "terminal",
                 "annual_rate_cap": .2, "day_count_basis": 365, "loss_tolerance": 1e-9}
        if any(manifest["identity"][k] != v for k, v in fixed.items()):
            raise ValueError("unsupported phase A schema/basis/fixed semantics")
        if tuple(manifest["identity"]["annual_rates"]) != pa.ANNUAL_RATES or manifest["cases_per_rate"] != 57:
            raise ValueError("unsupported phase A rates/case count")
        return manifest
    except (OSError, KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{directory / 'phase_a_metadata.json'}: {error}") from error


def _stat(path):
    try:
        stat = path.stat()
        return path.name, stat.st_size, stat.st_mtime_ns
    except FileNotFoundError:
        return path.name, None, None


def study_signature(directory: Path) -> tuple:
    directory = Path(directory).expanduser().resolve()
    try:
        before = _stat(directory / "phase_a_metadata.json")
        manifest = _manifest(directory)
        jobs = tuple(_stat(pa._job_path(directory, rate, ratio))
                     for rate in pa.ANNUAL_RATES for ratio in sorted(manifest["planned_ratios"]))
        if before != _stat(directory / "phase_a_metadata.json"):
            raise ValueError("source changed; reload study")
        return str(directory), before, jobs, tuple(sorted(pa._code_hashes().items()))
    except OSError as error:
        raise ValueError(f"{directory}: {error}") from error


def _assert_current(study):
    if study_signature(study.directory) != study.signature:
        raise ValueError("source changed; reload study")


def _read_job(path, manifest, rate, ratio):
    try:
        return pa._read_job(path, manifest, rate, ratio)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError(f"{path}: {error}") from error


def load_study(directory: Path) -> StudySnapshot:
    directory = Path(directory).expanduser().resolve()
    signature = study_signature(directory)
    manifest = _manifest(directory)
    summaries, jobs, runs = [], 0, 0
    for rate in pa.ANNUAL_RATES:
        for ratio in sorted(manifest["planned_ratios"]):
            path = pa._job_path(directory, rate, ratio)
            if path.exists():
                job = _read_job(path, manifest, rate, ratio)
                summaries.extend(job["summaries"])
                jobs += 1
                runs += job["completed_runs"]
    thresholds = pa._threshold_rows(summaries, manifest["planned_ratios"], manifest["windows"])
    expected = len(pa.ANNUAL_RATES) * len(manifest["planned_ratios"])
    study = StudySnapshot(directory, manifest, tuple(summaries), thresholds, signature,
                          jobs, expected, runs, expected * 57 * manifest["windows"])
    _assert_current(study)
    return study


def case_key(row) -> CaseKey:
    return row["annual_rate"], row["ratio"], row["k"], tuple(map(int, row["default_ids"].split("|")))


def member_rows(study: StudySnapshot, key: CaseKey) -> tuple[dict[str, object], ...]:
    _assert_current(study)
    summary = next((r for r in study.summaries if case_key(r) == key), None)
    if summary is None:
        raise ValueError("case has no validated summary")
    job = _read_job(pa._job_path(study.directory, key[0], key[1]), study.manifest, key[0], key[1])
    try:
        rows = tuple(r for r in job["worst_members"] if case_key(r) == key)
        if (len(rows) != 6 or sorted(r["member_id"] for r in rows) != list(range(6))
            or any(r["window_start"] != summary["worst_individual_start"] for r in rows)):
            raise ValueError("corrupt member IDs/window")
    except (KeyError, TypeError) as error:
        raise ValueError("corrupt member rows") from error
    _assert_current(study)
    return rows
