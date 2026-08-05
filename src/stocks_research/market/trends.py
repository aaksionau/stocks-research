import statistics
from dataclasses import dataclass
from datetime import date
from typing import Protocol, Sequence

DEFAULT_WINDOW_DAYS = 30


class FlaggedSnapshot(Protocol):
    """Structural type for whatever holds a ticker's flag/score on a given date.

    Satisfied by both the full `IndicatorSnapshot` and the lighter
    `SnapshotRepository.TrendFlagRow` the Trends page queries for.
    """

    ticker: str
    date: date
    score: float | None
    flagged: bool


@dataclass(frozen=True)
class TrendSummary:
    ticker: str
    flag_count: int
    days_considered: int
    avg_score: float | None
    last_flagged_date: date


def summarize_trends(
    snapshots: Sequence[FlaggedSnapshot], days: int = DEFAULT_WINDOW_DAYS
) -> list[TrendSummary]:
    """Ranks tickers by how often they were flagged over the most recent `days` of data present.

    The window is anchored to the most recent date in `snapshots`, not to today's
    calendar date, so this is verifiable against a small seeded set of historical
    days without needing real time to pass.
    """
    distinct_dates = sorted({s.date for s in snapshots}, reverse=True)[:days]
    if not distinct_dates:
        return []

    window = set(distinct_dates)
    flagged_by_ticker: dict[str, list[FlaggedSnapshot]] = {}
    for snapshot in snapshots:
        if snapshot.flagged and snapshot.date in window:
            flagged_by_ticker.setdefault(snapshot.ticker, []).append(snapshot)

    summaries = [
        TrendSummary(
            ticker=ticker,
            flag_count=len(entries),
            days_considered=len(distinct_dates),
            avg_score=_average_score(entries),
            last_flagged_date=max(e.date for e in entries),
        )
        for ticker, entries in flagged_by_ticker.items()
    ]

    return sorted(
        summaries, key=lambda t: (t.flag_count, t.avg_score or 0.0), reverse=True
    )


def _average_score(entries: list[FlaggedSnapshot]) -> float | None:
    scores = [e.score for e in entries if e.score is not None]
    return statistics.mean(scores) if scores else None
