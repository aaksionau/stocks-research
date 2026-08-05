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
- **Ticker Detail** — company overview, price/volume charts, full indicator + commentary
  history, and news sentiment for one ticker.
- **Trends** — which tickers have been flagged most often over a rolling window of days.

## Project layout

```
src/stocks_research/
├── config.py                  # env-driven configuration
├── market/                    # price/indicator pipeline
│   ├── pipeline.py            # orchestrates fetch -> compute -> flag -> commentary -> persist
│   ├── data.py                 # yfinance price history fetch
│   ├── indicators.py          # momentum / moving-average / volume indicator math
│   ├── flagging.py            # z-score composite ranking -> top-N flagged tickers
│   ├── commentary.py          # Azure AI Foundry (gpt-4o-mini) descriptive commentary
│   ├── repository.py          # Postgres schema + upsert/read queries
│   ├── trends.py              # rolling-window flag-frequency summaries
│   └── sp500_constituents.py  # the ticker universe
├── news/                      # news pipeline
│   ├── pipeline.py            # orchestrates fetch -> score -> persist for the news watchlist
│   ├── data.py                 # Finnhub company-news fetch
│   ├── sentiment.py            # Azure AI Foundry (gpt-4o-mini) headline sentiment scoring
│   ├── repository.py          # Postgres schema + upsert/read queries for news articles
│   └── trends.py               # rolling-window sentiment aggregation
├── company/                   # company profile pipeline
│   ├── pipeline.py            # orchestrates fetch -> persist for the ticker universe
│   ├── data.py                 # yfinance company profile fetch (sector, industry, description, ...)
│   └── repository.py          # Postgres schema + upsert/read queries for company profiles
└── ui/                         # Streamlit app (Overview, Ticker Detail, Trends, News Trends)
```

The market pipeline, news pipeline, company profile pipeline, and web UI are packaged as
separate Docker images (`docker/pipeline.Dockerfile`, `docker/news-pipeline.Dockerfile`,
`docker/company-pipeline.Dockerfile`, `docker/web.Dockerfile`) with separate dependency
extras and independent schedules -- news moves faster than end-of-day prices, and company
profiles change rarely, so each runs on its own cadence rather than folding into the market
pipeline. The always-on dashboard never needs market-data or LLM credentials, and none of
the batch jobs need Streamlit.

## Getting started

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra pipeline --extra web --group dev
cp .env.example .env   # fill in FOUNDRY_* if you want AI commentary
docker compose -f docker/docker-compose.yml up -d   # starts Postgres on localhost:5436
```

Run the pipeline once to populate data:

```bash
uv run python -m stocks_research.market.pipeline
```

Fetch, score, and persist news for the configured watchlist (requires `FINNHUB_API_KEY`;
sentiment scoring uses the same `FOUNDRY_*` credentials as market commentary):

```bash
uv run python -m stocks_research.news.pipeline
```

Fetch and persist company profiles (sector, industry, business description) for the
ticker universe:

```bash
uv run python -m stocks_research.company.pipeline
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
| `FINNHUB_API_KEY` | [Finnhub](https://finnhub.io) API key for news fetching |

News fetching runs only for tickers subscribed via the "Track news" toggle on the Ticker
Detail page (stored in the `news_subscriptions` table) — not the full S&P 500 universe.

Without `FOUNDRY_*` credentials, the pipeline still runs — commentary generation for
flagged tickers just fails per-ticker and is logged, not fatal to the run.

## Testing

```bash
uv run pytest
```
