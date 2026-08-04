import logging

import yfinance as yf

from stocks_research.company.profile import CompanyProfile

logger = logging.getLogger(__name__)


class CompanyProfileClient:
    def fetch_profiles(self, tickers: list[str]) -> dict[str, CompanyProfile]:
        profiles = {}
        for ticker in tickers:
            try:
                info = yf.Ticker(ticker).info
            except Exception:
                logger.exception("Failed to fetch company profile for %s", ticker)
                continue
            if not info:
                logger.warning("No company profile info returned for %s", ticker)
                continue
            profiles[ticker] = self._to_profile(ticker, info)
        return profiles

    @staticmethod
    def _to_profile(ticker: str, info: dict) -> CompanyProfile:
        return CompanyProfile(
            ticker=ticker,
            name=info.get("longName") or info.get("shortName"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            description=info.get("longBusinessSummary"),
            website=info.get("website"),
            employees=info.get("fullTimeEmployees"),
            country=info.get("country"),
            exchange=info.get("exchange"),
            market_cap=info.get("marketCap"),
        )
