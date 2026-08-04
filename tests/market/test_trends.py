from datetime import date, timedelta

from stocks_research.market.indicators import IndicatorSnapshot
from stocks_research.market.trends import summarize_trends

BASE_DATE = date(2020, 1, 1)


def build_snapshot(
    ticker: str,
    day_offset: int,
    flagged: bool = True,
    score: float | None = 1.0,
) -> IndicatorSnapshot:
    return IndicatorSnapshot(
        ticker=ticker,
        date=BASE_DATE + timedelta(days=day_offset),
        close=100.0,
        momentum_1d=None,
        momentum_5d=None,
        momentum_20d=None,
        ma_50=None,
        ma_200=None,
        ma_trend="neutral",
        pct_above_ma50=None,
        volume=1_000_000,
        volume_avg_20=None,
        volume_ratio=None,
        score=score,
        flagged=flagged,
    )


def test_no_snapshots_returns_empty_list():
    assert summarize_trends([]) == []


def test_ticker_flagged_more_often_ranks_first():
    snapshots = [
        build_snapshot("FREQUENT", day_offset=0),
        build_snapshot("FREQUENT", day_offset=1),
        build_snapshot("FREQUENT", day_offset=2),
        build_snapshot("RARE", day_offset=0),
    ]

    ranked = summarize_trends(snapshots, days=30)

    assert [t.ticker for t in ranked] == ["FREQUENT", "RARE"]
    assert ranked[0].flag_count == 3
    assert ranked[1].flag_count == 1


def test_unflagged_snapshots_are_excluded():
    snapshots = [
        build_snapshot("FLAGGED", day_offset=0, flagged=True),
        build_snapshot("NEVER_FLAGGED", day_offset=0, flagged=False),
    ]

    ranked = summarize_trends(snapshots, days=30)

    assert [t.ticker for t in ranked] == ["FLAGGED"]


def test_window_is_anchored_to_most_recent_seeded_date_not_real_time():
    # Seeded entirely in the past; the window must still resolve relative to
    # the latest date present in the data, not datetime.now().
    old_date_offset = -5000
    snapshots = [
        build_snapshot("OLD", day_offset=old_date_offset),
        build_snapshot("OLD", day_offset=old_date_offset + 1),
        build_snapshot("RECENT", day_offset=old_date_offset + 2),
    ]

    ranked = summarize_trends(snapshots, days=2)

    assert {t.ticker for t in ranked} == {"OLD", "RECENT"}
    assert ranked[0].days_considered == 2


def test_days_window_excludes_older_flags():
    snapshots = [
        build_snapshot("TICKER", day_offset=0),
        build_snapshot("TICKER", day_offset=1),
        build_snapshot("TICKER", day_offset=2),
    ]

    ranked = summarize_trends(snapshots, days=1)

    assert ranked[0].flag_count == 1
    assert ranked[0].last_flagged_date == BASE_DATE + timedelta(days=2)


def test_avg_score_ignores_missing_scores():
    snapshots = [
        build_snapshot("TICKER", day_offset=0, score=None),
        build_snapshot("TICKER", day_offset=1, score=4.0),
        build_snapshot("TICKER", day_offset=2, score=6.0),
    ]

    ranked = summarize_trends(snapshots, days=30)

    assert ranked[0].avg_score == 5.0


def test_avg_score_is_none_when_all_scores_missing():
    snapshots = [build_snapshot("TICKER", day_offset=0, score=None)]

    ranked = summarize_trends(snapshots, days=30)

    assert ranked[0].avg_score is None


def test_higher_flag_count_beats_higher_avg_score():
    snapshots = [
        build_snapshot("HIGH_SCORE_ONCE", day_offset=0, score=100.0),
        build_snapshot("FLAGGED_TWICE", day_offset=0, score=1.0),
        build_snapshot("FLAGGED_TWICE", day_offset=1, score=1.0),
    ]

    ranked = summarize_trends(snapshots, days=30)

    assert ranked[0].ticker == "FLAGGED_TWICE"
