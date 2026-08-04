import pandas as pd
import pytest

from stocks_research.indicators import IndicatorEngine

engine = IndicatorEngine()


def build_frame(closes: list[float], volumes: list[int]) -> pd.DataFrame:
    index = pd.date_range("2020-01-01", periods=len(closes), freq="D")
    return pd.DataFrame({"Close": closes, "Volume": volumes}, index=index)


def test_momentum_windows_use_known_pct_change():
    closes = [100.0 + i for i in range(25)]  # 100 .. 124
    volumes = [1_000_000] * 25
    snapshot = engine.compute_indicators("TEST", build_frame(closes, volumes))

    assert snapshot.momentum_1d == pytest.approx((124 - 123) / 123 * 100)
    assert snapshot.momentum_5d == pytest.approx((124 - 119) / 119 * 100)
    assert snapshot.momentum_20d == pytest.approx((124 - 104) / 104 * 100)


def test_flat_series_has_zero_momentum():
    closes = [50.0] * 30
    volumes = [1_000_000] * 30
    snapshot = engine.compute_indicators("TEST", build_frame(closes, volumes))

    assert snapshot.momentum_1d == pytest.approx(0)
    assert snapshot.momentum_5d == pytest.approx(0)
    assert snapshot.momentum_20d == pytest.approx(0)


def test_too_short_series_returns_none_instead_of_raising():
    snapshot = engine.compute_indicators("TEST", build_frame([100.0], [1_000_000]))

    assert snapshot.momentum_1d is None
    assert snapshot.momentum_5d is None
    assert snapshot.momentum_20d is None
    assert snapshot.ma_50 is None
    assert snapshot.ma_200 is None
    assert snapshot.ma_trend == "neutral"
    assert snapshot.pct_above_ma50 is None
    assert snapshot.volume_avg_20 is None
    assert snapshot.volume_ratio is None


def test_bullish_crossover_when_ma50_above_ma200():
    closes = [100.0] * 150 + [200.0] * 50
    volumes = [1_000_000] * 200
    snapshot = engine.compute_indicators("TEST", build_frame(closes, volumes))

    assert snapshot.ma_200 == pytest.approx((150 * 100 + 50 * 200) / 200)
    assert snapshot.ma_50 == pytest.approx(200)
    assert snapshot.ma_trend == "bullish"


def test_bearish_crossover_when_ma50_below_ma200():
    closes = [200.0] * 150 + [100.0] * 50
    volumes = [1_000_000] * 200
    snapshot = engine.compute_indicators("TEST", build_frame(closes, volumes))

    assert snapshot.ma_200 == pytest.approx((150 * 200 + 50 * 100) / 200)
    assert snapshot.ma_50 == pytest.approx(100)
    assert snapshot.ma_trend == "bearish"


def test_insufficient_history_for_ma200_is_neutral():
    closes = [100.0] * 100
    volumes = [1_000_000] * 100
    snapshot = engine.compute_indicators("TEST", build_frame(closes, volumes))

    assert snapshot.ma_50 is not None
    assert snapshot.ma_200 is None
    assert snapshot.ma_trend == "neutral"


def test_volume_ratio_detects_spike():
    closes = [50.0] * 20
    volumes = [1_000_000] * 19 + [5_000_000]
    snapshot = engine.compute_indicators("TEST", build_frame(closes, volumes))

    expected_avg = (19 * 1_000_000 + 5_000_000) / 20
    assert snapshot.volume_avg_20 == pytest.approx(expected_avg)
    assert snapshot.volume_ratio == pytest.approx(5_000_000 / expected_avg)
