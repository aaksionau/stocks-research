from dataclasses import dataclass


@dataclass(frozen=True)
class CompanyProfile:
    ticker: str
    name: str | None
    sector: str | None
    industry: str | None
    description: str | None
    website: str | None
    employees: int | None
    country: str | None
    exchange: str | None
    market_cap: int | None
    trailing_pe: float | None = None
    forward_pe: float | None = None
    peg_ratio: float | None = None
    price_to_book: float | None = None
    return_on_equity: float | None = None
    profit_margins: float | None = None
    debt_to_equity: float | None = None
    earnings_growth: float | None = None
    revenue_growth: float | None = None
