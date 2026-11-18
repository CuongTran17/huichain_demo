"""Read the archived BTL study and reproduce its paired demonstration case."""

import csv
from dataclasses import dataclass, replace
from datetime import date, timedelta
import json
from math import isfinite
from pathlib import Path
import random

from rosca_sim.auction import AuctionPeriodTrace, AuctionPriceOverride, AuctionRunResult
from rosca_sim.due_date_auction import DueDateAuctionModel
from rosca_sim.phase_b import LOSS_TOLERANCE
from rosca_sim.phase_b_upper import build_scenario
from rosca_sim.prices import load_price_csv, sample_historical_path

REPORT_MODE = "Kết quả báo cáo BTL"
FOCUS_DAY = "2022-06-18"
CLOSE = "historical_close"
LOW = "historical_low_execution"
ROOT = Path(__file__).resolve().parents[2]
UPPER = "results/phase-b-upper-2022-2026-verified"
SUMMARY = "results/phase-b-2022-2026-verified/phase_b_summary.csv"
EVENTS = "results/phase-b-crash-15-20/historical_event_replays.csv"
PRICES = "data/eth_usdt_binance_phase_b.csv"


@dataclass(frozen=True)
class RiskPoint:
    ratio: int
    category: str
    loss: float | None
    runs: int


@dataclass(frozen=True)
class EventResult:
    day: str
    basis: str
    ratio: int
    price: float
    change: float
    runs: int
    losses: int
    worst_loss: float
    total_loss: float
    start: str
    defaults: tuple[int, ...]
    profile: str
    capacity: float
    freeze_day: int
    lag: int


@dataclass(frozen=True)
class Report:
    threshold: int
    full_runs: int
    risks: tuple[RiskPoint, ...]
    events: dict[str, dict[str, EventResult]]


@dataclass(frozen=True)
class Replay:
    result: AuctionRunResult
    trace: tuple[AuctionPeriodTrace, ...]


def _read(root, relative, parse):
    try:
        with (root / relative).open(encoding="utf-8-sig", newline="") as source:
            return parse(source)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError(f"{relative}: {error}") from error


def _read_risks(root: Path, full_runs: int) -> tuple[RiskPoint, ...]:
    def main_rows(source):
        groups = {}
        for row in csv.DictReader(source):
            groups.setdefault(int(row["ratio_pct"]), []).append(row)
        if sorted(groups) != list(range(180, 201, 5)):
            raise ValueError("thiếu các mức quét đầy đủ 180–200%")
        points = []
        for ratio, rows in sorted(groups.items()):
            runs = sum(int(row["completed_runs"]) for row in rows)
            if runs != full_runs or any(row["completed_runs"] != row["expected_runs"] for row in rows):
                raise ValueError(f"số lượt không khớp ở {ratio}%")
            losses = [float(row["worst_member_loss"]) for row in rows]
            if any(not isfinite(loss) or loss < 0 for loss in losses):
                raise ValueError(f"số tiền mất gốc không hợp lệ ở {ratio}%")
            points.append(RiskPoint(ratio, "Quét đầy đủ", max(losses), runs))
        return points

    def upper_rows(source):
        points = []
        for row in csv.DictReader(source):
            ratio = int(row["ratio_pct"])
            status = row["status"]
            if status == "full_pass":
                runs = int(row["full_runs"])
                loss = float(row["full_worst_member_loss_usdc"])
                if runs != full_runs or not 0 <= loss <= LOSS_TOLERANCE:
                    raise ValueError("kết quả quét đầy đủ không khớp ngưỡng")
                points.append(RiskPoint(ratio, "Quét đầy đủ", loss, runs))
            elif status == "fail_witness":
                loss = float(row["witness_member_loss_usdc"])
                if not isfinite(loss) or loss <= LOSS_TOLERANCE:
                    raise ValueError(f"phản ví dụ không hợp lệ ở {ratio}%")
                points.append(RiskPoint(ratio, "Phản ví dụ qua sàng lọc", loss, int(row["screening_runs"])))
            elif status == "not_scanned":
                points.append(RiskPoint(ratio, "Chỉ sàng lọc", None, int(row["screening_runs"])))
            else:
                raise ValueError(f"trạng thái tỷ lệ không hợp lệ ở {ratio}%")
        if sorted(p.ratio for p in points) != list(range(205, 301, 5)):
            raise ValueError("lưới 205–300% không đầy đủ")
        return points

    return tuple(_read(root, SUMMARY, main_rows) + _read(root, f"{UPPER}/phase_b_upper_ratios.csv", upper_rows))


