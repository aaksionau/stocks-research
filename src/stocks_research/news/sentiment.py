import json

from openai import AzureOpenAI

from stocks_research.config import FOUNDRY_API_KEY, FOUNDRY_API_VERSION, FOUNDRY_DEPLOYMENT, FOUNDRY_ENDPOINT

SYSTEM_PROMPT = (
    "You are a financial news sentiment scorer. Given a numbered list of news headlines about a "
    "single stock ticker, score each headline's sentiment toward that ticker on a scale from -1 "
    "(very negative) to 1 (very positive), with 0 being neutral. Respond with only a JSON array of "
    "numbers, one score per headline, in the same order as the headlines -- no other text."
)


class NewsSentimentClient:
    """Wraps the Azure AI Foundry gpt-4o-mini deployment to batch-score a ticker's headlines for a day."""

    def __init__(
        self,
        api_key: str | None = FOUNDRY_API_KEY,
        endpoint: str | None = FOUNDRY_ENDPOINT,
        deployment: str = FOUNDRY_DEPLOYMENT,
        api_version: str = FOUNDRY_API_VERSION,
    ):
        self._deployment = deployment
        self._client = AzureOpenAI(api_key=api_key, azure_endpoint=endpoint, api_version=api_version)

    def score_headlines(self, ticker: str, headlines: list[str]) -> list[float]:
        if not headlines:
            return []

        response = self._client.chat.completions.create(
            model=self._deployment,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self._describe(ticker, headlines)},
            ],
        )
        content = response.choices[0].message.content.strip()

        try:
            scores = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Non-JSON sentiment response for {ticker}: {content}") from exc

        if not isinstance(scores, list) or len(scores) != len(headlines):
            raise ValueError(
                f"Expected {len(headlines)} scores for {ticker}, got: {content}"
            )
        return [float(score) for score in scores]

    @staticmethod
    def _describe(ticker: str, headlines: list[str]) -> str:
        numbered = "\n".join(f"{i}. {headline}" for i, headline in enumerate(headlines, start=1))
        return f"Ticker: {ticker}\nHeadlines:\n{numbered}"
