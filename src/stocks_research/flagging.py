import statistics
from dataclasses import dataclass

from stocks_research.indicators import IndicatorSnapshot

FLAG_COUNT = 30


@dataclass(frozen=True)
class FlaggedTicker:
    ticker: str
    score: float
    rank: int


class Flagger:
    """Combines momentum, trend-strength, and volume-anomaly signals into one score per ticker."""

    def rank(self, snapshots: list[IndicatorSnapshot]) -> list[FlaggedTicker]:
        if not snapshots:
            return []

        momentum = self._zscores([self._safe_abs(s.momentum_20d) for s in snapshots])
        trend = self._zscores([self._safe_abs(s.pct_above_ma50) for s in snapshots])
        volume = self._zscores([self._volume_excess(s.volume_ratio) for s in snapshots])
        scores = [m + t + v for m, t, v in zip(momentum, trend, volume)]

        ranked = sorted(zip(snapshots, scores), key=lambda pair: pair[1], reverse=True)

        return [
            FlaggedTicker(ticker=snapshot.ticker, score=score, rank=i + 1)
            for i, (snapshot, score) in enumerate(ranked[:FLAG_COUNT])
        ]

    @staticmethod
    def _safe_abs(value: float | None) -> float:
        return abs(value) if value is not None else 0.0

    @staticmethod
    def _volume_excess(volume_ratio: float | None) -> float:
        return max(volume_ratio - 1, 0.0) if volume_ratio is not None else 0.0

    @staticmethod
    def _zscores(values: list[float]) -> list[float]:
        if len(values) < 2:
            return [0.0] * len(values)
        mean = statistics.mean(values)
        stdev = statistics.pstdev(values)
        if stdev == 0:
            return [0.0] * len(values)
        return [(v - mean) / stdev for v in values]
