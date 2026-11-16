# Local web explorer for the auction ROSCA

## Purpose and status

Build a local, Vietnamese-language research interface for the existing auction ROSCA ABM. Its primary action is to run and compare any user-selected number of scenarios, then drill into what happened to each participant in one run. Scenarios may be named and edited manually or generated as a bounded parameter sweep. The intended user is the project researcher, not a depositor making a financial decision. Success means the web and CLI produce identical outcomes from identical model inputs, and the researcher can compare individual loss, total loss, and the cost of locking ETH across clearly labeled assumptions.

This is a visualization and experiment layer, not a new financial mechanism. The auction-and-stop model remains authoritative. Bids, defaults, USDC payment capacity, and settlement choices are supplied by the researcher; ETH prices come from dated historical data. Neither simulated defaults nor historical backtests establish a safe future collateral ratio.

## Chosen approach

Use Streamlit in the existing Python project, calling `AuctionRoscaModel` through a small, separately testable adapter. Do not implement a second simulation in the browser. Keep it localhost-only, without accounts, wallet connections, smart contracts, a database, or a public deployment. Use the existing `date,close` CSV reader and historical-window sampler. No synthetic price path is offered in this web version; the old CLI stress mode remains untouched.

The app has two views sharing one base scenario and one loaded price dataset:

1. **So sánh kịch bản** lets the researcher name and clone any number of cases, change assumptions in each case, run the selected cases, and compare their outcome charts. Selecting a result opens its period-by-period account and final settlement for every member.
2. **Quét tự động và tìm ngưỡng** expands selected named cases across a user-specified collateral-ratio grid and sampled historical ETH windows. It compares ratios within the requested grid, not an analytically proven optimum. The number of cases is not fixed at five; the work cap below limits computational cost.

An API/React frontend was rejected for the first local version because it would duplicate application boundaries without improving the research results. A static HTML report was rejected because it cannot edit and rerun scenarios.

## Shared scenario inputs

Start from the current six-member auction example. Allow the user to edit member count and per-period contribution; the number of periods equals the number of members. Show period length in days, a table of bids keyed by period and member, and per-member reputation, available ETH, USDC settlement capacity, settlement mode, and payment day within the grace period. The recipient posts collateral only when receiving the pot; they cannot win again and keep paying only the fixed contribution in later periods. The winning bid is deducted immediately and retained in the pool, exactly as in the existing engine.

Allow dated default events for recipients and missed-contribution events for members who have not received the pot. Events on the same day form one freeze batch; events scheduled after the first freeze are not applied, because this model stops the circle at the first freeze. Show that rule next to the editor. Let the user set grace days and the fixed collateral ratio, including values above 100%. Express this ratio against the recipient's remaining fixed contributions, not their discounted net payout. Do not expose synthetic execution-price overrides in the UI.

For historical prices, accept the absolute path of a local `date,close` CSV and offer a complete start date from that file. Display source/file, date span, number of valid windows, and the chosen start. The close is a daily observed value, not a guaranteed liquidation fill. Reject unreadable files, missing dates, duplicate dates, nonpositive prices, and any window lacking all due dates plus its grace-period tail. The app does not silently repeat a final observed price or fabricate intraday prices. Price download, if needed, remains the existing CLI/setup workflow; it is not a requirement of the web's first release.

## Named scenarios and one-circle drilldown

A named case contains the shared circle inputs plus its own bids, defaults, USDC capacities, settlement modes, grace period, fixed collateral ratio, and a specified complete historical start date for manual replay. The UI starts with the six-member example. The user may clone, rename, edit, and remove a case locally. Cases live in the current Streamlit session; JSON export/import makes them reusable without a database. Import is validated before it can affect a run. Different price windows are permitted in manually compared cases, but their dates and input differences must be visible beside each result. A case with the same inputs and seed produces the same results.

The comparison action runs all selected named cases, up to the 10,000-engine-run cap shared with automatic sweeps. Each run has an explicit case ID, case name, price window, ratio, event list, and seed; no chart may merge cases with different assumptions without labeling the grouping. If a case is edited, its prior displayed results are marked stale until rerun.

Submit edits through a single **Chạy các kịch bản** action so incomplete form changes do not run the model. Selecting one completed run opens its drilldown, presented in this order:

- A short summary: actual historical window, freeze/settlement day, payout order, number of defaults, pool interest retained/used/distributed, total principal loss, and worst individual principal loss.
- A compact period ledger: who contributed, which eligible bid won, gross pot, deducted bid interest, net payout, ETH locked or released, and whether the circle froze. This requires a read-only event trace from the engine; it must not be reconstructed from aggregate CSV by guessing.
- A price chart over the selected historical interval, marking payouts, freeze, grace deadline, and ETH sale days. A mark is an event, not proof that a trade could have filled at the plotted close.
- A member table: contributed, received, interest received, USDC paid at settlement, ETH locked/sold/returned, principal claim and repayment, principal loss, and uncollected obligation. Show which losses were covered by retained bid interest.

The UI labels ETH locked as still owned but unavailable while locked. The comparison defaults to the fixed-ratio policy; an optional side-by-side reputation-adjusted result can use the existing paired runner, clearly labeling that it is a different policy.

## Results charts

The comparison results—not architecture diagrams—are the visual center of the web app. Provide these charts and a sortable data table from the same run records:

