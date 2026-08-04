import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone

import requests

from stocks_research.config import FINNHUB_API_KEY

logger = logging.getLogger(__name__)

FINNHUB_NEWS_URL = "https://finnhub.io/api/v1/company-news"


@dataclass(frozen=True)
class NewsArticle:
    ticker: str
    headline: str
    summary: str
    url: str
    source: str
    published_at: datetime


class NewsClient:
    def __init__(self, api_key: str | None = FINNHUB_API_KEY):
        self._api_key = api_key

    def fetch_news(self, tickers: list[str], from_date: date, to_date: date) -> list[NewsArticle]:
        articles = []
        for ticker in tickers:
            try:
                response = requests.get(
                    FINNHUB_NEWS_URL,
                    params={
                        "symbol": ticker,
                        "from": from_date.isoformat(),
                        "to": to_date.isoformat(),
                        "token": self._api_key,
                    },
                    timeout=10,
                )
                response.raise_for_status()
                payload = response.json()
            except Exception:
                logger.exception("Failed to fetch news for %s", ticker)
                continue

            for item in payload:
                article = self._to_article(ticker, item)
                if article is not None:
                    articles.append(article)
        return articles

    @staticmethod
    def _to_article(ticker: str, item: dict) -> NewsArticle | None:
        headline = item.get("headline")
        url = item.get("url")
        published = item.get("datetime")
        if not headline or not url or published is None:
            logger.warning("Skipping malformed news item for %s: %s", ticker, item)
            return None
        return NewsArticle(
            ticker=ticker,
            headline=headline,
            summary=item.get("summary", ""),
            url=url,
            source=item.get("source", ""),
            published_at=datetime.fromtimestamp(published, tz=timezone.utc),
        )
