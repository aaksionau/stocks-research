import logging

from stocks_research.company.data import CompanyProfileClient
from stocks_research.company.repository import CompanyProfileRepository
from stocks_research.config import TICKERS

logger = logging.getLogger(__name__)


def run(
    client: CompanyProfileClient | None = None,
    repository: CompanyProfileRepository | None = None,
) -> None:
    client = client or CompanyProfileClient()
    repository = repository or CompanyProfileRepository()

    # Postgres unreachable raises here and aborts the run before any fetching happens.
    repository.ensure_schema()

    # Per-ticker fetch failures are logged and skipped inside CompanyProfileClient, not fatal here.
    profiles = client.fetch_profiles(TICKERS)
    repository.save_profiles(list(profiles.values()))

    logger.info("Company profile fetch complete: saved %d/%d tickers", len(profiles), len(TICKERS))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
