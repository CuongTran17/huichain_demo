"""Due-date default study. The auction engine owns all cash flows."""

from __future__ import annotations

import csv
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, replace
from datetime import date, timedelta
from hashlib import sha256
from io import StringIO
from itertools import combinations, product
import json
from math import isfinite
from pathlib import Path
import random
from tempfile import NamedTemporaryFile

from rosca_sim.auction import AuctionAgentSeed, AuctionBid, AuctionEvent, AuctionScenario
from rosca_sim.due_date_auction import DueDateAuctionModel, DueDateAuctionScenario
from rosca_sim.model import BehaviorConfig, CollateralConfig, RoscaConfig
from rosca_sim.prices import PricePath, PricePoint, sample_historical_path, valid_historical_starts


START = date(2022, 1, 1)
PROFILES = ("all_zero", "all_twenty", "mixed_rotating")
FRACTIONS = (0.0, 0.5, 1.0)
PILOT_RATIOS = (135, 140, 150, 180, 185, 190)
MODES = {"pilot": ("strategic", "all_pay", "forced"), "full": ("strategic", "forced")}
LOSS_TOLERANCE = 1e-9
RATES = (0.0, 0.05, 0.10, 0.15, 0.20)


def phase_b_paths(points: tuple[PricePoint, ...]) -> tuple[PricePath, ...]:
    points = tuple(sorted(points, key=lambda point: point.day))
    if len({point.day for point in points}) != len(points) or any(
        not isfinite(point.close) or point.close <= 0 for point in points
    ):
        raise ValueError("Phase B needs unique dates and finite positive prices")
    starts = valid_historical_starts(points, 6, 30, 7)
    if not starts:
        raise ValueError("Phase B needs at least one continuous 158-day price window")
    return tuple(sample_historical_path(points, 6, 30, random.Random(42), normalize=False,
                                       window_start=start, extra_days=7) for start in starts)


def forced_groups(payout_order: tuple[int, ...]) -> tuple[tuple[int, tuple[int, ...]], ...]:
    return tuple((k, group) for k in range(1, 6) for size in range(1, k + 1)
                 for group in combinations(payout_order[:k], size))


def phase_b_scenario(
    path: PricePath, ratio: float, profile: str, fraction: float, *,
    strategic: bool, paid_count: int | None = None, forced_ids: tuple[int, ...] = (),
) -> DueDateAuctionScenario:
    if profile not in PROFILES or type(ratio) not in (int, float) or not 0.25 <= ratio <= 2:
        raise ValueError("invalid Phase B profile or collateral ratio")
    if (paid_count is None) != (not forced_ids) or (
        paid_count is not None and (strategic or type(paid_count) is not int or not 1 <= paid_count <= 5)
    ):
        raise ValueError("invalid Phase B forced default")
    available_eth = 1000 / min(path.prices) + 1
    bids = tuple(
        AuctionBid(period, member, RATES[(member + period) % 5] if profile == "mixed_rotating"
                   else (0.20 if profile == "all_twenty" else 0.0))
        for period, member in product(range(6), repeat=2)
    )
    auction = AuctionScenario(
        RoscaConfig(6, 6, 100.0, 30), CollateralConfig(ratio, ratio, ratio),
        BehaviorConfig(10000, 10000),
        tuple(AuctionAgentSeed(i, 0.5, available_eth, "usdc_first", 500, 7) for i in range(6)),
        bids, forced_defaults=tuple(AuctionEvent(i, paid_count * 30) for i in forced_ids),
    )
    return DueDateAuctionScenario(auction, strategic, fraction)


def _digest(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def _atomic_write(path: Path, write) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", newline="", encoding="utf-8", dir=path.parent,
                            suffix=".tmp", delete=False) as handle:
        temporary = Path(handle.name)
        try:
            write(handle)
        except BaseException:
            handle.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_json(path: Path, data) -> None:
    _atomic_write(path, lambda handle: json.dump(data, handle, sort_keys=True, allow_nan=False))


def _write_csv(path: Path, rows) -> None:
    def write(handle):
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    _atomic_write(path, write)


