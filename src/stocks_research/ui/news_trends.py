import pandas as pd
import streamlit as st

from stocks_research.news.data import NewsArticle
from stocks_research.news.repository import NewsRepository
from stocks_research.news.subscriptions import NewsSubscriptionRepository
from stocks_research.news.trends import DEFAULT_WINDOW_DAYS, summarize_news_trends, windowed_articles
from stocks_research.ui.theme import sentiment_direction_label

st.title("News Trends")
st.caption("Daily sentiment for the tickers you're tracking, based on scored news headlines.")

subscription_repository = NewsSubscriptionRepository()


@st.cache_data(ttl=300)
def _load_scored_articles() -> list[NewsArticle]:
    return NewsRepository().get_all_scored_articles()


tracked_tickers = sorted(subscription_repository.get_subscribed_tickers())

if not tracked_tickers:
    st.info(
        "No tickers are tracked for news yet -- toggle \"Track news\" for a ticker on the "
        "Ticker Detail page first."
    )
else:
    # A placeholder reserves the top slot for the trend content, which is filled in further
    # down once we know which tickers are still tracked -- keeping the trend as the visual
    # focus of the page, with tracking management tucked below it.
    trend_slot = st.container()

    with st.expander(f"Manage tracked tickers ({len(tracked_tickers)})"):
        st.caption("Uncheck a ticker to stop tracking news for it.")
        edited = st.data_editor(
            pd.DataFrame({"ticker": tracked_tickers, "track": True}),
            use_container_width=True,
            hide_index=True,
            column_config={
                "ticker": st.column_config.TextColumn("Ticker", disabled=True),
                "track": st.column_config.CheckboxColumn("Track"),
            },
            key="news_trends_tracking_editor",
        )

        # Write-through per row, same as the single-ticker toggle on Ticker Detail --
        # unchecking here stops the pipeline from fetching this ticker going forward.
        for _, row in edited.iterrows():
            if not row["track"]:
                subscription_repository.unsubscribe(row["ticker"])

    still_tracked = set(edited.loc[edited["track"], "ticker"])
    articles = [a for a in _load_scored_articles() if a.ticker in still_tracked]

    with trend_slot:
        if not articles:
            st.info(
                "No scored news articles yet for the tracked tickers. Run the pipeline first: "
                "`uv run python -m stocks_research.news.pipeline`"
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

            window = windowed_articles(articles, days=days)

            if not window:
                st.info("No scored news in the selected window.")
            else:
                summaries = summarize_news_trends(articles, days=days)

                kpi_cols = st.columns(3)
                kpi_cols[0].metric("Tickers", len(summaries))
                kpi_cols[1].metric(
                    "Avg Sentiment", f"{sum(s.avg_sentiment for s in summaries) / len(summaries):+.2f}"
                )
                kpi_cols[2].metric("Total Articles", sum(s.article_count for s in summaries))

                st.markdown("##### Sentiment Over Time")
                daily = pd.DataFrame(
                    [
                        {"date": a.published_at.date(), "ticker": a.ticker, "sentiment_score": a.sentiment_score}
                        for a in window
                    ]
                )
                pivot = daily.groupby(["date", "ticker"])["sentiment_score"].mean().unstack("ticker")
                st.caption(f"Daily average sentiment per ticker over the last {days} day(s).")
                st.line_chart(pivot)

                st.markdown("##### Ranked by Sentiment")
                df = pd.DataFrame([vars(s) for s in summaries])
                df["sentiment_direction"] = df["sentiment_direction"].map(sentiment_direction_label)
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_order=["ticker", "avg_sentiment", "sentiment_direction", "article_count", "last_published_date"],
                    column_config={
                        "ticker": st.column_config.TextColumn("Ticker"),
                        "avg_sentiment": st.column_config.NumberColumn("Avg Sentiment", format="%+.2f"),
                        "sentiment_direction": st.column_config.TextColumn("Direction"),
                        "article_count": st.column_config.NumberColumn("Articles"),
                        "last_published_date": st.column_config.DateColumn("Last Published"),
                    },
                )
