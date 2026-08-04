from datetime import date, datetime, timezone

from stocks_research.news import pipeline as news_pipeline
from stocks_research.news.data import NewsArticle


def make_article(ticker: str) -> NewsArticle:
    return NewsArticle(
        ticker=ticker,
        headline=f"{ticker} headline",
        summary="summary",
        url=f"https://example.com/{ticker}",
        source="Reuters",
        published_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
    )


class FakeNewsClient:
    def __init__(self, articles: list[NewsArticle]):
        self._articles = articles
        self.calls: list[tuple[list[str], date, date]] = []

    def fetch_news(self, tickers: list[str], from_date: date, to_date: date) -> list[NewsArticle]:
        self.calls.append((tickers, from_date, to_date))
        return self._articles


class FakeNewsRepository:
    def __init__(self):
        self.saved: list[NewsArticle] = []
        self.schema_ensured = False

    def ensure_schema(self) -> None:
        self.schema_ensured = True

    def save_articles(self, articles: list[NewsArticle]) -> None:
        self.saved.extend(articles)


def test_run_ensures_schema_before_fetching():
    repository = FakeNewsRepository()

    news_pipeline.run(news_client=FakeNewsClient([]), repository=repository)

    assert repository.schema_ensured is True


def test_run_saves_fetched_articles_for_configured_watchlist():
    articles = [make_article("AAPL"), make_article("MSFT")]
    repository = FakeNewsRepository()
    news_client = FakeNewsClient(articles)

    news_pipeline.run(news_client=news_client, repository=repository)

    assert repository.saved == articles
    assert len(news_client.calls) == 1


def test_run_with_no_articles_saves_empty_list_not_fatal():
    repository = FakeNewsRepository()

    news_pipeline.run(news_client=FakeNewsClient([]), repository=repository)

    assert repository.saved == []