def _pilot_paths(paths):
    def drawdown(path):
        prices = path.prices
        return min(b / a for a, b in zip(prices, prices[1:]))
    oldest = [p for p in paths if p.start_date == "2022-04-18"]
    lowest = sorted(paths, key=lambda p: (drawdown(p), p.start_date))[:5]
    return tuple({p.start_date: p for p in oldest + lowest}.values())


def _jobs(scope, ratio):
    return tuple(product(PROFILES, FRACTIONS, (ratio,), MODES[scope]))


def _job_path(out, job):
    profile, fraction, ratio, mode = job
    return out / "jobs" / f"{profile}-usdc{int(fraction * 100)}-eth{ratio}-{mode}.json"


def _group_cases(order, scope):
    if scope == "full":
        return forced_groups(order)
    return ((1, order[:1]), (3, order[:2]), (5, order[:5]))


def _expected_runs(paths, scope, mode):
    return len(paths) * ((57 if scope == "full" else 3) if mode == "forced" else 1)


def _summary(paths, scope, job):
    profile, fraction, ratio, mode = job
    return dict(profile=profile, capacity_fraction=fraction, ratio_pct=ratio, mode=mode,
                windows=len(paths), expected_runs=_expected_runs(paths, scope, mode),
                completed_runs=0, loss_cases=0, worst_member_loss=0.0, no_eligible_bid=0,
                strategic_defaults=0, strategic_gap_total=0.0, interest_used_total=0.0,
                uncollected_total=0.0, secondary_shortfalls=0)


def _run_job(paths, scope, job):
    profile, fraction, ratio, mode = job
    summary = _summary(paths, scope, job)
    slots = [dict(payout_number=i + 1, payouts=0, max_eth_locked=0.0, max_locked_usdc=0.0,
                  min_usdc_received=None, max_locked_to_received=0.0,
                  max_locked_to_extra_cash=None) for i in range(6)]
    worst = None
    for path in paths:
        base = phase_b_scenario(path, ratio / 100, profile, fraction, strategic=(mode == "strategic"))
        if mode == "forced":
            order = DueDateAuctionModel(base, "fixed", path).run().payout_order
            if len(order) != 6:
                raise ValueError("forced default study requires a complete baseline payout order")
            groups = _group_cases(order, scope)
            cases = (replace(base, auction=replace(
                base.auction, forced_defaults=tuple(AuctionEvent(i, k * 30) for i in group)))
                     for k, group in groups)
        else:
            cases = (base,)
        for case in cases:
            model = DueDateAuctionModel(case, "fixed", path)
            result = model.run()
            events = case.auction.forced_defaults
            if events and (
                result.stop_reason != "default" or result.freeze_day != events[0].day
            ):
                raise ValueError("scripted default was not exercised")
            summary["completed_runs"] += 1
            summary["loss_cases"] += result.worst_member_loss > LOSS_TOLERANCE
            summary["no_eligible_bid"] += result.stop_reason == "no_eligible_bid"
            summary["strategic_defaults"] += len(model.strategic_default_gaps)
            summary["strategic_gap_total"] += sum(model.strategic_default_gaps.values())
            summary["interest_used_total"] += result.interest_used
            summary["uncollected_total"] += result.obligation_uncollected
            summary["secondary_shortfalls"] += result.secondary_shortfall_count
            if worst is None or result.worst_member_loss > summary["worst_member_loss"]:
                summary["worst_member_loss"] = result.worst_member_loss
                worst = {"window_start": path.start_date, "freeze_day": result.freeze_day,
                         "freeze_price": path.daily_prices[result.freeze_day],
                         "forced_ids": [event.member_id for event in events],
                         "strategic_gaps": model.strategic_default_gaps,
                         "result": asdict(result)}
            for slot, member_id in zip(slots, result.payout_order):
                member = result.agent_results[member_id]
                value = member.eth_locked * path.daily_prices[member.payout_day]
                received = member.net_payout
                slot["payouts"] += 1
                slot["max_eth_locked"] = max(slot["max_eth_locked"], member.eth_locked)
                slot["max_locked_usdc"] = max(slot["max_locked_usdc"], value)
                prior = slot["min_usdc_received"]
                slot["min_usdc_received"] = received if prior is None else min(prior, received)
                if received > 0:
                    slot["max_locked_to_received"] = max(slot["max_locked_to_received"], value / received)
                if received > 100:
                    slot["max_locked_to_extra_cash"] = max(slot["max_locked_to_extra_cash"] or 0,
                                                           value / (received - 100))
    return {"summary": summary, "slots": slots, "worst_case": worst}


