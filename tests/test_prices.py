from datetime import date
from datetime import timedelta
from io import BytesIO
import json
import random
from zipfile import ZipFile

import pytest

from rosca_sim.prices import (
    PricePoint,
    fetch_coingecko_prices,
    fetch_binance_spot_prices,
    load_price_csv,
    make_stress_path,
    sample_historical_path,
)


def test_load_price_csv_rejects_duplicate_dates(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text("date,close\n2026-01-01,100\n2026-01-01,101\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate date"):
        load_price_csv(path, date(2026, 1, 1), date(2026, 1, 2))


def test_load_price_csv_rejects_nonpositive_prices(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text("date,close\n2026-01-01,0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="positive"):
        load_price_csv(path, date(2026, 1, 1), date(2026, 1, 1))


def test_historical_path_uses_exact_period_spacing_and_normalizes(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text(
        "date,close\n2026-01-01,100\n2026-01-02,110\n2026-01-03,121\n",
        encoding="utf-8",
    )
    points = load_price_csv(path, date(2026, 1, 1), date(2026, 1, 3))
    result = sample_historical_path(points, periods=3, period_days=1, rng=random.Random(7))
    assert result.prices == pytest.approx((1.0, 1.1, 1.21))


def test_historical_path_rejects_missing_required_date(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text("date,close\n2026-01-01,100\n2026-01-03,121\n", encoding="utf-8")
    points = load_price_csv(path, date(2026, 1, 1), date(2026, 1, 3))
    with pytest.raises(ValueError, match="no complete historical window"):
        sample_historical_path(points, periods=3, period_days=1, rng=random.Random(7))


def test_historical_daily_dip_survives_due_date_sampling(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text(
        "date,close\n"
        + "\n".join(
            f"2026-01-{day:02d},{50 if day == 16 else 100}"
            for day in range(1, 32)
        )
        + "\n",
        encoding="utf-8",
    )
    points = load_price_csv(path, date(2026, 1, 1), date(2026, 1, 31))
    result = sample_historical_path(points, 2, 30, random.Random(7))
    assert result.prices == (1.0, 1.0)
    assert result.daily_prices[15] == 0.5


def test_historical_window_can_be_pinned(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text(
        "date,close\n2022-05-01,100\n2022-05-02,80\n2022-05-03,70\n",
        encoding="utf-8",
    )
    points = load_price_csv(path, date(2022, 5, 1), date(2022, 5, 3))
    result = sample_historical_path(
        points, 2, 1, random.Random(7), window_start=date(2022, 5, 2)
    )
    assert result.start_date == "2022-05-02"
    assert result.prices == pytest.approx((1.0, 0.875))


@pytest.mark.parametrize(
    ("scenario", "last"),
    [("constant", 1.0), ("drop_20", 0.8), ("drop_40", 0.6), ("drop_60", 0.4)],
)
def test_stress_path_endpoints(scenario, last):
    path = make_stress_path(scenario, periods=10)
    assert len(path.prices) == 10
    assert path.prices[0] == pytest.approx(1.0)
    assert path.prices[-1] == pytest.approx(last)


def test_gradual_and_crash_paths_have_expected_shape():
    gradual = make_stress_path("gradual_decline", periods=5)
    crash = make_stress_path("rise_then_crash", periods=5)
    assert gradual.prices == pytest.approx((1.0, 0.9, 0.8, 0.7, 0.6))
    assert max(crash.prices) == pytest.approx(1.3)
    assert crash.prices[-1] == pytest.approx(0.6)


def test_grace_tail_requires_complete_daily_history():
    start = date(2020, 1, 1)
    points = tuple(PricePoint(start + timedelta(days=i), 100.0) for i in range(165))
    path = sample_historical_path(points, 6, 30, random.Random(1), extra_days=14)
    assert len(path.prices) == 6
    assert len(path.daily_prices) == 165
    with pytest.raises(ValueError, match="no complete historical window"):
        sample_historical_path(points[:-1], 6, 30, random.Random(1), extra_days=14)


def test_stress_path_grace_tail_and_negative_rejection():
    path = make_stress_path("constant", 6, 30, extra_days=14)
    assert len(path.prices) == 6
    assert len(path.daily_prices) == 165
    with pytest.raises(ValueError, match="extra_days"):
        make_stress_path("constant", 6, 30, extra_days=-1)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_coingecko_fetch_writes_daily_csv(tmp_path):
    def opener(_request, timeout):
        assert timeout == 30
        return FakeResponse({"prices": [[1767225600000, 3000.0], [1767312000000, 3060.0]]})

    output = tmp_path / "eth.csv"
    fetch_coingecko_prices(
        date(2026, 1, 1), date(2026, 1, 2), "secret", output, opener=opener
    )
    assert output.read_text(encoding="utf-8").splitlines() == [
        "date,close",
        "2026-01-01,3000.0",
        "2026-01-02,3060.0",
    ]


def test_coingecko_fetch_uses_last_observation_as_daily_close(tmp_path):
    def opener(_request, timeout):
        return FakeResponse(
            {
                "prices": [
                    [1767225600000, 3000.0],
                    [1767268800000, 3030.0],
                    [1767312000000, 3060.0],
                ]
            }
        )

    output = tmp_path / "eth.csv"
    fetch_coingecko_prices(
        date(2026, 1, 1), date(2026, 1, 2), "secret", output, opener=opener
    )
    assert output.read_text(encoding="utf-8").splitlines() == [
        "date,close",
        "2026-01-01,3030.0",
        "2026-01-02,3060.0",
    ]


def test_coingecko_fetch_rejects_duplicate_timestamp(tmp_path):
    def opener(_request, timeout):
        return FakeResponse(
            {"prices": [[1767225600000, 3000.0], [1767225600000, 3001.0]]}
        )

    with pytest.raises(ValueError, match="duplicate timestamp"):
        fetch_coingecko_prices(
            date(2026, 1, 1),
            date(2026, 1, 2),
            "secret",
            tmp_path / "eth.csv",
            opener=opener,
        )


def test_binance_fetch_reads_daily_spot_archive(tmp_path):
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            "ETHUSDT-1d-2022-05.csv",
            "1651363200000,100,110,90,101,0\n"
            "1651449600000,101,111,91,99,0\n",
        )

    def opener(request, timeout):
        assert request.full_url.endswith("ETHUSDT-1d-2022-05.zip")
        assert timeout == 30
        return FakeResponseBytes(buffer.getvalue())

    output = tmp_path / "eth.csv"
    fetch_binance_spot_prices(
        date(2022, 5, 1), date(2022, 5, 2), output, opener=opener
    )
    assert output.read_text(encoding="utf-8").splitlines() == [
        "date,close",
        "2022-05-01,101.0",
        "2022-05-02,99.0",
    ]


class FakeResponseBytes(FakeResponse):
    def read(self):
        return self.payload
