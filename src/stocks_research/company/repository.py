import psycopg

from stocks_research.company.profile import CompanyProfile
from stocks_research.config import DATABASE_URL

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS company_profiles (
    ticker text PRIMARY KEY,
    name text,
    sector text,
    industry text,
    description text,
    website text,
    employees integer,
    country text,
    exchange text,
    market_cap bigint,
    updated_at timestamptz NOT NULL DEFAULT now()
)
"""

UPSERT_SQL = """
INSERT INTO company_profiles (
    ticker, name, sector, industry, description, website, employees, country, exchange, market_cap, updated_at
) VALUES (
    %(ticker)s, %(name)s, %(sector)s, %(industry)s, %(description)s, %(website)s,
    %(employees)s, %(country)s, %(exchange)s, %(market_cap)s, now()
)
ON CONFLICT (ticker) DO UPDATE SET
    name = EXCLUDED.name,
    sector = EXCLUDED.sector,
    industry = EXCLUDED.industry,
    description = EXCLUDED.description,
    website = EXCLUDED.website,
    employees = EXCLUDED.employees,
    country = EXCLUDED.country,
    exchange = EXCLUDED.exchange,
    market_cap = EXCLUDED.market_cap,
    updated_at = now()
"""

GET_PROFILE_SQL = """
SELECT ticker, name, sector, industry, description, website, employees, country, exchange, market_cap
FROM company_profiles
WHERE ticker = %(ticker)s
"""


class CompanyProfileRepository:
    def __init__(self, database_url: str = DATABASE_URL):
        self._database_url = database_url

    def ensure_schema(self) -> None:
        with psycopg.connect(self._database_url) as conn:
            conn.execute(CREATE_TABLE_SQL)

    def save_profiles(self, profiles: list[CompanyProfile]) -> None:
        if not profiles:
            return
        with psycopg.connect(self._database_url) as conn, conn.cursor() as cursor:
            cursor.executemany(UPSERT_SQL, [vars(p) for p in profiles])

    def get_profile(self, ticker: str) -> CompanyProfile | None:
        with psycopg.connect(self._database_url) as conn:
            row = conn.execute(GET_PROFILE_SQL, {"ticker": ticker}).fetchone()
        return None if row is None else self._row_to_profile(row)

    @staticmethod
    def _row_to_profile(row: tuple) -> CompanyProfile:
        ticker, name, sector, industry, description, website, employees, country, exchange, market_cap = row
        return CompanyProfile(
            ticker=ticker,
            name=name,
            sector=sector,
            industry=industry,
            description=description,
            website=website,
            employees=employees,
            country=country,
            exchange=exchange,
            market_cap=market_cap,
        )
