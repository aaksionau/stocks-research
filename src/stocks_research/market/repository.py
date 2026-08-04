import psycopg

from stocks_research.config import DATABASE_URL
from stocks_research.market.indicators import IndicatorSnapshot

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS indicator_snapshots (
    ticker text NOT NULL,
    date date NOT NULL,
    close numeric NOT NULL,
    momentum_1d numeric,
    momentum_5d numeric,
    momentum_20d numeric,
    ma_50 numeric,
    ma_200 numeric,
    ma_trend text NOT NULL,
    pct_above_ma50 numeric,
    volume bigint NOT NULL,
    volume_avg_20 numeric,
    volume_ratio numeric,
    score numeric,
    flagged boolean NOT NULL DEFAULT false,
    commentary text,
    PRIMARY KEY (ticker, date)
)
"""

ALTER_TABLE_SQL = """
ALTER TABLE indicator_snapshots
    ADD COLUMN IF NOT EXISTS score numeric,
    ADD COLUMN IF NOT EXISTS flagged boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS commentary text
"""

UPSERT_SQL = """
INSERT INTO indicator_snapshots (
    ticker, date, close, momentum_1d, momentum_5d, momentum_20d,
    ma_50, ma_200, ma_trend, pct_above_ma50, volume, volume_avg_20, volume_ratio,
    score, flagged, commentary
) VALUES (
    %(ticker)s, %(date)s, %(close)s, %(momentum_1d)s, %(momentum_5d)s, %(momentum_20d)s,
    %(ma_50)s, %(ma_200)s, %(ma_trend)s, %(pct_above_ma50)s, %(volume)s, %(volume_avg_20)s, %(volume_ratio)s,
    %(score)s, %(flagged)s, %(commentary)s
)
ON CONFLICT (ticker, date) DO UPDATE SET
    close = EXCLUDED.close,
    momentum_1d = EXCLUDED.momentum_1d,
    momentum_5d = EXCLUDED.momentum_5d,
    momentum_20d = EXCLUDED.momentum_20d,
    ma_50 = EXCLUDED.ma_50,
    ma_200 = EXCLUDED.ma_200,
    ma_trend = EXCLUDED.ma_trend,
    pct_above_ma50 = EXCLUDED.pct_above_ma50,
    volume = EXCLUDED.volume,
    volume_avg_20 = EXCLUDED.volume_avg_20,
    volume_ratio = EXCLUDED.volume_ratio,
    score = EXCLUDED.score,
    flagged = EXCLUDED.flagged,
    commentary = EXCLUDED.commentary
"""

LATEST_SNAPSHOTS_SQL = """
SELECT DISTINCT ON (ticker)
    ticker, date, close, momentum_1d, momentum_5d, momentum_20d,
    ma_50, ma_200, ma_trend, pct_above_ma50, volume, volume_avg_20, volume_ratio,
    score, flagged, commentary
FROM indicator_snapshots
ORDER BY ticker, date DESC
"""

TICKER_HISTORY_SQL = """
SELECT
    ticker, date, close, momentum_1d, momentum_5d, momentum_20d,
    ma_50, ma_200, ma_trend, pct_above_ma50, volume, volume_avg_20, volume_ratio,
    score, flagged, commentary
FROM indicator_snapshots
WHERE ticker = %(ticker)s
ORDER BY date ASC
"""

ALL_SNAPSHOTS_SQL = """
SELECT
    ticker, date, close, momentum_1d, momentum_5d, momentum_20d,
    ma_50, ma_200, ma_trend, pct_above_ma50, volume, volume_avg_20, volume_ratio,
    score, flagged, commentary
FROM indicator_snapshots
ORDER BY date DESC, ticker ASC
"""


class SnapshotRepository:
    def __init__(self, database_url: str = DATABASE_URL):
        self._database_url = database_url

    def ensure_schema(self) -> None:
        with psycopg.connect(self._database_url) as conn:
            conn.execute(CREATE_TABLE_SQL)
            conn.execute(ALTER_TABLE_SQL)

    def save_snapshot(self, snapshot: IndicatorSnapshot) -> None:
        with psycopg.connect(self._database_url) as conn:
            conn.execute(UPSERT_SQL, vars(snapshot))

    def get_latest_snapshots(self) -> list[IndicatorSnapshot]:
        with psycopg.connect(self._database_url) as conn:
            rows = conn.execute(LATEST_SNAPSHOTS_SQL).fetchall()
        return [self._row_to_snapshot(row) for row in rows]

    def get_ticker_history(self, ticker: str) -> list[IndicatorSnapshot]:
        with psycopg.connect(self._database_url) as conn:
            rows = conn.execute(TICKER_HISTORY_SQL, {"ticker": ticker}).fetchall()
        return [self._row_to_snapshot(row) for row in rows]

    def get_all_snapshots(self) -> list[IndicatorSnapshot]:
        with psycopg.connect(self._database_url) as conn:
            rows = conn.execute(ALL_SNAPSHOTS_SQL).fetchall()
        return [self._row_to_snapshot(row) for row in rows]

    @staticmethod
    def _row_to_snapshot(row: tuple) -> IndicatorSnapshot:
        (
            ticker, date, close, momentum_1d, momentum_5d, momentum_20d,
            ma_50, ma_200, ma_trend, pct_above_ma50, volume, volume_avg_20, volume_ratio,
            score, flagged, commentary,
        ) = row
        as_float = lambda value: None if value is None else float(value)
        return IndicatorSnapshot(
            ticker=ticker,
            date=date,
            close=as_float(close),
            momentum_1d=as_float(momentum_1d),
            momentum_5d=as_float(momentum_5d),
            momentum_20d=as_float(momentum_20d),
            ma_50=as_float(ma_50),
            ma_200=as_float(ma_200),
            ma_trend=ma_trend,
            pct_above_ma50=as_float(pct_above_ma50),
            volume=int(volume),
            volume_avg_20=as_float(volume_avg_20),
            volume_ratio=as_float(volume_ratio),
            score=as_float(score),
            flagged=bool(flagged),
            commentary=commentary,
        )
