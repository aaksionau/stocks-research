import json

from openai import AzureOpenAI

from stocks_research.config import FOUNDRY_API_KEY, FOUNDRY_API_VERSION, FOUNDRY_DEPLOYMENT, FOUNDRY_ENDPOINT

SYSTEM_PROMPT = (
    "You are a financial news sentiment scorer. Given a numbered list of news headlines about a "
    "single stock ticker, score each headline's sentiment toward that ticker on a scale from -1 "
    "(very negative) to 1 (very positive), with 0 being neutral. Respond with only a JSON array of "
    "numbers, one score per headline, in the same order as the headlines -- no other text."
)

# Backlog days (e.g. after an outage) can pile up hundreds of headlines for one ticker/day.
# A single request that large risks the response being cut off at the model's output token
# limit, which surfaces as a JSONDecodeError on a truncated array -- chunking keeps each
# request's output well within that limit.
MAX_HEADLINES_PER_REQUEST = 40


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

        scores: list[float] = []
        for start in range(0, len(headlines), MAX_HEADLINES_PER_REQUEST):
            batch = headlines[start : start + MAX_HEADLINES_PER_REQUEST]
            scores.extend(self._score_batch(ticker, batch))
        return scores

    def _score_batch(self, ticker: str, headlines: list[str]) -> list[float]:
        response = self._client.chat.completions.create(
            model=self._deployment,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self._describe(ticker, headlines)},
            ],
        )
        choice = response.choices[0]
        if choice.finish_reason == "length":
            raise ValueError(
                f"Sentiment response for {ticker} was truncated at the model's output token "
                f"limit ({len(headlines)} headlines in this batch); lower MAX_HEADLINES_PER_REQUEST"
            )
        content = self._strip_code_fence(choice.message.content.strip())

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

    @staticmethod
    def _strip_code_fence(content: str) -> str:
        # gpt-4o-mini sometimes wraps the JSON in a markdown code fence despite
        # being told not to -- strip it rather than failing the whole batch.
        if not content.startswith("```"):
            return content
        content = content.removeprefix("```json").removeprefix("```")
        return content.removesuffix("```").strip()
