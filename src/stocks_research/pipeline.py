from stocks_research.config import TICKERS
from stocks_research.indicators import IndicatorEngine
from stocks_research.market_data import MarketDataClient
from stocks_research.repository import SnapshotRepository


def run() -> None:
    market_data = MarketDataClient()
    engine = IndicatorEngine()
    repository = SnapshotRepository()

    repository.ensure_schema()

    price_histories = market_data.fetch_price_history(TICKERS)
    for ticker, history in price_histories.items():
        snapshot = engine.compute_indicators(ticker, history)
        repository.save_snapshot(snapshot)
        print(f"Saved snapshot for {ticker} on {snapshot.date}")


if __name__ == "__main__":
    run()
