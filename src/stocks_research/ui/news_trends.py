import pandas as pd
import streamlit as st

from stocks_research.news.repository import NewsRepository
from stocks_research.news.trends import DEFAULT_WINDOW_DAYS, summarize_news_trends, windowed_articles

st.title("News Sentiment Trends")

articles = NewsRepository().get_scored_articles()

if not articles:
    st.info(
        "No scored news articles yet. Run the pipeline first: "
        "`uv run python -m stocks_research.news.pipeline` then "
        "`uv run python -m stocks_research.news.sentiment_pipeline`"
    )
else:
    available_days = len({a.published_at.date() for a in articles})
    if available_days <= 1:
        st.caption("Only one day of data so far -- the window slider needs at least two.")
        days = available_days
    else:
        days = st.slider(
            "Days to consider",
            min_value=1,
            max_value=available_days,
            value=min(DEFAULT_WINDOW_DAYS, available_days),
        )

    ticker_filter = st.text_input("Filter by ticker").upper()
    filtered_articles = [a for a in articles if ticker_filter in a.ticker.upper()] if ticker_filter else articles

    summaries = summarize_news_trends(filtered_articles, days=days)

    if not summaries:
        st.info("No tickers have scored news in the selected window.")
    else:
        summary_df = pd.DataFrame([vars(t) for t in summaries])

        st.caption(
            f"{len(summary_df)} ticker(s) with scored news across the last {days} day(s) of data."
        )

        daily = pd.DataFrame(
            [
                {
                    "date": a.published_at.date(),
                    "ticker": a.ticker,
                    "sentiment_score": a.sentiment_score,
                }
                for a in windowed_articles(filtered_articles, days=days)
            ]
        )
        daily_avg = daily.groupby(["date", "ticker"])["sentiment_score"].mean().unstack("ticker")
        st.line_chart(daily_avg)

        st.dataframe(
            summary_df.sort_values(["avg_sentiment", "article_count"], ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "article_count": st.column_config.NumberColumn("Articles"),
                "avg_sentiment": st.column_config.NumberColumn("Avg Sentiment", format="%.2f"),
                "sentiment_direction": st.column_config.TextColumn("Direction"),
                "last_published_date": st.column_config.DateColumn("Last Published"),
            },
        )
