from datetime import datetime, timezone

from stocks_research.news import sentiment_pipeline
from stocks_research.news.data import NewsArticle


def make_article(ticker: str, headline: str, day: str, sentiment_score: float | None = None) -> NewsArticle:
    return NewsArticle(
        ticker=ticker,
        headline=headline,
        summary="summary",
        url=f"https://example.com/{ticker}/{headline}",
        source="Reuters",
        published_at=datetime.fromisoformat(f"{day}T12:00:00+00:00"),
        sentiment_score=sentiment_score,
    )


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
    def __init__(self, unscored: list[NewsArticle]):
        self._unscored = unscored
        self.saved: list[NewsArticle] = []
        self.schema_ensured = False

    def ensure_schema(self) -> None:
        self.schema_ensured = True

    def get_unscored_articles(self) -> list[NewsArticle]:
        return self._unscored

    def save_sentiment_scores(self, articles: list[NewsArticle]) -> None:
        self.saved.extend(articles)


def test_run_ensures_schema_before_scoring():
    repository = FakeNewsRepository([])

    sentiment_pipeline.run(sentiment_client=FakeNewsSentimentClient(), repository=repository)

    assert repository.schema_ensured is True


def test_run_batches_headlines_by_ticker_and_day_in_a_single_call():
    unscored = [
        make_article("AAPL", "Headline 1", "2024-01-01"),
        make_article("AAPL", "Headline 2", "2024-01-01"),
    ]
    repository = FakeNewsRepository(unscored)
    sentiment_client = FakeNewsSentimentClient(scores_by_ticker={"AAPL": [0.5, -0.1]})

    sentiment_pipeline.run(sentiment_client=sentiment_client, repository=repository)

    assert len(sentiment_client.calls) == 1
    ticker, headlines = sentiment_client.calls[0]
    assert ticker == "AAPL"
    assert headlines == ["Headline 1", "Headline 2"]


def test_run_writes_scores_back_to_matching_articles():
    unscored = [
        make_article("AAPL", "Headline 1", "2024-01-01"),
        make_article("AAPL", "Headline 2", "2024-01-01"),
    ]
    repository = FakeNewsRepository(unscored)
    sentiment_client = FakeNewsSentimentClient(scores_by_ticker={"AAPL": [0.5, -0.1]})

    sentiment_pipeline.run(sentiment_client=sentiment_client, repository=repository)

    assert [a.sentiment_score for a in repository.saved] == [0.5, -0.1]


def test_run_separates_batches_by_ticker_and_by_day():
    unscored = [
        make_article("AAPL", "AAPL day 1", "2024-01-01"),
        make_article("AAPL", "AAPL day 2", "2024-01-02"),
        make_article("MSFT", "MSFT headline", "2024-01-01"),
    ]
    repository = FakeNewsRepository(unscored)
    # Each call scores exactly one headline, proving AAPL's two days were split into separate batches.
    sentiment_client = FakeNewsSentimentClient(scores_by_ticker={"AAPL": [0.1], "MSFT": [0.2]})

    sentiment_pipeline.run(sentiment_client=sentiment_client, repository=repository)

    assert len(sentiment_client.calls) == 3
    assert all(len(headlines) == 1 for _, headlines in sentiment_client.calls)
    assert len(repository.saved) == 3


def test_run_with_no_unscored_articles_makes_no_calls():
    repository = FakeNewsRepository([])
    sentiment_client = FakeNewsSentimentClient()

    sentiment_pipeline.run(sentiment_client=sentiment_client, repository=repository)

    assert sentiment_client.calls == []
    assert repository.saved == []


def test_run_skips_failing_ticker_day_batch_not_fatal():
    unscored = [
        make_article("AAPL", "Headline 1", "2024-01-01"),
        make_article("MSFT", "Headline 2", "2024-01-01"),
    ]
    repository = FakeNewsRepository(unscored)
    sentiment_client = FakeNewsSentimentClient(
        scores_by_ticker={"MSFT": [0.2]}, fail_tickers={"AAPL"}
    )

    sentiment_pipeline.run(sentiment_client=sentiment_client, repository=repository)

    assert [a.ticker for a in repository.saved] == ["MSFT"]
