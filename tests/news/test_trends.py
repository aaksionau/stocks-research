from datetime import datetime, timedelta, timezone

import pytest

from stocks_research.news.data import NewsArticle
from stocks_research.news.trends import summarize_news_trends

BASE_DATETIME = datetime(2020, 1, 1, tzinfo=timezone.utc)


def build_article(
    ticker: str,
    day_offset: int,
    sentiment_score: float | None = 0.0,
    hour_offset: int = 0,
) -> NewsArticle:
    return NewsArticle(
        ticker=ticker,
        headline=f"{ticker} headline {day_offset}-{hour_offset}",
        summary="summary",
        url=f"https://example.com/{ticker}/{day_offset}/{hour_offset}",
        source="Reuters",
        published_at=BASE_DATETIME + timedelta(days=day_offset, hours=hour_offset),
        sentiment_score=sentiment_score,
    )


def test_no_articles_returns_empty_list():
    assert summarize_news_trends([]) == []


def test_ticker_with_higher_avg_sentiment_ranks_first():
    articles = [
        build_article("POSITIVE", day_offset=0, sentiment_score=0.8),
        build_article("POSITIVE", day_offset=1, sentiment_score=0.6),
        build_article("NEGATIVE", day_offset=0, sentiment_score=-0.5),
    ]

    ranked = summarize_news_trends(articles, days=30)

    assert [t.ticker for t in ranked] == ["POSITIVE", "NEGATIVE"]
    assert ranked[0].article_count == 2


def test_unscored_articles_are_excluded():
    articles = [
        build_article("SCORED", day_offset=0, sentiment_score=0.5),
        build_article("UNSCORED", day_offset=0, sentiment_score=None),
    ]

    ranked = summarize_news_trends(articles, days=30)

    assert [t.ticker for t in ranked] == ["SCORED"]


def test_avg_sentiment_is_computed_correctly():
    articles = [
        build_article("TICKER", day_offset=0, sentiment_score=0.2),
        build_article("TICKER", day_offset=1, sentiment_score=0.6),
    ]

    ranked = summarize_news_trends(articles, days=30)

    assert ranked[0].avg_sentiment == 0.4


@pytest.mark.parametrize(
    "scores, expected_direction",
    [
        ([-0.5, -0.4, 0.4, 0.5], "rising"),
        ([0.5, 0.4, -0.4, -0.5], "falling"),
        ([0.1, 0.12, 0.09, 0.11], "flat"),
        ([0.9], "flat"),
    ],
)
def test_sentiment_direction(scores, expected_direction):
    articles = [
        build_article("TICKER", day_offset=i, sentiment_score=score)
        for i, score in enumerate(scores)
    ]

    ranked = summarize_news_trends(articles, days=30)

    assert ranked[0].sentiment_direction == expected_direction


def test_window_is_anchored_to_most_recent_seeded_date_not_real_time():
    # Seeded entirely in the past; the window must still resolve relative to
    # the latest date present in the data, not datetime.now().
    old_day_offset = -5000
    articles = [
        build_article("OLD", day_offset=old_day_offset, sentiment_score=0.1),
        build_article("OLD", day_offset=old_day_offset + 1, sentiment_score=0.2),
        build_article("RECENT", day_offset=old_day_offset + 2, sentiment_score=0.3),
    ]

    ranked = summarize_news_trends(articles, days=2)

    assert {t.ticker for t in ranked} == {"OLD", "RECENT"}


def test_days_window_excludes_older_articles():
    articles = [
        build_article("TICKER", day_offset=0, sentiment_score=0.1),
        build_article("TICKER", day_offset=1, sentiment_score=0.2),
        build_article("TICKER", day_offset=2, sentiment_score=0.3),
    ]

    ranked = summarize_news_trends(articles, days=1)

    assert ranked[0].article_count == 1
    assert ranked[0].last_published_date == (BASE_DATETIME + timedelta(days=2)).date()
