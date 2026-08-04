import logging

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


class MarketDataClient:
    def fetch_price_history(self, tickers: list[str], period: str = "5y") -> dict[str, pd.DataFrame]:
        histories = {}
        for ticker in tickers:
            try:
                history = yf.Ticker(ticker).history(period=period)
            except Exception:
                logger.exception("Failed to fetch price history for %s", ticker)
                continue
            if history.empty:
                logger.warning("No price history returned for %s", ticker)
                continue
            histories[ticker] = history
        return histories
