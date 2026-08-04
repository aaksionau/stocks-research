# Batch image for the daily pipeline (fetch -> compute -> flag -> commentary
# -> persist). Runs as a Kubernetes CronJob; never serves traffic. Installs
# only the "pipeline" extra (yfinance/pandas/openai/psycopg) -- no streamlit.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --no-dev --extra pipeline

COPY src ./src
RUN uv sync --frozen --no-dev --extra pipeline

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "-m", "stocks_research.pipeline"]
