from datetime import date

import pytest

from stocks_research.market.commentary import CommentaryClient
from stocks_research.market.indicators import IndicatorSnapshot


def make_snapshot(**overrides) -> IndicatorSnapshot:
    defaults = dict(
        ticker="AAPL",
        date=date(2020, 1, 1),
        close=150.0,
        momentum_1d=1.2,
        momentum_5d=3.4,
        momentum_20d=-2.1,
        ma_50=145.0,
        ma_200=140.0,
        ma_trend="bullish",
        pct_above_ma50=3.4,
        volume=1_000_000,
        volume_avg_20=800_000,
        volume_ratio=1.25,
    )
    defaults.update(overrides)
    return IndicatorSnapshot(**defaults)


class FakeMessage:
    def __init__(self, content: str):
        self.content = content


class FakeChoice:
    def __init__(self, content: str):
        self.message = FakeMessage(content)


class FakeCompletion:
    def __init__(self, content: str):
        self.choices = [FakeChoice(content)]


class FakeCompletions:
    def __init__(self, content: str):
        self._content = content
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeCompletion(self._content)


class FakeChat:
    def __init__(self, content: str):
        self.completions = FakeCompletions(content)


class FakeAzureOpenAI:
    def __init__(self, content: str = "  Broke above its 50-day MA on above-average volume.  "):
        self.chat = FakeChat(content)


@pytest.fixture
def patch_azure_openai(monkeypatch):
    fake_client = FakeAzureOpenAI()
    monkeypatch.setattr(
        "stocks_research.market.commentary.AzureOpenAI", lambda **kwargs: fake_client
    )
    return fake_client


def test_generate_commentary_returns_stripped_text(patch_azure_openai):
    client = CommentaryClient(api_key="key", endpoint="https://example.com")

    commentary = client.generate_commentary("AAPL", make_snapshot())

    assert commentary == "Broke above its 50-day MA on above-average volume."


def test_generate_commentary_sends_system_prompt_forbidding_advice(patch_azure_openai):
    client = CommentaryClient(api_key="key", endpoint="https://example.com")

    client.generate_commentary("AAPL", make_snapshot())

    [call] = patch_azure_openai.chat.completions.calls
    system_message = call["messages"][0]
    assert system_message["role"] == "system"
    assert "buy" in system_message["content"].lower()
    assert "never" in system_message["content"].lower()


def test_generate_commentary_includes_ticker_and_indicators_in_prompt(patch_azure_openai):
    client = CommentaryClient(api_key="key", endpoint="https://example.com")

    client.generate_commentary("AAPL", make_snapshot(momentum_20d=None))

    [call] = patch_azure_openai.chat.completions.calls
    user_message = call["messages"][1]["content"]
    assert "AAPL" in user_message
    assert "20-day change: n/a" in user_message
