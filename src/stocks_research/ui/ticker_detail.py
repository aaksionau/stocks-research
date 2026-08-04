import pandas as pd
import streamlit as st

from stocks_research.company.repository import CompanyProfileRepository
from stocks_research.market.repository import SnapshotRepository
from stocks_research.news.repository import NewsRepository
from stocks_research.news.trends import DEFAULT_WINDOW_DAYS, summarize_news_trends, windowed_articles

st.title("Ticker Detail")

repository = SnapshotRepository()
tickers = sorted(s.ticker for s in repository.get_latest_snapshots())

if not tickers:
    st.info("No snapshots yet. Run the pipeline first: `uv run python -m stocks_research.market.pipeline`")
else:
    preselected = st.session_state.get("selected_ticker") or st.query_params.get("ticker")
    default_index = tickers.index(preselected) if preselected in tickers else 0

    ticker = st.selectbox("Ticker", tickers, index=default_index)
    st.session_state["selected_ticker"] = ticker
    st.query_params["ticker"] = ticker

    history = repository.get_ticker_history(ticker)
    df = pd.DataFrame([vars(s) for s in history]).sort_values("date")

    overview_tab, price_tab, indicators_tab, commentary_tab, news_tab = st.tabs(
        ["Company Overview", "Price & Volume", "Indicator History", "AI Commentary", "News Sentiment"]
    )

    with overview_tab:
        profile = CompanyProfileRepository().get_profile(ticker)

        if profile is None:
            st.info(
                "No company profile yet for this ticker. Run the pipeline first: "
                "`uv run python -m stocks_research.company.pipeline`"
            )
        else:
            st.subheader(profile.name or ticker)
            st.caption(" · ".join(filter(None, [profile.sector, profile.industry, profile.country])))

            cols = st.columns(3)
            cols[0].metric("Market Cap", f"${profile.market_cap:,}" if profile.market_cap else "N/A")
            cols[1].metric("Employees", f"{profile.employees:,}" if profile.employees else "N/A")
            cols[2].metric("Exchange", profile.exchange or "N/A")

            if profile.website:
                st.markdown(f"[{profile.website}]({profile.website})")

            if profile.description:
                st.write(profile.description)
            else:
                st.caption("No business description available for this ticker.")

    with price_tab:
        by_date = df.set_index("date")
        st.line_chart(by_date[["close"]])
        st.bar_chart(by_date[["volume"]])

    with indicators_tab:
        st.dataframe(
            df.sort_values("date", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "flagged": st.column_config.CheckboxColumn("Flagged"),
                "score": st.column_config.NumberColumn("Score", format="%.2f"),
                "commentary": st.column_config.TextColumn("AI Commentary", width="large"),
            },
        )

    with commentary_tab:
        commentary_history = df[df["commentary"].notna()].sort_values("date", ascending=False)
        if commentary_history.empty:
            st.caption("No AI commentary recorded yet for this ticker.")
        else:
            for _, row in commentary_history.iterrows():
                st.markdown(f"**{row['date']}**")
                st.write(row["commentary"])

    with news_tab:
        articles = [a for a in NewsRepository().get_scored_articles() if a.ticker == ticker]

        if not articles:
            st.info(
                "No scored news articles yet for this ticker. Run the pipeline first: "
                "`uv run python -m stocks_research.news.pipeline`"
            )
        else:
            available_days = len({a.published_at.date() for a in articles})
            if available_days <= 1:
                st.caption("Only one day of data so far -- the window slider needs at least two.")
                news_days = available_days
            else:
                news_days = st.slider(
                    "Days to consider",
                    min_value=1,
                    max_value=available_days,
                    value=min(DEFAULT_WINDOW_DAYS, available_days),
                )

            summaries = summarize_news_trends(articles, days=news_days)

            if not summaries:
                st.info("No scored news in the selected window.")
            else:
                summary = summaries[0]
                st.caption(
                    f"{summary.article_count} article(s) across the last {news_days} day(s) of data -- "
                    f"sentiment is {summary.sentiment_direction}."
                )

                daily = pd.DataFrame(
                    [
                        {"date": a.published_at.date(), "sentiment_score": a.sentiment_score}
                        for a in windowed_articles(articles, days=news_days)
                    ]
                )
                daily_avg = daily.groupby("date")["sentiment_score"].mean()
                st.line_chart(daily_avg)

                articles_df = pd.DataFrame(
                    [
                        {
                            "published_at": a.published_at,
                            "headline": a.headline,
                            "source": a.source,
                            "sentiment_score": a.sentiment_score,
                        }
                        for a in windowed_articles(articles, days=news_days)
                    ]
                ).sort_values("published_at", ascending=False)

                st.dataframe(
                    articles_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "published_at": st.column_config.DatetimeColumn("Published"),
                        "headline": st.column_config.TextColumn("Headline", width="large"),
                        "sentiment_score": st.column_config.NumberColumn("Sentiment", format="%.2f"),
                    },
                )
