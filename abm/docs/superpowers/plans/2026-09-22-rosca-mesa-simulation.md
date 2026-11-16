# Mesa ROSCA Simulation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible Mesa-based fixed-order ROSCA simulator that compares fixed and reputation-adjusted collateral policies on paired ETH price paths.

**Architecture:** A small Python package separates the Mesa model, price-path preparation, paired experiment runner, and CLI. TOML is the authoritative configuration, immutable run inputs guarantee paired comparisons, and CSV outputs preserve results and reproducibility metadata.

**Tech Stack:** Python 3.12+, Mesa 3.5.1, standard-library `tomllib`, `csv`, `argparse`, `random`, `datetime`, `urllib`, and pytest.

**Spec:** `docs/superpowers/specs/2026-09-22-rosca-mesa-simulation-design.md`

## Global Constraints

- Use Python 3.12 or newer; Mesa 3.5.1 requires Python 3.12 or newer.
- Pin `mesa==3.5.1`; do not install visualization extras.
- Use Mesa agents and model lifecycle without a grid or browser UI.
- Use TOML for every model and experiment parameter.
- Use only standard-library modules besides Mesa and pytest.
- Never download data during simulation runs or tests.
- Policy A and Policy B must receive identical immutable run inputs.
- Evaluate strategic default before contribution collection and collateral release.
- Do not run the full Monte Carlo experiment until deterministic tests and a small pilot pass.

## Review Focus

- Floating-point residue must not leave tiny negative pool, obligation, or collateral balances; tests use a single `EPSILON = 1e-9` rule.
- A last-position recipient has zero post-payout obligation and must lock zero ETH without division by zero.
- Historical paths with duplicate dates, nonpositive prices, gaps on required sampling dates, or insufficient coverage must fail clearly.
- An agent whose collateral exceeds its remaining obligation forfeits only the required value and receives the excess back.
- Paired results must remain identical under repeat execution with the same config, price CSV, and master seed.

---

## File Map

- `pyproject.toml`: package metadata, Mesa pin, pytest dependency, and console entry point.
- `src/rosca_sim/__init__.py`: package version.
- `src/rosca_sim/model.py`: configuration dataclasses, pure policy/utility functions, Mesa agent/model, accounting, and result type.
- `src/rosca_sim/prices.py`: CSV validation, path sampling/normalization, stress paths, and optional explicit CoinGecko fetch.
- `src/rosca_sim/experiment.py`: immutable paired run generation, policy execution, CSV aggregation, and metadata.
- `src/rosca_sim/cli.py`: TOML loading/validation and `run`/`fetch-prices` commands.
- `configs/baseline.toml`: historical replay example.
- `configs/stress.toml`: deterministic stress example.
- `data/.gitkeep`: retains the local data directory without committing fetched datasets.
- `tests/test_policies.py`: policy boundaries and utility calculations.
- `tests/test_prices.py`: price validation, sampling, stress paths, and fetch parsing.
- `tests/test_model.py`: event order, accounting, collateral, and default integration.
- `tests/test_experiment.py`: pairing, reproducibility, CSV, and metadata.
- `tests/test_cli.py`: TOML validation and CLI smoke tests.
- `README.md`: setup and pilot commands.

### Task 1: Scaffold the package and implement policy primitives

**Files:**
- Create: `pyproject.toml`
- Create: `src/rosca_sim/__init__.py`
- Create: `src/rosca_sim/model.py`
- Create: `tests/test_policies.py`

**Interfaces:**
- Produces: `CollateralConfig`, `BehaviorConfig`, `RoscaConfig`, `fixed_collateral_ratio()`, `reputation_collateral_ratio()`, and `strategic_default_utility()`.
- Consumes: no project interfaces.

- [ ] **Step 1: Initialize the repository and virtual environment**

Run:

```powershell
git init
py -3.12 -m venv .venv
```

Expected: `.git/` and `.venv/` exist. Do not commit `.venv/`.

- [ ] **Step 2: Add package metadata**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "rosca-sim"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["mesa==3.5.1"]

[project.optional-dependencies]
dev = ["pytest>=8,<10"]

[project.scripts]
rosca-sim = "rosca_sim.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Create `src/rosca_sim/__init__.py`:

