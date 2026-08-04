import pandas as pd
import pytest

from stocks_research.market.indicators import IndicatorEngine

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


def test_indicator_history_returns_one_snapshot_per_row():
    closes = [100.0 + i for i in range(25)]
    volumes = [1_000_000] * 25
    history = engine.compute_indicator_history("TEST", build_frame(closes, volumes))

    assert len(history) == 25
    assert [s.date for s in history] == [pd.Timestamp("2020-01-01").date() + pd.Timedelta(days=i) for i in range(25)]


def test_indicator_history_last_row_matches_compute_indicators():
    closes = [100.0] * 150 + [200.0] * 60
    volumes = [1_000_000] * 209 + [5_000_000]
    frame = build_frame(closes, volumes)

    single = engine.compute_indicators("TEST", frame)
    history = engine.compute_indicator_history("TEST", frame)
    last = history[-1]

    assert last.date == single.date
    assert last.close == pytest.approx(single.close)
    assert last.momentum_1d == pytest.approx(single.momentum_1d)
    assert last.momentum_5d == pytest.approx(single.momentum_5d)
    assert last.momentum_20d == pytest.approx(single.momentum_20d)
    assert last.ma_50 == pytest.approx(single.ma_50)
    assert last.ma_200 == pytest.approx(single.ma_200)
    assert last.ma_trend == single.ma_trend
    assert last.pct_above_ma50 == pytest.approx(single.pct_above_ma50)
    assert last.volume == single.volume
    assert last.volume_avg_20 == pytest.approx(single.volume_avg_20)
    assert last.volume_ratio == pytest.approx(single.volume_ratio)


def test_indicator_history_early_rows_have_none_indicators():
    closes = [100.0 + i for i in range(25)]
    volumes = [1_000_000] * 25
    history = engine.compute_indicator_history("TEST", build_frame(closes, volumes))

    first = history[0]
    assert first.momentum_1d is None
    assert first.momentum_5d is None
    assert first.momentum_20d is None
    assert first.ma_50 is None
    assert first.ma_200 is None
    assert first.ma_trend == "neutral"
    assert first.volume_avg_20 is None
    assert first.volume_ratio is None
