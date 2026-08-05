import pandas as pd
import streamlit as st

from stocks_research.company.repository import CompanyProfileRepository
from stocks_research.market import signals
from stocks_research.market.repository import SnapshotRepository
from stocks_research.news.repository import NewsRepository
from stocks_research.news.subscriptions import NewsSubscriptionRepository
from stocks_research.news.trends import summarize_ticker_trend, windowed_articles
from stocks_research.ui.news_widgets import days_window_slider
from stocks_research.ui.theme import sentiment_direction_label, trend_badge, verdict_badge

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
    latest_snapshot = history[-1]
    df = pd.DataFrame([vars(s) for s in history]).sort_values("date")
    latest = df.iloc[-1]

    profile = CompanyProfileRepository().get_profile(ticker)
    news_repository = NewsRepository()
    subscription_repository = NewsSubscriptionRepository()
    is_subscribed = subscription_repository.is_subscribed(ticker)

    with st.container(border=True):
        header_cols = st.columns([2, 1.2, 1, 1, 1])
        with header_cols[0]:
            st.markdown(f"### {ticker}")
            trend_badge(latest["ma_trend"])
            if latest["flagged"]:
                st.badge("Flagged", icon=":material/flag:", color="orange")
            track_news = st.toggle("📰 Track news", value=is_subscribed, key=f"news_toggle_{ticker}")
            if track_news != is_subscribed:
                (subscription_repository.subscribe if track_news else subscription_repository.unsubscribe)(ticker)
                is_subscribed = track_news
        header_cols[1].metric(
            "Close",
            f"${latest['close']:,.2f}",
            delta=f"{latest['momentum_1d']:+.2f}%" if pd.notna(latest["momentum_1d"]) else None,
        )
        header_cols[2].metric(
            "5D", f"{latest['momentum_5d']:+.2f}%" if pd.notna(latest["momentum_5d"]) else "N/A"
        )
        header_cols[3].metric(
            "20D", f"{latest['momentum_20d']:+.2f}%" if pd.notna(latest["momentum_20d"]) else "N/A"
        )
        header_cols[4].metric("Score", f"{latest['score']:.2f}" if pd.notna(latest["score"]) else "N/A")

    CHECK_ICON = {True: ":material/check_circle:", False: ":material/cancel:", None: ":material/help:"}
    with st.container(border=True):
        signal = signals.evaluate(latest_snapshot, profile)
        st.markdown("##### Long-Term Buy Signal")
        verdict_badge(signal.verdict)
        for check in signal.checks:
            st.markdown(f"{CHECK_ICON[check.passed]} **{check.name}** -- {check.detail}")

    overview_tab, price_tab, indicators_tab, commentary_tab, news_tab = st.tabs(
        ["Company Overview", "Price & Volume", "Indicator History", "AI Commentary", "News Sentiment"]
    )

    with overview_tab:
        if profile is None:
            st.info(
                "No company profile yet for this ticker. Run the pipeline first: "
                "`uv run python -m stocks_research.company.pipeline`"
            )
        else:

            def _format_market_cap(value: int | None) -> str:
                if not value:
                    return "N/A"
                for threshold, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
                    if value >= threshold:
                        return f"${value / threshold:,.2f}{suffix}"
                return f"${value:,.0f}"

            st.subheader(profile.name or ticker)
            st.caption(" · ".join(filter(None, [profile.sector, profile.industry, profile.country])))

            cols = st.columns(3)
            cols[0].metric("Market Cap", _format_market_cap(profile.market_cap))
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
            column_order=[
                "date",
                "close",
                "flagged",
                "score",
                "ma_trend",
                "momentum_1d",
                "momentum_5d",
                "momentum_20d",
                "pct_above_ma50",
                "volume",
                "volume_ratio",
                "commentary",
            ],
            column_config={
                "date": st.column_config.DateColumn("Date"),
                "close": st.column_config.NumberColumn("Close", format="$%.2f"),
                "flagged": st.column_config.CheckboxColumn("Flagged"),
                "score": st.column_config.NumberColumn("Score", format="%.2f"),
                "ma_trend": st.column_config.TextColumn("MA Trend"),
                "momentum_1d": st.column_config.NumberColumn("1D %", format="%.2f"),
                "momentum_5d": st.column_config.NumberColumn("5D %", format="%.2f"),
                "momentum_20d": st.column_config.NumberColumn("20D %", format="%.2f"),
                "pct_above_ma50": st.column_config.NumberColumn("Above MA50 %", format="%.2f"),
                "volume": st.column_config.NumberColumn("Volume", format="%d"),
                "volume_ratio": st.column_config.NumberColumn("Vol Ratio", format="%.2f"),
                "commentary": st.column_config.TextColumn("AI Commentary", width="large"),
            },
        )

    with commentary_tab:
        commentary_history = df[df["commentary"].notna()].sort_values("date", ascending=False)
        if commentary_history.empty:
            st.caption("No AI commentary recorded yet for this ticker.")
        else:
            for _, row in commentary_history.iterrows():
                with st.container(border=True):
                    st.caption(str(row["date"]))
                    st.write(row["commentary"])

    with news_tab:
        articles = news_repository.get_scored_articles(ticker)

        if not articles:
            if not is_subscribed:
                st.info("Not tracking this ticker yet -- toggle \"Track news\" above to include it in news fetching.")
            else:
                st.info(
                    "No scored news articles yet for this ticker. Run the pipeline first: "
                    "`uv run python -m stocks_research.news.pipeline`"
                )
        else:
            news_days = days_window_slider(articles)
            window = windowed_articles(articles, days=news_days)

            if not window:
                st.info("No scored news in the selected window.")
            else:
                summary = summarize_ticker_trend(window)

                summary_cols = st.columns(3)
                summary_cols[0].metric("Articles", summary.article_count)
                summary_cols[1].metric("Avg Sentiment", f"{summary.avg_sentiment:+.2f}")
                summary_cols[2].metric("Direction", sentiment_direction_label(summary.sentiment_direction))

                daily = pd.DataFrame(
                    [{"date": a.published_at.date(), "sentiment_score": a.sentiment_score} for a in window]
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
                        for a in window
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
