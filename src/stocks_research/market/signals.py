from dataclasses import dataclass

from stocks_research.company.profile import CompanyProfile
from stocks_research.market.indicators import IndicatorSnapshot

PULLBACK_BAND_LOW = -8.0
PULLBACK_BAND_HIGH = 5.0
MAX_TRAILING_PE = 40.0
MAX_PEG_RATIO = 2.0
MIN_RETURN_ON_EQUITY = 0.10
MIN_PROFIT_MARGINS = 0.0
MAX_DEBT_TO_EQUITY = 200.0
MIN_EARNINGS_GROWTH = 0.0
NOT_AT_TOP_THRESHOLD = 5.0

STRONG_BUY = "Strong Buy"
BUY = "Buy"
HOLD = "Hold"
AVOID = "Avoid"
INSUFFICIENT_DATA = "Insufficient Data"

MIN_DECIDABLE_CHECKS = 2


@dataclass(frozen=True)
class SignalCheck:
    name: str
    passed: bool | None
    detail: str


@dataclass(frozen=True)
class LongTermBuySignal:
    ticker: str
    verdict: str
    checks: list[SignalCheck]


def evaluate(snapshot: IndicatorSnapshot, profile: CompanyProfile | None) -> LongTermBuySignal:
    """Rule-based buy/avoid check for a single ticker, tuned for a multi-year hold.

    Each check is independently omittable when its inputs are missing (`passed=None`),
    rather than scoring a data gap as a failure. Entry timing is a bonus modifier on top
    of the four core checks, not itself required for a "Buy" verdict.
    """
    trend = _trend_health(snapshot)
    entry_timing = _entry_timing(snapshot, trend)
    valuation = _valuation(profile)
    quality = _quality(profile)
    not_at_top = _not_at_top(snapshot)

    core_checks = [trend, valuation, quality, not_at_top]
    verdict = _verdict(core_checks, entry_timing)

    return LongTermBuySignal(
        ticker=snapshot.ticker,
        verdict=verdict,
        checks=[trend, entry_timing, valuation, quality, not_at_top],
    )


def _verdict(core_checks: list[SignalCheck], entry_timing: SignalCheck) -> str:
    decidable = [c for c in core_checks if c.passed is not None]
    if len(decidable) < MIN_DECIDABLE_CHECKS:
        return INSUFFICIENT_DATA

    ratio = sum(1 for c in decidable if c.passed) / len(decidable)

    if ratio == 1.0 and entry_timing.passed:
        return STRONG_BUY
    if ratio >= 0.75:
        return BUY
    if ratio >= 0.5:
        return HOLD
    return AVOID


def _trend_health(snapshot: IndicatorSnapshot) -> SignalCheck:
    if snapshot.ma_trend == "neutral" or snapshot.ma_200 is None:
        return SignalCheck("Trend health", None, "Not enough history for a 200-day trend yet.")

    passed = snapshot.ma_trend == "bullish" and snapshot.close > snapshot.ma_200
    detail = f"MA trend {snapshot.ma_trend}, close {'above' if snapshot.close > snapshot.ma_200 else 'below'} MA200."
    return SignalCheck("Trend health", passed, detail)


def _entry_timing(snapshot: IndicatorSnapshot, trend: SignalCheck) -> SignalCheck:
    if not trend.passed or snapshot.pct_above_ma50 is None:
        return SignalCheck("Entry timing", None, "Only meaningful once the trend is healthy.")

    passed = PULLBACK_BAND_LOW <= snapshot.pct_above_ma50 <= PULLBACK_BAND_HIGH
    detail = f"{snapshot.pct_above_ma50:+.1f}% vs MA50 (target band {PULLBACK_BAND_LOW:.0f}% to {PULLBACK_BAND_HIGH:.0f}%)."
    return SignalCheck("Entry timing", passed, detail)


def _valuation(profile: CompanyProfile | None) -> SignalCheck:
    if profile is None or (profile.trailing_pe is None and profile.peg_ratio is None):
        return SignalCheck("Valuation", None, "No PE/PEG data available.")

    pe_ok = profile.trailing_pe is None or profile.trailing_pe < MAX_TRAILING_PE
    peg_ok = profile.peg_ratio is None or profile.peg_ratio < MAX_PEG_RATIO
    passed = pe_ok and peg_ok

    pe_text = f"PE {profile.trailing_pe:.1f}" if profile.trailing_pe is not None else "PE N/A"
    peg_text = f"PEG {profile.peg_ratio:.2f}" if profile.peg_ratio is not None else "PEG N/A"
    return SignalCheck("Valuation", passed, f"{pe_text}, {peg_text}.")


def _quality(profile: CompanyProfile | None) -> SignalCheck:
    fields = None if profile is None else (
        profile.return_on_equity,
        profile.profit_margins,
        profile.debt_to_equity,
        profile.earnings_growth,
    )
    if profile is None or all(value is None for value in fields):
        return SignalCheck("Quality", None, "No fundamentals data available.")

    roe_ok = profile.return_on_equity is None or profile.return_on_equity >= MIN_RETURN_ON_EQUITY
    margin_ok = profile.profit_margins is None or profile.profit_margins > MIN_PROFIT_MARGINS
    debt_ok = profile.debt_to_equity is None or profile.debt_to_equity < MAX_DEBT_TO_EQUITY
    growth_ok = profile.earnings_growth is None or profile.earnings_growth >= MIN_EARNINGS_GROWTH
    passed = roe_ok and margin_ok and debt_ok and growth_ok

    roe_text = f"ROE {profile.return_on_equity:.0%}" if profile.return_on_equity is not None else "ROE N/A"
    margin_text = f"margin {profile.profit_margins:.0%}" if profile.profit_margins is not None else "margin N/A"
    debt_text = f"D/E {profile.debt_to_equity:.0f}" if profile.debt_to_equity is not None else "D/E N/A"
    growth_text = (
        f"earnings growth {profile.earnings_growth:+.0%}" if profile.earnings_growth is not None else "growth N/A"
    )
    return SignalCheck("Quality", passed, f"{roe_text}, {margin_text}, {debt_text}, {growth_text}.")


def _not_at_top(snapshot: IndicatorSnapshot) -> SignalCheck:
    if snapshot.pct_below_52w_high is None:
        return SignalCheck("Not at the top", None, "Not enough history for a 52-week high yet.")

    passed = snapshot.pct_below_52w_high > NOT_AT_TOP_THRESHOLD
    detail = f"{snapshot.pct_below_52w_high:.1f}% below its 52-week high."
    return SignalCheck("Not at the top", passed, detail)
