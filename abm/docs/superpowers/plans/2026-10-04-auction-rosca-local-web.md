# Auction ROSCA Local Web Explorer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a localhost Streamlit app that compares named auction-ROSCA scenarios and bounded collateral sweeps using historical ETH prices, with auditable charts and per-member drilldowns.

**Architecture:** Keep `AuctionRoscaModel` as the only auction/settlement engine. Add an append-only period trace, a small pure-Python case/analysis/reporting layer, and a Streamlit view over those outputs. Historical paths are shared across ratios for fair comparison; the web never invents execution prices or silently changes model rules.

**Tech Stack:** Existing Python >=3.12, Mesa 3.5.1, pytest, standard-library CSV/JSON/dataclasses/Decimal; optional `streamlit>=1.51,<2` and `altair>=5,<7` in `[project.optional-dependencies].web`.

**Spec:** `docs/superpowers/specs/2026-10-04-auction-rosca-local-web-design.md`

## Global Constraints

- Run locally on `127.0.0.1`; no wallet, real transaction, database, public hosting, game-theoretic agent, synthetic price option, or automatic margin call.
- Auction mode has `members == periods >= 6`; the recipient posts ETH only at payout, bid interest is deducted then retained, and later contributions remain fixed.
- Price CSV has `date,close`; use actual unnormalized daily closes for the web. Require a source label and USD/USDT quote selection. Comparing ETH collateral value with USDC obligations assumes 1 USD or 1 USDT ≈ 1 USDC; label this as a proxy, not a stablecoin-peg guarantee. Never imply a close or candle low was an executable liquidation fill.
- Preserve existing CLI/output semantics and the older fixed-order model. Default events, USDC capacity, bids, and settlement mode are explicit assumptions, not observed facts.
- Manual cases may have different dates and assumptions; ratio comparisons within a case must use the same sampled starts, behavior, and seed. If case durations differ, label their different ending dates.
- Limit `case count × ratio count × historical-start count` to 10,000 engine runs. Report a candidate only as the lowest *tested* zero-loss ratio for the selected sample; warn on nonmonotonic results.
- All user-facing copy is Vietnamese; every plot states USDC versus ETH units, its historical date span, sample size, and modeled assumptions. A zero-loss historical run is not a protection guarantee.
- Respect the existing untracked `work/` directory; stage only task files. Work on the user-requested local `main`; do not push to GitHub.
- Commands below assume the repository's Python 3.12+ `.venv` is activated; on this Windows host, `python` can be replaced by `.\.venv\Scripts\python.exe`.

## Review Focus

1. A CSV with duplicate/nonfinite prices or a gap in a grace-period tail must fail clearly, never become a zero-loss run (Task 1 tests).
2. Imported JSON with fake execution-price overrides, duplicate IDs, or invalid rates must not enter the editable case list (Task 3 tests).
3. A same-day batch of defaults and an event after the first freeze must yield the same trace and losses as the existing engine (Task 2 tests).
4. An ETH balance too low at a higher ratio can change the winner or stop the circle; charts and threshold reporting must flag that, not assume monotonic safety (Tasks 5–6 tests).
5. Editing a displayed case or its CSV path after a run must mark the result stale; the web must not present cached old charts as new evidence (Task 7 tests).

---

## File map

- Modify `src/rosca_sim/prices.py` for reusable complete-start enumeration.
- Modify `src/rosca_sim/auction.py` for a read-only, append-only `AuctionPeriodTrace`; do not alter the `AuctionRunResult` CSV shape.
- Create `src/rosca_sim/web_cases.py` for `NamedCase`, example case, validated JSON import/export.
- Create `src/rosca_sim/web_analysis.py` for pinned manual runs, common-window sweeps, and typed run records.
- Create `src/rosca_sim/web_reporting.py` for pure chart/table rows and candidate-threshold summaries.
- Create `src/rosca_sim/web_app.py` for the two Streamlit views and local case session state.
- Modify `pyproject.toml` only for the optional web extra; update `README.md` with local launch and interpretation.
- Extend `tests/test_prices.py`, `tests/test_auction.py`; create `tests/test_web_cases.py`, `tests/test_web_analysis.py`, `tests/test_web_reporting.py`, and `tests/test_web_app.py`.

