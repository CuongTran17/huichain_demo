"""Read-only adapter for the fixed annual-interest phase-A study."""

from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import csv
import json
from io import StringIO
from pathlib import Path
from math import isfinite

from rosca_sim import phase_a as pa
from rosca_sim.prices import load_price_csv
from rosca_sim.web_analysis import CaseRun, run_named_cases
from rosca_sim.web_cases import NamedCase

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


@dataclass(frozen=True)
class ReplayResult:
    run: CaseRun
    checks: tuple[str, ...]
    mismatches: tuple[str, ...]


def replay_case(study: StudySnapshot, key: CaseKey, window_start: str, csv_path: Path) -> ReplayResult:
    _assert_current(study)
    summary = next((r for r in study.summaries if case_key(r) == key), None)
    if summary is None or window_start not in study.manifest["identity"]["window_starts"]:
        raise ValueError("case/window is not in the validated study")
    csv_path = Path(csv_path).expanduser().resolve()
    before = _stat(csv_path)
    provenance = study.manifest["identity"]["provenance"]
    try:
        if hashlib.sha256(csv_path.read_bytes()).hexdigest() != provenance["price_csv_sha256"]:
            raise ValueError("price CSV SHA256 does not match study")
        points = load_price_csv(csv_path, date(2022, 1, 1), date(2022, 12, 31))
        paths = pa.phase_a_paths(points)
        identity = study.manifest["identity"]
        if (pa._paths_hash(paths) != identity["paths_sha256"]
            or sorted(p.start_date for p in paths) != identity["window_starts"]):
            raise ValueError("price paths/starts do not match study")
        if _stat(csv_path) != before:
            raise ValueError("price source changed; reload")
        path = next(p for p in paths if p.start_date == window_start)
        scenario = pa.phase_a_scenario(pa.PhaseACase(key[0], key[2], key[3]), key[1], path)
        case = NamedCase("phase-a-replay", str(key), scenario, date.fromisoformat(window_start))
        run, = run_named_cases((case,), points, 42, provenance["source_label"], provenance["quote_asset"])
    except (OSError, KeyError, TypeError) as error:
        raise ValueError(f"{csv_path}: {error}") from error
    checks, mismatches = [], []
    def check(label, actual, expected):
        checks.append(label)
        equal = (type(actual) is type(expected) and actual == expected)
        if type(actual) in (int, float) and type(expected) in (int, float):
            equal = abs(actual - expected) <= 1e-9 if isinstance(actual, float) else actual == expected
        if not equal:
            mismatches.append(label)
    result = run.result
    if window_start == summary["worst_total_start"]:
        check("principal_loss", result.principal_loss, summary["max_total_loss"])
    if window_start == summary["worst_individual_start"]:
        check("worst_member_loss", result.worst_member_loss, summary["max_individual_loss"])
        check("interest_used", result.interest_used, summary["interest_used_at_worst_individual"])
        check("obligation_uncollected", result.obligation_uncollected, summary["uncollected_at_worst_individual"])
        saved = {r["member_id"]: r for r in member_rows(study, key)}
        for member in result.agent_results:
            for field, value in asdict(member).items():
                check(f"member[{member.member_id}].{field}", value, saved[member.member_id].get(field))
    _assert_current(study)
    if _stat(csv_path) != before:
        raise ValueError("price source changed; reload")
    return ReplayResult(run, tuple(checks), tuple(mismatches))


def replay_frames(replay: ReplayResult) -> tuple[dict[str, object], ...]:
    frames = [("initial", "Ban đầu", 0, None)]
    frames.extend(("period", f"Sau kỳ {t.period + 1}", t.day, i) for i, t in enumerate(replay.run.trace))
    frames.extend((("freeze", "Đóng băng", replay.run.result.freeze_day, None),
                   ("settlement", "Quyết toán", replay.run.result.settlement_day, None)))
    return tuple(dict(index=i, kind=kind, label=label, day=day, trace_index=trace)
                 for i, (kind, label, day, trace) in enumerate(frames))


def csv_bytes(rows: tuple[dict[str, object], ...], provenance: dict[str, object]) -> bytes:
    output = StringIO(newline="")
    merged = [dict(r, **provenance) for r in rows]
    fields = list(dict.fromkeys(k for r in merged or [provenance] for k in r))
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (tuple, list, dict)) else v
                     for k, v in r.items()} for r in merged)
    return output.getvalue().encode("utf-8-sig")
