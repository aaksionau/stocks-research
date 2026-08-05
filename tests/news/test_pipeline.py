from collections import defaultdict
from datetime import date, datetime, timezone

from stocks_research.news import pipeline as news_pipeline
from stocks_research.news.data import NewsArticle


def make_article(ticker: str, headline: str = "headline", day: str = "2024-01-01") -> NewsArticle:
    return NewsArticle(
        ticker=ticker,
        headline=headline,
        summary="summary",
        url=f"https://example.com/{ticker}/{headline}",
        source="Reuters",
        published_at=datetime.fromisoformat(f"{day}T12:00:00+00:00"),
    )


class FakeNewsClient:
    def __init__(self, articles: list[NewsArticle]):
        self._articles = articles
        self.calls: list[tuple[list[str], date, date]] = []

    def fetch_news(self, tickers: list[str], from_date: date, to_date: date) -> list[NewsArticle]:
        self.calls.append((tickers, from_date, to_date))
        return self._articles


class FakeNewsSentimentClient:
    def __init__(self, scores_by_ticker: dict[str, list[float]] | None = None, fail_tickers: set[str] | None = None):
        self._scores_by_ticker = scores_by_ticker or {}
        self._fail_tickers = fail_tickers or set()
        self.calls: list[tuple[str, list[str]]] = []

    def score_headlines(self, ticker: str, headlines: list[str]) -> list[float]:
        self.calls.append((ticker, headlines))
        if ticker in self._fail_tickers:
            raise RuntimeError(f"scoring failed for {ticker}")
        return self._scores_by_ticker[ticker]


class FakeNewsRepository:
    """Fake standing in for Postgres: fetched articles land straight in `saved_articles`, mirroring the real repo."""

    def __init__(self, subscribed_tickers: list[str] | None = None):
        self.saved_articles: list[NewsArticle] = []
        self.saved_scores: list[NewsArticle] = []
        self.schema_ensured = False
        self._subscribed_tickers = subscribed_tickers if subscribed_tickers is not None else ["AAPL", "MSFT"]

    def ensure_schema(self) -> None:
        self.schema_ensured = True

    def get_subscribed_tickers(self) -> list[str]:
        return self._subscribed_tickers

    def save_articles(self, articles: list[NewsArticle]) -> None:
        self.saved_articles.extend(articles)

    def get_unscored_articles_by_ticker_and_day(self) -> dict[tuple[str, date], list[NewsArticle]]:
        groups: dict[tuple[str, date], list[NewsArticle]] = defaultdict(list)
        for article in self.saved_articles:
            groups[(article.ticker, article.published_at.date())].append(article)
        return groups

    def save_sentiment_scores(self, articles: list[NewsArticle]) -> None:
        self.saved_scores.extend(articles)


def test_run_ensures_schema_before_fetching():
    repository = FakeNewsRepository()

    news_pipeline.run(
        news_client=FakeNewsClient([]),
        sentiment_client=FakeNewsSentimentClient(),
        repository=repository,
    )

    assert repository.schema_ensured is True


def test_run_fetches_and_saves_articles_for_subscribed_tickers():
    articles = [make_article("AAPL"), make_article("MSFT")]
    repository = FakeNewsRepository(subscribed_tickers=["AAPL", "MSFT"])
    news_client = FakeNewsClient(articles)

    news_pipeline.run(
        news_client=news_client,
        sentiment_client=FakeNewsSentimentClient(scores_by_ticker={"AAPL": [0.1], "MSFT": [0.2]}),
        repository=repository,
    )

    assert repository.saved_articles == articles
    assert len(news_client.calls) == 1
    assert news_client.calls[0][0] == ["AAPL", "MSFT"]


def test_run_with_no_subscribed_tickers_skips_fetch():
    repository = FakeNewsRepository(subscribed_tickers=[])
    news_client = FakeNewsClient([make_article("AAPL")])
    sentiment_client = FakeNewsSentimentClient()

    news_pipeline.run(
        news_client=news_client,
        sentiment_client=sentiment_client,
        repository=repository,
    )

    assert repository.schema_ensured is True
    assert news_client.calls == []
    assert repository.saved_articles == []
    assert sentiment_client.calls == []


def test_run_scores_newly_fetched_articles_in_a_single_batched_call():
    articles = [make_article("AAPL", "Headline 1"), make_article("AAPL", "Headline 2")]
    repository = FakeNewsRepository()
    sentiment_client = FakeNewsSentimentClient(scores_by_ticker={"AAPL": [0.5, -0.1]})

    news_pipeline.run(
        news_client=FakeNewsClient(articles),
        sentiment_client=sentiment_client,
        repository=repository,
    )

    assert [a.sentiment_score for a in repository.saved_scores] == [0.5, -0.1]
    assert len(sentiment_client.calls) == 1
    ticker, headlines = sentiment_client.calls[0]
    assert ticker == "AAPL"
    assert headlines == ["Headline 1", "Headline 2"]


def test_run_with_no_articles_fetched_makes_no_scoring_calls():
    repository = FakeNewsRepository()
    sentiment_client = FakeNewsSentimentClient()

    news_pipeline.run(
        news_client=FakeNewsClient([]),
        sentiment_client=sentiment_client,
        repository=repository,
    )

    assert repository.saved_articles == []
    assert sentiment_client.calls == []
    assert repository.saved_scores == []


def test_run_skips_failing_ticker_day_scoring_batch_not_fatal():
    articles = [make_article("AAPL", "Headline 1"), make_article("MSFT", "Headline 2")]
    repository = FakeNewsRepository()
    sentiment_client = FakeNewsSentimentClient(
        scores_by_ticker={"MSFT": [0.2]}, fail_tickers={"AAPL"}
    )

    news_pipeline.run(
        news_client=FakeNewsClient(articles),
        sentiment_client=sentiment_client,
        repository=repository,
    )

    # Both articles were still fetched and persisted; only AAPL's scoring failed.
    assert {a.ticker for a in repository.saved_articles} == {"AAPL", "MSFT"}
    assert [a.ticker for a in repository.saved_scores] == ["MSFT"]