```python
__version__ = "0.1.0"
```

Install:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Expected: installation succeeds with Mesa 3.5.1.

- [ ] **Step 3: Write failing policy tests**

Create `tests/test_policies.py`:

```python
import pytest

from rosca_sim.model import (
    CollateralConfig,
    fixed_collateral_ratio,
    reputation_collateral_ratio,
    strategic_default_utility,
)


def test_reputation_policy_boundaries():
    config = CollateralConfig(fixed_ratio=0.5, alpha_min=0.2, alpha_max=0.8)
    assert reputation_collateral_ratio(0.0, config) == pytest.approx(0.8)
    assert reputation_collateral_ratio(1.0, config) == pytest.approx(0.2)


def test_fixed_policy_returns_configured_ratio():
    config = CollateralConfig(fixed_ratio=0.5, alpha_min=0.2, alpha_max=0.8)
    assert fixed_collateral_ratio(config) == pytest.approx(0.5)


def test_default_utility_uses_only_forfeitable_collateral():
    utility = strategic_default_utility(
        remaining_obligation=300.0,
        collateral_value=500.0,
        reputation_loss=25.0,
        future_access_loss=50.0,
    )
    assert utility == pytest.approx(-75.0)
```

- [ ] **Step 4: Run tests and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_policies.py -v
```

Expected: FAIL because `rosca_sim.model` does not exist.

- [ ] **Step 5: Implement the minimum policy primitives**

Create `src/rosca_sim/model.py` with:

```python
from dataclasses import dataclass

EPSILON = 1e-9


@dataclass(frozen=True)
class RoscaConfig:
    members: int
    periods: int
    contribution: float
    period_days: int


@dataclass(frozen=True)
class CollateralConfig:
    fixed_ratio: float
    alpha_min: float
    alpha_max: float
    require_top_up: bool = False


@dataclass(frozen=True)
class BehaviorConfig:
    reputation_loss: float
    future_access_loss: float
    decision_mode: str = "every_due_date"
    decision_rule: str = "deterministic"


def fixed_collateral_ratio(config: CollateralConfig) -> float:
    return config.fixed_ratio


def reputation_collateral_ratio(
    reputation: float, config: CollateralConfig
) -> float:
    if not 0.0 <= reputation <= 1.0:
        raise ValueError("reputation must be between 0 and 1")
    return config.alpha_max - (config.alpha_max - config.alpha_min) * reputation


def strategic_default_utility(
    remaining_obligation: float,
    collateral_value: float,
    reputation_loss: float,
    future_access_loss: float,
) -> float:
    collateral_loss = min(collateral_value, remaining_obligation)
    return remaining_obligation - collateral_loss - reputation_loss - future_access_loss
```

- [ ] **Step 6: Run policy tests and confirm GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_policies.py -v
```

Expected: 3 tests pass.

- [ ] **Step 7: Commit**

```powershell
git add pyproject.toml src/rosca_sim tests/test_policies.py
git commit -m "feat: add ROSCA policy primitives"
```

### Task 2: Implement historical and stress price paths

**Files:**
- Create: `src/rosca_sim/prices.py`
- Create: `tests/test_prices.py`

**Interfaces:**
- Produces: `PricePoint`, `PricePath`, `load_price_csv()`, `sample_historical_path()`, `make_stress_path()`, and `fetch_coingecko_prices()`.
- Consumes: `EPSILON` only for numeric validation.

- [ ] **Step 1: Write failing CSV and historical-window tests**

Create `tests/test_prices.py` with temporary CSV fixtures and these core tests:

```python
from datetime import date
import random

import pytest

from rosca_sim.prices import load_price_csv, sample_historical_path


def test_load_price_csv_rejects_duplicate_dates(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text("date,close\n2026-01-01,100\n2026-01-01,101\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate date"):
        load_price_csv(path, date(2026, 1, 1), date(2026, 1, 2))


def test_historical_path_uses_exact_period_spacing_and_normalizes(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text(
        "date,close\n2026-01-01,100\n2026-01-02,110\n2026-01-03,121\n",
        encoding="utf-8",
    )
    points = load_price_csv(path, date(2026, 1, 1), date(2026, 1, 3))
    result = sample_historical_path(points, periods=3, period_days=1, rng=random.Random(7))
    assert result.prices == pytest.approx((1.0, 1.1, 1.21))
```

