from stocks_research.company import pipeline as company_pipeline
from stocks_research.company.data import CompanyProfile


def make_profile(ticker: str) -> CompanyProfile:
    return CompanyProfile(
        ticker=ticker,
        name=f"{ticker} Inc.",
        sector="Technology",
        industry="Software",
        description="A software company.",
        website="https://example.com",
        employees=1000,
        country="United States",
        exchange="NMS",
        market_cap=1_000_000_000,
    )


class FakeCompanyProfileClient:
    def __init__(self, profiles: dict[str, CompanyProfile]):
        self._profiles = profiles
        self.calls: list[list[str]] = []

    def fetch_profiles(self, tickers: list[str]) -> dict[str, CompanyProfile]:
        self.calls.append(tickers)
        return self._profiles


class FakeCompanyProfileRepository:
    """Fake standing in for Postgres: fetched profiles land straight in `saved_profiles`."""

    def __init__(self):
        self.saved_profiles: list[CompanyProfile] = []
        self.schema_ensured = False

    def ensure_schema(self) -> None:
        self.schema_ensured = True

    def save_profiles(self, profiles: list[CompanyProfile]) -> None:
        self.saved_profiles.extend(profiles)


def test_run_ensures_schema_before_fetching():
    repository = FakeCompanyProfileRepository()

    company_pipeline.run(client=FakeCompanyProfileClient({}), repository=repository)

    assert repository.schema_ensured is True


def test_run_fetches_and_saves_profiles_for_configured_universe():
    profiles = {"AAPL": make_profile("AAPL"), "MSFT": make_profile("MSFT")}
    repository = FakeCompanyProfileRepository()
    client = FakeCompanyProfileClient(profiles)

    company_pipeline.run(client=client, repository=repository)

    assert repository.saved_profiles == list(profiles.values())
    assert len(client.calls) == 1


def test_run_with_no_profiles_fetched_saves_nothing():
    repository = FakeCompanyProfileRepository()

    company_pipeline.run(client=FakeCompanyProfileClient({}), repository=repository)

    assert repository.saved_profiles == []
