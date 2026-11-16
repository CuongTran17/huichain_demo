"""Extend the verified Phase B study without changing its engine or checkpoints."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import csv
from dataclasses import asdict, replace
from datetime import date
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
from time import perf_counter

from rosca_sim import phase_b
from rosca_sim.auction import AuctionEvent, annual_bid_interest
from rosca_sim.due_date_auction import DueDateAuctionModel, DueDateAuctionScenario
from rosca_sim.prices import PricePath, PricePoint


GRID = tuple(range(205, 301, 5))
END = date(2026, 10, 31)
CSV_SHA256 = "64dbd0eaf9908d5f1b59079f29610e824bc156a7112e2648e4f427d401091f16"
WITNESS_START = "2022-04-19"


def build_scenario(
    path: PricePath, ratio_pct: int, profile: str, fraction: float, *,
    strategic: bool, paid_count: int | None = None, forced_ids: tuple[int, ...] = (),
) -> DueDateAuctionScenario:
    if type(ratio_pct) is not int or ratio_pct not in (200, *GRID):
        raise ValueError("upper collateral ratio must be 200 or a grid point from 205 to 300")
    base = phase_b.phase_b_scenario(path, 2, profile, fraction, strategic=strategic,
                                    paid_count=paid_count, forced_ids=forced_ids)
    if ratio_pct == 200:
        return base
    ratio = ratio_pct / 100
    available = ratio * 500 / min(path.prices) + 1
    collateral = replace(base.auction.collateral, fixed_ratio=ratio, alpha_min=ratio, alpha_max=ratio)
    return replace(base, auction=replace(base.auction, collateral=collateral, agents=tuple(
        replace(member, available_eth=available) for member in base.auction.agents
    )))


def stress_score(path: PricePath) -> float:
    prices = path.daily_prices
    return max(
        (6 - paid) * prices[30 * slot] / ((5 - slot) * prices[sale_day])
        for paid in range(1, 6)
        for slot in range(paid)
        for sale_day in ((30 * paid,) if paid == 1 else (30 * paid, 30 * paid + 7))
    )


def screening_paths(paths: tuple[PricePath, ...]) -> tuple[PricePath, ...]:
    ranked = sorted(paths, key=lambda path: (-stress_score(path), path.start_date))
    witness = [path for path in paths if path.start_date == WITNESS_START]
    return tuple({p.start_date: p for p in witness + ranked[:12] + list(phase_b._pilot_paths(paths))}.values())


def _case_runs(path, ratio, profile, fraction, mode):
    base = build_scenario(path, ratio, profile, fraction, strategic=(mode == "strategic"))
    if mode == "strategic":
        cases = (base,)
    else:
        order = DueDateAuctionModel(base, "fixed", path).run().payout_order
        if len(order) != 6:
            raise ValueError("forced groups require a complete baseline payout order")
        cases = (replace(base, auction=replace(base.auction, forced_defaults=tuple(
            AuctionEvent(i, paid * 30) for i in group))) for paid, group in phase_b.forced_groups(order))
    for case in cases:
        model = DueDateAuctionModel(case, "fixed", path)
        result = model.run()
        if result.stop_reason == "no_eligible_bid":
            raise ValueError("Phase B extension assumes sufficient ETH to receive a payout")
        if case.auction.forced_defaults and (
            result.stop_reason != "default" or result.freeze_day != case.auction.forced_defaults[0].day
        ):
            raise ValueError("scripted default was not exercised")
        yield result


def _evidence(path, result):
    agents = result.agent_results
    return {
        "window_start": path.start_date,
        "freeze_day": result.freeze_day,
        "freeze_price_usdt": path.daily_prices[result.freeze_day],
        "payout_order": list(result.payout_order),
        "default_ids": [agent.member_id for agent in agents if agent.is_trigger_default],
        "eth_sale_proceeds_usdc": result.eth_sale_proceeds,
        "principal_shortfall_usdc": sum(agent.principal_loss for agent in agents),
        "worst_member_loss": result.worst_member_loss,
        "result": asdict(result),
    }


def screen_ratio(paths, ratio):
    runs = 0
    for path in paths:
        for mode in phase_b.MODES["full"]:
            for result in _case_runs(path, ratio, "all_zero", 0.0, mode):
                runs += 1
                if result.worst_member_loss > phase_b.LOSS_TOLERANCE:
                    witness = _evidence(path, result)
                    witness["mode"] = mode
                    return dict(ratio_pct=ratio, status="fail_witness", runs=runs, witness=witness)
    return dict(ratio_pct=ratio, status="needs_full", runs=runs, witness=None)


def select_threshold(grid, outcomes):
    for ratio in grid:
        status = outcomes.get(ratio)
        if status == "full_pass":
            return ratio, "found"
        if status not in {"fail_witness", "full_fail"}:
            return None, "incomplete"
    return None, "not_found"


def _run_job(paths, job):
    profile, fraction, ratio, mode = job
    summary = phase_b._summary(paths, "full", job)
    worst = None
    for path in paths:
        for result in _case_runs(path, ratio, profile, fraction, mode):
            summary["completed_runs"] += 1
            summary["loss_cases"] += result.worst_member_loss > phase_b.LOSS_TOLERANCE
            summary["interest_used_total"] += result.interest_used
            summary["uncollected_total"] += result.obligation_uncollected
            summary["secondary_shortfalls"] += result.secondary_shortfall_count
            if mode == "strategic":
                summary["strategic_defaults"] += result.default_count
                summary["strategic_gap_total"] += result.obligation_uncollected - sum(
                    agent.obligation_uncollected for agent in result.agent_results if not agent.is_trigger_default
                )
            if worst is None or result.worst_member_loss > summary["worst_member_loss"]:
                summary["worst_member_loss"] = result.worst_member_loss
                worst = _evidence(path, result)
    return {"summary": summary, "worst_case": worst}


def checkpoint(out, identity, paths, job, *, run):
    existing = phase_b._checkpoint(out, identity, paths, job, run=False)
    if existing is not None or not run:
        return existing
    data = _run_job(paths, job)
    if data["summary"]["completed_runs"] != data["summary"]["expected_runs"]:
        raise ValueError(f"incomplete Phase B upper job: {job}")
    phase_b._write_json(phase_b._job_path(out, job), {
        "fingerprint": phase_b._digest(identity), "job": job,
        "sha256": phase_b._digest(data), "data": data,
    })
    return data


def _execute_job(args):
    return checkpoint(*args, run=True)["summary"]


def _screening(out, identity, paths, *, run):
    path = out / "screening.json"
    fingerprint = phase_b._digest(identity)
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        rows = saved["data"]
        if (saved["fingerprint"] != fingerprint or saved["sha256"] != phase_b._digest(rows)
            or [row["ratio_pct"] for row in rows] != list(GRID)):
            raise ValueError("screening checkpoint mismatch or incomplete")
        return rows
    if not run:
        return None
    rows = [screen_ratio(paths, ratio) for ratio in GRID]
    phase_b._write_json(path, {"fingerprint": fingerprint, "sha256": phase_b._digest(rows), "data": rows})
    return rows


def _witness_columns(witness):
    witness = witness or {}
    return {
        "witness_window_start": witness.get("window_start"),
        "witness_freeze_day": witness.get("freeze_day"),
        "witness_default_ids": "|".join(map(str, witness.get("default_ids", ()))),
        "witness_eth_sale_usdc": witness.get("eth_sale_proceeds_usdc"),
        "witness_total_shortfall_usdc": witness.get("principal_shortfall_usdc"),
        "witness_member_loss_usdc": witness.get("worst_member_loss"),
    }


def _write_table(path, rows, columns):
    if rows:
        phase_b._write_csv(path, rows)
    else:
        phase_b._atomic_write(path, lambda handle: csv.DictWriter(handle, fieldnames=columns).writeheader())


def _first_payout_capital(candidate):
    if candidate is None:
        return []
    locked = 500 * candidate / 100
    rows = []
    for rate in phase_b.RATES:
        received = 600 - annual_bid_interest(500, rate, 150)
        extra = received - 100
        rows.append(dict(annual_bid_pct=round(rate * 100), net_payout_usdc=received,
                         extra_cash_usdc=extra, collateral_to_net_payout=locked / received,
                         collateral_to_extra_cash=locked / extra))
    return rows


def _aggregate(out, identity, paths, screening):
    outcomes, ratios, jobs = {}, [], []
    for screen in screening:
        ratio = screen["ratio_pct"]
        observed = [checkpoint(out, identity, paths, job, run=False)
                    for job in phase_b._jobs("full", ratio)] if screen["status"] == "needs_full" else []
        summaries = [item["summary"] for item in observed if item is not None]
        jobs.extend(summaries)
        witness = screen["witness"]
        if witness:
            status = "fail_witness"
        elif len(summaries) == len(observed) and summaries:
            status = "full_pass" if phase_b._passed(summaries) else "full_fail"
            if status == "full_fail":
                witness = max((item["worst_case"] for item in observed), key=lambda case: case["worst_member_loss"])
        else:
            status = "incomplete" if summaries else "not_scanned"
        outcomes[ratio] = status
        ratios.append({
            "ratio_pct": ratio, "status": status,
            "screening_runs": screen["runs"],
            "full_runs": sum(row["completed_runs"] for row in summaries),
            "expected_full_runs": len(paths) * len(phase_b.PROFILES) * len(phase_b.FRACTIONS) * 58,
            "full_worst_member_loss_usdc": max((row["worst_member_loss"] for row in summaries), default=None),
            **_witness_columns(witness),
        })
    candidate, status = select_threshold(GRID, outcomes)
    witness_columns = tuple(_witness_columns(None))
    _write_table(out / "screening.csv", [
        dict(ratio_pct=screen["ratio_pct"], status=screen["status"], runs=screen["runs"],
             **_witness_columns(screen["witness"]))
        for screen in screening
    ], ("ratio_pct", "status", "runs", *witness_columns))
    _write_table(out / "phase_b_upper_ratios.csv", ratios, (
        "ratio_pct", "status", "screening_runs", "full_runs", "expected_full_runs",
        "full_worst_member_loss_usdc", *witness_columns,
    ))
    _write_table(out / "phase_b_upper_jobs.csv", jobs,
                 sorted(phase_b._summary(paths, "full", phase_b._jobs("full", GRID[0])[0])))
    phase_b._write_json(out / "threshold.json", {
        "status": status, "min_passing_ratio_pct": candidate,
        "fingerprint": phase_b._digest(identity), "full_runs": sum(row["full_runs"] for row in ratios),
        "screening_runs": sum(row["screening_runs"] for row in ratios),
        "first_payout_locked_value_usdc": 500 * candidate / 100 if candidate else None,
        "first_payout_capital_by_bid": _first_payout_capital(candidate),
    })
    return 1 if status == "incomplete" else 0


def run_upper(prices: Path, out: Path, end: date, action: str) -> int:
    data = prices.read_bytes()
    digest = sha256(data).hexdigest()
    if end != END or digest != CSV_SHA256:
        raise ValueError("upper study requires the verified Phase B price CSV through 2026-10-31")
    points = tuple(PricePoint(date.fromisoformat(row["date"]), float(row["close"]))
                   for row in csv.DictReader(StringIO(data.decode("utf-8"))))
    paths = phase_b.phase_b_paths(points)
    if len(paths) != 1608 or points[0].day != phase_b.START or points[-1].day != END:
        raise ValueError("unexpected Phase B upper date range or window count")
    selected = screening_paths(paths)
    if action == "dry_run":
        print(json.dumps({"grid_pct": GRID, "windows": len(paths), "screen_windows": len(selected),
                          "runs_per_full_ratio": len(paths) * 3 * 3 * 58}))
        return 0
    identity = {
        "study": "phase-b-upper-v1", "scope": "full", "price_sha256": digest,
        "end": end.isoformat(), "windows": len(paths), "grid_pct": list(GRID),
        "screen_window_starts": [p.start_date for p in selected],
        "code_sha256": {name: sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                        for name in ("phase_b_upper.py", "phase_b.py", "due_date_auction.py",
                                     "auction.py", "prices.py", "model.py")},
    }
    manifest = out / "manifest.json"
    if manifest.exists():
        if json.loads(manifest.read_text(encoding="utf-8")) != identity:
            raise ValueError("Phase B upper input fingerprint differs")
    elif action == "run" and (not out.exists() or not any(out.iterdir())):
        phase_b._write_json(manifest, identity)
    else:
        raise ValueError("Phase B upper requires an empty output directory or matching manifest")
    phase_b._write_json(out / "threshold.json", {"status": "incomplete", "min_passing_ratio_pct": None})
    _aggregate(out, identity, paths, [])
    start = perf_counter()
    screening = _screening(out, identity, selected, run=(action == "run"))
    if screening is None:
        return 1
    if action == "run":
        candidates = [row["ratio_pct"] for row in screening if row["status"] == "needs_full"]
        print(f"Phase B upper: screened {len(GRID)} ratios; full candidates: {candidates}", flush=True)
        if candidates:
            with ProcessPoolExecutor(max_workers=6) as pool:
                for ratio in candidates:
                    print(f"Phase B upper full: {ratio}%, {len(paths)} windows", flush=True)
                    jobs = phase_b._jobs("full", ratio)
                    summaries = list(pool.map(_execute_job, ((out, identity, paths, job) for job in jobs)))
                    if phase_b._passed(summaries):
                        break
        phase_b._write_json(out / "last_run_timing.json", {"elapsed_seconds": perf_counter() - start})
    return _aggregate(out, identity, paths, screening)
