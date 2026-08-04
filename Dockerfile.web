# Long-running web UI image (Streamlit, read-only over Postgres). Installs
# only the "web" extra (streamlit/pandas/psycopg) -- no yfinance/openai, so
# this image never needs Foundry or market-data credentials.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --no-dev --extra web

COPY src ./src
RUN uv sync --frozen --no-dev --extra web

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8501

CMD ["streamlit", "run", "src/stocks_research/ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
