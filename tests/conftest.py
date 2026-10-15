from datetime import date, timedelta
import hashlib
import shutil

import pytest

from rosca_sim import phase_a
from rosca_sim.prices import load_price_csv


@pytest.fixture(scope="session")
def phase_a_fixture(tmp_path_factory):
    root = tmp_path_factory.mktemp("phase-a-fixture")
    prices = root / "prices.csv"
    prices.write_text("date,close\n" + "".join(
        f"{date(2022, 1, 1) + timedelta(days=i)},2000\n" for i in range(158)), encoding="utf-8")
    paths = phase_a.phase_a_paths(load_price_csv(prices, date.min, date.max))
    directory = root / "study"
    fingerprint = phase_a.prepare_phase_a(paths, directory, {
        "source_label": "synthetic test only", "quote_asset": "USDT",
        "price_csv_sha256": hashlib.sha256(prices.read_bytes()).hexdigest()})
    for rate in phase_a.ANNUAL_RATES:
        for ratio in phase_a.COARSE_RATIOS:
            phase_a.run_phase_a_job(paths, rate, ratio, directory, fingerprint)
    phase_a.aggregate_phase_a(directory)
    return directory, prices


@pytest.fixture
def phase_a_copy(phase_a_fixture, tmp_path):
    directory, prices = phase_a_fixture
    copied = tmp_path / "study"
    shutil.copytree(directory, copied)
    csv = tmp_path / "prices.csv"
    shutil.copy2(prices, csv)
    return copied, csv
