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
