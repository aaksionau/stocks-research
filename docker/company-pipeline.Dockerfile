# Batch image for the company profile pipeline (fetch -> persist). Company
# profile data (sector, industry, business summary) changes rarely, so this
# runs on a much looser schedule than the daily market or news pipelines.
# Installs only the "pipeline" extra (yfinance/psycopg) -- no streamlit.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --no-dev --extra pipeline

COPY src ./src
RUN uv sync --frozen --no-dev --extra pipeline

ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "-m", "stocks_research.company.pipeline"]