def _read_events(root: Path) -> dict[str, dict[str, EventResult]]:
    def parse(source):
        dates = {}
        for row in csv.DictReader(source):
            day = date.fromisoformat(row["event_date"]).isoformat()
            group = dates.setdefault(day, {})
            basis = row["price_type"]
            if basis not in (CLOSE, LOW) or basis in group:
                raise ValueError(f"loại giá thiếu hoặc trùng tại {day}")
            event = EventResult(
                day, basis, int(row["ratio_pct"]), float(row["sale_price"]),
                float(row["change_from_previous_close_pct"]), int(row["runs"]), int(row["loss_cases"]),
                float(row["worst_member_loss_usdc"]), float(row["total_principal_loss_usdc"]),
                row["worst_window_start"], tuple(int(member) for member in row["worst_group"].split("|")),
                row["worst_profile"], float(row["worst_capacity"]), int(row["freeze_day"]), int(row["worst_lag_days"]),
            )
            if event.runs <= 0 or not 0 <= event.losses <= event.runs:
                raise ValueError(f"số lượt không hợp lệ tại {day}")
            if (event.ratio != 250 or not all(isfinite(value) for value in
                    (event.price, event.change, event.worst_loss, event.total_loss, event.capacity))
                    or event.price <= 0 or not 0 <= event.worst_loss <= event.total_loss
                    or (event.losses == 0) != (event.worst_loss <= LOSS_TOLERANCE)):
                raise ValueError(f"giá hoặc số tiền mất gốc không hợp lệ tại {day}")
            group[basis] = event
        if len(dates) != 8 or FOCUS_DAY not in dates or any(set(group) != {CLOSE, LOW} for group in dates.values()):
            raise ValueError("cần đủ hai cách định giá cho tám ngày đã công bố")
        focus = dates[FOCUS_DAY]
        if ((focus[CLOSE].runs, focus[CLOSE].losses, focus[LOW].runs, focus[LOW].losses) != (825, 0, 825, 22)
                or any(sum(group[basis].runs for group in dates.values()) != 6141 for basis in (CLOSE, LOW))):
            raise ValueError("số lượt không khớp bộ kết quả công bố")
        return dates

    return _read(root, EVENTS, parse)


def load_report(root: Path = ROOT) -> Report:
    relative = f"{UPPER}/threshold.json"

    def parse(source):
        threshold = json.load(source)
        ratio, runs = int(threshold["min_passing_ratio_pct"]), int(threshold["full_runs"])
        if threshold["status"] != "found" or (ratio, runs) != (250, 1608 * 3 * 3 * 58):
            raise ValueError("ngưỡng hoặc số lượt khác kết quả báo cáo")
        return ratio, runs

    ratio, runs = _read(root, relative, parse)
    risks = _read_risks(root, runs)
    if [p.ratio for p in risks if p.category == "Quét đầy đủ" and p.loss is not None and p.loss <= LOSS_TOLERANCE] != [ratio]:
        raise ValueError(f"{UPPER}/phase_b_upper_ratios.csv: các mức đạt không khớp ngưỡng")
    return Report(ratio, runs, risks, _read_events(root))


def replay_focus_case(event: EventResult, root: Path = ROOT) -> dict[str, Replay]:
    if event.day != FOCUS_DAY or event.basis != LOW:
        raise ValueError("cần bản ghi ca giá đáy ngày 18/06/2022")
    if (event.start, event.freeze_day, event.defaults, event.profile, event.capacity, event.lag) != (
        "2022-04-19", 60, (0,), "all_zero", 0, 0,
    ):
        raise ValueError(f"{EVENTS}: cấu hình ca phát lại khác ca dùng trong báo cáo")
    start = date.fromisoformat(event.start)
    end = start + timedelta(days=157)
    try:
        points = load_price_csv(root / PRICES, start, end)
        path = sample_historical_path(points, 6, 30, random.Random(42), normalize=False, window_start=start, extra_days=7)
    except (OSError, ValueError) as error:
        raise ValueError(f"{PRICES}: {error}") from error
    scenario = build_scenario(path, event.ratio, event.profile, event.capacity,
                              strategic=False, paid_count=event.freeze_day // 30, forced_ids=event.defaults)
    override = AuctionPriceOverride(event.freeze_day + event.lag, event.price)
    low_case = replace(scenario, auction=replace(scenario.auction, execution_price_overrides=(override,)))
    output = {}
    for basis, case in ((CLOSE, scenario), (LOW, low_case)):
        model = DueDateAuctionModel(case, "fixed", path)
        result = model.run()
        output[basis] = Replay(result, model.period_trace)
    low = output[LOW].result
    if (abs(low.worst_member_loss - event.worst_loss) > LOSS_TOLERANCE
            or abs(low.principal_loss - event.total_loss) > LOSS_TOLERANCE):
        raise ValueError(f"{EVENTS}: kết quả phát lại không khớp bản ghi giá đáy")
    return output
