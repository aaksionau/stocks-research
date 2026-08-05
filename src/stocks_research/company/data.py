import logging

import yfinance as yf

from stocks_research.company.profile import CompanyProfile

logger = logging.getLogger(__name__)

# Fields sourced from Yahoo's financialData/defaultKeyStatistics modules. These have been
# observed to drop out of `info` under load while the descriptive fields (name/sector/market_cap,
# sourced from a different module) still come through -- a partial-payload failure mode that
# looks like success (non-empty `info`) but leaves every fundamentals check undecidable downstream.
FINANCIAL_RATIO_KEYS = (
    "trailingPE",
    "forwardPE",
    "pegRatio",
    "priceToBook",
    "returnOnEquity",
    "profitMargins",
    "debtToEquity",
    "earningsGrowth",
    "revenueGrowth",
)


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
            if all(info.get(key) is None for key in FINANCIAL_RATIO_KEYS):
                logger.warning(
                    "Profile info for %s has no financial ratios (PE/PEG/ROE/margin/debt/growth) -- "
                    "Yahoo likely returned a partial payload for this fetch.",
                    ticker,
                )
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
            trailing_pe=info.get("trailingPE"),
            forward_pe=info.get("forwardPE"),
            peg_ratio=info.get("pegRatio"),
            price_to_book=info.get("priceToBook"),
            return_on_equity=info.get("returnOnEquity"),
            profit_margins=info.get("profitMargins"),
            debt_to_equity=info.get("debtToEquity"),
            earnings_growth=info.get("earningsGrowth"),
            revenue_growth=info.get("revenueGrowth"),
        )
