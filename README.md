# Stocks Research

A daily pipeline and Streamlit dashboard for surfacing which S&P 500 stocks are doing
something statistically unusual — momentum spikes, moving-average crossovers, or
volume anomalies — and which ones look like reasonable long-term buy candidates, with
short AI-generated commentary for the names it flags.

## How it works

1. **Fetch** — five years of daily price/volume history for every S&P 500 constituent, via
   [yfinance](https://github.com/ranaroussi/yfinance).
2. **Compute** — per ticker: 1/5/20-day momentum, 50- and 200-day moving averages (and
   the bullish/bearish/neutral trend between them), % above the 50-day MA, % below the
   52-week high, and volume vs. its 20-day average.
3. **Flag** — the 30 tickers with the highest combined z-score across momentum, trend
   strength, and volume anomaly are flagged for that day.
4. **Explain** — flagged tickers get a strictly descriptive (never advisory) 2-3 sentence
   commentary from an Azure AI Foundry `gpt-4o-mini` deployment.
5. **Score** — every ticker also gets a rule-based **Long-Term Buy Signal**
   (`Strong Buy`/`Buy`/`Hold`/`Avoid`/`Insufficient Data`), combining trend health, entry
   timing, valuation (PE/PEG), quality (ROE/margins/debt/earnings growth), and distance
   from its 52-week high — using company fundamentals from a separate profile pipeline.
6. **Persist** — everything is upserted into Postgres, one row per `(ticker, date)`.

A separate news pipeline fetches and sentiment-scores headlines (via Finnhub +
`gpt-4o-mini`) for tickers a user explicitly subscribes to from the dashboard.

A Streamlit app then reads those tables to power six views:

- **Overview** — all tickers for the latest run, filterable by ticker/trend/Buy Signal/
  industry/flagged status, with KPI counts and quick filters, sorted by verdict then score.
- **Ticker Detail** — company overview, price/volume charts, full indicator + commentary
  history, the Long-Term Buy Signal breakdown, news sentiment, and a "⭐ Follow" toggle
  to add the ticker to your watchlist.
- **Watchlist** — followed tickers with their latest metrics, Buy Signal, and a price
  chart, one card per ticker.
- **Trends** — which tickers have trended toward a Buy Signal most often over a rolling
  window of days, recomputed against today's fundamentals.
- **News Trends** — rolling sentiment trends for subscribed tickers' news.
- **Glossary** — plain-language definitions for every indicator, verdict, and score shown
  in the app.

## Project layout

```
src/stocks_research/
├── config.py                  # env-driven configuration
├── market/                    # price/indicator pipeline
│   ├── pipeline.py            # orchestrates fetch -> compute -> flag -> commentary -> persist
│   ├── data.py                 # yfinance price history fetch
│   ├── indicators.py          # momentum / moving-average / volume indicator math
│   ├── flagging.py            # z-score composite ranking -> top-N flagged tickers
│   ├── signals.py              # rule-based Long-Term Buy Signal (trend/valuation/quality/timing)
│   ├── commentary.py          # Azure AI Foundry (gpt-4o-mini) descriptive commentary
│   ├── repository.py          # Postgres schema + upsert/read queries
│   ├── backfill.py             # per-ticker history backfill
│   ├── trends.py               # rolling-window Buy Signal frequency summaries
│   └── sp500_constituents.py  # the ticker universe
├── news/                      # news pipeline
│   ├── pipeline.py            # orchestrates fetch -> score -> persist for the news watchlist
│   ├── data.py                 # Finnhub company-news fetch
│   ├── sentiment.py            # Azure AI Foundry (gpt-4o-mini) headline sentiment scoring
│   ├── repository.py          # Postgres schema + upsert/read queries for news articles
│   ├── subscriptions.py        # per-ticker "Track news" opt-in used to scope the fetch
│   └── trends.py               # rolling-window sentiment aggregation
├── company/                   # company profile pipeline
│   ├── pipeline.py            # orchestrates fetch -> persist for the ticker universe
│   ├── data.py                 # yfinance company profile fetch (sector, industry, PE/PEG, ROE, ...)
│   ├── profile.py               # CompanyProfile dataclass
│   └── repository.py          # Postgres schema + upsert/read queries for company profiles
├── watchlist/                 # ticker follow/star state
│   └── repository.py          # Postgres schema + upsert/read queries for followed tickers
└── ui/                         # Streamlit app (Overview, Ticker Detail, Watchlist, Trends,
                                 # News Trends, Glossary)
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

Fetch and persist company profiles (sector, industry, business description, PE/PEG,
ROE, margins, debt-to-equity, earnings growth) for the ticker universe -- these feed the
Long-Term Buy Signal's valuation and quality checks:

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
