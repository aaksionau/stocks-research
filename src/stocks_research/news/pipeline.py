import logging
from dataclasses import replace
from datetime import date, timedelta

from stocks_research.config import NEWS_TICKERS
from stocks_research.news.data import NewsClient
from stocks_research.news.repository import NewsRepository
from stocks_research.news.sentiment import NewsSentimentClient

logger = logging.getLogger(__name__)

LOOKBACK_DAYS = 7


def run(
    news_client: NewsClient | None = None,
    sentiment_client: NewsSentimentClient | None = None,
    repository: NewsRepository | None = None,
) -> None:
    news_client = news_client or NewsClient()
    sentiment_client = sentiment_client or NewsSentimentClient()
    repository = repository or NewsRepository()

    # Postgres unreachable raises here and aborts the run before any fetching happens.
    repository.ensure_schema()

    to_date = date.today()
    from_date = to_date - timedelta(days=LOOKBACK_DAYS)

    # Per-ticker fetch failures are logged and skipped inside NewsClient, not fatal here.
    articles = news_client.fetch_news(NEWS_TICKERS, from_date, to_date)
    repository.save_articles(articles)
    logger.info(
        "News fetch complete: saved %d articles for %d tickers", len(articles), len(NEWS_TICKERS)
    )

    _score_unscored_articles(sentiment_client, repository)


def _score_unscored_articles(sentiment_client: NewsSentimentClient, repository: NewsRepository) -> None:
    # Re-queries rather than scoring `articles` directly so any backlog left over from a
    # previous run's per-batch failures gets retried here too, not just this run's fetch.
    groups = repository.get_unscored_articles_by_ticker_and_day()
    total_unscored = sum(len(group) for group in groups.values())
    scored_count = 0
    for (ticker, day), group_articles in groups.items():
        try:
            scores = sentiment_client.score_headlines(ticker, [a.headline for a in group_articles])
            scored = [replace(a, sentiment_score=score) for a, score in zip(group_articles, scores)]
            repository.save_sentiment_scores(scored)
            scored_count += len(scored)
        except Exception:
            logger.exception("Failed to score sentiment for %s on %s", ticker, day)

    logger.info(
        "Sentiment scoring complete: scored %d/%d unscored articles across %d ticker/day batches",
        scored_count, total_unscored, len(groups),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
