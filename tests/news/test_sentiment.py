import pytest

from stocks_research.news.sentiment import NewsSentimentClient


class FakeMessage:
    def __init__(self, content: str):
        self.content = content


class FakeChoice:
    def __init__(self, content: str, finish_reason: str = "stop"):
        self.message = FakeMessage(content)
        self.finish_reason = finish_reason


class FakeCompletion:
    def __init__(self, content: str, finish_reason: str = "stop"):
        self.choices = [FakeChoice(content, finish_reason)]


class FakeCompletions:
    def __init__(self, content: str, finish_reason: str = "stop"):
        self._content = content
        self._finish_reason = finish_reason
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeCompletion(self._content, self._finish_reason)


class FakeChat:
    def __init__(self, content: str, finish_reason: str = "stop"):
        self.completions = FakeCompletions(content, finish_reason)


class FakeAzureOpenAI:
    def __init__(self, content: str = "[0.5, -0.2]", finish_reason: str = "stop"):
        self.chat = FakeChat(content, finish_reason)


def patch_azure_openai_content(
    monkeypatch, content: str, finish_reason: str = "stop"
) -> FakeAzureOpenAI:
    fake_client = FakeAzureOpenAI(content, finish_reason)
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


def test_score_headlines_strips_markdown_code_fence(monkeypatch):
    patch_azure_openai_content(monkeypatch, "```json\n[0.5, -0.2]\n```")
    client = NewsSentimentClient(api_key="key", endpoint="https://example.com")

    scores = client.score_headlines("AAPL", ["Good news", "Bad news"])

    assert scores == [0.5, -0.2]


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


def test_score_headlines_raises_clear_error_on_truncated_response(monkeypatch):
    patch_azure_openai_content(monkeypatch, "[0.5, -0.2", finish_reason="length")
    client = NewsSentimentClient(api_key="key", endpoint="https://example.com")

    with pytest.raises(ValueError, match="truncated"):
        client.score_headlines("AAPL", ["Headline 1", "Headline 2"])


class FakeCompletionsPerBatch:
    """Returns one score per numbered headline actually sent in that call's prompt."""

    def __init__(self):
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        user_message = kwargs["messages"][1]["content"]
        headline_count = user_message.count("\n") - 1  # "Ticker:" + "Headlines:" lines
        return FakeCompletion("[" + ", ".join(["0.1"] * headline_count) + "]")


def test_score_headlines_chunks_large_batches(monkeypatch):
    headlines = [f"Headline {i}" for i in range(85)]
    fake_completions = FakeCompletionsPerBatch()
    fake_client = FakeAzureOpenAI()
    fake_client.chat.completions = fake_completions
    monkeypatch.setattr(
        "stocks_research.news.sentiment.AzureOpenAI", lambda **kwargs: fake_client
    )
    client = NewsSentimentClient(api_key="key", endpoint="https://example.com")

    scores = client.score_headlines("AAPL", headlines)

    assert len(fake_completions.calls) == 3
    assert [len(call["messages"][1]["content"].splitlines()) - 2 for call in fake_completions.calls] == [
        40,
        40,
        5,
    ]
    assert scores == [0.1] * 85