### Task 1: Enumerate complete historical starts

**Files:** Modify `src/rosca_sim/prices.py`; extend `tests/test_prices.py`.

**Interfaces:** Produce `valid_historical_starts(points: tuple[PricePoint, ...], periods: int, period_days: int, extra_days: int = 0) -> tuple[date, ...]`. `sample_historical_path` calls it rather than maintaining a second continuity algorithm.

- [ ] **Step 1: Write failing tests** `test_complete_starts_skip_gap` (`assert starts == (date(2026, 1, 4), date(2026, 1, 5))`) using dates Jan 1–2 and Jan 4–7, `periods=2`, `period_days=1`, `extra_days=1`; `test_nonfinite_close_rejected` and `test_missing_grace_tail_rejected` (`pytest.raises(ValueError)`); `test_pinned_window_keeps_real_close` (`assert path.daily_prices[0] == 100.0` with `normalize=False`).
- [ ] **Step 2: Run** `python -m pytest tests/test_prices.py -q` and confirm the new assertions fail before the change.
- [ ] **Step 3: Implement** `valid_historical_starts` by extracting the existing reverse consecutive-day scan; tighten `load_price_csv` to require finite positive closes, preserving its sorting and duplicate-date behavior.
- [ ] **Step 4: Run** `python -m pytest tests/test_prices.py -q`; require zero failures and unchanged old sampler tests.
- [ ] **Step 5: Commit only Task 1 files** with `feat: enumerate complete historical price windows`.

### Task 2: Record the engine's actual period events

**Files:** Modify `src/rosca_sim/auction.py`; extend `tests/test_auction.py`.

**Interfaces:** Produce immutable `AuctionPeriodTrace(period: int, day: int, contributions_by_member: tuple[float, ...], winner_id: int | None, gross_pot: float, bid_interest: float, net_payout: float, eth_locked_by_member: tuple[float, ...], eth_released_by_member: tuple[float, ...], pool_cash: float, retained_interest: float)` and `AuctionRoscaModel.period_trace: tuple[AuctionPeriodTrace, ...]`. The contribution and ETH tuples are changes *during that period*, in ascending member-ID order; cash/interest are balances *after* the period. A freeze before a due-date contribution adds no invented round; `AuctionRunResult` remains unchanged.

- [ ] **Step 1: Write failing tests** `test_trace_matches_first_auction` (`assert trace[0].winner_id == 0`, `bid_interest == 120`, `net_payout == 480`, and `eth_locked_by_member[1:] == (0,)*5`); `test_trace_releases_after_fixed_contribution` (`trace[1].contributions_by_member[0] == 100` and `eth_released_by_member[0] > 0`); `test_freeze_trace_omits_next_round` (`len(trace) == 1` at a day-30 default); `test_same_day_default_trace_order_independent` (trace and result equality after reversed events), with later events creating no extra trace.
- [ ] **Step 2: Run** `python -m pytest tests/test_auction.py -q` and observe the trace assertions fail.
- [ ] **Step 3: Implement** trace recording inside existing `step()` and freeze handling, using before/after agent state; do not duplicate auction decisions in the web layer or add trace fields to CSV rows.
- [ ] **Step 4: Run** `python -m pytest tests/test_auction.py tests/test_auction_experiment.py -q`; require zero failures and existing cash-conservation assertions intact.
- [ ] **Step 5: Commit only Task 2 files** with `feat: expose auction period trace for charts`.

### Task 3: Safe, portable named cases

**Files:** Create `src/rosca_sim/web_cases.py`, `tests/test_web_cases.py`.

**Interfaces:** Produce frozen `NamedCase(case_id: str, name: str, scenario: AuctionScenario, window_start: date | None)`, `example_case() -> NamedCase`, `dump_cases_json(cases: tuple[NamedCase, ...]) -> str`, and `load_cases_json(payload: str) -> tuple[NamedCase, ...]`. JSON has `schema_version: 1`; only documented scenario fields are accepted; `execution_price_overrides` must be empty.

