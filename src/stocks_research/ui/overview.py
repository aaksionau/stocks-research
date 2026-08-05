import pandas as pd
import streamlit as st

from stocks_research.company.repository import CompanyProfileRepository
from stocks_research.market import signals
from stocks_research.market.repository import SnapshotRepository
from stocks_research.news.subscriptions import NewsSubscriptionRepository
from stocks_research.ui.theme import verdict_label

st.title("Overview")


@st.cache_data(ttl=300)
def _get_all_profiles() -> dict:
    # Company profiles only change on a (much less frequent) manual pipeline run,
    # so caching avoids re-querying all ~500 rows on every filter/selection rerun.
    return CompanyProfileRepository().get_all_profiles()


snapshots = SnapshotRepository().get_latest_snapshots()

if not snapshots:
    st.info("No snapshots yet. Run the pipeline first: `uv run python -m stocks_research.market.pipeline`")
else:
    st.caption("Latest daily snapshot across your tracked tickers · click a ticker to open its drill-down view.")

    profiles = _get_all_profiles()
    rows = [
        {**vars(s), "buy_verdict": signals.evaluate(s, profiles.get(s.ticker)).verdict} for s in snapshots
    ]
    df = pd.DataFrame(rows).sort_values("ticker")
    trend_counts = df["ma_trend"].value_counts()

    kpi_cols = st.columns(5)
    kpi_cols[0].metric("Tickers Tracked", len(df))
    kpi_cols[1].metric("Flagged", int(df["flagged"].sum()))
    kpi_cols[2].metric("Bullish", int(trend_counts.get("bullish", 0)))
    kpi_cols[3].metric("Bearish", int(trend_counts.get("bearish", 0)))
    kpi_cols[4].metric(
        "News Tracked",
        NewsSubscriptionRepository().get_subscribed_ticker_count(),
        help="Tickers subscribed for news sentiment fetching -- keeps an eye on API spend.",
    )

    with st.container(border=True):
        filter_cols = st.columns([2, 2, 2])
        ticker_filter = filter_cols[0].text_input("Filter by ticker", placeholder="e.g. AAPL")
        trend_filter = filter_cols[1].multiselect(
            "Filter by MA trend", options=sorted(df["ma_trend"].unique()), default=[]
        )
        verdict_filter = filter_cols[2].multiselect(
            "Filter by Buy Signal",
            options=[signals.STRONG_BUY, signals.BUY, signals.HOLD, signals.AVOID, signals.INSUFFICIENT_DATA],
            default=[],
        )
        quick_filter = st.segmented_control(
            "Quick filter",
            options=["All", "Flagged only", "Bearish + flagged"],
            default="All",
            required=True,
        )

    if ticker_filter:
        df = df[df["ticker"].str.contains(ticker_filter, case=False)]
    if trend_filter:
        df = df[df["ma_trend"].isin(trend_filter)]
    if verdict_filter:
        df = df[df["buy_verdict"].isin(verdict_filter)]
    if quick_filter == "Flagged only":
        df = df[df["flagged"]]
    elif quick_filter == "Bearish + flagged":
        df = df[df["flagged"] & (df["ma_trend"] == "bearish")]

    df = df.sort_values(["flagged", "score"], ascending=[False, False])

    st.caption(
        f"{len(df)} of {len(snapshots)} tickers shown ({int(df['flagged'].sum())} flagged in view) · "
        "full history and price charts live on the Ticker Detail page."
    )

    TREND_ICON = {"bullish": "📈 Bullish", "bearish": "📉 Bearish", "neutral": "➖ Neutral"}
    display_df = df.copy()
    display_df["ticker"] = "/ticker_detail?ticker=" + display_df["ticker"]
    display_df["flagged"] = display_df["flagged"].map({True: "🚩", False: ""})
    display_df["ma_trend"] = display_df["ma_trend"].map(TREND_ICON).fillna(display_df["ma_trend"])
    display_df["buy_verdict"] = display_df["buy_verdict"].apply(verdict_label)
    display_df["volume_ratio"] = display_df["volume_ratio"].apply(
        lambda ratio: f"🔥 {ratio:.2f}" if ratio is not None and ratio >= 2 else ratio
    )

    def _momentum_color(value: float | None) -> str:
        if value is None:
            return ""
        return "color: #16a34a" if value > 0 else "color: #dc2626" if value < 0 else ""

    styled_df = display_df.style.map(
        _momentum_color, subset=["momentum_1d", "momentum_5d", "momentum_20d"]
    )

    score_max = df["score"].max()
    score_max = float(score_max) if pd.notna(score_max) else 1.0

    st.dataframe(
        styled_df,
        width="stretch",
        height=560,
        hide_index=True,
        column_order=[
            "ticker",
            "flagged",
            "buy_verdict",
            "score",
            "ma_trend",
            "momentum_1d",
            "momentum_5d",
            "momentum_20d",
            "volume_ratio",
            "commentary",
        ],
        column_config={
            "ticker": st.column_config.LinkColumn("Ticker", width="small", display_text=r"ticker=(\w+)"),
            "flagged": st.column_config.TextColumn("Flagged", width="small"),
            "buy_verdict": st.column_config.TextColumn("Buy Signal"),
            "score": st.column_config.ProgressColumn(
                "Score", format="%.2f", min_value=0, max_value=max(score_max, 1.0)
            ),
            "ma_trend": st.column_config.TextColumn("MA Trend"),
            "momentum_1d": st.column_config.NumberColumn("1D %", format="%.2f"),
            "momentum_5d": st.column_config.NumberColumn("5D %", format="%.2f"),
            "momentum_20d": st.column_config.NumberColumn("20D %", format="%.2f"),
            "volume_ratio": st.column_config.TextColumn("Vol Ratio"),
            "commentary": st.column_config.TextColumn("AI Commentary", width="large"),
        },
    )
