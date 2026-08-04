# Batch image for the news pipeline (fetch -> score -> persist). Runs as its
# own Kubernetes CronJob on a tighter schedule than the daily market pipeline,
# since news moves faster than end-of-day prices. Installs only the
# "pipeline" extra (requests/openai/psycopg) -- no streamlit, no yfinance use.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --no-dev --extra pipeline

COPY src ./src
RUN uv sync --frozen --no-dev --extra pipeline

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "-m", "stocks_research.news.pipeline"]