- [ ] **Step 1: Write failing tests** `test_named_case_roundtrip` (`assert load_cases_json(dump_cases_json(cases)) == cases`) for two distinct IDs/names and a start date; `test_example_has_first_bid` (`assert example_case().scenario.bids[0].rate == 0.2`); `test_case_import_rejects_unsafe_data` (`pytest.raises(ValueError)`) for duplicate IDs, unsupported schema, nonempty execution-price overrides, `rate >= 1`, nonfinite values, `members != periods`, and invalid event/member references.
- [ ] **Step 2: Run** `python -m pytest tests/test_web_cases.py -q`; confirm failures due to missing interfaces.
- [ ] **Step 3: Implement** explicit dataclass-to-JSON mapping and structural validation; use `uuid` only to assign a fresh ID when the UI clones a case. Do not deserialize arbitrary Python objects or silently discard unknown fields.
- [ ] **Step 4: Run** `python -m pytest tests/test_web_cases.py -q`; require zero failures.
- [ ] **Step 5: Commit only Task 3 files** with `feat: add validated named web scenarios`.

### Task 4: Run selected cases through the existing ABM

**Files:** Create `src/rosca_sim/web_analysis.py`, `tests/test_web_analysis.py`.

**Interfaces:** Produce frozen `CaseRun(case: NamedCase, result: AuctionRunResult, trace: tuple[AuctionPeriodTrace, ...], price_path: PricePath, source_label: str, quote_asset: Literal['USD', 'USDT'])` and `run_named_cases(cases: tuple[NamedCase, ...], points: tuple[PricePoint, ...], seed: int, source_label: str, quote_asset: Literal['USD', 'USDT']) -> tuple[CaseRun, ...]`. Every case needs a pinned complete `window_start`; use `sample_historical_path(..., normalize=False, extra_days=case.scenario.grace_days)` and `AuctionRoscaModel(..., 'fixed')`.

- [ ] **Step 1: Write failing tests** `test_named_run_matches_engine` (`assert run.result == direct_result` and `run.trace == direct_model.period_trace`); `test_two_cases_keep_distinct_freeze_days` (`assert runs[0].case.case_id != runs[1].case.case_id` and `freeze_day` differs); `test_bad_case_does_not_become_zero_loss` (`pytest.raises(ValueError, match=case.name)`) for missing start, incomplete tail, or event conflicting with realized payout timing.
- [ ] **Step 2: Run** `python -m pytest tests/test_web_analysis.py -q`; confirm the new tests fail.
- [ ] **Step 3: Implement** the thin adapter and immutable `CaseRun`; preserve the engine's `no_eligible_bid` stop reason as a reported outcome.
- [ ] **Step 4: Run** `python -m pytest tests/test_web_analysis.py tests/test_auction.py -q`; require zero failures.
- [ ] **Step 5: Commit only Task 4 files** with `feat: run named historical auction cases`.

### Task 5: Run a bounded, paired collateral sweep

**Files:** Extend `src/rosca_sim/web_analysis.py`, `tests/test_web_analysis.py`.

**Interfaces:** Produce `ratio_grid(min_ratio: Decimal, max_ratio: Decimal, step: Decimal) -> tuple[float, ...]`, `sample_common_starts(cases: tuple[NamedCase, ...], points: tuple[PricePoint, ...], count: int, seed: int) -> tuple[date, ...]`, frozen `SweepRun(case_id: str, ratio: float, start: date, result: AuctionRunResult, price_path: PricePath, source_label: str, quote_asset: Literal['USD', 'USDT'])`, and `run_sweep(cases: tuple[NamedCase, ...], points: tuple[PricePoint, ...], ratios: tuple[float, ...], starts: tuple[date, ...], seed: int, source_label: str, quote_asset: Literal['USD', 'USDT'], max_runs: int = 10_000) -> tuple[SweepRun, ...]`.

