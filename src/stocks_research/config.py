import os

from dotenv import load_dotenv

from stocks_research.sp500_constituents import SP500_TICKERS

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://stocks:stocks@localhost:5436/stocks")

FOUNDRY_ENDPOINT = os.environ.get("FOUNDRY_ENDPOINT")
FOUNDRY_API_KEY = os.environ.get("FOUNDRY_API_KEY")
FOUNDRY_DEPLOYMENT = os.environ.get("FOUNDRY_DEPLOYMENT", "gpt-4o-mini")
FOUNDRY_API_VERSION = os.environ.get("FOUNDRY_API_VERSION", "2024-10-21")

TICKERS = SP500_TICKERS
