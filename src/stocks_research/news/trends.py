import statistics
from dataclasses import dataclass
from datetime import date

from stocks_research.news.data import NewsArticle

DEFAULT_WINDOW_DAYS = 30
DIRECTION_FLAT_THRESHOLD = 0.05


@dataclass(frozen=True)
class NewsSentimentTrend:
    ticker: str
    article_count: int
    avg_sentiment: float
    sentiment_direction: str
    last_published_date: date


def summarize_news_trends(
    articles: list[NewsArticle], days: int = DEFAULT_WINDOW_DAYS
) -> list[NewsSentimentTrend]:
    """Ranks tickers by news sentiment over the most recent `days` of data present.

    The window is anchored to the most recent published date in `articles`, not to
    today's calendar date, mirroring `market.trends.summarize_trends()` so this is
    verifiable against seeded historical dates without real time passing.
    """
    scored = [a for a in articles if a.sentiment_score is not None]

    distinct_dates = sorted({a.published_at.date() for a in scored}, reverse=True)[:days]
    if not distinct_dates:
        return []

    window = set(distinct_dates)
    by_ticker: dict[str, list[NewsArticle]] = {}
    for article in scored:
        if article.published_at.date() in window:
            by_ticker.setdefault(article.ticker, []).append(article)

    summaries = [
        NewsSentimentTrend(
            ticker=ticker,
            article_count=len(entries),
            avg_sentiment=statistics.mean(a.sentiment_score for a in entries),
            sentiment_direction=_sentiment_direction(entries),
            last_published_date=max(a.published_at.date() for a in entries),
        )
        for ticker, entries in by_ticker.items()
    ]

    return sorted(summaries, key=lambda t: (t.avg_sentiment, t.article_count), reverse=True)


def _sentiment_direction(entries: list[NewsArticle]) -> str:
    ordered = sorted(entries, key=lambda a: a.published_at)
    midpoint = len(ordered) // 2
    if midpoint == 0:
        return "flat"

    first_half_avg = statistics.mean(a.sentiment_score for a in ordered[:midpoint])
    second_half_avg = statistics.mean(a.sentiment_score for a in ordered[midpoint:])
    delta = second_half_avg - first_half_avg

    if delta > DIRECTION_FLAT_THRESHOLD:
        return "rising"
    if delta < -DIRECTION_FLAT_THRESHOLD:
        return "falling"
    return "flat"
