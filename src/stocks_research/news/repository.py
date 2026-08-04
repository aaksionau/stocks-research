import psycopg

from stocks_research.config import DATABASE_URL
from stocks_research.news.data import NewsArticle

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS news_articles (
    ticker text NOT NULL,
    url text NOT NULL,
    headline text NOT NULL,
    summary text,
    source text,
    published_at timestamptz NOT NULL,
    PRIMARY KEY (ticker, url)
)
"""

UPSERT_SQL = """
INSERT INTO news_articles (ticker, url, headline, summary, source, published_at)
VALUES (%(ticker)s, %(url)s, %(headline)s, %(summary)s, %(source)s, %(published_at)s)
ON CONFLICT (ticker, url) DO UPDATE SET
    headline = EXCLUDED.headline,
    summary = EXCLUDED.summary,
    source = EXCLUDED.source,
    published_at = EXCLUDED.published_at
"""

RECENT_ARTICLES_SQL = """
SELECT ticker, url, headline, summary, source, published_at
FROM news_articles
WHERE ticker = %(ticker)s
ORDER BY published_at DESC
LIMIT %(limit)s
"""


class NewsRepository:
    def __init__(self, database_url: str = DATABASE_URL):
        self._database_url = database_url

    def ensure_schema(self) -> None:
        with psycopg.connect(self._database_url) as conn:
            conn.execute(CREATE_TABLE_SQL)

    def save_articles(self, articles: list[NewsArticle]) -> None:
        if not articles:
            return
        with psycopg.connect(self._database_url) as conn, conn.cursor() as cursor:
            cursor.executemany(UPSERT_SQL, [vars(article) for article in articles])

    def get_recent_articles(self, ticker: str, limit: int = 20) -> list[NewsArticle]:
        with psycopg.connect(self._database_url) as conn:
            rows = conn.execute(RECENT_ARTICLES_SQL, {"ticker": ticker, "limit": limit}).fetchall()
        return [self._row_to_article(row) for row in rows]

    @staticmethod
    def _row_to_article(row: tuple) -> NewsArticle:
        ticker, url, headline, summary, source, published_at = row
        return NewsArticle(
            ticker=ticker,
            headline=headline,
            summary=summary,
            url=url,
            source=source,
            published_at=published_at,
        )
