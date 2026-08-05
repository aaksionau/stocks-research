import logging
from dataclasses import replace

from stocks_research.company.repository import CompanyProfileRepository
from stocks_research.config import TICKERS
from stocks_research.market import signals
from stocks_research.market.backfill import backfill_histories
from stocks_research.market.commentary import CommentaryClient
from stocks_research.market.data import MarketDataClient
from stocks_research.market.flagging import Flagger
from stocks_research.market.indicators import IndicatorEngine
from stocks_research.market.repository import SnapshotRepository

logger = logging.getLogger(__name__)


class PipelineFailedError(RuntimeError):
    """Raised when the run produced no usable data at all -- a systemic failure, not a per-ticker one."""


def run(
    market_data: MarketDataClient | None = None,
    engine: IndicatorEngine | None = None,
    flagger: Flagger | None = None,
    commentary_client: CommentaryClient | None = None,
    repository: SnapshotRepository | None = None,
    profile_repository: CompanyProfileRepository | None = None,
) -> None:
    market_data = market_data or MarketDataClient()
    engine = engine or IndicatorEngine()
    flagger = flagger or Flagger()
    commentary_client = commentary_client or CommentaryClient()
    repository = repository or SnapshotRepository()
    profile_repository = profile_repository or CompanyProfileRepository()

    # Postgres unreachable raises here and aborts the run before any fetching happens.
    repository.ensure_schema()

    price_histories = market_data.fetch_price_history(TICKERS)
    if not price_histories:
        raise PipelineFailedError(
            f"Fetched no price history for any of {len(TICKERS)} tickers; treating as a systemic failure."
        )

    existing_tickers = repository.get_tickers_with_snapshots()
    missing_histories = {ticker: history for ticker, history in price_histories.items() if ticker not in existing_tickers}
    if missing_histories:
        logger.info(
            "Backfilling history for %d ticker(s) with no snapshots yet: %s",
            len(missing_histories),
            sorted(missing_histories),
        )
        backfill_histories(missing_histories, engine, repository)

    snapshots = []
    for ticker, history in price_histories.items():
        try:
            snapshots.append(engine.compute_indicators(ticker, history))
        except Exception:
            logger.exception("Failed to compute indicators for %s", ticker)
            continue

    flagged_scores = {f.ticker: f.score for f in flagger.rank(snapshots)}
    profiles = profile_repository.get_all_profiles()

    saved = 0
    for snapshot in snapshots:
        score = flagged_scores.get(snapshot.ticker)
        flagged = score is not None

        # Momentum/volume-anomaly flags and the fundamentals-driven buy verdict are
        # orthogonal -- a calm, fundamentally strong ticker near its MA50 can be a
        # Strong Buy without ever showing up as flagged, so it's included here too.
        verdict = signals.evaluate(snapshot, profiles.get(snapshot.ticker)).verdict
        needs_commentary = flagged or verdict == signals.STRONG_BUY

        commentary = None
        if needs_commentary:
            try:
                commentary = commentary_client.generate_commentary(snapshot.ticker, snapshot)
            except Exception:
                logger.exception("Failed to generate commentary for %s", snapshot.ticker)

        enriched = replace(snapshot, score=score, flagged=flagged, commentary=commentary)

        # Not caught: a Postgres outage here should abort the run rather than be swallowed per ticker.
        repository.save_snapshot(enriched)
        saved += 1
        print(f"Saved snapshot for {enriched.ticker} on {enriched.date}")

    logger.info("Pipeline run complete: saved %d/%d tickers", saved, len(TICKERS))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
