import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://stocks:stocks@localhost:5436/stocks")

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
