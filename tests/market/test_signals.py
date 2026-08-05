from datetime import date

from stocks_research.company.profile import CompanyProfile
from stocks_research.market import signals
from stocks_research.market.indicators import IndicatorSnapshot


def build_snapshot(
    ticker: str = "TEST",
    close: float = 100.0,
    ma_50: float | None = 100.0,
    ma_200: float | None = 90.0,
    ma_trend: str = "bullish",
    pct_above_ma50: float | None = 0.0,
    pct_below_52w_high: float | None = 10.0,
) -> IndicatorSnapshot:
    return IndicatorSnapshot(
        ticker=ticker,
        date=date(2020, 1, 1),
        close=close,
        momentum_1d=None,
        momentum_5d=None,
        momentum_20d=None,
        ma_50=ma_50,
        ma_200=ma_200,
        ma_trend=ma_trend,
        pct_above_ma50=pct_above_ma50,
        volume=1_000_000,
        volume_avg_20=None,
        volume_ratio=None,
        pct_below_52w_high=pct_below_52w_high,
    )


def build_profile(
    ticker: str = "TEST",
    trailing_pe: float | None = 20.0,
    peg_ratio: float | None = 1.0,
    return_on_equity: float | None = 0.15,
    profit_margins: float | None = 0.10,
    debt_to_equity: float | None = 50.0,
    earnings_growth: float | None = 0.05,
) -> CompanyProfile:
    return CompanyProfile(
        ticker=ticker,
        name=None,
        sector=None,
        industry=None,
        description=None,
        website=None,
        employees=None,
        country=None,
        exchange=None,
        market_cap=None,
        trailing_pe=trailing_pe,
        forward_pe=None,
        peg_ratio=peg_ratio,
        price_to_book=None,
        return_on_equity=return_on_equity,
        profit_margins=profit_margins,
        debt_to_equity=debt_to_equity,
        earnings_growth=earnings_growth,
        revenue_growth=None,
    )


def checks_by_name(signal: signals.LongTermBuySignal) -> dict[str, signals.SignalCheck]:
    return {check.name: check for check in signal.checks}


def test_everything_healthy_is_strong_buy():
    signal = signals.evaluate(build_snapshot(), build_profile())

    assert signal.verdict == signals.STRONG_BUY
    assert all(check.passed for check in signal.checks)


def test_extended_above_ma50_misses_entry_timing_but_can_still_be_buy():
    snapshot = build_snapshot(pct_above_ma50=20.0)
    signal = signals.evaluate(snapshot, build_profile())

    checks = checks_by_name(signal)
    assert checks["Entry timing"].passed is False
    assert signal.verdict == signals.BUY


def test_bearish_trend_fails_trend_and_entry_timing():
    snapshot = build_snapshot(ma_trend="bearish", ma_50=80.0, ma_200=90.0)
    signal = signals.evaluate(snapshot, build_profile())

    checks = checks_by_name(signal)
    assert checks["Trend health"].passed is False
    assert checks["Entry timing"].passed is None


def test_neutral_trend_with_no_ma200_is_undecidable():
    snapshot = build_snapshot(ma_trend="neutral", ma_50=None, ma_200=None)
    signal = signals.evaluate(snapshot, build_profile())

    checks = checks_by_name(signal)
    assert checks["Trend health"].passed is None


def test_high_pe_and_peg_fail_valuation():
    signal = signals.evaluate(build_snapshot(), build_profile(trailing_pe=60.0, peg_ratio=3.0))

    checks = checks_by_name(signal)
    assert checks["Valuation"].passed is False


def test_missing_valuation_fields_is_undecidable():
    signal = signals.evaluate(build_snapshot(), build_profile(trailing_pe=None, peg_ratio=None))

    checks = checks_by_name(signal)
    assert checks["Valuation"].passed is None


def test_weak_quality_metrics_fail_quality():
    signal = signals.evaluate(
        build_snapshot(),
        build_profile(return_on_equity=0.02, profit_margins=-0.05, debt_to_equity=300.0, earnings_growth=-0.10),
    )

    checks = checks_by_name(signal)
    assert checks["Quality"].passed is False


def test_no_profile_leaves_valuation_and_quality_undecidable():
    signal = signals.evaluate(build_snapshot(), None)

    checks = checks_by_name(signal)
    assert checks["Valuation"].passed is None
    assert checks["Quality"].passed is None


def test_near_52w_high_fails_not_at_top():
    signal = signals.evaluate(build_snapshot(pct_below_52w_high=1.0), build_profile())

    checks = checks_by_name(signal)
    assert checks["Not at the top"].passed is False


def test_missing_52w_high_is_undecidable():
    signal = signals.evaluate(build_snapshot(pct_below_52w_high=None), build_profile())

    checks = checks_by_name(signal)
    assert checks["Not at the top"].passed is None


def test_fewer_than_two_decidable_checks_is_insufficient_data():
    snapshot = build_snapshot(ma_trend="neutral", ma_50=None, ma_200=None, pct_below_52w_high=None)
    signal = signals.evaluate(snapshot, None)

    assert signal.verdict == signals.INSUFFICIENT_DATA


def test_mostly_failing_checks_is_avoid():
    snapshot = build_snapshot(ma_trend="bearish", ma_50=80.0, ma_200=90.0, pct_below_52w_high=1.0)
    profile = build_profile(trailing_pe=60.0, peg_ratio=3.0, return_on_equity=0.15)
    signal = signals.evaluate(snapshot, profile)

    assert signal.verdict == signals.AVOID


def test_split_checks_is_hold():
    # Trend and valuation fail, quality and not-at-top pass: 2/4 decidable checks -> ratio 0.5.
    snapshot = build_snapshot(ma_trend="bearish", ma_50=80.0, ma_200=90.0, pct_below_52w_high=10.0)
    profile = build_profile(trailing_pe=60.0, peg_ratio=3.0)
    signal = signals.evaluate(snapshot, profile)

    assert signal.verdict == signals.HOLD