Add tests for nonpositive prices, insufficient coverage, and a missing required sampling date.

- [ ] **Step 2: Run price tests and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prices.py -v
```

Expected: FAIL because `rosca_sim.prices` does not exist.

- [ ] **Step 3: Implement CSV parsing and historical sampling**

Implement these public types and signatures in `prices.py`:

```python
@dataclass(frozen=True)
class PricePoint:
    day: date
    close: float


@dataclass(frozen=True)
class PricePath:
    prices: tuple[float, ...]
    label: str
    start_date: str | None


def load_price_csv(path: Path, start: date, end: date) -> tuple[PricePoint, ...]:
    seen: set[date] = set()
    points: list[PricePoint] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
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
) -> PricePath:
    by_day = {point.day: point.close for point in points}
    starts = [
        point.day
        for point in points
        if all(point.day + timedelta(days=period_days * i) in by_day for i in range(periods))
    ]
    if not starts:
        raise ValueError("no complete historical window")
    start = rng.choice(starts)
    values = tuple(by_day[start + timedelta(days=period_days * i)] for i in range(periods))
    if normalize:
        first = values[0]
        values = tuple(value / first for value in values)
    return PricePath(values, "historical", start.isoformat())
```

Build candidate starts only when every exact target date exists. Raise `ValueError("no complete historical window")` when there is no valid window.

- [ ] **Step 4: Add failing stress-path tests**

```python
from rosca_sim.prices import make_stress_path


@pytest.mark.parametrize(
    ("scenario", "last"),
    [("constant", 1.0), ("drop_20", 0.8), ("drop_40", 0.6), ("drop_60", 0.4)],
)
def test_stress_path_endpoints(scenario, last):
    path = make_stress_path(scenario, periods=10)
    assert len(path.prices) == 10
    assert path.prices[0] == pytest.approx(1.0)
    assert path.prices[-1] == pytest.approx(last)
```

- [ ] **Step 5: Implement stress paths**

Implement `make_stress_path(scenario: str, periods: int) -> PricePath` with:

- `constant`: all 1.0.
- `drop_20`, `drop_40`, `drop_60`: first value 1.0, all later values at the stated level.
- `gradual_decline`: linear from 1.0 to 0.6.
- `rise_then_crash`: linear from 1.0 to 1.3 through the midpoint, then linear to 0.6.

Reject `periods < 1` and unknown scenarios with clear `ValueError` messages.

- [ ] **Step 6: Run price tests and confirm GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prices.py -v
```

Expected: all price tests pass.

- [ ] **Step 7: Commit**

```powershell
git add src/rosca_sim/prices.py tests/test_prices.py
git commit -m "feat: add reproducible ETH price paths"
```

### Task 3: Implement a no-default Mesa ROSCA round

**Files:**
- Modify: `src/rosca_sim/model.py`
- Create: `tests/test_model.py`

**Interfaces:**
- Produces: `AgentSeed`, `RunInputs`, `SimulationResult`, `RoscaAgent`, `RoscaModel`, and `RoscaModel.run()`.
- Consumes: `RoscaConfig`, `CollateralConfig`, `BehaviorConfig`, and a tuple of normalized prices.

- [ ] **Step 1: Write failing no-default and accounting tests**

Create a helper that makes three agents with very large behavioral losses so default utility remains negative:

```python
from rosca_sim.model import (
    AgentSeed,
    BehaviorConfig,
    CollateralConfig,
    RoscaConfig,
    RoscaModel,
    RunInputs,
)


def safe_model():
    inputs = RunInputs(
        run_id=0,
        seed=7,
        agents=tuple(AgentSeed(position=i, reputation=0.5) for i in range(3)),
        prices=(1.0, 1.0, 1.0),
        price_label="constant",
        price_window_start=None,
    )
    return RoscaModel(
        rosca=RoscaConfig(3, 3, 100.0, 30),
        collateral=CollateralConfig(0.5, 0.2, 0.8),
        behavior=BehaviorConfig(10_000.0, 10_000.0),
        policy="fixed",
        inputs=inputs,
    )


def test_no_default_round_funds_every_payout():
    result = safe_model().run()
    assert result.default_count == 0
    assert result.completion_rate == 1.0
    assert result.default_loss == 0.0


def test_pool_identity_holds_after_every_period():
    model = safe_model()
    model.run()
    for row in model.period_records:
        assert row.opening_pool + row.contributions + row.recovered_collateral \
            == pytest.approx(row.actual_payout + row.closing_pool)
```

