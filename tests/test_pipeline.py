from datetime import date

import pandas as pd
import pytest

from stocks_research import pipeline
from stocks_research.indicators import IndicatorSnapshot


def make_snapshot(ticker: str) -> IndicatorSnapshot:
    return IndicatorSnapshot(
        ticker=ticker,
        date=date(2020, 1, 1),
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
    )


class FakeMarketDataClient:
    def __init__(self, histories: dict[str, pd.DataFrame]):
        self._histories = histories

    def fetch_price_history(self, tickers: list[str], period: str = "5y") -> dict[str, pd.DataFrame]:
        return self._histories


class FakeIndicatorEngine:
    def __init__(self, failing_tickers: set[str] = frozenset()):
        self._failing_tickers = failing_tickers

    def compute_indicators(self, ticker: str, history: pd.DataFrame) -> IndicatorSnapshot:
        if ticker in self._failing_tickers:
            raise ValueError(f"bad data for {ticker}")
        return make_snapshot(ticker)


class FakeSnapshotRepository:
    def __init__(self, fail_on_save: bool = False):
        self._fail_on_save = fail_on_save
        self.saved: list[IndicatorSnapshot] = []
        self.schema_ensured = False

    def ensure_schema(self) -> None:
        self.schema_ensured = True

    def save_snapshot(self, snapshot: IndicatorSnapshot) -> None:
        if self._fail_on_save:
            raise ConnectionError("Postgres unreachable")
        self.saved.append(snapshot)


def test_per_ticker_indicator_failure_is_skipped_not_fatal():
    histories = {"AAPL": pd.DataFrame(), "BADCO": pd.DataFrame()}
    repository = FakeSnapshotRepository()

    pipeline.run(
        market_data=FakeMarketDataClient(histories),
        engine=FakeIndicatorEngine(failing_tickers={"BADCO"}),
        repository=repository,
    )

    assert [s.ticker for s in repository.saved] == ["AAPL"]


def test_no_price_history_at_all_raises_pipeline_failed_error():
    repository = FakeSnapshotRepository()

    with pytest.raises(pipeline.PipelineFailedError):
        pipeline.run(
            market_data=FakeMarketDataClient({}),
            engine=FakeIndicatorEngine(),
            repository=repository,
        )


def test_repository_failure_propagates_and_aborts_run():
    histories = {"AAPL": pd.DataFrame(), "MSFT": pd.DataFrame()}
    repository = FakeSnapshotRepository(fail_on_save=True)

    with pytest.raises(ConnectionError):
        pipeline.run(
            market_data=FakeMarketDataClient(histories),
            engine=FakeIndicatorEngine(),
            repository=repository,
        )
