import pandas as pd
import yfinance as yf


class MarketDataClient:
    def fetch_price_history(self, tickers: list[str], period: str = "5y") -> dict[str, pd.DataFrame]:
        return {ticker: yf.Ticker(ticker).history(period=period) for ticker in tickers}
