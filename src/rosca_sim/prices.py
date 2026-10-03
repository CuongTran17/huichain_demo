from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from io import BytesIO, TextIOWrapper
import json
from pathlib import Path
import random
from tempfile import NamedTemporaryFile
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zipfile import ZipFile


@dataclass(frozen=True)
class PricePoint:
    day: date
    close: float


@dataclass(frozen=True)
class PricePath:
    prices: tuple[float, ...]
    label: str
    start_date: str | None
    daily_prices: tuple[float, ...] = ()


def load_price_csv(path: Path, start: date, end: date) -> tuple[PricePoint, ...]:
    seen: set[date] = set()
    points: list[PricePoint] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {"date", "close"}.issubset(reader.fieldnames):
            raise ValueError("price CSV must contain date and close columns")
        for row in reader:
            day = date.fromisoformat(row["date"])
            close = float(row["close"])
            if day in seen:
                raise ValueError(f"duplicate date: {day.isoformat()}")
            if close <= 0:
                raise ValueError(f"price must be positive: {day.isoformat()}")
            seen.add(day)
            if start <= day <= end:
                points.append(PricePoint(day, close))
    return tuple(sorted(points, key=lambda point: point.day))


def sample_historical_path(
    points: tuple[PricePoint, ...],
    periods: int,
    period_days: int,
    rng: random.Random,
    normalize: bool = True,
    window_start: date | None = None,
) -> PricePath:
    if periods < 1 or period_days < 1:
        raise ValueError("periods and period_days must be positive")
    by_day = {point.day: point.close for point in points}
    days_needed = (periods - 1) * period_days + 1
    starts: list[date] = []
    next_day: date | None = None
    run_length = 0
    for point in reversed(points):
        run_length = run_length + 1 if next_day == point.day + timedelta(days=1) else 1
        if run_length >= days_needed:
            starts.append(point.day)
        next_day = point.day
    starts.reverse()
    if not starts:
        raise ValueError("no complete historical window")
    if window_start is not None and window_start not in starts:
        raise ValueError("selected historical window is incomplete")
    start = window_start if window_start is not None else rng.choice(starts)
    daily = tuple(by_day[start + timedelta(days=i)] for i in range(days_needed))
    if normalize:
        initial = daily[0]
        daily = tuple(value / initial for value in daily)
    values = daily[::period_days]
    return PricePath(values, "historical", start.isoformat(), daily)


def _linear(start: float, end: float, count: int) -> tuple[float, ...]:
    if count == 1:
        return (start,)
    return tuple(start + (end - start) * i / (count - 1) for i in range(count))


def make_stress_path(scenario: str, periods: int, period_days: int = 1) -> PricePath:
    if periods < 1 or period_days < 1:
        raise ValueError("periods and period_days must be positive")
    levels = {"constant": 1.0, "drop_20": 0.8, "drop_40": 0.6, "drop_60": 0.4}
    if scenario in levels:
        end = levels[scenario]
        prices = (1.0,) + (end,) * (periods - 1)
    elif scenario == "gradual_decline":
        prices = _linear(1.0, 0.6, periods)
    elif scenario == "rise_then_crash":
        peak_index = periods // 2
        rising = _linear(1.0, 1.3, peak_index + 1)
        falling = _linear(1.3, 0.6, periods - peak_index)
        prices = rising + falling[1:]
    else:
        raise ValueError(f"unknown stress scenario: {scenario}")
    daily = tuple(
        prices[day // period_days]
        for day in range((periods - 1) * period_days + 1)
    )
    return PricePath(prices, scenario, None, daily)


def fetch_coingecko_prices(
    start: date,
    end: date,
    api_key: str,
    output_path: Path,
    opener: Callable = urlopen,
) -> None:
    if not api_key:
        raise ValueError("CoinGecko API key is required")
    start_ts = int(datetime.combine(start, time.min, timezone.utc).timestamp())
    end_ts = int(datetime.combine(end + timedelta(days=1), time.min, timezone.utc).timestamp()) - 1
    query = urlencode({"vs_currency": "usd", "from": start_ts, "to": end_ts})
    request = Request(
        f"https://api.coingecko.com/api/v3/coins/ethereum/market_chart/range?{query}",
        headers={"x-cg-demo-api-key": api_key},
    )
    with opener(request, timeout=30) as response:
        payload = json.loads(response.read())
    rows = payload.get("prices")
    if not isinstance(rows, list):
        raise ValueError("CoinGecko response has no prices list")
    daily: dict[date, tuple[float, float]] = {}
    seen_timestamps: set[float] = set()
    for row in rows:
        if not isinstance(row, list) or len(row) != 2:
            raise ValueError("malformed CoinGecko price row")
        timestamp = float(row[0])
        if timestamp in seen_timestamps:
            raise ValueError(f"duplicate timestamp: {row[0]}")
        seen_timestamps.add(timestamp)
        day = datetime.fromtimestamp(timestamp / 1000, timezone.utc).date()
        close = float(row[1])
        if close <= 0:
            raise ValueError(f"price must be positive: {day.isoformat()}")
        if day not in daily or timestamp > daily[day][0]:
            daily[day] = (timestamp, close)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", newline="", encoding="utf-8", delete=False, dir=output_path.parent) as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("date", "close"))
        for day in sorted(daily):
            writer.writerow((day.isoformat(), daily[day][1]))
        temporary = Path(handle.name)
    temporary.replace(output_path)


def fetch_binance_spot_prices(
    start: date,
    end: date,
    output_path: Path,
    opener: Callable = urlopen,
) -> None:
    """Download complete daily ETH/USDT spot candles from Binance's monthly archive."""
    if start > end:
        raise ValueError("start date must not exceed end date")
    daily: dict[date, float] = {}
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        name = f"ETHUSDT-1d-{year}-{month:02d}.zip"
        url = (
            "https://data.binance.vision/data/spot/monthly/klines/"
            f"ETHUSDT/1d/{name}"
        )
        with opener(Request(url), timeout=30) as response:
            archive_bytes = response.read()
        with ZipFile(BytesIO(archive_bytes)) as archive:
            csv_names = [item for item in archive.namelist() if item.endswith(".csv")]
            if len(csv_names) != 1:
                raise ValueError(f"unexpected Binance archive contents: {name}")
            with archive.open(csv_names[0]) as raw:
                for row in csv.reader(TextIOWrapper(raw, encoding="utf-8-sig")):
                    if not row or row[0] == "open_time":
                        continue
                    timestamp = int(row[0])
                    divisor = 1_000_000 if timestamp >= 10**14 else 1_000
                    day = datetime.fromtimestamp(
                        timestamp / divisor, timezone.utc
                    ).date()
                    close = float(row[4])
                    if close <= 0 or day in daily:
                        raise ValueError(f"invalid or duplicate Binance price: {day}")
                    if start <= day <= end:
                        daily[day] = close
        month += 1
        if month == 13:
            year, month = year + 1, 1
    expected = (end - start).days + 1
    if len(daily) != expected:
        raise ValueError(f"missing daily ETH prices: expected {expected}, got {len(daily)}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w", newline="", encoding="utf-8", delete=False, dir=output_path.parent
    ) as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("date", "close"))
        for day in sorted(daily):
            writer.writerow((day.isoformat(), daily[day]))
        temporary = Path(handle.name)
    temporary.replace(output_path)
