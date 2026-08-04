import pandas as pd
import pytest

from stocks_research.market.data import MarketDataClient


class FakeYfTicker:
    def __init__(self, symbol: str):
        self.symbol = symbol

    def history(self, period: str = "5y") -> pd.DataFrame:
        if self.symbol == "RAISES":
            raise ConnectionError("network unreachable")
        if self.symbol == "EMPTY":
            return pd.DataFrame()
        return pd.DataFrame({"Close": [1.0, 2.0], "Volume": [100, 200]})


@pytest.fixture(autouse=True)
def patch_yf_ticker(monkeypatch):
    monkeypatch.setattr("stocks_research.market.data.yf.Ticker", FakeYfTicker)


def test_failed_ticker_fetch_is_skipped_not_fatal():
    histories = MarketDataClient().fetch_price_history(["AAPL", "RAISES", "MSFT"])

    assert set(histories.keys()) == {"AAPL", "MSFT"}


def test_empty_history_is_skipped():
    histories = MarketDataClient().fetch_price_history(["AAPL", "EMPTY"])

    assert set(histories.keys()) == {"AAPL"}


def test_all_tickers_failing_returns_empty_dict():
    histories = MarketDataClient().fetch_price_history(["RAISES", "EMPTY"])

    assert histories == {}