def _checkpoint(out, identity, paths, job, *, run):
    path = _job_path(out, job)
    scope = identity["scope"]
    fingerprint = _digest(identity)
    expected = _expected_runs(paths, scope, job[3])
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        data = saved.get("data", {})
        if (saved.get("fingerprint") != fingerprint or saved.get("job") != list(job)
            or saved.get("sha256") != _digest(data)
            or data.get("summary", {}).get("completed_runs") != expected):
            raise ValueError(f"Phase B checkpoint mismatch or incomplete: {path.name}")
        return data
    if not run:
        return None
    data = _run_job(paths, scope, job)
    if data["summary"]["completed_runs"] != expected:
        raise ValueError(f"Phase B job did not finish: {path.name}")
    _write_json(path, {"fingerprint": fingerprint, "job": job, "sha256": _digest(data), "data": data})
    return data


def _run_checkpoint(args):
    return _checkpoint(*args, run=True)["summary"]


def _passed(rows):
    return all(row["worst_member_loss"] <= LOSS_TOLERANCE and row["no_eligible_bid"] == 0 for row in rows)


def _thresholds(rows, ratios, complete, scope):
    for profile, fraction in (*product(PROFILES, FRACTIONS), ("all", "all")):
        relevant = [row for row in rows if profile == "all" or
                    (row["profile"], row["capacity_fraction"]) == (profile, fraction)]
        observed = {r: [row for row in relevant if row["ratio_pct"] == r] for r in ratios}
        passed = [r for r in ratios if complete and observed[r] and _passed(observed[r])]
        candidate = min(passed) if complete and scope == "full" and passed else None
        lower = candidate - 5 if candidate is not None else None
        status = ("incomplete" if not complete else "pilot" if scope == "pilot" else
                  "complete" if candidate is not None else "not_found")
        yield dict(profile=profile, capacity_fraction=fraction, status=status,
                   tested_ratios_pct="|".join(map(str, ratios)), min_passing_ratio_pct=candidate,
                   adjacent_lower_fails_pct=lower if lower in observed and lower not in passed else None,
                   result_at_180=("PASS" if 180 in passed else "FAIL")
                   if complete and observed.get(180) else None)