Add a last-position test asserting zero locked ETH and no division by zero.

- [ ] **Step 2: Run model tests and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_model.py -v
```

Expected: FAIL because the Mesa model types do not exist.

- [ ] **Step 3: Implement immutable inputs and result records**

Add frozen dataclasses:

```python
@dataclass(frozen=True)
class AgentSeed:
    position: int
    reputation: float


@dataclass(frozen=True)
class RunInputs:
    run_id: int
    seed: int
    agents: tuple[AgentSeed, ...]
    prices: tuple[float, ...]
    price_label: str
    price_window_start: str | None


@dataclass(frozen=True)
class PeriodRecord:
    period: int
    opening_pool: float
    contributions: float
    recovered_collateral: float
    scheduled_payout: float
    actual_payout: float
    closing_pool: float


@dataclass(frozen=True)
class SimulationResult:
    run_id: int
    policy: str
    seed: int
    price_label: str
    price_window_start: str | None
    default_count: int
    default_loss: float
    capital_locked: float
    net_liquidity: float
    completion_rate: float
    recovered_collateral: float
```

- [ ] **Step 4: Implement the minimum Mesa model without default mechanics**

Implement `RoscaAgent(Agent)` and `RoscaModel(Model)`. Keep a deterministic `members` list ordered by payout position. `step()` must collect contributions, release any due collateral, lock the current recipient's collateral, pay from the pool, and append `PeriodRecord`.

Use `max(0.0, value)` and `EPSILON` only at balance boundaries; do not round stored values during the simulation.

Define result metrics exactly as follows:

- `capital_locked`: sum of required collateral value at each agent's lock time.
- `net_liquidity`: sum of actual payouts received minus `capital_locked`.
- `completion_rate`: fully funded scheduled payouts divided by total periods.
- `recovered_collateral`: sum of stablecoin value transferred from liquidated collateral into the pool.

- [ ] **Step 5: Run model tests and confirm GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_model.py -v
```

Expected: no-default, accounting, and last-position tests pass.

- [ ] **Step 6: Commit**

```powershell
git add src/rosca_sim/model.py tests/test_model.py
git commit -m "feat: simulate a complete fixed-order ROSCA round"
```

### Task 4: Add collateral release and repeated strategic default

**Files:**
- Modify: `src/rosca_sim/model.py`
- Modify: `tests/test_model.py`

**Interfaces:**
- Produces: complete `RoscaAgent.should_default()`, `RoscaAgent.release_collateral()`, and `RoscaModel.process_defaults()` behavior.
- Consumes: policy and utility primitives from Task 1.

- [ ] **Step 1: Write failing collateral and event-order tests**

First add `settle_default(remaining_obligation, locked_eth, eth_price)` as a planned pure interface returning `DefaultSettlement(recovered, default_loss, liquidated_eth, returned_eth)`. Then add these exact tests:

```python
def test_fully_covering_collateral_produces_zero_default_loss():
    settlement = settle_default(300.0, locked_eth=3.0, eth_price=100.0)
    assert settlement.recovered == pytest.approx(300.0)
    assert settlement.default_loss == pytest.approx(0.0)


def test_insufficient_collateral_records_exact_shortfall():
    settlement = settle_default(300.0, locked_eth=2.0, eth_price=100.0)
    assert settlement.recovered == pytest.approx(200.0)
    assert settlement.default_loss == pytest.approx(100.0)


def test_excess_collateral_is_returned_not_forfeited():
    settlement = settle_default(300.0, locked_eth=5.0, eth_price=100.0)
    assert settlement.liquidated_eth == pytest.approx(3.0)
    assert settlement.returned_eth == pytest.approx(2.0)


def defaulting_model():
    inputs = RunInputs(
        run_id=1,
        seed=11,
        agents=(AgentSeed(0, 0.5), AgentSeed(1, 0.5)),
        prices=(1.0, 1.0),
        price_label="constant",
        price_window_start=None,
    )
    return RoscaModel(
        rosca=RoscaConfig(2, 2, 100.0, 30),
        collateral=CollateralConfig(0.2, 0.2, 0.8),
        behavior=BehaviorConfig(0.0, 0.0),
        policy="fixed",
        inputs=inputs,
    )


def test_default_happens_before_current_contribution_and_release():
    model = defaulting_model()
    model.run()
    agent = model.members[0]
    assert agent.default_period == 1
    assert agent.total_contributed == pytest.approx(100.0)
    assert agent.collateral_released == pytest.approx(0.0)
    assert model.period_records[1].contributions == pytest.approx(100.0)


def test_defaulted_agent_never_contributes_again():
    model = defaulting_model()
    model.run()
    assert model.members[0].active is False
    assert model.members[0].total_contributed == pytest.approx(100.0)


def test_completed_agent_has_zero_locked_eth():
    model = safe_model()
    model.run()
    assert model.members[0].locked_eth == pytest.approx(0.0, abs=EPSILON)


def test_released_eth_never_exceeds_initial_lock():
    model = safe_model()
    model.run()
    for agent in model.members:
        assert agent.collateral_released <= agent.initial_locked_eth + EPSILON
```

- [ ] **Step 2: Run the new tests and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_model.py -v
```

Expected: new default and collateral tests fail.

- [ ] **Step 3: Implement repeated default decisions**

Before collecting contributions in each period, evaluate active post-payout agents with remaining obligation above `EPSILON`:

```python
def should_default(self, eth_price: float) -> bool:
    utility = strategic_default_utility(
        remaining_obligation=self.remaining_obligation,
        collateral_value=self.locked_eth * eth_price,
        reputation_loss=self.behavior.reputation_loss,
        future_access_loss=self.behavior.future_access_loss,
    )
    return utility > EPSILON
```

On default, compute recovered value, default loss, liquidated ETH, and returned excess. Set `active = False` before the contribution phase.

Implement the pure settlement function with the exact cap behavior:

```python
@dataclass(frozen=True)
class DefaultSettlement:
    recovered: float
    default_loss: float
    liquidated_eth: float
    returned_eth: float


def settle_default(
    remaining_obligation: float, locked_eth: float, eth_price: float
) -> DefaultSettlement:
    collateral_value = locked_eth * eth_price
    recovered = min(collateral_value, remaining_obligation)
    liquidated_eth = recovered / eth_price
    return DefaultSettlement(
        recovered=recovered,
        default_loss=max(0.0, remaining_obligation - recovered),
        liquidated_eth=liquidated_eth,
        returned_eth=max(0.0, locked_eth - liquidated_eth),
    )
```

- [ ] **Step 4: Implement bounded collateral release**

After a successful post-payout contribution:

```python
release = min(
    self.locked_eth,
    self.initial_locked_eth
    * self.model.rosca.contribution
    / self.initial_post_payout_obligation,
)
self.locked_eth = max(0.0, self.locked_eth - release)
```

Skip release when initial post-payout obligation is zero.

- [ ] **Step 5: Run all model and policy tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_policies.py tests/test_model.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add src/rosca_sim/model.py tests/test_model.py
git commit -m "feat: add dynamic collateral and strategic default"
```

### Task 5: Implement paired experiment generation and CSV output

**Files:**
- Create: `src/rosca_sim/experiment.py`
- Create: `tests/test_experiment.py`

**Interfaces:**
- Produces: `ReputationConfig`, `ExperimentConfig`, `build_run_inputs()`, `run_pair()`, and `run_experiment()`.
- Consumes: `RunInputs`, `RoscaModel`, `PricePath`, and model configuration dataclasses.

- [ ] **Step 1: Write failing pairing and reproducibility tests**

Create `tests/test_experiment.py` with a concrete paired setup:

```python
def paired_settings():
    return (
        RoscaConfig(3, 3, 100.0, 30),
        CollateralConfig(0.5, 0.2, 0.8),
        BehaviorConfig(50.0, 100.0),
    )


def test_run_pair_uses_identical_inputs_for_both_policies():
    rosca, collateral, behavior = paired_settings()
    inputs = RunInputs(
        run_id=4,
        seed=19,
        agents=(AgentSeed(0, 0.0), AgentSeed(1, 0.5), AgentSeed(2, 1.0)),
        prices=(1.0, 0.8, 0.6),
        price_label="drop_40",
        price_window_start=None,
    )
    fixed, adjusted, paired = run_pair(
        rosca, collateral, behavior, inputs, risk_tolerance=0.0
    )
    assert fixed.run_id == adjusted.run_id == inputs.run_id
    assert fixed.seed == adjusted.seed == inputs.seed
    assert fixed.price_label == adjusted.price_label == inputs.price_label
    assert paired["run_id"] == inputs.run_id


def test_same_inputs_reproduce_pair_exactly():
    rosca, collateral, behavior = paired_settings()
    inputs = RunInputs(
        run_id=5,
        seed=23,
        agents=(AgentSeed(0, 0.1), AgentSeed(1, 0.5), AgentSeed(2, 0.9)),
        prices=(1.0, 1.1, 0.7),
        price_label="manual",
        price_window_start=None,
    )
    first = run_pair(rosca, collateral, behavior, inputs, risk_tolerance=5.0)
    second = run_pair(rosca, collateral, behavior, inputs, risk_tolerance=5.0)
    assert first == second
```

Add a test that verifies cold-start members receive reputation zero and all other generated reputations remain in `[0, 1]`.

- [ ] **Step 2: Run experiment tests and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_experiment.py -v
```

Expected: FAIL because `rosca_sim.experiment` does not exist.

- [ ] **Step 3: Implement deterministic run-input generation**

Define:

```python
@dataclass(frozen=True)
class ReputationConfig:
    distribution: str
    alpha: float
    beta: float
    new_member_share: float


@dataclass(frozen=True)
class ExperimentConfig:
    runs: int
    seed: int
    risk_tolerance: float
```

Use `random.Random(master_seed)` to allocate one child seed per run. Use a separate `random.Random(child_seed)` for reputation and path sampling so repeat executions are stable.

- [ ] **Step 4: Implement paired policy execution**

Implement this exact public signature:

```python
def run_pair(
    rosca: RoscaConfig,
    collateral: CollateralConfig,
    behavior: BehaviorConfig,
    inputs: RunInputs,
    risk_tolerance: float,
) -> tuple[SimulationResult, SimulationResult, dict[str, object]]:
```

It constructs two independent `RoscaModel` instances from the same frozen `RunInputs`. Return the fixed result, adjusted result, and paired fields computed as Policy B minus Policy A.

Set:

```python
risk_equivalent = adjusted.default_loss <= fixed.default_loss + risk_tolerance + EPSILON
```

- [ ] **Step 5: Implement CSV and metadata output**

Use `csv.DictWriter` to create `run_results.csv` and `paired_results.csv`. Write `metadata.json` with the package version, master seed, run count, price source/range, UTC timestamp, and SHA-256 hash of the input price CSV when applicable.

- [ ] **Step 6: Run experiment tests and confirm GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_experiment.py -v
```

Expected: pairing, cold-start, CSV, metadata, and reproducibility tests pass.

- [ ] **Step 7: Commit**

```powershell
git add src/rosca_sim/experiment.py tests/test_experiment.py
git commit -m "feat: add paired Monte Carlo experiments"
```

### Task 6: Add TOML configuration and command-line execution

**Files:**
- Create: `src/rosca_sim/cli.py`
- Create: `configs/baseline.toml`
- Create: `configs/stress.toml`
- Create: `data/.gitkeep`
- Create: `tests/test_cli.py`

**Interfaces:**
- Produces: `load_config(path: Path)`, `build_parser()`, and `main()`.
- Consumes: all configuration dataclasses, price loaders, and `run_experiment()`.

- [ ] **Step 1: Write failing configuration-validation tests**

Create a complete valid TOML helper, then mutate one field per test:

```python
def valid_toml() -> str:
    return """
[rosca]
members = 2
periods = 2
contribution = 100.0
period_days = 30
[collateral]
fixed_ratio = 0.5
alpha_min = 0.2
alpha_max = 0.8
require_top_up = false
[reputation]
distribution = "beta"
alpha = 2.0
beta = 2.0
new_member_share = 0.2
[behavior]
decision_mode = "every_due_date"
decision_rule = "deterministic"
reputation_loss = 50.0
future_access_loss = 100.0
[prices]
source = "stress"
scenario = "constant"
[experiment]
runs = 2
seed = 42
risk_tolerance = 0.0
"""


def write_config(tmp_path, content):
    path = tmp_path / "config.toml"
    path.write_text(content, encoding="utf-8")
    return path


def test_config_rejects_member_period_mismatch(tmp_path):
    path = write_config(tmp_path, valid_toml().replace("periods = 2", "periods = 3"))
    with pytest.raises(ValueError, match="members must equal periods"):
        load_config(path)


def test_config_rejects_alpha_min_above_alpha_max(tmp_path):
    path = write_config(tmp_path, valid_toml().replace("alpha_min = 0.2", "alpha_min = 0.9"))
    with pytest.raises(ValueError, match="alpha_min must not exceed alpha_max"):
        load_config(path)


def test_config_rejects_negative_contribution(tmp_path):
    path = write_config(tmp_path, valid_toml().replace("contribution = 100.0", "contribution = -1.0"))
    with pytest.raises(ValueError, match="contribution must be positive"):
        load_config(path)


def test_config_rejects_unsupported_decision_mode(tmp_path):
    path = write_config(tmp_path, valid_toml().replace("every_due_date", "once_after_payout"))
    with pytest.raises(ValueError, match="supports decision_mode='every_due_date'"):
        load_config(path)
```

Add the missing-file test:

```python
def test_config_reports_missing_price_file(tmp_path):
    historical = valid_toml().replace(
        'source = "stress"\nscenario = "constant"',
        'source = "historical"\nfile = "missing.csv"\nstart_date = "2026-01-01"\nend_date = "2026-12-31"\nnormalize = true',
    )
    path = write_config(tmp_path, historical)
    with pytest.raises(FileNotFoundError, match="missing.csv"):
        load_config(path)
```

- [ ] **Step 2: Run CLI tests and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -v
```

Expected: FAIL because `rosca_sim.cli` does not exist.

- [ ] **Step 3: Implement TOML loading and validation**

Use `tomllib.load()`. Validate every range explicitly, including:

```python
if rosca.members != rosca.periods:
    raise ValueError("members must equal periods in version one")
if rosca.contribution <= 0:
    raise ValueError("contribution must be positive")
if collateral.alpha_min > collateral.alpha_max:
    raise ValueError("alpha_min must not exceed alpha_max")
if behavior.decision_mode != "every_due_date":
    raise ValueError("version one supports decision_mode='every_due_date'")
```

- [ ] **Step 4: Implement the `run` command**

Command shape:

```powershell
rosca-sim run --config configs/baseline.toml --output results/baseline
```

The command loads TOML, loads or creates price paths, calls `run_experiment()`, copies the exact config to the output directory as `config.toml`, and prints only the output directory and run count.

- [ ] **Step 5: Add example configurations**

Use the values in the approved spec for `baseline.toml`. Make `stress.toml` identical except:

```toml
[prices]
source = "stress"
scenario = "drop_40"
```

Start both examples with `runs = 100`; the examples are pilots, not full experiments.

- [ ] **Step 6: Run CLI tests and a stress smoke test**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -v
.\.venv\Scripts\rosca-sim.exe run --config configs/stress.toml --output results/smoke
```

Expected: tests pass and `results/smoke` contains both CSV files, `metadata.json`, and `config.toml`.

- [ ] **Step 7: Commit**

```powershell
git add src/rosca_sim/cli.py configs data/.gitkeep tests/test_cli.py
git commit -m "feat: add TOML-driven simulation CLI"
```

### Task 7: Add an explicit optional CoinGecko price fetch

**Files:**
- Modify: `src/rosca_sim/prices.py`
- Modify: `src/rosca_sim/cli.py`
- Modify: `tests/test_prices.py`

**Interfaces:**
- Produces: `fetch_coingecko_prices(start, end, api_key, output_path, opener=urlopen)` and `fetch-prices` CLI command.
- Consumes: the same `date,close` CSV schema used by historical replay.

- [ ] **Step 1: Write a failing response-parsing test with no network**

Use a fake opener that returns:

```json
{"prices": [[1767225600000, 3000.0], [1767312000000, 3060.0]]}
```

Assert the written CSV is:

```text
date,close
2026-01-01,3000.0
2026-01-02,3060.0
```

Also test missing `prices`, malformed rows, and a duplicate UTC date.

- [ ] **Step 2: Run the fetch tests and confirm RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prices.py -k coingecko -v
```

Expected: FAIL because the fetch function does not exist.

- [ ] **Step 3: Implement the explicit fetch function**

Use `urllib.parse.urlencode`, `urllib.request.Request`, and `urlopen`. Query CoinGecko's Ethereum market-chart range endpoint in USD with UTC Unix timestamps. Send the demo key only through the `x-cg-demo-api-key` header; never write it to logs or metadata.

Convert timestamps to UTC dates, validate positive prices, reject duplicate dates, and write sorted CSV atomically through a temporary file followed by `Path.replace()`.

- [ ] **Step 4: Add the CLI command**

Command shape:

```powershell
$env:COINGECKO_API_KEY = "user-supplied-key"
rosca-sim fetch-prices --start 2021-01-01 --end 2026-08-31 --output data/eth_prices.csv
```

Fail before making a request when the environment variable is absent. Do not automatically fetch when `rosca-sim run` finds a missing CSV.

- [ ] **Step 5: Run price and CLI tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_prices.py tests/test_cli.py -v
```

Expected: all tests pass without external network access.

- [ ] **Step 6: Commit**

```powershell
git add src/rosca_sim/prices.py src/rosca_sim/cli.py tests/test_prices.py tests/test_cli.py
git commit -m "feat: add explicit ETH price download"
```

### Task 8: Document and verify the complete pilot workflow

**Files:**
- Create: `README.md`
- Create: `.gitignore`
- Modify: any source or test file only when verification exposes a defect.

**Interfaces:**
- Produces: a documented setup, data-fetch, stress-pilot, historical-pilot, and result-inspection workflow.
- Consumes: all earlier commands and output schemas.

- [ ] **Step 1: Add repository hygiene**

Create `.gitignore` containing:

```text
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
results/
data/*.csv
```

- [ ] **Step 2: Write the README**

Document these exact commands:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\rosca-sim.exe run --config configs/stress.toml --output results/stress-pilot
$env:COINGECKO_API_KEY = "user-supplied-key"
.\.venv\Scripts\rosca-sim.exe fetch-prices --start 2021-01-01 --end 2026-08-31 --output data/eth_prices.csv
.\.venv\Scripts\rosca-sim.exe run --config configs/baseline.toml --output results/historical-pilot
```

Explain that historical replay is conditional analysis, not an ETH forecast, and that the full run must use a fixed configuration and data cutoff.

- [ ] **Step 3: Run the complete automated suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Expected: all tests pass with no warnings from project code.

- [ ] **Step 4: Run the 100-run stress pilot twice**

Run:

```powershell
.\.venv\Scripts\rosca-sim.exe run --config configs/stress.toml --output results/pilot-a
.\.venv\Scripts\rosca-sim.exe run --config configs/stress.toml --output results/pilot-b
```

Compare:

```powershell
Compare-Object (Get-Content results/pilot-a/paired_results.csv) (Get-Content results/pilot-b/paired_results.csv)
```

Expected: no differences.

- [ ] **Step 5: Inspect pilot invariants**

Confirm:

- Both CSV files contain 100 paired runs.
- Completion rates are between 0 and 1.
- Default losses and capital locked are nonnegative.
- Each `run_id` has exactly one fixed and one reputation-adjusted row.
- Metadata records Mesa 3.5.1, the master seed, and the stress scenario.

- [ ] **Step 6: Commit documentation and final verified state**

```powershell
git add .gitignore README.md
git commit -m "docs: document the ROSCA simulation pilot"
```

## Final Verification Gate

Before claiming implementation complete, run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\rosca-sim.exe run --config configs/stress.toml --output results/final-smoke
git status --short
```

Expected:

- Test process exits with status 0.
- Final smoke output contains `run_results.csv`, `paired_results.csv`, `metadata.json`, and `config.toml`.
- Git status contains no unintended files; ignored results and environment files do not appear.
