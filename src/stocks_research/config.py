import os

from dotenv import load_dotenv

from stocks_research.sp500_constituents import SP500_TICKERS

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://stocks:stocks@localhost:5436/stocks")

TICKERS = SP500_TICKERS