- [ ] **Step 1: Write failing tests** `test_decimal_ratio_grid` (`assert ratio_grid(Decimal('1'), Decimal('2'), Decimal('.5')) == (1.0, 1.5, 2.0)`; reject nonpositive step and do not exceed a nondividing max); `test_common_windows_are_paired` (`assert starts == sample_common_starts(cases, points, count, seed)` and the start set is identical at every ratio, with differing grace tails); `test_sweep_cap_rejects_before_running` (`pytest.raises(ValueError)` for >10,000 evaluations or excessive starts); `test_higher_ratio_can_change_winner` (`assert low.result.payout_order != high.result.payout_order` with constrained ETH).
- [ ] **Step 2: Run** `python -m pytest tests/test_web_analysis.py -q`; confirm the new sweep tests fail.
- [ ] **Step 3: Implement** common-start intersection via Task 1, seeded sampling via `random.Random(seed).sample`, ratio replacement via `dataclasses.replace`, and existing engine runs. Keep all dates/results, including `no_eligible_bid`; do not assume loss falls monotonically with the ratio.
- [ ] **Step 4: Run** `python -m pytest tests/test_web_analysis.py -q`; require zero failures.
- [ ] **Step 5: Commit only Task 5 files** with `feat: compare collateral ratios on paired price windows`.

### Task 6: Make chart data auditable

**Files:** Create `src/rosca_sim/web_reporting.py`, `tests/test_web_reporting.py`.

**Interfaces:** Produce `comparison_rows(runs: tuple[CaseRun, ...])`, `member_loss_rows(runs: tuple[CaseRun, ...])`, `tradeoff_rows(runs: tuple[CaseRun, ...])`, `trace_rows(run: CaseRun)`, and `frontier_rows(runs: tuple[SweepRun, ...])`, each returning `tuple[dict[str, object], ...]`; also `candidate_ratio(rows: tuple[dict[str, object], ...], case_id: str) -> float | None`. Comparison rows include `case_id`, `case_name`, `start_date`, `end_date`, `ratio`, `principal_loss_usdc`, `worst_member_loss_usdc`, `stop_reason`, and `default_count`. Member rows include `case_id`, `member_id`, `principal_loss_usdc`, `contributed_usdc`, `net_payout_usdc`, `interest_received_usdc`, `eth_sold`, `eth_returned`, and `principal_repaid_usdc`. Tradeoff rows add `max_member_initial_lock_usdc_proxy`. Trace rows include `day`, `period`, `member_id`, `contribution_usdc`, `cumulative_contribution_usdc`, `payout_usdc`, `cumulative_payout_usdc`, `pool_cash_usdc`, and `retained_interest_usdc`. Frontier rows include `case_id`, `ratio`, `runs`, `mean_loss_usdc`, `worst_member_loss_usdc`, `loss_run_count`, `loss_run_share`, `median_max_member_lock_usdc_proxy`, `changed_order_count`, and `nonmonotonic`. All exported rows also carry `source_label`, `quote_asset`, source/date, and behavior-assumption labels.

