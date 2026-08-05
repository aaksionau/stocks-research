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
    trailing_pe numeric,
    forward_pe numeric,
    peg_ratio numeric,
    price_to_book numeric,
    return_on_equity numeric,
    profit_margins numeric,
    debt_to_equity numeric,
    earnings_growth numeric,
    revenue_growth numeric,
    updated_at timestamptz NOT NULL DEFAULT now()
)
"""

ALTER_TABLE_SQL = """
ALTER TABLE company_profiles
    ADD COLUMN IF NOT EXISTS trailing_pe numeric,
    ADD COLUMN IF NOT EXISTS forward_pe numeric,
    ADD COLUMN IF NOT EXISTS peg_ratio numeric,
    ADD COLUMN IF NOT EXISTS price_to_book numeric,
    ADD COLUMN IF NOT EXISTS return_on_equity numeric,
    ADD COLUMN IF NOT EXISTS profit_margins numeric,
    ADD COLUMN IF NOT EXISTS debt_to_equity numeric,
    ADD COLUMN IF NOT EXISTS earnings_growth numeric,
    ADD COLUMN IF NOT EXISTS revenue_growth numeric
"""

UPSERT_SQL = """
INSERT INTO company_profiles (
    ticker, name, sector, industry, description, website, employees, country, exchange, market_cap,
    trailing_pe, forward_pe, peg_ratio, price_to_book, return_on_equity, profit_margins,
    debt_to_equity, earnings_growth, revenue_growth, updated_at
) VALUES (
    %(ticker)s, %(name)s, %(sector)s, %(industry)s, %(description)s, %(website)s,
    %(employees)s, %(country)s, %(exchange)s, %(market_cap)s,
    %(trailing_pe)s, %(forward_pe)s, %(peg_ratio)s, %(price_to_book)s, %(return_on_equity)s,
    %(profit_margins)s, %(debt_to_equity)s, %(earnings_growth)s, %(revenue_growth)s, now()
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
    trailing_pe = EXCLUDED.trailing_pe,
    forward_pe = EXCLUDED.forward_pe,
    peg_ratio = EXCLUDED.peg_ratio,
    price_to_book = EXCLUDED.price_to_book,
    return_on_equity = EXCLUDED.return_on_equity,
    profit_margins = EXCLUDED.profit_margins,
    debt_to_equity = EXCLUDED.debt_to_equity,
    earnings_growth = EXCLUDED.earnings_growth,
    revenue_growth = EXCLUDED.revenue_growth,
    updated_at = now()
"""

GET_PROFILE_SQL = """
SELECT ticker, name, sector, industry, description, website, employees, country, exchange, market_cap,
    trailing_pe, forward_pe, peg_ratio, price_to_book, return_on_equity, profit_margins,
    debt_to_equity, earnings_growth, revenue_growth
FROM company_profiles
WHERE ticker = %(ticker)s
"""

GET_ALL_PROFILES_SQL = """
SELECT ticker, name, sector, industry, description, website, employees, country, exchange, market_cap,
    trailing_pe, forward_pe, peg_ratio, price_to_book, return_on_equity, profit_margins,
    debt_to_equity, earnings_growth, revenue_growth
FROM company_profiles
"""


class CompanyProfileRepository:
    def __init__(self, database_url: str = DATABASE_URL):
        self._database_url = database_url

    def ensure_schema(self) -> None:
        with psycopg.connect(self._database_url) as conn:
            conn.execute(CREATE_TABLE_SQL)
            conn.execute(ALTER_TABLE_SQL)

    def save_profiles(self, profiles: list[CompanyProfile]) -> None:
        if not profiles:
            return
        with psycopg.connect(self._database_url) as conn, conn.cursor() as cursor:
            cursor.executemany(UPSERT_SQL, [vars(p) for p in profiles])

    def get_profile(self, ticker: str) -> CompanyProfile | None:
        with psycopg.connect(self._database_url) as conn:
            row = conn.execute(GET_PROFILE_SQL, {"ticker": ticker}).fetchone()
        return None if row is None else self._row_to_profile(row)

    def get_all_profiles(self) -> dict[str, CompanyProfile]:
        with psycopg.connect(self._database_url) as conn:
            rows = conn.execute(GET_ALL_PROFILES_SQL).fetchall()
        return {row[0]: self._row_to_profile(row) for row in rows}

    @staticmethod
    def _row_to_profile(row: tuple) -> CompanyProfile:
        (
            ticker, name, sector, industry, description, website, employees, country, exchange, market_cap,
            trailing_pe, forward_pe, peg_ratio, price_to_book, return_on_equity, profit_margins,
            debt_to_equity, earnings_growth, revenue_growth,
        ) = row
        as_float = lambda value: None if value is None else float(value)
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
            trailing_pe=as_float(trailing_pe),
            forward_pe=as_float(forward_pe),
            peg_ratio=as_float(peg_ratio),
            price_to_book=as_float(price_to_book),
            return_on_equity=as_float(return_on_equity),
            profit_margins=as_float(profit_margins),
            debt_to_equity=as_float(debt_to_equity),
            earnings_growth=as_float(earnings_growth),
            revenue_growth=as_float(revenue_growth),
        )
