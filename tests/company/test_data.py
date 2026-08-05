import pytest

from stocks_research.company.data import CompanyProfileClient


class FakeYfTicker:
    def __init__(self, symbol: str):
        self.symbol = symbol

    @property
    def info(self) -> dict:
        if self.symbol == "RAISES":
            raise ConnectionError("network unreachable")
        if self.symbol == "EMPTY":
            return {}
        return {
            "longName": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "longBusinessSummary": "Apple designs, manufactures, and markets smartphones.",
            "website": "https://www.apple.com",
            "fullTimeEmployees": 164000,
            "country": "United States",
            "exchange": "NMS",
            "marketCap": 3_000_000_000_000,
            "trailingPE": 28.5,
            "forwardPE": 25.1,
            "pegRatio": 1.9,
            "priceToBook": 45.2,
            "returnOnEquity": 1.5,
            "profitMargins": 0.25,
            "debtToEquity": 150.0,
            "earningsGrowth": 0.08,
            "revenueGrowth": 0.05,
        }


@pytest.fixture(autouse=True)
def patch_yf_ticker(monkeypatch):
    monkeypatch.setattr("stocks_research.company.data.yf.Ticker", FakeYfTicker)


def test_fetch_profiles_maps_info_fields():
    profiles = CompanyProfileClient().fetch_profiles(["AAPL"])

    profile = profiles["AAPL"]
    assert profile.ticker == "AAPL"
    assert profile.name == "Apple Inc."
    assert profile.sector == "Technology"
    assert profile.industry == "Consumer Electronics"
    assert profile.description == "Apple designs, manufactures, and markets smartphones."
    assert profile.website == "https://www.apple.com"
    assert profile.employees == 164000
    assert profile.country == "United States"
    assert profile.exchange == "NMS"
    assert profile.market_cap == 3_000_000_000_000
    assert profile.trailing_pe == 28.5
    assert profile.forward_pe == 25.1
    assert profile.peg_ratio == 1.9
    assert profile.price_to_book == 45.2
    assert profile.return_on_equity == 1.5
    assert profile.profit_margins == 0.25
    assert profile.debt_to_equity == 150.0
    assert profile.earnings_growth == 0.08
    assert profile.revenue_growth == 0.05


def test_failed_ticker_fetch_is_skipped_not_fatal():
    profiles = CompanyProfileClient().fetch_profiles(["AAPL", "RAISES", "MSFT"])

    assert set(profiles.keys()) == {"AAPL", "MSFT"}


def test_empty_info_is_skipped():
    profiles = CompanyProfileClient().fetch_profiles(["AAPL", "EMPTY"])

    assert set(profiles.keys()) == {"AAPL"}


def test_all_tickers_failing_returns_empty_dict():
    profiles = CompanyProfileClient().fetch_profiles(["RAISES", "EMPTY"])

    assert profiles == {}
