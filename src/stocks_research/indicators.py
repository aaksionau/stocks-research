from dataclasses import dataclass
from datetime import date

import pandas as pd

MOMENTUM_WINDOWS = (1, 5, 20)
MA_SHORT_WINDOW = 50
MA_LONG_WINDOW = 200
VOLUME_WINDOW = 20


@dataclass(frozen=True)
class IndicatorSnapshot:
    ticker: str
    date: date
    close: float
    momentum_1d: float | None
    momentum_5d: float | None
    momentum_20d: float | None
    ma_50: float | None
    ma_200: float | None
    ma_trend: str
    pct_above_ma50: float | None
    volume: int
    volume_avg_20: float | None
    volume_ratio: float | None
    score: float | None = None
    flagged: bool = False
    commentary: str | None = None


class IndicatorEngine:
    def compute_indicators(self, ticker: str, price_history: pd.DataFrame) -> IndicatorSnapshot:
        close = price_history["Close"]
        volume = price_history["Volume"]

        last_close = float(close.iloc[-1])
        last_volume = int(volume.iloc[-1])
        last_date = pd.Timestamp(price_history.index[-1]).date()

        momentum = {
            window: self._pct_change(close, window) for window in MOMENTUM_WINDOWS
        }

        ma_50 = self._sma(close, MA_SHORT_WINDOW)
        ma_200 = self._sma(close, MA_LONG_WINDOW)
        ma_trend = self._ma_trend(ma_50, ma_200)
        pct_above_ma50 = (
            (last_close - ma_50) / ma_50 * 100 if ma_50 is not None else None
        )

        volume_avg_20 = self._sma(volume, VOLUME_WINDOW)
        volume_ratio = (
            last_volume / volume_avg_20
            if volume_avg_20 is not None and volume_avg_20 != 0
            else None
        )

        return IndicatorSnapshot(
            ticker=ticker,
            date=last_date,
            close=last_close,
            momentum_1d=momentum[1],
            momentum_5d=momentum[5],
            momentum_20d=momentum[20],
            ma_50=ma_50,
            ma_200=ma_200,
            ma_trend=ma_trend,
            pct_above_ma50=pct_above_ma50,
            volume=last_volume,
            volume_avg_20=volume_avg_20,
            volume_ratio=volume_ratio,
        )

    @staticmethod
    def _pct_change(series: pd.Series, window: int) -> float | None:
        if len(series) <= window:
            return None
        previous = series.iloc[-1 - window]
        if previous == 0:
            return None
        return (series.iloc[-1] - previous) / previous * 100

    @staticmethod
    def _sma(series: pd.Series, window: int) -> float | None:
        if len(series) < window:
            return None
        return float(series.iloc[-window:].mean())

    @staticmethod
    def _ma_trend(ma_50: float | None, ma_200: float | None) -> str:
        if ma_50 is None or ma_200 is None:
            return "neutral"
        if ma_50 > ma_200:
            return "bullish"
        if ma_50 < ma_200:
            return "bearish"
        return "neutral"