1. **Case comparison:** grouped bars for total principal loss and worst one-person principal loss, by named case. Display zero explicitly. If there are too many cases to label legibly, show a filter and the worst cases rather than compressing every label into one unreadable chart.
2. **Who bears the loss:** a case-by-member heatmap or matrix of principal loss in USDC. Opening a cell shows that member's contribution, net payout, interest received, ETH sold/returned, and principal repaid. This keeps a low group loss from hiding a large individual loss.
3. **Protection versus participation cost:** scatterplot with locked ETH value at payout on one axis and worst one-person principal loss on the other, with points colored by named case or ratio. Explain that locked ETH is still the recipient's property, not a fee. Where an auction winner changes because they cannot post collateral, mark that point separately.
4. **Within one run:** separate plots for observed ETH daily close, pool cash/retained interest, and per-member cumulative contributions and payouts across the circle's periods. Mark payout, freeze, deadline, and ETH sale dates. Never put USDC and ETH units on an unlabeled shared axis.

For repeated historical windows, also show the distribution of worst one-person loss (not only the mean) and the number/share of runs with any principal loss. Every plot includes the case count, price-data source and date range, tested ratios, and the user-supplied default assumptions. Offer CSV download of the plotted rows so visual numbers can be checked independently. Empty, running, invalid-input, and no-loss states must be distinct.

## Automatic comparison and collateral frontier

Inputs are selected named cases, price CSV, ratio minimum/maximum/step, number of historical windows, and random seed. A named case supplies default timing, identities, bids, payment capacity, and grace period; thus multiple named cases test those different conditions without an uncontrolled Cartesian product of every possible event. The sweep explicitly overrides each case's manual start date with sampled historical start dates, without changing its other inputs. Sample without replacement from start dates that have a complete price path for every selected case; reject a run count greater than the size of that intersection. Ratios within each case use identical paths and exogenous behavior. If cases have different circle lengths or grace periods, the start dates match but the ending dates differ; label the actual date range and do not describe their price paths as identical. Cap `selected cases × tested ratios × historical starts` at 10,000 engine runs before starting and show that count. Do not run merely because a widget changed; require **Quét tỷ lệ**. A single manually selected historical window is also valid when the researcher wants exact case-by-case replay.

For each case and ratio report mean loss, worst individual principal loss, count/share of runs with any principal loss, median ETH value locked at payout, and count of runs where payout order changed from that case's baseline ratio because a bidder lacked ETH. Show the curves and a small table, not just a selected 'best' ratio. Each case's empirical candidate threshold is the lowest *tested* ratio with zero principal loss across its sampled windows and stated defaults; if none qualifies, say so. A combined worst-case-across-selected-cases curve is allowed but must be labeled separately. If the results are nonmonotonic as the ratio increases, warn that there is no simple safe-above-this-point interpretation. State the sample size, price range, seed, ratio grid, and that this is not a guarantee against future ETH moves, liquidation slippage, missed execution, or coordinated strategic behavior. Do not call the result a Nash equilibrium.

## Architecture and data flow

The Streamlit view gathers input and displays output. A pure Python adapter validates UI input, builds `AuctionScenario` and `PricePath`, runs the authoritative engine, and returns typed per-run and grouped comparison records. A tiny case-serialization boundary handles validated JSON import/export. The event trace is added at the engine boundary in a way that preserves existing `AuctionRunResult` semantics and CLI outputs. Price parsing and valid-window generation reuse `rosca_sim.prices`; auction rules and settlement reuse `rosca_sim.auction`. Only the historical CSV load may be cached, keyed by its path and file modification time; model results are not cached across edits unless every case, price, ratio-grid, window count, and seed is part of the key.

Streamlit is an optional `web` dependency group. Running the CLI and its tests must not require Streamlit. The web is launched with a documented local command bound to localhost. Results may be downloaded as CSV using the existing row fields; no persistent scenario store is required.

## Errors and verification

Display validation problems inline next to the relevant input where possible: bad bid rate, duplicate bid/event, invalid default timing, unreadable price file, incomplete price window, and excessive sweep size. A bidder lacking enough ETH is a model outcome, not invalid input; explain any resulting changed winner or `no_eligible_bid` stop reason. Likewise, a participant lacking enough USDC is an explicit settlement assumption and possible loss, not a form error. Never turn a model error into a zero-loss result.

Test the adapter without a browser: six-member example parity with the CLI, immediate bid-interest deduction, collateral posted only on payout, fixed post-payout contribution, same-day multiple defaults, first-freeze behavior, 7-day settlement, and per-member losses. Test validated case JSON roundtrip and rejection of malformed imports. Test multiple named cases and the frontier with a tiny deterministic CSV: identical windows at each ratio, reproducible seed, changed payout order flagged, no qualifying ratio and qualifying ratio cases, and exact chart-row parity with the run records. Smoke-test Streamlit startup and manually inspect both views at desktop and narrow widths, including empty/loading/error states and keyboard-readable labels.

## Out of scope for this release

No game-theoretic best response or collusion solver; no live ETH oracle, candle-low execution assumption, auto-liquidation, real funds, identity, multiuser hosting, or claims of full protection. A later study may add actual daily-low data as a separate sensitivity bound, carefully labeled as a hypothetical execution price rather than an observed fill.
