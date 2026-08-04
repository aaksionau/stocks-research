from openai import AzureOpenAI

from stocks_research.config import FOUNDRY_API_KEY, FOUNDRY_API_VERSION, FOUNDRY_DEPLOYMENT, FOUNDRY_ENDPOINT
from stocks_research.market.indicators import IndicatorSnapshot

SYSTEM_PROMPT = (
    "You are a market data analyst producing short notes on daily stock movement. "
    "Given a ticker's price and volume indicators, describe in 2-3 plain-English sentences "
    "what the numbers show (e.g. moving average crossovers, momentum, volume relative to its "
    "recent average). Be strictly descriptive, not advisory: never recommend, imply, or hint "
    "at a buy, sell, or hold decision, and never use words like 'buy', 'sell', 'hold', "
    "'recommend', 'should', or 'target price'."
)


class CommentaryClient:
    """Wraps the Azure AI Foundry gpt-4o-mini deployment. Descriptive-only prompt, no I/O beyond the API call."""

    def __init__(
        self,
        api_key: str | None = FOUNDRY_API_KEY,
        endpoint: str | None = FOUNDRY_ENDPOINT,
        deployment: str = FOUNDRY_DEPLOYMENT,
        api_version: str = FOUNDRY_API_VERSION,
    ):
        self._deployment = deployment
        self._client = AzureOpenAI(api_key=api_key, azure_endpoint=endpoint, api_version=api_version)

    def generate_commentary(self, ticker: str, snapshot: IndicatorSnapshot) -> str:
        response = self._client.chat.completions.create(
            model=self._deployment,
            temperature=0.3,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self._describe(ticker, snapshot)},
            ],
        )
        return response.choices[0].message.content.strip()

    @staticmethod
    def _describe(ticker: str, snapshot: IndicatorSnapshot) -> str:
        pct = lambda value: "n/a" if value is None else f"{value:+.2f}%"
        num = lambda value: "n/a" if value is None else f"{value:.2f}"
        return (
            f"Ticker: {ticker}\n"
            f"Close: {snapshot.close:.2f}\n"
            f"1-day change: {pct(snapshot.momentum_1d)}\n"
            f"5-day change: {pct(snapshot.momentum_5d)}\n"
            f"20-day change: {pct(snapshot.momentum_20d)}\n"
            f"50-day moving average: {num(snapshot.ma_50)}\n"
            f"200-day moving average: {num(snapshot.ma_200)}\n"
            f"Moving-average trend: {snapshot.ma_trend}\n"
            f"% above 50-day moving average: {pct(snapshot.pct_above_ma50)}\n"
            f"Volume: {snapshot.volume:,}\n"
            f"20-day average volume: {num(snapshot.volume_avg_20)}\n"
            f"Volume vs. 20-day average (ratio): {num(snapshot.volume_ratio)}\n"
        )
