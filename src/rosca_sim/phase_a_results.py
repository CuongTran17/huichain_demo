"""Read-only adapter for the fixed annual-interest phase-A study."""

from dataclasses import dataclass
from pathlib import Path
from math import isfinite

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


@dataclass(frozen=True)
class StudyFilters:
    annual_rates: tuple[float, ...]
    min_ratio: float
    max_ratio: float
    paid_counts: tuple[int, ...]
    groups: tuple[GroupKey, ...]


def _groups(filters):
    if (not isfinite(filters.min_ratio) or not isfinite(filters.max_ratio)
        or filters.min_ratio > filters.max_ratio):
        raise ValueError("invalid ratio range")
    valid = {(c.paid_count, c.default_ids) for c in pa.phase_a_cases()}
    if (any(rate not in pa.ANNUAL_RATES for rate in filters.annual_rates)
        or any(k not in range(1, 6) for k in filters.paid_counts)
        or any(g not in valid for g in filters.groups)):
        raise ValueError("invalid rate, paid count or group")
    return tuple(sorted(set(g for g in filters.groups if g[0] in filters.paid_counts)))


def filter_summaries(study: StudySnapshot, filters: StudyFilters) -> tuple[dict[str, object], ...]:
    groups = _groups(filters)
    return tuple(r for r in study.summaries if r["annual_rate"] in filters.annual_rates
                 and filters.min_ratio <= r["ratio"] <= filters.max_ratio
                 and (case_key(r)[2], case_key(r)[3]) in groups)


def select_worst(rows: tuple[dict[str, object], ...]) -> CaseKey | None:
    if not rows:
        return None
    return case_key(min(rows, key=lambda r: (-r["max_individual_loss"],
                                            r["worst_individual_start"], case_key(r))))


def member_label(member_id: int) -> str:
    return f"Người {member_id + 1}"


def _aggregate(study, filters, heat_rate=None):
    groups = _groups(filters)
    if not groups:
        return ()
    selected = filter_summaries(study, filters)
    index = {case_key(r): r for r in selected}
    result = []
    for rate in sorted(set(filters.annual_rates)):
        if heat_rate is not None and rate != heat_rate:
            continue
        for ratio in sorted(study.manifest["planned_ratios"]):
            if not filters.min_ratio <= ratio <= filters.max_ratio:
                continue
            for k in (sorted({g[0] for g in groups}) if heat_rate is not None else (None,)):
                expected_groups = [g for g in groups if k is None or g[0] == k]
                found = tuple(index[(rate, ratio, *g)] for g in expected_groups if (rate, ratio, *g) in index)
                worst = select_worst(found)
                row = next((r for r in found if case_key(r) == worst), None)
                completed = sum(r["completed_windows"] for r in found)
                expected = len(expected_groups) * study.manifest["windows"]
                result.append(dict(annual_rate=rate, ratio=ratio,
                    max_individual_loss=row["max_individual_loss"] if row else None,
                    loss_count=sum(r["loss_window_count"] for r in found) if found else None,
                    completed_runs=completed, expected_runs=expected, coverage_complete=completed == expected,
                    group_count=len(expected_groups), worst_key=worst,
                    worst_start=row["worst_individual_start"] if row else None,
                    **({"k": k} if k is not None else {})))
    return tuple(result)


def risk_rows(study: StudySnapshot, filters: StudyFilters) -> tuple[dict[str, object], ...]:
    return _aggregate(study, filters)


def heatmap_rows(study: StudySnapshot, filters: StudyFilters, annual_rate: float) -> tuple[dict[str, object], ...]:
    return _aggregate(study, filters, annual_rate)
