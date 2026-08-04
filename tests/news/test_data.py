from datetime import date

import pytest

from stocks_research.news.data import NewsClient


class FakeResponse:
    def __init__(self, payload: list[dict], status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> list[dict]:
        return self._payload


def fake_get(url: str, params: dict, timeout: int):
    ticker = params["symbol"]
    if ticker == "RAISES":
        raise ConnectionError("network unreachable")
    if ticker == "EMPTY":
        return FakeResponse([])
    if ticker == "BADITEM":
        return FakeResponse(
            [
                {"headline": "missing url and datetime"},
                {
                    "headline": "ok",
                    "url": "https://example.com/ok",
                    "source": "Reuters",
                    "summary": "a valid item",
                    "datetime": 1700000000,
                },
            ]
        )
    return FakeResponse(
        [
            {
                "headline": "Headline 1",
                "url": "https://example.com/1",
                "source": "Reuters",
                "summary": "Summary 1",
                "datetime": 1700000000,
            },
            {
                "headline": "Headline 2",
                "url": "https://example.com/2",
                "source": "Bloomberg",
                "summary": "Summary 2",
                "datetime": 1700003600,
            },
        ]
    )


@pytest.fixture(autouse=True)
def patch_requests_get(monkeypatch):
    monkeypatch.setattr("stocks_research.news.data.requests.get", fake_get)


def test_fetch_news_returns_articles_for_ticker():
    articles = NewsClient(api_key="test").fetch_news(["AAPL"], date(2023, 1, 1), date(2023, 1, 10))

    assert len(articles) == 2
    assert articles[0].ticker == "AAPL"
    assert articles[0].headline == "Headline 1"
    assert articles[0].url == "https://example.com/1"
    assert articles[0].source == "Reuters"


def test_failed_ticker_fetch_is_skipped_not_fatal():
    articles = NewsClient(api_key="test").fetch_news(
        ["AAPL", "RAISES"], date(2023, 1, 1), date(2023, 1, 10)
    )

    assert {a.ticker for a in articles} == {"AAPL"}


def test_empty_response_is_skipped():
    articles = NewsClient(api_key="test").fetch_news(["EMPTY"], date(2023, 1, 1), date(2023, 1, 10))

    assert articles == []


def test_all_tickers_failing_returns_empty_list():
    articles = NewsClient(api_key="test").fetch_news(
        ["RAISES", "EMPTY"], date(2023, 1, 1), date(2023, 1, 10)
    )

    assert articles == []


def test_items_missing_required_fields_are_skipped():
    articles = NewsClient(api_key="test").fetch_news(["BADITEM"], date(2023, 1, 1), date(2023, 1, 10))

    assert len(articles) == 1
    assert articles[0].headline == "ok"
