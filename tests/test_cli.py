import csv
import json
from datetime import date, timedelta

import pytest

import rosca_sim.cli as cli
from rosca_sim.cli import load_config, main


def valid_toml() -> str:
    return """
[rosca]
members = 2
periods = 2
contribution = 100.0
period_days = 30
reserve_initial = 0.0

[collateral]
fixed_ratio = 0.5
alpha_min = 0.2
alpha_max = 0.8
require_top_up = false

[reputation]
distribution = "beta"
alpha = 2.0
beta = 2.0
new_member_share = 0.5

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


def write_config(tmp_path, content: str):
    path = tmp_path / "config.toml"
    path.write_text(content, encoding="utf-8")
    return path


def test_auction_pilot_command_writes_separate_outputs(tmp_path):
    from pathlib import Path

    source = Path(__file__).parents[1] / "configs" / "auction-six-member.toml"
    output = tmp_path / "auction"
    assert main(["auction-run", "--config", str(source), "--output", str(output)]) == 0
    assert (output / "auction_run_results.csv").is_file()
    assert (output / "auction_agent_results.csv").is_file()
    assert (output / "auction_pair_results.csv").is_file()
    assert (output / "auction_metadata.json").is_file()
    assert (output / "config.toml").read_bytes() == source.read_bytes()
    with (output / "auction_agent_results.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    first = next(row for row in rows if row["policy"] == "fixed" and row["member_id"] == "0")
    assert float(first["net_payout"]) == pytest.approx(480)
    assert float(first["winning_bid"]) == pytest.approx(0.2)


@pytest.mark.parametrize("old,new,match", [
    ("reserve_initial = 0.0", "reserve_initial = 1.0", "reserve_initial"),
    ("grace_days = 7", "grace_days = -1", "grace_days"),
    ("usdc_capacity = 500.0", "usdc_capacity = -1.0", "invalid auction agent"),
    ("member_id = 5", "member_id = 9", "member IDs"),
])
def test_auction_config_rejects_invalid_inputs(tmp_path, old, new, match):
    from pathlib import Path

    source = Path(__file__).parents[1] / "configs" / "auction-six-member.toml"
    config = write_config(tmp_path, source.read_text(encoding="utf-8").replace(old, new, 1))
    with pytest.raises(ValueError, match=match):
        cli.load_auction_config(config)


def test_config_rejects_member_period_mismatch(tmp_path):
    path = write_config(tmp_path, valid_toml().replace("periods = 2", "periods = 3"))
    with pytest.raises(ValueError, match="members must equal periods"):
        load_config(path)


def test_config_rejects_alpha_min_above_alpha_max(tmp_path):
    path = write_config(tmp_path, valid_toml().replace("alpha_min = 0.2", "alpha_min = 0.9"))
    with pytest.raises(ValueError, match="alpha_min must not exceed alpha_max"):
        load_config(path)


def test_config_accepts_stress_coverage_inputs(tmp_path):
    path = write_config(
        tmp_path,
        valid_toml().replace(
            "require_top_up = false",
            "require_top_up = false\nstress_drop = 0.4\nliquidation_slippage = 0.1",
        ),
    )
    config = load_config(path)
    assert config.collateral.stress_drop == pytest.approx(0.4)
    assert config.collateral.liquidation_slippage == pytest.approx(0.1)


@pytest.mark.parametrize(
    ("key", "value"),
    [("stress_drop", "1.0"), ("stress_drop", "-0.1"), ("liquidation_slippage", "1.0")],
)
def test_config_rejects_invalid_stress_coverage_inputs(tmp_path, key, value):
    path = write_config(tmp_path, valid_toml().replace("require_top_up = false", f"require_top_up = false\n{key} = {value}"))
    with pytest.raises(ValueError, match=key):
        load_config(path)


def test_config_rejects_negative_contribution(tmp_path):
    path = write_config(tmp_path, valid_toml().replace("contribution = 100.0", "contribution = -1.0"))
    with pytest.raises(ValueError, match="contribution must be positive"):
        load_config(path)


def test_config_rejects_unsupported_decision_mode(tmp_path):
    path = write_config(tmp_path, valid_toml().replace("every_due_date", "once_after_payout"))
    with pytest.raises(ValueError, match="supports decision_mode='every_due_date'"):
        load_config(path)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("fixed_ratio = 0.5", "fixed_ratio = 1.2", "collateral ratios"),
        ("new_member_share = 0.5", "new_member_share = -0.1", "new_member_share"),
        ("runs = 2", "runs = 0", "runs must be positive"),
        ("risk_tolerance = 0.0", "risk_tolerance = -1.0", "risk_tolerance"),
        ("reserve_initial = 0.0", "reserve_initial = -1.0", "reserve_initial"),
    ],
)
def test_config_rejects_invalid_ranges(tmp_path, old, new, message):
    path = write_config(tmp_path, valid_toml().replace(old, new))
    with pytest.raises(ValueError, match=message):
        load_config(path)


def test_config_reports_missing_price_file(tmp_path):
    historical = valid_toml().replace(
        'source = "stress"\nscenario = "constant"',
        'source = "historical"\nfile = "missing.csv"\nstart_date = "2026-01-01"\nend_date = "2026-12-31"\nnormalize = true',
    )
    path = write_config(tmp_path, historical)
    with pytest.raises(FileNotFoundError, match="missing.csv"):
        load_config(path)


def test_config_accepts_forced_default_after_payout(tmp_path):
    path = write_config(
        tmp_path,
        valid_toml() + "\n[events]\nforced_defaults = [{position = 0, day = 1}]\n",
    )
    config = load_config(path)
    assert config.forced_defaults[0].position == 0
    assert config.forced_defaults[0].day == 1


def test_config_rejects_forced_default_before_payout(tmp_path):
    path = write_config(
        tmp_path,
        valid_toml() + "\n[events]\nforced_defaults = [{position = 1, day = 1}]\n",
    )
    with pytest.raises(ValueError, match="after recipient payout"):
        load_config(path)


def test_run_command_writes_complete_outputs_and_historical_metadata(tmp_path, capsys):
    prices = tmp_path / "prices.csv"
    prices.write_text(
        "date,close\n"
        + "".join(
            f"{(date(2026, 1, 1) + timedelta(days=i)).isoformat()},100\n"
            for i in range(61)
        ),
        encoding="utf-8",
    )
    historical = valid_toml().replace(
        'source = "stress"\nscenario = "constant"',
        'source = "historical"\nfile = "prices.csv"\nstart_date = "2026-01-01"\nend_date = "2026-03-02"\nnormalize = true',
    )
    config_path = write_config(tmp_path, historical)
    output = tmp_path / "results"

    assert main(["run", "--config", str(config_path), "--output", str(output)]) == 0

    assert {path.name for path in output.iterdir()} == {
        "config.toml",
        "metadata.json",
        "paired_results.csv",
        "recipient_results.csv",
        "run_results.csv",
        "summary.json",
    }
    with (output / "run_results.csv").open(newline="", encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == 4
    metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["price_source"] == "historical"
    assert metadata["price_file_sha256"]
    assert metadata["price_start_date"] == "2026-01-01"
    assert capsys.readouterr().out.strip().splitlines() == [str(output), "runs: 2"]


def test_fetch_command_requires_api_key_before_network(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("COINGECKO_API_KEY", raising=False)
    with pytest.raises(ValueError, match="COINGECKO_API_KEY"):
        main(
            [
                "fetch-prices",
                "--start",
                "2026-01-01",
                "--end",
                "2026-01-02",
                "--output",
                str(tmp_path / "prices.csv"),
            ]
        )


def test_fetch_command_reads_api_key_from_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("COINGECKO_API_KEY", raising=False)
    (tmp_path / ".env").write_text(
        "# CoinGecko Demo key\nCOINGECKO_API_KEY=CG-DEMO-FROM-FILE\n",
        encoding="utf-8",
    )
    output = tmp_path / "prices.csv"

    def fake_fetch(start, end, api_key, output_path):
        assert api_key == "CG-DEMO-FROM-FILE"
        output_path.write_text("date,close\n2026-01-01,100\n", encoding="utf-8")

    monkeypatch.setattr(cli, "fetch_coingecko_prices", fake_fetch)

    assert main(
        [
            "fetch-prices",
            "--start",
            "2026-01-01",
            "--end",
            "2026-01-02",
            "--output",
            str(output),
        ]
    ) == 0
    assert output.read_text(encoding="utf-8") == "date,close\n2026-01-01,100\n"


def test_fetch_binance_command_needs_no_key(tmp_path, monkeypatch):
    output = tmp_path / "eth.csv"

    def fake_fetch(start, end, output_path):
        assert start == date(2022, 5, 1)
        assert end == date(2022, 5, 2)
        output_path.write_text("date,close\n", encoding="utf-8")

    monkeypatch.setattr(cli, "fetch_binance_spot_prices", fake_fetch)
    assert main(
        [
            "fetch-binance-prices",
            "--start", "2022-05-01",
            "--end", "2022-05-02",
            "--output", str(output),
        ]
    ) == 0
    assert output.exists()


def test_sweep_compares_capped_collateral_on_same_six_member_shock(tmp_path):
    config_text = (
        valid_toml()
        .replace("members = 2", "members = 6")
        .replace("periods = 2", "periods = 6")
        .replace("runs = 2", "runs = 1")
        .replace("reputation_loss = 50.0", "reputation_loss = 10000.0")
        .replace("future_access_loss = 100.0", "future_access_loss = 10000.0")
        .replace("require_top_up = false", "require_top_up = false\nliquidation_slippage = 0.1")
        .replace('scenario = "constant"', 'scenario = "drop_40"')
        + "\n[events]\nforced_defaults = [{position = 0, day = 30}]\n"
    )
    config_path = write_config(tmp_path, config_text)
    output = tmp_path / "frontier"

    assert main(["sweep", "--config", str(config_path), "--output", str(output), "--ratios", "0.2", "0.5"]) == 0

    with (output / "frontier.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [float(row["ratio"]) for row in rows] == [0.2, 0.5]
    assert [float(row["mean_first_recipient_collateral_locked"]) for row in rows] == pytest.approx([100.0, 250.0])
    assert [float(row["mean_first_recipient_net_liquidity"]) for row in rows] == pytest.approx([500.0, 350.0])
    assert [float(row["mean_participant_shortfall"]) for row in rows] == pytest.approx([446.0, 365.0])
    assert [float(row["shortfall_run_rate"]) for row in rows] == pytest.approx([1.0, 1.0])
    left = list(csv.DictReader((output / "ratio-0.2" / "run_results.csv").open(newline="", encoding="utf-8")))[0]
    right = list(csv.DictReader((output / "ratio-0.5" / "run_results.csv").open(newline="", encoding="utf-8")))[0]
    assert (left["seed"], left["price_label"]) == (right["seed"], right["price_label"])


@pytest.mark.parametrize("ratios", [["-0.1"], ["1.1"], ["0.2", "0.2"]])
def test_sweep_rejects_invalid_or_duplicate_ratios(tmp_path, ratios):
    config_path = write_config(tmp_path, valid_toml())
    with pytest.raises(ValueError, match="ratios"):
        main(["sweep", "--config", str(config_path), "--output", str(tmp_path / "frontier"), "--ratios", *ratios])


def test_sweep_rejects_stress_coverage_floor_that_would_hide_ratio_changes(tmp_path):
    config_path = write_config(
        tmp_path,
        valid_toml().replace("require_top_up = false", "require_top_up = false\nstress_drop = 0.4"),
    )
    with pytest.raises(ValueError, match="stress_drop"):
        main(["sweep", "--config", str(config_path), "--output", str(tmp_path / "frontier"), "--ratios", "0.2", "0.5"])
