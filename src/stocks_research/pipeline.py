import logging
from dataclasses import replace

from stocks_research.config import TICKERS
from stocks_research.flagging import Flagger
from stocks_research.indicators import IndicatorEngine
from stocks_research.market_data import MarketDataClient
from stocks_research.repository import SnapshotRepository

logger = logging.getLogger(__name__)


class PipelineFailedError(RuntimeError):
    """Raised when the run produced no usable data at all -- a systemic failure, not a per-ticker one."""


def run(
    market_data: MarketDataClient | None = None,
    engine: IndicatorEngine | None = None,
    flagger: Flagger | None = None,
    repository: SnapshotRepository | None = None,
) -> None:
    market_data = market_data or MarketDataClient()
    engine = engine or IndicatorEngine()
    flagger = flagger or Flagger()
    repository = repository or SnapshotRepository()

    # Postgres unreachable raises here and aborts the run before any fetching happens.
    repository.ensure_schema()

    price_histories = market_data.fetch_price_history(TICKERS)
    if not price_histories:
        raise PipelineFailedError(
            f"Fetched no price history for any of {len(TICKERS)} tickers; treating as a systemic failure."
        )

    snapshots = []
    for ticker, history in price_histories.items():
        try:
            snapshots.append(engine.compute_indicators(ticker, history))
        except Exception:
            logger.exception("Failed to compute indicators for %s", ticker)
            continue

    flagged_scores = {f.ticker: f.score for f in flagger.rank(snapshots)}

    saved = 0
    for snapshot in snapshots:
        score = flagged_scores.get(snapshot.ticker)
        enriched = replace(snapshot, score=score, flagged=score is not None)

        # Not caught: a Postgres outage here should abort the run rather than be swallowed per ticker.
        repository.save_snapshot(enriched)
        saved += 1
        print(f"Saved snapshot for {enriched.ticker} on {enriched.date}")

    logger.info("Pipeline run complete: saved %d/%d tickers", saved, len(TICKERS))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
