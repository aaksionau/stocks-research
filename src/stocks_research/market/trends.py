from dataclasses import dataclass
from datetime import date
from typing import Protocol, Sequence

from stocks_research.company.profile import CompanyProfile
from stocks_research.market import signals
from stocks_research.market.indicators import IndicatorSnapshot

DEFAULT_WINDOW_DAYS = 30
MAX_WINDOW_DAYS = 180

BUY_VERDICTS = frozenset({signals.STRONG_BUY, signals.BUY})


class BuySignalSnapshot(Protocol):
    """Structural type for whatever holds the price/trend fields `signals.evaluate()` needs.

    Satisfied by both the full `IndicatorSnapshot` and the lighter
    `SnapshotRepository.TrendIndicatorRow` the Trends page queries for.
    """

    ticker: str
    date: date
    close: float
    ma_200: float | None
    ma_trend: str
    pct_above_ma50: float | None
    pct_below_52w_high: float | None


@dataclass(frozen=True)
class TrendSummary:
    ticker: str
    buy_signal_count: int
    strong_buy_count: int
    days_considered: int
    last_buy_date: date


def summarize_buy_signal_trends(
    rows: Sequence[BuySignalSnapshot],
    profiles: dict[str, CompanyProfile],
    days: int = DEFAULT_WINDOW_DAYS,
) -> list[TrendSummary]:
    """Ranks tickers by how often their Buy Signal verdict was Strong Buy/Buy over the most recent `days`.

    Verdicts are recomputed here with `signals.evaluate()` using *today's* company profiles, not
    a stored historical verdict -- so this reflects current fundamentals applied to past price
    action, not what Overview actually displayed on that day. The window is anchored to the most
    recent date in `rows`, not to today's calendar date, so this is verifiable against a small
    seeded set of historical days without needing real time to pass.
    """
    distinct_dates = sorted({r.date for r in rows}, reverse=True)[:days]
    if not distinct_dates:
        return []

    window = set(distinct_dates)
    buy_dates_by_ticker: dict[str, list[date]] = {}
    strong_buy_counts: dict[str, int] = {}

    for row in rows:
        if row.date not in window:
            continue
        verdict = signals.evaluate(_to_indicator_snapshot(row), profiles.get(row.ticker)).verdict
        if verdict not in BUY_VERDICTS:
            continue
        buy_dates_by_ticker.setdefault(row.ticker, []).append(row.date)
        if verdict == signals.STRONG_BUY:
            strong_buy_counts[row.ticker] = strong_buy_counts.get(row.ticker, 0) + 1

    summaries = [
        TrendSummary(
            ticker=ticker,
            buy_signal_count=len(dates),
            strong_buy_count=strong_buy_counts.get(ticker, 0),
            days_considered=len(distinct_dates),
            last_buy_date=max(dates),
        )
        for ticker, dates in buy_dates_by_ticker.items()
    ]

    return sorted(
        summaries, key=lambda t: (t.buy_signal_count, t.strong_buy_count), reverse=True
    )


def _to_indicator_snapshot(row: BuySignalSnapshot) -> IndicatorSnapshot:
    return IndicatorSnapshot(
        ticker=row.ticker,
        date=row.date,
        close=row.close,
        momentum_1d=None,
        momentum_5d=None,
        momentum_20d=None,
        ma_50=None,
        ma_200=row.ma_200,
        ma_trend=row.ma_trend,
        pct_above_ma50=row.pct_above_ma50,
        volume=0,
        volume_avg_20=None,
        volume_ratio=None,
        pct_below_52w_high=row.pct_below_52w_high,
    )
