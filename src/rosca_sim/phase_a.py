"""Bounded, deterministic phase-A study; the Mesa auction engine owns all cash flows."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
import csv
import hashlib
from itertools import combinations
import json
from math import isfinite
import os
from pathlib import Path
import random
import subprocess
import tempfile
from time import perf_counter

from rosca_sim.auction import (ANNUAL_BID_METADATA, AuctionAgentSeed, AuctionBid,
                               AuctionEvent, AuctionScenario, AuctionRoscaModel)
from rosca_sim.model import BehaviorConfig, CollateralConfig, RoscaConfig
from rosca_sim.prices import PricePath, PricePoint, sample_historical_path, valid_historical_starts


ANNUAL_RATES = (0.0, 0.05, 0.10, 0.15, 0.20)
COARSE_RATIOS = (0.25, 0.50, 0.75, 1.00, 1.25, 1.50, 1.75, 2.00)


@dataclass(frozen=True)
class PhaseACase:
    annual_rate: float
    paid_count: int
    default_ids: tuple[int, ...]

    def __post_init__(self):
        if (type(self.annual_rate) not in (int, float) or self.annual_rate not in ANNUAL_RATES
            or type(self.paid_count) is not int or not 1 <= self.paid_count <= 5
            or type(self.default_ids) is not tuple or not self.default_ids
            or any(type(i) is not int or not 0 <= i < self.paid_count for i in self.default_ids)
            or len(set(self.default_ids)) != len(self.default_ids)):
            raise ValueError("invalid phase A rate, paid count or default group")

    @property
    def default_day(self) -> int:
        return (self.paid_count - 1) * 30 + 1


def phase_a_cases() -> tuple[PhaseACase, ...]:
    return tuple(PhaseACase(rate, k, group) for rate in ANNUAL_RATES
                 for k in range(1, 6) for size in range(1, k + 1)
                 for group in combinations(range(k), size))


def phase_a_paths(points: tuple[PricePoint, ...]) -> tuple[PricePath, ...]:
    selected = tuple(sorted((p for p in points if date(2022, 1, 1) <= p.day <= date(2022, 12, 31)),
                            key=lambda p: p.day))
    if (len({p.day for p in selected}) != len(selected)
        or any(not isfinite(p.close) or p.close <= 0 for p in selected)):
        raise ValueError("invalid or duplicate phase A prices")
    starts = valid_historical_starts(selected, 6, 30, 7)
    if not starts:
        raise ValueError("no complete 2022 window for phase A")
    return tuple(sample_historical_path(selected, 6, 30, random.Random(42),
                                       normalize=False, window_start=start, extra_days=7)
                 for start in starts)


def phase_a_scenario(case: PhaseACase, ratio: float, path: PricePath) -> AuctionScenario:
    if type(ratio) not in (int, float) or not isfinite(ratio) or not 0.25 <= ratio <= 2:
        raise ValueError("phase A ratio must be between 0.25 and 2.00")
    available = 1000 / min(path.prices) + 1
    return AuctionScenario(
        RoscaConfig(6, 6, 100.0, 30), CollateralConfig(ratio, ratio, ratio),
        BehaviorConfig(10000, 10000),
        tuple(AuctionAgentSeed(i, 0.5, available, "usdc_first", 500.0, 7) for i in range(6)),
        tuple(AuctionBid(period, member, case.annual_rate)
              for period in range(6) for member in range(period, 6)),
        forced_defaults=tuple(AuctionEvent(i, case.default_day) for i in case.default_ids),
        grace_days=7,
    )


def _hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _code_hashes() -> dict[str, str]:
    return {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ("phase_a.py", "auction.py", "model.py", "prices.py")}


def _paths_hash(paths) -> str:
    if not paths or any(not p.start_date or len(p.daily_prices) != 158 for p in paths):
        raise ValueError("phase A needs complete dated paths")
    if len({p.start_date for p in paths}) != len(paths):
        raise ValueError("duplicate path starts")
    return _hash([asdict(p) for p in paths])


def describe_phase_a(paths, provenance) -> dict:
    identity = {"study_version": 1, **ANNUAL_BID_METADATA, "code_hashes": _code_hashes(),
                "collateral_release_policy": "terminal",
                "paths_sha256": _paths_hash(paths), "provenance": provenance,
                "window_starts": sorted(p.start_date for p in paths),
                "annual_rates": ANNUAL_RATES, "coarse_ratios": COARSE_RATIOS,
                "members": 6, "contribution": 100, "period_days": 30, "grace_days": 7,
                "slippage": 0, "loss_tolerance": 1e-9}
    return {"identity": identity, "fingerprint": _hash(identity),
            "windows": len(paths), "cases_per_rate": 57, "coarse_jobs": 40,
            "expected_coarse_runs": len(paths) * 57 * 40,
            "planned_ratios": list(COARSE_RATIOS),
            "interpretation": "Historical coverage only; overlapping windows are not independent. "
                              "Assumes sufficient ETH and compliant USDC repayment; USDT=USDC. "
                              "Not a safety guarantee or legal compliance assessment."}


def _atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Completed files are published only after serialization succeeds.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     suffix=".tmp", delete=False) as handle:
        json.dump(value, handle, sort_keys=True, allow_nan=False)
        temporary = handle.name
    os.replace(temporary, path)


def _manifest(output_dir: Path) -> dict:
    data = json.loads((output_dir / "phase_a_metadata.json").read_text(encoding="utf-8"))
    if (_hash(data["identity"]) != data["fingerprint"]
        or data["identity"]["code_hashes"] != _code_hashes()):
        raise ValueError("phase A fingerprint/input code conflict")
    starts = data["identity"]["window_starts"]
    if (data["windows"] != len(starts) or not starts or len(set(starts)) != len(starts)
        or not set(COARSE_RATIOS) <= set(data["planned_ratios"])
        or len(set(data["planned_ratios"])) != len(data["planned_ratios"])):
        raise ValueError("corrupt phase A manifest coverage")
    for ratio in data["planned_ratios"]:
        _validate_selectors(0, ratio)
    return data


def prepare_phase_a(paths, output_dir: Path, provenance) -> str:
    proposed = describe_phase_a(paths, provenance)
    target = Path(output_dir) / "phase_a_metadata.json"
    if target.exists():
        if _manifest(Path(output_dir))["fingerprint"] != proposed["fingerprint"]:
            raise ValueError("phase A input fingerprint conflict; use a new output directory")
    else:
        if Path(output_dir).exists() and any(Path(output_dir).iterdir()):
            raise ValueError("output directory has files but no phase A manifest")
        repo = Path(__file__).resolve().parents[2]
        try:
            proposed["git_commit_informational"] = subprocess.run(
                ["git", "-c", f"safe.directory={repo.as_posix()}", "rev-parse", "HEAD"],
                cwd=repo, capture_output=True, text=True, check=True, timeout=3,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            proposed["git_commit_informational"] = None
        _atomic_json(target, proposed)
    return proposed["fingerprint"]


def _validate_selectors(rate, ratio):
    if type(rate) not in (float, int) or rate not in ANNUAL_RATES:
        raise ValueError("annual rate must be 0, .05, .10, .15 or .20")
    if (type(ratio) not in (float, int) or not isfinite(ratio)
        or not .25 <= ratio <= 2 or Decimal(str(ratio)) % Decimal(".05")):
        raise ValueError("ratio must be on the 5-point grid from .25 to 2.00")


def _job_path(output_dir, rate, ratio):
    return Path(output_dir) / "jobs" / f"rate-{round(rate * 100):02d}-ratio-{round(ratio * 100):03d}.json"


def _case_key(case):
    return (case.annual_rate, case.paid_count, "|".join(map(str, case.default_ids)))


def _read_job(path, manifest, rate, ratio):
    try:
        job = json.loads(path.read_text(encoding="utf-8"))
        expected = {_case_key(c) for c in phase_a_cases() if c.annual_rate == rate}
        summaries = job["summaries"]
        keys = {(r["annual_rate"], r["k"], r["default_ids"]) for r in summaries}
        if (job["fingerprint"] != manifest["fingerprint"] or job["annual_rate"] != rate
            or job["ratio"] != ratio or job["completed_runs"] != manifest["windows"] * 57
            or len(summaries) != 57 or keys != expected or len(job["worst_members"]) != 342
            or job["payload_sha256"] != _hash([summaries, job["worst_members"]])):
            raise ValueError("incomplete/corrupt phase A job or fingerprint conflict")
        for row in summaries:
            if (row["ratio"] != ratio or row["expected_windows"] != manifest["windows"]
                or row["completed_windows"] != manifest["windows"]
                or not 0 <= row["loss_window_count"] <= manifest["windows"]
                or any(not isfinite(row[key]) or row[key] < 0 for key in (
                    "max_total_loss", "max_individual_loss", "interest_used_at_worst_individual",
                    "uncollected_at_worst_individual", "max_initial_collateral_value"))
                or row["worst_individual_start"] not in manifest["identity"]["window_starts"]
                or row["worst_total_start"] not in manifest["identity"]["window_starts"]):
                raise ValueError("incomplete/corrupt phase A summary")
        return job
    except (KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("incomplete/corrupt phase A job") from error


def run_phase_a_job(paths, annual_rate, ratio, output_dir: Path, fingerprint: str) -> Path:
    _validate_selectors(annual_rate, ratio)
    output_dir = Path(output_dir)
    manifest = _manifest(output_dir)
    if (manifest["fingerprint"] != fingerprint
        or manifest["identity"]["paths_sha256"] != _paths_hash(paths)):
        raise ValueError("phase A input/path fingerprint conflict")
    target = _job_path(output_dir, annual_rate, ratio)
    if target.exists():
        _read_job(target, manifest, annual_rate, ratio)
        return target
    if ratio not in manifest["planned_ratios"]:
        manifest["planned_ratios"] = sorted(set(manifest["planned_ratios"]) | {ratio})
        _atomic_json(output_dir / "phase_a_metadata.json", manifest)
    started = perf_counter()
    summaries, members = [], []
    for case in (c for c in phase_a_cases() if c.annual_rate == annual_rate):
        row = {"annual_rate": annual_rate, "ratio": ratio, "k": case.paid_count,
               "default_ids": _case_key(case)[2], "expected_windows": len(paths),
               "completed_windows": 0, "loss_window_count": 0,
               "max_total_loss": -1.0, "max_individual_loss": -1.0,
               "max_initial_collateral_value": 0.0}
        worst = None
        for path in sorted(paths, key=lambda p: p.start_date):
            result = AuctionRoscaModel(phase_a_scenario(case, ratio, path),
                                      policy="fixed", price_path=path, seed=42).run()
            if (result.stop_reason != "default" or result.freeze_day != case.default_day
                or result.payout_order != tuple(range(case.paid_count))
                or result.secondary_shortfall_count != 0):
                raise ValueError("incomplete phase A run: unexpected default/no-eligible outcome")
            row["completed_windows"] += 1
            row["loss_window_count"] += result.worst_member_loss > 1e-9
            row["max_initial_collateral_value"] = max(row["max_initial_collateral_value"],
                max(a.eth_locked * path.daily_prices[a.payout_day] for a in result.agent_results
                    if a.payout_day is not None))
            if result.principal_loss > row["max_total_loss"]:
                row.update(max_total_loss=result.principal_loss, worst_total_start=path.start_date)
            if result.worst_member_loss > row["max_individual_loss"]:
                row.update(max_individual_loss=result.worst_member_loss,
                           worst_individual_start=path.start_date,
                           interest_used_at_worst_individual=result.interest_used,
                           uncollected_at_worst_individual=result.obligation_uncollected)
                worst = result.agent_results
        summaries.append(row)
        members.extend({"annual_rate": annual_rate, "ratio": ratio, "k": case.paid_count,
                        "default_ids": row["default_ids"], "window_start": row["worst_individual_start"],
                        **asdict(member)} for member in worst)
    job = {"fingerprint": fingerprint, "annual_rate": annual_rate, "ratio": ratio,
           "completed_runs": len(paths) * 57, "summaries": summaries, "worst_members": members,
           "payload_sha256": _hash([summaries, members]), "wall_seconds": perf_counter() - started}
    _atomic_json(target, job)
    return target


def _threshold_rows(summaries, ratios, window_count):
    index = {(r["annual_rate"], r["k"], r["default_ids"], r["ratio"]): r for r in summaries}
    cases = [_case_key(c) for c in phase_a_cases()]
    groups = [("case", [key]) for key in cases]
    groups += [("rate", [key for key in cases if key[0] == rate]) for rate in ANNUAL_RATES]
    groups += [("global", cases)]
    rows = []
    for scope, keys in groups:
        passing, tested = [], []
        completed = 0
        for ratio in sorted(ratios):
            found = [index.get((*key, ratio)) for key in keys]
            completed += sum(r is not None and r["completed_windows"] == window_count
                             and r["expected_windows"] == window_count for r in found)
            if all(r is not None and r["completed_windows"] == window_count
                   and r["expected_windows"] == window_count for r in found):
                tested.append(ratio)
                if all(r["max_individual_loss"] <= 1e-9 for r in found):
                    passing.append(ratio)
        complete = len(tested) == len(ratios)
        rows.append({"scope": scope, "annual_rate": keys[0][0] if scope != "global" else None,
                     "k": keys[0][1] if scope == "case" else None,
                     "default_ids": keys[0][2] if scope == "case" else None,
                     "candidate_ratio": min(passing) if complete and passing else None,
                     "tested_ratios": tested, "passing_ratios": passing,
                     "completed_checks": completed, "expected_checks": len(keys) * len(ratios),
                     "status": "incomplete" if not complete else "complete" if passing else "not_found",
                     "nonmonotonic": any(r > min(passing) and r not in passing for r in tested)
                                      if passing else False})
    return tuple(rows)


def _atomic_csv(path, rows):
    if not rows:
        return
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent,
                                     suffix=".tmp", delete=False) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({k: json.dumps(v) if isinstance(v, list) else v for k, v in r.items()}
                         for r in rows)
        temporary = handle.name
    os.replace(temporary, path)


def _collect_jobs(output_dir, manifest, ratios):
    summaries, members = [], []
    for rate in ANNUAL_RATES:
        for ratio in ratios:
            target = _job_path(output_dir, rate, ratio)
            if target.exists():
                job = _read_job(target, manifest, rate, ratio)
                summaries.extend(job["summaries"])
                members.extend(job["worst_members"])
    return summaries, members


def aggregate_phase_a(output_dir: Path) -> tuple[dict[str, object], ...]:
    output_dir = Path(output_dir)
    manifest = _manifest(output_dir)
    summaries, members = _collect_jobs(output_dir, manifest, manifest["planned_ratios"])
    rows = _threshold_rows(summaries, manifest["planned_ratios"], manifest["windows"])
    _atomic_csv(output_dir / "phase_a_summary.csv", summaries)
    _atomic_csv(output_dir / "phase_a_worst_members.csv", members)
    _atomic_csv(output_dir / "phase_a_thresholds.csv", rows)
    manifest.update(completed_jobs=len(summaries) // 57, aggregate_status=rows[-1]["status"])
    _atomic_json(output_dir / "phase_a_metadata.json", manifest)
    return rows


def refinement_ratios(rows) -> tuple[float, ...]:
    if not rows or any(r["status"] == "incomplete" for r in rows):
        raise ValueError("coarse study is incomplete")
    result = set()
    for row in rows:
        candidate = row["candidate_ratio"]
        if candidate is not None and candidate > .25:
            lower = max(r for r in COARSE_RATIOS if r < candidate)
            result.update(float(Decimal(str(lower)) + Decimal(".05") * i) for i in range(1, 5))
    return tuple(sorted(result))


def plan_phase_a_refinement(output_dir: Path) -> tuple[float, ...]:
    output_dir = Path(output_dir)
    manifest = _manifest(output_dir)
    summaries, _ = _collect_jobs(output_dir, manifest, COARSE_RATIOS)
    additions = refinement_ratios(_threshold_rows(summaries, COARSE_RATIOS, manifest["windows"]))
    manifest["planned_ratios"] = sorted(set(manifest["planned_ratios"]) | set(additions))
    _atomic_json(output_dir / "phase_a_metadata.json", manifest)
    return additions
