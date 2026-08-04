# Stocks Research

A daily pipeline and Streamlit dashboard for surfacing which S&P 500 stocks are doing
something statistically unusual — momentum spikes, moving-average crossovers, or
volume anomalies — with short AI-generated commentary for the names it flags.

## How it works

1. **Fetch** — five years of daily price/volume history for every S&P 500 constituent, via
   [yfinance](https://github.com/ranaroussi/yfinance).
2. **Compute** — per ticker: 1/5/20-day momentum, 50- and 200-day moving averages (and
   the bullish/bearish/neutral trend between them), % above the 50-day MA, and volume vs.
   its 20-day average.
3. **Flag** — the 30 tickers with the highest combined z-score across momentum, trend
   strength, and volume anomaly are flagged for that day.
4. **Explain** — flagged tickers get a strictly descriptive (never advisory) 2-3 sentence
   commentary from an Azure AI Foundry `gpt-4o-mini` deployment.
5. **Persist** — everything is upserted into Postgres, one row per `(ticker, date)`.

A Streamlit app then reads that table to power three views:

- **Overview** — all tickers for the latest run, filterable by ticker/trend/flagged
  status, sorted by score.
- **Ticker Detail** — price/volume charts and full indicator + commentary history for
  one ticker.
- **Trends** — which tickers have been flagged most often over a rolling window of days.

## Project layout

```
src/stocks_research/
├── pipeline.py              # orchestrates fetch -> compute -> flag -> commentary -> persist
├── market_data.py           # yfinance price history fetch
├── indicators.py            # momentum / moving-average / volume indicator math
├── flagging.py               # z-score composite ranking -> top-N flagged tickers
├── commentary.py            # Azure AI Foundry (gpt-4o-mini) descriptive commentary
├── repository.py            # Postgres schema + upsert/read queries
├── trends.py                 # rolling-window flag-frequency summaries
├── config.py                 # env-driven configuration
├── sp500_constituents.py    # the ticker universe
└── ui/                        # Streamlit app (Overview, Ticker Detail, Trends)
```

The pipeline and web UI are packaged as separate Docker images (`Dockerfile.pipeline`,
`Dockerfile.web`) with separate dependency extras, so the always-on dashboard never
needs market-data or LLM credentials, and the batch job never needs Streamlit.

## Getting started

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra pipeline --extra web --group dev
cp .env.example .env   # fill in FOUNDRY_* if you want AI commentary
docker compose up -d   # starts Postgres on localhost:5436
```

Run the pipeline once to populate data:

```bash
uv run python -m stocks_research.pipeline
```

Launch the dashboard:

```bash
uv run streamlit run src/stocks_research/ui/app.py
```

### Configuration

Set via environment variables or `.env` (see `.env.example`):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection string |
| `FOUNDRY_ENDPOINT`, `FOUNDRY_API_KEY` | Azure AI Foundry resource for commentary |
| `FOUNDRY_DEPLOYMENT` | Model deployment name (default `gpt-4o-mini`) |
| `FOUNDRY_API_VERSION` | Azure OpenAI API version |

Without `FOUNDRY_*` credentials, the pipeline still runs — commentary generation for
flagged tickers just fails per-ticker and is logged, not fatal to the run.

## Testing

```bash
uv run pytest
```
