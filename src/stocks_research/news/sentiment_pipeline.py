import logging
from dataclasses import replace

from stocks_research.news.repository import NewsRepository
from stocks_research.news.sentiment import NewsSentimentClient

logger = logging.getLogger(__name__)


def run(
    sentiment_client: NewsSentimentClient | None = None,
    repository: NewsRepository | None = None,
) -> None:
    sentiment_client = sentiment_client or NewsSentimentClient()
    repository = repository or NewsRepository()

    # Postgres unreachable raises here and aborts the run before any scoring happens.
    repository.ensure_schema()

    groups = repository.get_unscored_articles_by_ticker_and_day()

    total_unscored = sum(len(articles) for articles in groups.values())
    scored_count = 0
    for (ticker, day), articles in groups.items():
        try:
            scores = sentiment_client.score_headlines(ticker, [a.headline for a in articles])
            scored = [replace(article, sentiment_score=score) for article, score in zip(articles, scores)]
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
