from datetime import date

import pandas as pd

from stocks_research.market import backfill
from stocks_research.market.indicators import IndicatorSnapshot


def make_snapshot(ticker: str, day: int) -> IndicatorSnapshot:
    return IndicatorSnapshot(
        ticker=ticker,
        date=date(2020, 1, day),
        close=100.0 + day,
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
    )


class FakeMarketDataClient:
    def __init__(self, histories: dict[str, pd.DataFrame]):
        self._histories = histories
        self.requested_period: str | None = None

    def fetch_price_history(self, tickers: list[str], period: str = "5y") -> dict[str, pd.DataFrame]:
        self.requested_period = period
        return self._histories


class FakeIndicatorEngine:
    def __init__(self, failing_tickers: set[str] = frozenset()):
        self._failing_tickers = failing_tickers

    def compute_indicator_history(self, ticker: str, history: pd.DataFrame) -> list[IndicatorSnapshot]:
        if ticker in self._failing_tickers:
            raise ValueError(f"bad data for {ticker}")
        return [make_snapshot(ticker, day) for day in range(1, 4)]


class FakeSnapshotRepository:
    def __init__(self):
        self.saved: list[IndicatorSnapshot] = []
        self.schema_ensured = False

    def ensure_schema(self) -> None:
        self.schema_ensured = True

    def save_snapshot(self, snapshot: IndicatorSnapshot) -> None:
        self.saved.append(snapshot)


def test_backfill_saves_every_historical_snapshot_per_ticker():
    histories = {"AAPL": pd.DataFrame(), "MSFT": pd.DataFrame()}
    repository = FakeSnapshotRepository()

    backfill.run(
        market_data=FakeMarketDataClient(histories),
        engine=FakeIndicatorEngine(),
        repository=repository,
    )

    assert repository.schema_ensured is True
    assert len(repository.saved) == 6
    assert {s.ticker for s in repository.saved} == {"AAPL", "MSFT"}
    assert all(s.commentary is None and s.score is None and s.flagged is False for s in repository.saved)


def test_backfill_per_ticker_failure_is_skipped_not_fatal():
    histories = {"AAPL": pd.DataFrame(), "BADCO": pd.DataFrame()}
    repository = FakeSnapshotRepository()

    backfill.run(
        market_data=FakeMarketDataClient(histories),
        engine=FakeIndicatorEngine(failing_tickers={"BADCO"}),
        repository=repository,
    )

    assert {s.ticker for s in repository.saved} == {"AAPL"}


def test_backfill_passes_period_through_to_market_data():
    market_data = FakeMarketDataClient({"AAPL": pd.DataFrame()})
    repository = FakeSnapshotRepository()

    backfill.run(
        period="10y",
        market_data=market_data,
        engine=FakeIndicatorEngine(),
        repository=repository,
    )

    assert market_data.requested_period == "10y"
