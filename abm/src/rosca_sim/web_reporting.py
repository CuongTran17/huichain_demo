"""Auditable chart rows derived only from authoritative auction results."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, replace
from datetime import timedelta
import json
from statistics import mean, median
from rosca_sim.auction import ANNUAL_BID_METADATA

from rosca_sim.web_analysis import CaseRun, SweepRun
from rosca_sim.web_cases import NamedCase


def _meta(run: CaseRun | SweepRun) -> dict[str, object]:
    start = run.case.window_start if isinstance(run, CaseRun) else run.start
    assert start is not None
    return {
        **ANNUAL_BID_METADATA,
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=len(run.price_path.daily_prices) - 1)).isoformat(),
        "source_label": run.source_label,
        "quote_asset": run.quote_asset,
        "proxy_assumption": f"1 {run.quote_asset} ≈ 1 USDC; ETH close is not an executable fill",
        "behavior_assumption": "Researcher-supplied bids/defaults; no strategic adaptation",
        "collateral_release_policy": "terminal",
    }


def _lock_proxy(run: CaseRun | SweepRun) -> float:
    return max((member.eth_locked * run.price_path.daily_prices[member.payout_day]
                for member in run.result.agent_results if member.payout_day is not None),
               default=0.0)


def comparison_rows(runs: tuple[CaseRun, ...]) -> tuple[dict[str, object], ...]:
    return tuple({
        **_meta(run), "case_id": run.case.case_id, "case_name": run.case.name,
        "ratio": run.case.scenario.collateral.fixed_ratio,
        "liquidation_slippage": run.case.scenario.collateral.liquidation_slippage,
        "principal_loss_usdc": run.result.principal_loss,
        "worst_member_loss_usdc": run.result.worst_member_loss,
        "stop_reason": run.result.stop_reason, "default_count": run.result.default_count,
        "freeze_day": run.result.freeze_day, "settlement_day": run.result.settlement_day,
        "interest_retained_usdc": run.result.interest_retained,
        "interest_used_usdc": run.result.interest_used,
        "interest_used_from_defaulting_usdc": run.result.interest_used_from_defaulting,
        "interest_used_from_other_members_usdc": run.result.interest_used_from_other_members,
        "secondary_shortfall_count": run.result.secondary_shortfall_count,
        "obligation_uncollected_usdc": run.result.obligation_uncollected,
        "interest_distributed_usdc": run.result.interest_distributed,
        "payout_order": ", ".join(map(str, run.result.payout_order)),
    } for run in runs)


def member_loss_rows(runs: tuple[CaseRun, ...]) -> tuple[dict[str, object], ...]:
    return tuple({
        **_meta(run), "case_id": run.case.case_id, "case_name": run.case.name,
        "member_id": member.member_id,
        "principal_loss_usdc": member.principal_loss,
        "contributed_usdc": member.total_contributed,
        "net_payout_usdc": member.net_payout,
        "interest_received_usdc": member.interest_received,
        "bid_interest_paid_usdc": member.bid_interest_paid,
        "is_trigger_default": member.is_trigger_default,
        "settlement_shortfall": member.settlement_shortfall,
        "eth_locked": member.eth_locked, "eth_released": member.eth_released,
        "eth_sold": member.eth_sold, "eth_returned": member.eth_returned,
        "principal_claim_usdc": member.principal_claim,
        "principal_repaid_usdc": member.principal_repaid,
        "usdc_settlement_paid": member.usdc_settlement_paid,
        "obligation_uncollected_usdc": member.obligation_uncollected,
        "payout_day": member.payout_day, "eth_sale_day": member.eth_sale_day,
        "payment_day": member.payment_day,
    } for run in runs for member in run.result.agent_results)


def tradeoff_rows(runs: tuple[CaseRun, ...]) -> tuple[dict[str, object], ...]:
    comparison = comparison_rows(runs)
    return tuple({**row, "max_member_initial_lock_usdc_proxy": _lock_proxy(run)}
                 for row, run in zip(comparison, runs))


def trace_rows(run: CaseRun) -> tuple[dict[str, object], ...]:
    cumulative_contribution = [0.0] * run.case.scenario.rosca.members
    cumulative_payout = [0.0] * run.case.scenario.rosca.members
    rows = []
    for period in run.trace:
        for member_id, amount in enumerate(period.contributions_by_member):
            payout = period.net_payout if period.winner_id == member_id else 0.0
            cumulative_contribution[member_id] += amount
            cumulative_payout[member_id] += payout
            obligation = period.remaining_obligation_by_member[member_id]
            retained_eth = period.retained_eth_by_member[member_id]
            collateral_value = retained_eth * run.price_path.prices[period.period]
            rows.append({
                **_meta(run), "case_id": run.case.case_id, "case_name": run.case.name,
                "day": period.day, "period": period.period, "member_id": member_id,
                "contribution_usdc": amount,
                "cumulative_contribution_usdc": cumulative_contribution[member_id],
                "payout_usdc": payout,
                "cumulative_payout_usdc": cumulative_payout[member_id],
                "pool_cash_usdc": period.pool_cash,
                "retained_interest_usdc": period.retained_interest,
                "bid_interest_usdc": period.bid_interest,
                "gross_pot_usdc": period.gross_pot,
                "eth_locked": period.eth_locked_by_member[member_id],
                "eth_released": period.eth_released_by_member[member_id],
                "winner_id": period.winner_id,
                "remaining_obligation_usdc": obligation,
                "retained_eth": retained_eth,
                "coverage_ratio": collateral_value / obligation if obligation > 1e-9 else None,
                "collateral_shortfall_usdc": max(0.0, obligation - collateral_value),
                "skipped_for_insufficient_eth": member_id in period.insufficient_eth_bidder_ids,
            })
    return tuple(rows)


def frontier_rows(runs: tuple[SweepRun, ...]) -> tuple[dict[str, object], ...]:
    grouped: dict[tuple[str, float], list[SweepRun]] = defaultdict(list)
    for run in runs:
        grouped[(run.case_id, run.ratio)].append(run)
    baseline = {}
    for case_id in {run.case_id for run in runs}:
        low = min(ratio for key_case, ratio in grouped if key_case == case_id)
        baseline.update({(case_id, run.start): run.result.payout_order
                         for run in grouped[(case_id, low)]})
    rows = []
    prior: dict[str, dict[str, float]] = {}
    for (case_id, ratio), group in sorted(grouped.items()):
        losses = [run.result.principal_loss for run in group]
        worst = max(run.result.worst_member_loss for run in group)
        first_day = min(run.start for run in group)
        last_day = max(run.start + timedelta(days=len(run.price_path.daily_prices) - 1)
                       for run in group)
        loss_count = sum(loss > 1e-9 for loss in losses)
        metrics = {
            "mean_loss_usdc": mean(losses),
            "worst_member_loss_usdc": worst,
            "loss_run_share": loss_count / len(group),
        }
        rising = tuple(key for key, value in metrics.items()
                       if case_id in prior and value > prior[case_id][key] + 1e-9)
        row = {
            **_meta(group[0]), "case_id": case_id, "ratio": ratio,
            "start_date": first_day.isoformat(), "end_date": last_day.isoformat(),
            "runs": len(group), **metrics,
            "loss_run_count": loss_count,
            "completed_run_count": sum(run.result.stop_reason == "completed" for run in group),
            "completion_share": sum(run.result.stop_reason == "completed" for run in group) / len(group),
            "mean_payout_count": mean(len(run.result.payout_order) for run in group),
            "median_max_member_lock_usdc_proxy": median(_lock_proxy(run) for run in group),
            "changed_order_count": sum(run.result.payout_order != baseline[(case_id, run.start)]
                                       for run in group),
            "no_eligible_bid_count": sum(run.result.stop_reason == "no_eligible_bid"
                                         for run in group),
            "nonmonotonic": bool(rising),
            "nonmonotonic_metrics": ", ".join(rising),
            "window_count": len(group),
            "seed": group[0].result.seed,
        }
        rows.append(row)
        prior[case_id] = metrics
    return tuple(rows)


def sweep_run_rows(runs: tuple[SweepRun, ...], cases: tuple[NamedCase, ...]
                   ) -> tuple[dict[str, object], ...]:
    """Export each run with the exact scenario snapshot used to generate it."""
    by_id = {case.case_id: case for case in cases}
    return tuple({
        **_meta(run), "case_id": run.case_id, "case_name": by_id[run.case_id].name,
        "ratio": run.ratio, "seed": run.result.seed,
        "scenario_json": json.dumps(asdict(replace(
            by_id[run.case_id].scenario,
            collateral=replace(by_id[run.case_id].scenario.collateral, fixed_ratio=run.ratio))),
                                    ensure_ascii=False, sort_keys=True),
        "worst_member_loss_usdc": run.result.worst_member_loss,
        "principal_loss_usdc": run.result.principal_loss,
        "stop_reason": run.result.stop_reason,
        "payout_order": ", ".join(map(str, run.result.payout_order)),
    } for run in runs)


def candidate_ratio(rows: tuple[dict[str, object], ...], case_id: str) -> float | None:
    candidates = [float(row["ratio"]) for row in rows
                  if row["case_id"] == case_id and row["loss_run_count"] == 0
                  and row.get("no_eligible_bid_count", 0) == 0]
    return min(candidates) if candidates else None
