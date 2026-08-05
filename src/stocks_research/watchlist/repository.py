import psycopg

from stocks_research.config import DATABASE_URL

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS watchlist (
    ticker text PRIMARY KEY,
    followed_at timestamptz NOT NULL DEFAULT now()
)
"""

FOLLOW_SQL = """
INSERT INTO watchlist (ticker)
VALUES (%(ticker)s)
ON CONFLICT (ticker) DO NOTHING
"""

UNFOLLOW_SQL = """
DELETE FROM watchlist WHERE ticker = %(ticker)s
"""

IS_FOLLOWED_SQL = """
SELECT 1 FROM watchlist WHERE ticker = %(ticker)s
"""

FOLLOWED_TICKERS_SQL = """
SELECT ticker FROM watchlist ORDER BY ticker
"""


class WatchlistRepository:
    def __init__(self, database_url: str = DATABASE_URL):
        self._database_url = database_url

    def ensure_schema(self) -> None:
        with psycopg.connect(self._database_url) as conn:
            conn.execute(CREATE_TABLE_SQL)

    def follow(self, ticker: str) -> None:
        with psycopg.connect(self._database_url) as conn:
            conn.execute(FOLLOW_SQL, {"ticker": ticker})

    def unfollow(self, ticker: str) -> None:
        with psycopg.connect(self._database_url) as conn:
            conn.execute(UNFOLLOW_SQL, {"ticker": ticker})

    def is_following(self, ticker: str) -> bool:
        with psycopg.connect(self._database_url) as conn:
            row = conn.execute(IS_FOLLOWED_SQL, {"ticker": ticker}).fetchone()
        return row is not None

    def get_followed_tickers(self) -> list[str]:
        with psycopg.connect(self._database_url) as conn:
            rows = conn.execute(FOLLOWED_TICKERS_SQL).fetchall()
        return [row[0] for row in rows]
