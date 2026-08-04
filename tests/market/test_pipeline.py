from datetime import date

import pandas as pd
import pytest

from stocks_research.market import pipeline
from stocks_research.market.indicators import IndicatorSnapshot


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

    def compute_indicator_history(self, ticker: str, history: pd.DataFrame) -> list[IndicatorSnapshot]:
        if ticker in self._failing_tickers:
            raise ValueError(f"bad data for {ticker}")
        return [make_snapshot(ticker), make_snapshot(ticker)]


class FakeCommentaryClient:
    def __init__(self, failing_tickers: set[str] = frozenset()):
        self._failing_tickers = failing_tickers
        self.calls: list[str] = []

    def generate_commentary(self, ticker: str, snapshot: IndicatorSnapshot) -> str:
        self.calls.append(ticker)
        if ticker in self._failing_tickers:
            raise ValueError(f"Foundry unreachable for {ticker}")
        return f"commentary for {ticker}"


class FakeSnapshotRepository:
    def __init__(self, fail_on_save: bool = False, has_snapshots: bool = True):
        self._fail_on_save = fail_on_save
        self._has_snapshots = has_snapshots
        self.saved: list[IndicatorSnapshot] = []
        self.schema_ensured = False

    def ensure_schema(self) -> None:
        self.schema_ensured = True

    def save_snapshot(self, snapshot: IndicatorSnapshot) -> None:
        if self._fail_on_save:
            raise ConnectionError("Postgres unreachable")
        self.saved.append(snapshot)

    def has_any_snapshots(self) -> bool:
        return self._has_snapshots


def test_per_ticker_indicator_failure_is_skipped_not_fatal():
    histories = {"AAPL": pd.DataFrame(), "BADCO": pd.DataFrame()}
    repository = FakeSnapshotRepository()

    pipeline.run(
        market_data=FakeMarketDataClient(histories),
        engine=FakeIndicatorEngine(failing_tickers={"BADCO"}),
        commentary_client=FakeCommentaryClient(),
        repository=repository,
    )

    assert [s.ticker for s in repository.saved] == ["AAPL"]


def test_backfills_from_fetched_history_when_no_snapshots_exist():
    histories = {"AAPL": pd.DataFrame(), "MSFT": pd.DataFrame()}
    repository = FakeSnapshotRepository(has_snapshots=False)

    pipeline.run(
        market_data=FakeMarketDataClient(histories),
        engine=FakeIndicatorEngine(),
        commentary_client=FakeCommentaryClient(),
        repository=repository,
    )

    # 2 backfilled rows per ticker from compute_indicator_history(), plus 1 today's row from compute_indicators().
    assert len([s for s in repository.saved if s.ticker == "AAPL"]) == 3
    assert len([s for s in repository.saved if s.ticker == "MSFT"]) == 3


def test_no_price_history_at_all_raises_pipeline_failed_error():
    repository = FakeSnapshotRepository()

    with pytest.raises(pipeline.PipelineFailedError):
        pipeline.run(
            market_data=FakeMarketDataClient({}),
            engine=FakeIndicatorEngine(),
            commentary_client=FakeCommentaryClient(),
            repository=repository,
        )


def test_repository_failure_propagates_and_aborts_run():
    histories = {"AAPL": pd.DataFrame(), "MSFT": pd.DataFrame()}
    repository = FakeSnapshotRepository(fail_on_save=True)

    with pytest.raises(ConnectionError):
        pipeline.run(
            market_data=FakeMarketDataClient(histories),
            engine=FakeIndicatorEngine(),
            commentary_client=FakeCommentaryClient(),
            repository=repository,
        )


def test_flagged_tickers_get_commentary_persisted_on_snapshot():
    histories = {"AAPL": pd.DataFrame(), "MSFT": pd.DataFrame()}
    repository = FakeSnapshotRepository()
    commentary_client = FakeCommentaryClient()

    pipeline.run(
        market_data=FakeMarketDataClient(histories),
        engine=FakeIndicatorEngine(),
        commentary_client=commentary_client,
        repository=repository,
    )

    saved_by_ticker = {s.ticker: s for s in repository.saved}
    assert saved_by_ticker["AAPL"].flagged is True
    assert saved_by_ticker["AAPL"].commentary == "commentary for AAPL"
    assert saved_by_ticker["MSFT"].commentary == "commentary for MSFT"


def test_commentary_failure_is_skipped_not_fatal():
    histories = {"AAPL": pd.DataFrame(), "MSFT": pd.DataFrame()}
    repository = FakeSnapshotRepository()
    commentary_client = FakeCommentaryClient(failing_tickers={"AAPL"})

    pipeline.run(
        market_data=FakeMarketDataClient(histories),
        engine=FakeIndicatorEngine(),
        commentary_client=commentary_client,
        repository=repository,
    )

    saved_by_ticker = {s.ticker: s for s in repository.saved}
    assert saved_by_ticker["AAPL"].flagged is True
    assert saved_by_ticker["AAPL"].commentary is None
    assert saved_by_ticker["MSFT"].commentary == "commentary for MSFT"


def test_unflagged_tickers_are_not_sent_for_commentary():
    histories = {f"T{i}": pd.DataFrame() for i in range(35)}
    repository = FakeSnapshotRepository()
    commentary_client = FakeCommentaryClient()

    pipeline.run(
        market_data=FakeMarketDataClient(histories),
        engine=FakeIndicatorEngine(),
        commentary_client=commentary_client,
        repository=repository,
    )

    flagged = [s for s in repository.saved if s.flagged]
    unflagged = [s for s in repository.saved if not s.flagged]
    assert unflagged, "expected some tickers to be unflagged with 35 candidates and a top-30 cutoff"
    assert set(commentary_client.calls) == {s.ticker for s in flagged}
    assert all(s.commentary is None for s in unflagged)
