"""Targeted crash checks using the verified Phase B engine and price input."""

import csv
from dataclasses import replace
from datetime import date, timedelta
import json
from pathlib import Path

from rosca_sim.auction import AuctionPriceOverride
from rosca_sim.due_date_auction import DueDateAuctionModel
from rosca_sim.phase_b import FRACTIONS, LOSS_TOLERANCE, PROFILES, forced_groups, phase_b_paths
from rosca_sim.phase_b_upper import build_scenario
from rosca_sim.prices import PricePath, PricePoint


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
EVENTS = ("2022-05-09", "2022-06-13", "2022-06-18", "2022-11-09",
          "2024-08-05", "2025-04-06", "2025-10-10", "2026-02-05")
RATIO = 250


def run(path, paid, ids, profile="all_zero", capacity=0.0, override=None, strategic=False):
    settings = {} if strategic else {"paid_count": paid, "forced_ids": ids}
    case = build_scenario(path, RATIO, profile, capacity, strategic=strategic, **settings)
    if override:
        day, price = override
        case = replace(case, auction=replace(case.auction,
                       execution_price_overrides=(AuctionPriceOverride(day, price),)))
    result = DueDateAuctionModel(case, "fixed", path).run()
    if not strategic:
        assert result.freeze_day == paid * 30 and result.default_count == len(ids)
    return result


def write_csv(name, rows):
    with (OUT / name).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def measure(result):
    return dict(eth_sale_usdc=result.eth_sale_proceeds,
                total_principal_loss_usdc=result.principal_loss,
                worst_member_loss_usdc=result.worst_member_loss,
                freeze_day=result.freeze_day, defaults=result.default_count)


def event_replays(paths, prices, lows):
    rows = []
    for event in EVENTS:
        event_day = date.fromisoformat(event)
        prior = prices[(event_day - timedelta(days=1)).isoformat()]
        for kind, price in [("historical_close", prices[event]), *(
                [("historical_low_execution", lows[event])] if event in lows else [])]:
            results = []
            for paid in range(1, 6):
                for lag in (0, 7) if paid > 1 else (0,):
                    sale_day = 30 * paid + lag
                    start = (event_day - timedelta(days=sale_day)).isoformat()
                    path = paths.get(start)
                    if path is None:
                        continue
                    for profile in PROFILES:
                        base = build_scenario(path, RATIO, profile, 0.0, strategic=False)
                        order = DueDateAuctionModel(base, "fixed", path).run().payout_order
                        for count, ids in forced_groups(order):
                            if count != paid or (lag and len(ids) == paid):
                                continue
                            for capacity in FRACTIONS:
                                override = (sale_day, price) if kind != "historical_close" else None
                                result = run(path, paid, ids, profile, capacity, override)
                                if not any(agent.eth_sale_day == sale_day for agent in result.agent_results):
                                    continue
                                results.append((result, start, ids, profile, capacity, lag))
            assert results
            worst, start, ids, profile, capacity, lag = max(
                results, key=lambda item: item[0].worst_member_loss)
            rows.append(dict(event_date=event, price_type=kind, ratio_pct=RATIO, previous_close=prior,
                             sale_price=price, change_from_previous_close_pct=100*(price/prior-1),
                             runs=len(results),
                             loss_cases=sum(r.worst_member_loss > LOSS_TOLERANCE for r, *_ in results),
                             worst_window_start=start, worst_group="|".join(map(str, ids)),
                             worst_profile=profile, worst_capacity=capacity, worst_lag_days=lag,
                             **measure(worst)))
    return rows


def synthetic_replays(paths):
    flat = PricePath((2000.0,)*6, "flat ETH", None, (2000.0,)*158)
    history = paths["2022-04-19"]
    rows = []
    for label, path, paid, ids in (("flat_before_crash", flat, 1, (0,)),
                                  ("2022-04-19_after_drawdown", history, 2, (0, 1))):
        day = paid*30
        prior = path.daily_prices[day-1]
        for shock in (0, 15, 20):
            sale = path.daily_prices[day] if shock == 0 else prior*(1-shock/100)
            for profile in ("all_zero", "all_twenty"):
                for strategic in (False, True):
                    override = (day, sale) if shock else None
                    result = run(path, paid, ids, profile, override=override, strategic=strategic)
                    rows.append(dict(path=label, ratio_pct=RATIO, profile=profile, mode="strategic" if strategic else "forced",
                                     imposed_daily_drop_pct=shock, previous_close=prior,
                                     price_at_selected_day=sale, selected_day=day, **measure(result)))
    return rows


def main():
    with (ROOT / "data/eth_usdt_binance_phase_b.csv").open(newline="", encoding="utf-8") as handle:
        points = tuple(PricePoint(date.fromisoformat(r["date"]), float(r["close"])) for r in csv.DictReader(handle))
    paths = {p.start_date: p for p in phase_b_paths(points)}
    prices = {p.day.isoformat(): p.close for p in points}
    ohlc = OUT / "historical_ohlc.json"
    lows = {}
    if ohlc.exists():
        for row in json.loads(ohlc.read_text(encoding="utf-8")):
            assert prices[row["day"]] == row["close"]
            lows[row["day"]] = row["low"]
    write_csv("synthetic_crashes.csv", synthetic_replays(paths))
    write_csv("historical_event_replays.csv", event_replays(paths, prices, lows))


if __name__ == "__main__":
    main()
