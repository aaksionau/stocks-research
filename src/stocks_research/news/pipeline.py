import logging
from datetime import date, timedelta

from stocks_research.config import NEWS_TICKERS
from stocks_research.news.data import NewsClient
from stocks_research.news.repository import NewsRepository

logger = logging.getLogger(__name__)

LOOKBACK_DAYS = 7


def run(news_client: NewsClient | None = None, repository: NewsRepository | None = None) -> None:
    news_client = news_client or NewsClient()
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
