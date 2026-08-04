import pytest

from stocks_research.news.sentiment import NewsSentimentClient


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
    def __init__(self, content: str = "[0.5, -0.2]"):
        self.chat = FakeChat(content)


def patch_azure_openai_content(monkeypatch, content: str) -> FakeAzureOpenAI:
    fake_client = FakeAzureOpenAI(content)
    monkeypatch.setattr(
        "stocks_research.news.sentiment.AzureOpenAI", lambda **kwargs: fake_client
    )
    return fake_client


@pytest.fixture
def patch_azure_openai(monkeypatch):
    return patch_azure_openai_content(monkeypatch, "[0.5, -0.2]")


def test_score_headlines_returns_parsed_scores(patch_azure_openai):
    client = NewsSentimentClient(api_key="key", endpoint="https://example.com")

    scores = client.score_headlines("AAPL", ["Good news", "Bad news"])

    assert scores == [0.5, -0.2]


def test_score_headlines_makes_a_single_batched_call(patch_azure_openai):
    client = NewsSentimentClient(api_key="key", endpoint="https://example.com")

    client.score_headlines("AAPL", ["Good news", "Bad news"])

    assert len(patch_azure_openai.chat.completions.calls) == 1
    [call] = patch_azure_openai.chat.completions.calls
    user_message = call["messages"][1]["content"]
    assert "AAPL" in user_message
    assert "Good news" in user_message
    assert "Bad news" in user_message


def test_score_headlines_with_no_headlines_makes_no_call(patch_azure_openai):
    client = NewsSentimentClient(api_key="key", endpoint="https://example.com")

    scores = client.score_headlines("AAPL", [])

    assert scores == []
    assert patch_azure_openai.chat.completions.calls == []


def test_score_headlines_raises_on_non_json_response(monkeypatch):
    patch_azure_openai_content(monkeypatch, "not json")
    client = NewsSentimentClient(api_key="key", endpoint="https://example.com")

    with pytest.raises(ValueError):
        client.score_headlines("AAPL", ["Some headline"])


def test_score_headlines_raises_on_mismatched_score_count(monkeypatch):
    patch_azure_openai_content(monkeypatch, "[0.5]")
    client = NewsSentimentClient(api_key="key", endpoint="https://example.com")

    with pytest.raises(ValueError):
        client.score_headlines("AAPL", ["Headline 1", "Headline 2"])
