import logging

from stocks_research.config import TICKERS
from stocks_research.market.data import MarketDataClient
from stocks_research.market.indicators import IndicatorEngine
from stocks_research.market.repository import SnapshotRepository

logger = logging.getLogger(__name__)


def run(
    period: str = "5y",
    market_data: MarketDataClient | None = None,
    engine: IndicatorEngine | None = None,
    repository: SnapshotRepository | None = None,
) -> None:
    """Seed indicator_snapshots with one row per historical trading day, not just "today".

    No flagging or commentary here -- flagging is a cross-sectional ranking of "today"
    against the rest of the universe, and commentary is an LLM call; neither makes sense
    (or is worth paying for) per historical day. The daily pipeline continues to own both
    for the current day and will overwrite that day's row via upsert.
    """
    market_data = market_data or MarketDataClient()
    engine = engine or IndicatorEngine()
    repository = repository or SnapshotRepository()

    repository.ensure_schema()

    price_histories = market_data.fetch_price_history(TICKERS, period=period)

    saved = 0
    for ticker, history in price_histories.items():
        try:
            snapshots = engine.compute_indicator_history(ticker, history)
        except Exception:
            logger.exception("Failed to compute indicator history for %s", ticker)
            continue

        for snapshot in snapshots:
            repository.save_snapshot(snapshot)
            saved += 1
        print(f"Backfilled {len(snapshots)} days for {ticker}")

    logger.info("Backfill complete: saved %d rows across %d tickers", saved, len(price_histories))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
