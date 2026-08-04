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

    def compute_indicator_history(self, ticker: str, price_history: pd.DataFrame) -> list[IndicatorSnapshot]:
        """One IndicatorSnapshot per row of price_history, each computed as if that row were "today"."""
        close = price_history["Close"]
        volume = price_history["Volume"]

        momentum = {
            window: self._pct_change_series(close, window) for window in MOMENTUM_WINDOWS
        }
        ma_50 = self._sma_series(close, MA_SHORT_WINDOW)
        ma_200 = self._sma_series(close, MA_LONG_WINDOW)
        pct_above_ma50 = (close - ma_50) / ma_50 * 100

        volume_avg_20 = self._sma_series(volume, VOLUME_WINDOW)
        volume_ratio = (volume / volume_avg_20).mask(volume_avg_20 == 0)

        snapshots = []
        for position, timestamp in enumerate(price_history.index):
            ma_50_value = self._to_optional(ma_50.iloc[position])
            ma_200_value = self._to_optional(ma_200.iloc[position])
            snapshots.append(
                IndicatorSnapshot(
                    ticker=ticker,
                    date=pd.Timestamp(timestamp).date(),
                    close=float(close.iloc[position]),
                    momentum_1d=self._to_optional(momentum[1].iloc[position]),
                    momentum_5d=self._to_optional(momentum[5].iloc[position]),
                    momentum_20d=self._to_optional(momentum[20].iloc[position]),
                    ma_50=ma_50_value,
                    ma_200=ma_200_value,
                    ma_trend=self._ma_trend(ma_50_value, ma_200_value),
                    pct_above_ma50=self._to_optional(pct_above_ma50.iloc[position]),
                    volume=int(volume.iloc[position]),
                    volume_avg_20=self._to_optional(volume_avg_20.iloc[position]),
                    volume_ratio=self._to_optional(volume_ratio.iloc[position]),
                )
            )
        return snapshots

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
    def _pct_change_series(series: pd.Series, window: int) -> pd.Series:
        previous = series.shift(window)
        return ((series - previous) / previous * 100).mask(previous == 0)

    @staticmethod
    def _sma_series(series: pd.Series, window: int) -> pd.Series:
        return series.rolling(window=window, min_periods=window).mean()

    @staticmethod
    def _to_optional(value: float) -> float | None:
        return None if pd.isna(value) else float(value)

    @staticmethod
    def _ma_trend(ma_50: float | None, ma_200: float | None) -> str:
        if ma_50 is None or ma_200 is None:
            return "neutral"
        if ma_50 > ma_200:
            return "bullish"
        if ma_50 < ma_200:
            return "bearish"
        return "neutral"
