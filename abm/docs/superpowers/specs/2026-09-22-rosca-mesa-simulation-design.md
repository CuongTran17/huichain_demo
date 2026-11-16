# Mesa ROSCA Simulation Design

## 1. Purpose

Build a reproducible Python research prototype using Mesa to compare two collateral policies in a fixed-order on-chain ROSCA:

1. Fixed Collateral Policy.
2. Reputation-Adjusted Collateral Policy.

The model studies whether reputation-adjusted collateral can reduce locked capital and improve net liquidity while keeping default loss within a predeclared tolerance relative to fixed collateral. ETH collateral changes value over time; contributions and payouts are denominated in a stablecoin.

The first version is a command-line batch simulation. It has no web interface or spatial grid.

## 2. Success Criteria

The prototype is successful when it can:

- Load all experiment parameters from TOML without source-code changes.
- Run both policies on identical agents, payout order, price path, and random seed.
- Re-evaluate strategic default before every contribution due after an agent receives its payout.
- Replay normalized historical ETH price windows and deterministic stress paths.
- Produce per-policy and paired CSV results.
- Reproduce identical results from the same configuration, data, and seed.
- Pass accounting, collateral, policy-boundary, and price-data tests.

## 3. Scope

### Included

- Fixed-order ROSCA.
- Configurable member count, number of periods, contribution, and period length.
- Stablecoin-denominated contributions and payouts.
- ETH as the only collateral asset.
- Fixed and reputation-adjusted collateral policies.
- Existing reputation assigned before a ROSCA round.
- Cold-start members with reputation zero.
- Deterministic utility-based strategic default.
- Repeated default evaluation at every due date after payout.
- Historical ETH price replay and deterministic stress scenarios.
- Paired Monte Carlo runs.
- CSV outputs and reproducibility metadata.

### Excluded from version one

- Web UI or Mesa visualization server.
- Spatial grids.
- Multiple collateral assets.
- Mandatory collateral top-ups.
- Liquidation fees, delay, or slippage.
- Income, unemployment, or liquidity-shock defaults.
- Probabilistic default decisions.
- Reputation updates across multiple ROSCA rounds.
- Sybil resistance and decentralized identity.
- Smart-contract implementation.

## 4. Project Structure

```text
rosca-simulation/
|-- pyproject.toml
|-- configs/
|   |-- baseline.toml
|   `-- stress.toml
|-- data/
|   `-- eth_prices.csv
|-- src/
|   `-- rosca_sim/
|       |-- __init__.py
|       |-- model.py
|       |-- prices.py
|       |-- experiment.py
|       `-- cli.py
`-- tests/
    |-- test_model.py
    |-- test_policies.py
    `-- test_prices.py
```

Responsibilities:

- `model.py`: Mesa model, agents, policy calculations, event ordering, and metrics.
- `prices.py`: CSV loading, validation, normalization, historical-window selection, and stress paths.
- `experiment.py`: paired policy execution and result aggregation.
- `cli.py`: command-line entry point that selects a TOML configuration and output directory.
- `configs/`: reproducible experiment definitions.
- `tests/`: deterministic model and data checks.

The source tree remains deliberately small. Separate modules are added only when a responsibility is independently testable.

## 5. Configuration

TOML is the authoritative source of experiment parameters. A baseline configuration contains the following groups:

```toml
[rosca]
members = 10
periods = 10
contribution = 100.0
period_days = 30

[collateral]
fixed_ratio = 0.50
alpha_min = 0.20
alpha_max = 0.80
require_top_up = false

[reputation]
distribution = "beta"
alpha = 2.0
beta = 2.0
new_member_share = 0.20

[behavior]
decision_mode = "every_due_date"
decision_rule = "deterministic"
reputation_loss = 50.0
future_access_loss = 100.0

[prices]
source = "historical"
file = "data/eth_prices.csv"
start_date = "2021-01-01"
end_date = "2026-08-31"
normalize = true

[experiment]
runs = 500
seed = 42
risk_tolerance = 0.0
```

All numeric assumptions are configurable. Validation rejects inconsistent values such as `members != periods`, negative contributions, reputation outside `[0, 1]`, or `alpha_min > alpha_max`.

Version one assumes one payout per period and therefore requires `members == periods`.

## 6. Agent State

Each agent stores:

- `position`: scheduled payout period.
- `reputation`: fixed value in `[0, 1]` for the current round.
- `has_received_payout`.
- `remaining_obligation`.
- `locked_eth`.
- `initial_locked_eth`.
- `initial_post_payout_obligation`.
- `active`.
- `default_period`, if any.
- `total_contributed`.
- `payout_received`.
- `collateral_released`.

Reputation represents history accumulated before the simulated round. It remains fixed during the round. A configurable share of agents are cold-start members and receive reputation zero. Other reputations are sampled from a configurable beta distribution using Python's seeded standard-library random generator.

## 7. Policies

### Fixed Collateral Policy

```text
CR_i = fixed_ratio
```

### Reputation-Adjusted Collateral Policy

```text
CR_i = alpha_max - (alpha_max - alpha_min) * reputation_i
```

Required collateral immediately before payout is:

```text
required_collateral_value = CR_i * post_payout_remaining_obligation
locked_eth = required_collateral_value / current_eth_price
```

Boundary requirements:

- Reputation zero gives `alpha_max`.
- Reputation one gives `alpha_min`.
- No top-up is required after an ETH price decline.

## 8. Period Event Order

For each period:

1. Set the current ETH price.
2. For each active agent that received a payout and still owes contributions, calculate strategic-default utility before collecting the current contribution.
3. Default agents, liquidate the necessary amount of remaining collateral, return any excess collateral, add recovered value to the ROSCA pool, and record uncovered loss.
4. Collect the current contribution from every remaining active agent.
5. Release collateral for each post-payout agent that contributed successfully.
6. Require the scheduled payout recipient to lock collateral based on the obligation remaining after the current period.
7. Pay the scheduled recipient from the available pool.
8. Record period and system metrics.

Agents that have not yet received a payout do not strategically default in version one.

## 9. Strategic Default

Before each contribution due after payout:

```text
saved_contribution = remaining_obligation
collateral_value = locked_eth * current_eth_price
collateral_loss = min(collateral_value, remaining_obligation)

delta_utility = (
    saved_contribution
    - collateral_loss
    - reputation_loss
    - future_access_loss
)
```

The agent defaults when `delta_utility > 0`. A defaulted agent exits permanently and makes no further contributions.

This is a myopic deterministic decision: an agent uses current state without forecasting future ETH prices. A one-time decision mode may be added as a sensitivity configuration, but `every_due_date` is the primary design.

## 10. Collateral Release and Default Loss

For an agent that contributes successfully after payout, release a fixed ETH amount proportional to the contribution completed:

```text
released_eth = initial_locked_eth * contribution / initial_post_payout_obligation
```

The final release is capped at the remaining locked ETH to avoid floating-point over-release.

At default:

```text
collateral_value = locked_eth * current_eth_price
recovered_collateral = min(collateral_value, remaining_obligation)
default_loss = max(0, remaining_obligation - recovered_collateral)
```

Only collateral required to cover the remaining obligation is forfeited. Any excess value is returned to the agent. Recovered collateral enters the shared ROSCA pool and can support later payouts.

## 11. Pool and Payout Accounting

The pool contains:

- Contributions collected in the current period.
- Recovered collateral from defaults.
- Unused balance carried from previous periods.

For each scheduled payout:

```text
scheduled_payout = members * contribution
actual_payout = min(pool_balance, scheduled_payout)
```

A payout is fully funded when `actual_payout` equals `scheduled_payout` within a defined floating-point tolerance. A short payout is recorded in its period and is not converted into a separate receivable.

The implementation records enough period-level flows to verify:

```text
opening_pool
+ contributions
+ recovered_collateral
- actual_payout
= closing_pool
```

## 12. ETH Price Data

The simulation reads a local CSV with at least:

```text
date,close
```

Data download is a separate explicit operation; simulations never silently refresh external data. Historical-data validation checks:

- Parseable and unique dates.
- Positive prices.
- Ascending order after normalization.
- Coverage of the configured date range.
- Sufficient observations for the requested ROSCA window.

For each paired run, the experiment selects a valid start date and samples one observation every `period_days` until it has one price per period. The selected path is normalized by its first observation when `normalize = true`. Both policies receive the same path.

Supported deterministic stress paths in version one:

- `constant`.
- `drop_20`.
- `drop_40`.
- `drop_60`.
- `gradual_decline`.
- `rise_then_crash`.

## 13. Paired Experiment Design

Each `run_id` defines one seed, agent population, payout order, reputation vector, and ETH price path. That immutable run input is passed separately to both policies.

Per-policy output fields:

- `run_id`.
- `policy`.
- `seed`.
- `price_window_start` or stress-scenario name.
- `default_count`.
- `default_loss`.
- `capital_locked`.
- `net_liquidity`.
- `completion_rate`.
- `recovered_collateral`.

Paired output fields:

- `run_id`.
- Difference in each primary outcome, calculated as Policy B minus Policy A.
- `risk_equivalent`, defined as `DefaultLoss_B <= DefaultLoss_A + risk_tolerance`.

The output directory also contains the exact TOML configuration, master seed, price-date range, run timestamp, and program version.

## 14. Tests

Tests are written before their corresponding implementation behavior.

Required deterministic tests:

1. With no defaults, every payout is fully funded.
2. Fully covering collateral produces zero default loss.
3. Insufficient collateral produces the exact uncovered loss.
4. Reputation zero maps to `alpha_max`.
5. Reputation one maps to `alpha_min`.
6. Released ETH never exceeds initially locked ETH.
7. A completed agent has zero remaining locked ETH.
8. A defaulted agent never contributes again.
9. Both policies receive identical paired run inputs.
10. The same TOML, data, and seed reproduce identical results.
11. Invalid or insufficient price data fails with a clear error.
12. The pool accounting identity holds after every period.
13. Default decisions occur before contribution and collateral release.

## 15. Implementation Constraints

- Use Mesa for the model and agent lifecycle, without a grid.
- Prefer Python's standard library for TOML, CSV, random sampling, argument parsing, and file handling.
- Add dependencies only when Mesa or a verified research requirement needs them.
- Keep policy functions pure where possible so they can be tested without running a full model.
- Do not download data during tests.
- Do not run the full Monte Carlo experiment until deterministic and pilot tests pass.

## 16. Research Interpretation Boundary

Historical replay measures how the proposed policies would behave under selected past ETH paths. It is not a forecast of future ETH prices. The main comparison is conditional on the model assumptions, especially persistent identity, deterministic utility, no top-up, immediate liquidation, and fixed reputation within a round.

The experiment configuration, price cutoff date, risk tolerance, and primary outcomes must be fixed before the full run to reduce post-result tuning.
