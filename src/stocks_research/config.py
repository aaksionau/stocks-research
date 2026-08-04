import os

from dotenv import load_dotenv

from stocks_research.sp500_constituents import SP500_TICKERS

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://stocks:stocks@localhost:5436/stocks")

FOUNDRY_ENDPOINT = os.environ.get("FOUNDRY_ENDPOINT")
FOUNDRY_API_KEY = os.environ.get("FOUNDRY_API_KEY")
FOUNDRY_DEPLOYMENT = os.environ.get("FOUNDRY_DEPLOYMENT", "gpt-4o-mini")
FOUNDRY_API_VERSION = os.environ.get("FOUNDRY_API_VERSION", "2024-10-21")

FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY")

TICKERS = SP500_TICKERS


def _parse_ticker_list(value: str) -> list[str]:
    return [ticker.strip() for ticker in value.split(",") if ticker.strip()]


# Smaller, separately-configured watchlist for news fetching -- not the full S&P 500 universe.
NEWS_TICKERS = _parse_ticker_list(os.environ.get("NEWS_TICKERS", "AAPL,MSFT,GOOGL,AMZN,NVDA"))
