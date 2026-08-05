import psycopg

from stocks_research.config import DATABASE_URL

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS news_subscriptions (
    ticker text PRIMARY KEY,
    subscribed_at timestamptz NOT NULL DEFAULT now()
)
"""

SUBSCRIBE_SQL = """
INSERT INTO news_subscriptions (ticker)
VALUES (%(ticker)s)
ON CONFLICT (ticker) DO NOTHING
"""

UNSUBSCRIBE_SQL = """
DELETE FROM news_subscriptions WHERE ticker = %(ticker)s
"""

IS_SUBSCRIBED_SQL = """
SELECT 1 FROM news_subscriptions WHERE ticker = %(ticker)s
"""

SUBSCRIBED_TICKERS_SQL = """
SELECT ticker FROM news_subscriptions ORDER BY ticker
"""

SUBSCRIBED_TICKER_COUNT_SQL = """
SELECT count(*) FROM news_subscriptions
"""


class NewsSubscriptionRepository:
    def __init__(self, database_url: str = DATABASE_URL):
        self._database_url = database_url

    def ensure_schema(self) -> None:
        with psycopg.connect(self._database_url) as conn:
            conn.execute(CREATE_TABLE_SQL)

    def subscribe(self, ticker: str) -> None:
        with psycopg.connect(self._database_url) as conn:
            conn.execute(SUBSCRIBE_SQL, {"ticker": ticker})

    def unsubscribe(self, ticker: str) -> None:
        with psycopg.connect(self._database_url) as conn:
            conn.execute(UNSUBSCRIBE_SQL, {"ticker": ticker})

    def is_subscribed(self, ticker: str) -> bool:
        with psycopg.connect(self._database_url) as conn:
            row = conn.execute(IS_SUBSCRIBED_SQL, {"ticker": ticker}).fetchone()
        return row is not None

    def get_subscribed_tickers(self) -> list[str]:
        with psycopg.connect(self._database_url) as conn:
            rows = conn.execute(SUBSCRIBED_TICKERS_SQL).fetchall()
        return [row[0] for row in rows]

    def get_subscribed_ticker_count(self) -> int:
        with psycopg.connect(self._database_url) as conn:
            row = conn.execute(SUBSCRIBED_TICKER_COUNT_SQL).fetchone()
        return row[0]