def run_phase_b(prices: Path, output: Path, source_label: str, end: date, action: str) -> int:
    if not source_label.strip() or end < START:
        raise ValueError("Phase B requires a source label and a date at or after 2022-01-01")
    csv_bytes = prices.read_bytes()
    reader = csv.DictReader(StringIO(csv_bytes.decode("utf-8-sig")))
    if not reader.fieldnames or not {"date", "close"}.issubset(reader.fieldnames):
        raise ValueError("price CSV must contain date and close columns")
    points = tuple(sorted((PricePoint(day, float(row["close"])) for row in reader
                           if START <= (day := date.fromisoformat(row["date"])) <= end),
                          key=lambda point: point.day))
    if not points or points[0].day != START or points[-1].day != end:
        raise ValueError("Phase B start and end dates must be present in the price CSV")
    paths = phase_b_paths(points)
    pilot_paths = _pilot_paths(paths)
    if action == "dry_run":
        print(json.dumps({"windows": len(paths), "pilot_windows": len(pilot_paths),
                          "pilot_ratios_pct": PILOT_RATIOS,
                          "full_runs_per_ratio": len(paths) * len(PROFILES) * len(FRACTIONS) * 58}))
        return 0
    manifest_path = output / "phase_b_metadata.json"
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    if action == "aggregate_only" and previous is None:
        raise ValueError("Phase B metadata is missing")
    scope = previous["identity"]["scope"] if action == "aggregate_only" else action
    selected = pilot_paths if scope == "pilot" else paths
    identity = {
        "study_version": 1, "scope": scope, "source_label": source_label, "quote_asset": "USDT",
        "csv_sha256": sha256(csv_bytes).hexdigest(),
        "start": START.isoformat(), "end": end.isoformat(),
        "profiles": list(PROFILES), "capacity_fractions": list(FRACTIONS),
        "window_starts": [p.start_date for p in selected], "missing_price_days": (end - START).days + 1 - len(points),
        "code_sha256": {name: sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                        for name in ("phase_b.py", "due_date_auction.py", "auction.py", "prices.py", "model.py")},
        "slippage": 0, "grace_days": 7, "price_basis": "ETH/USDT daily close, USDT≈USDC",
        "eligibility_basis": "assumes enough ETH to bid",
    }
    if previous and (previous["identity"] != identity or previous["fingerprint"] != _digest(identity)):
        raise ValueError("Phase B input fingerprint differs; use a new output directory")
    if previous is None and output.exists() and any(output.iterdir()):
        raise ValueError("Phase B output directory must be empty or contain matching metadata")
    ratios = set(previous["tested_ratios_pct"]) if previous else set()
    search_finished = bool(previous and previous["search_finished"])

    def coverage():
        return {"search_finished": search_finished, "tested_ratios_pct": sorted(ratios)}

    def write_metadata(status):
        _write_json(manifest_path, {"identity": identity, "fingerprint": _digest(identity),
                                   "status": status, **coverage(), "coverage_sha256": _digest(coverage())})

    if previous and (previous.get("coverage_sha256") != _digest(coverage())
                     or any(type(r) is not int or not 25 <= r <= 200 or r % 5 for r in ratios)
                     or (search_finished and 180 not in ratios)
                     or (search_finished and scope == "pilot" and ratios != set(PILOT_RATIOS))):
        raise ValueError("Phase B manifest coverage is invalid")
    write_metadata("incomplete")
    _write_csv(output / "phase_b_thresholds.csv", list(_thresholds([], sorted(ratios), False, scope)))

    def run_ratio(ratio, pool=None):
        ratios.add(ratio)
        write_metadata("incomplete")
        print(f"Phase B {scope}: {ratio}% collateral, {len(selected)} windows", flush=True)
        inputs = ((output, identity, selected, job) for job in _jobs(scope, ratio))
        return list(map(_run_checkpoint, inputs) if pool is None else pool.map(_run_checkpoint, inputs))

    def run_full(pool=None):
        pilot_candidate = next((r for r in PILOT_RATIOS if _passed([
            _run_job(pilot_paths, "pilot", job)["summary"] for job in _jobs("pilot", r)
        ])), 180)
        verified = {180: _passed(run_ratio(180, pool))}
        ratio = pilot_candidate
        visited = set()
        while 25 <= ratio <= 200 and ratio not in visited:
            visited.add(ratio)
            if ratio not in verified:
                verified[ratio] = _passed(run_ratio(ratio, pool))
            ratio += -5 if verified[ratio] else 5

    if action == "pilot":
        for ratio in PILOT_RATIOS:
            run_ratio(ratio)
        search_finished = True
    elif action == "full":
        if len(selected) >= 50:
            with ProcessPoolExecutor(max_workers=6) as pool:
                run_full(pool)
        else:
            run_full()
        search_finished = True

    rows, slots = [], []
    missing = False
    for ratio in sorted(ratios):
        for job in _jobs(scope, ratio):
            data = _checkpoint(output, identity, selected, job, run=False)
            if data is None:
                missing = True
                summary = _summary(selected, scope, job)
                rows.append({key: value if key in (
                    "profile", "capacity_fraction", "ratio_pct", "mode", "windows",
                    "expected_runs", "completed_runs",
                ) else None for key, value in summary.items()})
                continue
            row = data["summary"]
            rows.append(row)
            slots.extend({**{key: row[key] for key in ("profile", "capacity_fraction", "ratio_pct", "mode")},
                          **slot} for slot in data["slots"] if slot["payouts"])
    complete = bool(ratios) and search_finished and not missing
    if rows:
        _write_csv(output / "phase_b_summary.csv", rows)
    if slots:
        _write_csv(output / "phase_b_payouts.csv", slots)
    _write_csv(output / "phase_b_thresholds.csv", list(_thresholds(rows, sorted(ratios), complete, scope)))
    write_metadata("complete" if complete else "incomplete")
    return 0 if complete else 1