- [ ] **Step 1: Write failing tests** `test_chart_rows_reconcile_to_engine` (`assert sum(r['principal_loss_usdc'] for r in member_loss_rows(runs)) == runs[0].result.principal_loss` and first-round trace rows show payout 480/interest 120); `test_locked_value_has_quote_proxy_label` (max recipient initial `eth_locked × payout-day close`, labeled USDC proxy with the actual USD/USDT quote); `test_frontier_counts_changed_winners` (count against each case's lowest-ratio payout order); `test_candidate_none_and_nonmonotonic_warning` (`candidate_ratio(rows, case_id) is None` when no ratio has zero loss, and `nonmonotonic=True` when a higher ratio increases worst loss by >`1e-9`).
- [ ] **Step 2: Run** `python -m pytest tests/test_web_reporting.py -q`; confirm failures for missing reporting functions.
- [ ] **Step 3: Implement** pure transformations over `CaseRun`, `SweepRun`, and engine results; keep raw per-run rows available for CSV audit. Do not label historical zero loss as a guaranteed safe threshold.
- [ ] **Step 4: Run** `python -m pytest tests/test_web_reporting.py -q`; require zero failures.
- [ ] **Step 5: Commit only Task 6 files** with `feat: prepare auditable auction result charts`.

### Task 7: Local scenario editor and comparison charts

**Files:** Create `src/rosca_sim/web_app.py`, `tests/test_web_app.py`; modify `pyproject.toml` for `[project.optional-dependencies].web`.

**Interfaces:** `streamlit run src/rosca_sim/web_app.py --server.address=127.0.0.1`. UI uses `NamedCase` session state, Task 4 manual runner, Task 6 chart rows, `st.form`/`st.data_editor` for inputs, and Altair charts for comparison bars, member-loss matrix, tradeoff scatter, and one-run drilldown.

- [ ] **Step 1: Write failing `AppTest` tests** `test_app_starts_with_example` (`assert not at.exception` and six members shown); `test_case_editor_clone_import_and_remove` (new ID on clone, JSON roundtrip, removed ID absent); `test_run_shows_charts_and_discount` (480 payout/120 retained interest shown, no extra installment); `test_missing_csv_is_inline_error` (visible error, no chart); `test_edit_marks_result_stale` (visible stale warning after case, CSV path/mtime, or quote changes), using `AppTest.from_file('src/rosca_sim/web_app.py').run()`.
- [ ] **Step 2: Install only the optional web extra**, then run `python -m pytest tests/test_web_app.py -q` and observe the app tests fail before implementation. The base package/CLI must still install without Streamlit.
- [ ] **Step 3: Implement** the local Streamlit comparison view: case editor, CSV path/source-label/quote inputs, grouped-loss bars, case-by-member loss matrix, locked-value-versus-loss scatter, sortable rows, and CSV download. The selected-run drilldown shows the dated ETH-close chart with event markers, pool cash/retained-interest chart, per-member contribution/payout lines, and settlement table. Cache only parsed CSV points, keyed by absolute path and modification time; do not cache model results across changed case inputs. Use Vietnamese labels, explicit units/date/source/assumption captions, no hidden synthetic price control; render empty, loading, error, and zero-loss states distinctly. Mark old results stale whenever case, CSV, source label, or quote input changes; filter long case lists rather than compressing every label.
- [ ] **Step 4: Run** `python -m pytest tests/test_web_app.py tests/test_web_cases.py tests/test_web_reporting.py -q`; require zero failures and no uncaught `AppTest.exception`.
- [ ] **Step 5: Commit only Task 7 files** with `feat: add local auction scenario dashboard`.

### Task 8: Sweep UI, documentation, and end-to-end verification

**Files:** Extend `src/rosca_sim/web_app.py`, `tests/test_web_app.py`; modify `README.md`.

**Interfaces:** Add **Quét tự động và tìm ngưỡng** view using Tasks 5–6, with ratio grid, selected cases, window count, seed, estimated run count, progress/error state, frontier chart, distribution of worst-member losses, CSV download, and case-specific candidate/no-candidate statement.

- [ ] **Step 1: Write failing `AppTest` tests** `test_sweep_requires_submit` (editing a widget leaves previous results unchanged); `test_sweep_guard_is_visible` (10,001 estimated runs yields inline error and no chart); `test_sweep_result_explains_candidate_or_none` (ratio grid 1.0–2.0, common window count, case-specific message, changed-winner warning); `test_different_horizon_labels_own_end_date` (different actual end dates displayed).
- [ ] **Step 2: Run** `python -m pytest tests/test_web_app.py -q` and confirm the new sweep assertions fail.
- [ ] **Step 3: Implement** the sweep view and README local setup (`pip install -e ".[dev,web]"`, documented localhost command, price CSV preparation, meaning/limits of charts). Avoid persisting private local paths in exported report CSV unless the user explicitly requests them.
- [ ] **Step 4: Run** `python -m pytest -q` and `python -m compileall -q src/rosca_sim`, requiring zero failures. Start `python -m streamlit run src/rosca_sim/web_app.py --server.headless true --server.address 127.0.0.1` in a bounded local process, confirm `http://127.0.0.1:8501/_stcore/health` responds successfully, then stop only that process. Inspect both views manually at desktop and narrow widths, including keyboard labels and malformed-input/empty states; record actual results before claiming completion.
- [ ] **Step 5: Commit only Task 8 files** with `feat: add historical collateral sweep dashboard` and keep the resulting commits local on `main`.
