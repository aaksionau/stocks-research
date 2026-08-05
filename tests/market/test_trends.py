from datetime import date, timedelta

from stocks_research.company.profile import CompanyProfile
from stocks_research.market.indicators import IndicatorSnapshot
from stocks_research.market.trends import summarize_buy_signal_trends

BASE_DATE = date(2020, 1, 1)

# Trend healthy, in the pullback entry band, and not at the 52-week high --
# combined with GOOD_PROFILE this is a Strong Buy by default.
GOOD_PROFILE = CompanyProfile(
    ticker="X",
    name=None,
    sector=None,
    industry=None,
    description=None,
    website=None,
    employees=None,
    country=None,
    exchange=None,
    market_cap=None,
    trailing_pe=15.0,
    peg_ratio=1.0,
    return_on_equity=0.15,
    profit_margins=0.10,
    debt_to_equity=50.0,
    earnings_growth=0.05,
)


def build_row(
    ticker: str,
    day_offset: int,
    ma_trend: str = "bullish",
    close: float = 100.0,
    ma_200: float | None = 90.0,
    pct_above_ma50: float | None = 2.0,
    pct_below_52w_high: float | None = 10.0,
) -> IndicatorSnapshot:
    return IndicatorSnapshot(
        ticker=ticker,
        date=BASE_DATE + timedelta(days=day_offset),
        close=close,
        momentum_1d=None,
        momentum_5d=None,
        momentum_20d=None,
        ma_50=None,
        ma_200=ma_200,
        ma_trend=ma_trend,
        pct_above_ma50=pct_above_ma50,
        volume=0,
        volume_avg_20=None,
        volume_ratio=None,
        pct_below_52w_high=pct_below_52w_high,
    )


def buy_row(ticker: str, day_offset: int) -> IndicatorSnapshot:
    """Ratio 0.75 (not_at_top fails) -- a Buy, not a Strong Buy, when grounded."""
    return build_row(ticker, day_offset, pct_below_52w_high=2.0)


def test_no_rows_returns_empty_list():
    assert summarize_buy_signal_trends([], {}) == []


def test_ticker_with_more_buy_signal_days_ranks_first():
    rows = [
        build_row("FREQUENT", day_offset=0),
        build_row("FREQUENT", day_offset=1),
        build_row("FREQUENT", day_offset=2),
        build_row("RARE", day_offset=0),
    ]
    profiles = {"FREQUENT": GOOD_PROFILE, "RARE": GOOD_PROFILE}

    ranked = summarize_buy_signal_trends(rows, profiles, days=30)

    assert [t.ticker for t in ranked] == ["FREQUENT", "RARE"]
    assert ranked[0].buy_signal_count == 3
    assert ranked[1].buy_signal_count == 1


def test_non_buy_verdicts_are_excluded():
    rows = [
        build_row("GROUNDED", day_offset=0),
        build_row("UNGROUNDED", day_offset=0),
    ]
    # UNGROUNDED has no profile -- price action alone caps the verdict at Hold,
    # so it must never count toward the trend even with a perfect snapshot.
    profiles = {"GROUNDED": GOOD_PROFILE}

    ranked = summarize_buy_signal_trends(rows, profiles, days=30)

    assert [t.ticker for t in ranked] == ["GROUNDED"]


def test_window_is_anchored_to_most_recent_seeded_date_not_real_time():
    old_date_offset = -5000
    rows = [
        build_row("OLD", day_offset=old_date_offset),
        build_row("OLD", day_offset=old_date_offset + 1),
        build_row("RECENT", day_offset=old_date_offset + 2),
    ]
    profiles = {"OLD": GOOD_PROFILE, "RECENT": GOOD_PROFILE}

    ranked = summarize_buy_signal_trends(rows, profiles, days=2)

    assert {t.ticker for t in ranked} == {"OLD", "RECENT"}
    assert ranked[0].days_considered == 2


def test_days_window_excludes_older_signals():
    rows = [
        build_row("TICKER", day_offset=0),
        build_row("TICKER", day_offset=1),
        build_row("TICKER", day_offset=2),
    ]
    profiles = {"TICKER": GOOD_PROFILE}

    ranked = summarize_buy_signal_trends(rows, profiles, days=1)

    assert ranked[0].buy_signal_count == 1
    assert ranked[0].last_buy_date == BASE_DATE + timedelta(days=2)


def test_strong_buy_count_breaks_ties_on_equal_buy_signal_count():
    rows = [
        build_row("STRONG", day_offset=0),
        build_row("STRONG", day_offset=1),
        buy_row("PLAIN", day_offset=0),
        buy_row("PLAIN", day_offset=1),
    ]
    profiles = {"STRONG": GOOD_PROFILE, "PLAIN": GOOD_PROFILE}

    ranked = summarize_buy_signal_trends(rows, profiles, days=30)

    assert [t.ticker for t in ranked] == ["STRONG", "PLAIN"]
    assert ranked[0].buy_signal_count == ranked[1].buy_signal_count == 2
    assert ranked[0].strong_buy_count == 2
    assert ranked[1].strong_buy_count == 0
