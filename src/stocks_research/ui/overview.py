import pandas as pd
import streamlit as st

from stocks_research.market.repository import SnapshotRepository

st.title("Overview")

snapshots = SnapshotRepository().get_latest_snapshots()

if not snapshots:
    st.info("No snapshots yet. Run the pipeline first: `uv run python -m stocks_research.market.pipeline`")
else:
    st.caption("Latest daily snapshot across your tracked tickers · tap a row to open its drill-down view.")

    df = pd.DataFrame([vars(s) for s in snapshots]).sort_values("ticker")
    trend_counts = df["ma_trend"].value_counts()

    kpi_cols = st.columns(4)
    kpi_cols[0].metric("Tickers Tracked", len(df))
    kpi_cols[1].metric("Flagged", int(df["flagged"].sum()))
    kpi_cols[2].metric("Bullish", int(trend_counts.get("bullish", 0)))
    kpi_cols[3].metric("Bearish", int(trend_counts.get("bearish", 0)))

    with st.container(border=True):
        filter_cols = st.columns([2, 2])
        ticker_filter = filter_cols[0].text_input("Filter by ticker", placeholder="e.g. AAPL")
        trend_filter = filter_cols[1].multiselect(
            "Filter by MA trend", options=sorted(df["ma_trend"].unique()), default=[]
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
    display_df["flagged"] = display_df["flagged"].map({True: "🚩", False: ""})
    display_df["ma_trend"] = display_df["ma_trend"].map(TREND_ICON).fillna(display_df["ma_trend"])
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

    event = st.dataframe(
        styled_df,
        width="stretch",
        height=560,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_order=[
            "ticker",
            "flagged",
            "score",
            "ma_trend",
            "momentum_1d",
            "momentum_5d",
            "momentum_20d",
            "volume_ratio",
            "commentary",
        ],
        column_config={
            "ticker": st.column_config.TextColumn("Ticker", width="small"),
            "flagged": st.column_config.TextColumn("Flagged", width="small"),
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

    selected_rows = event.selection.rows if event and event.selection else []
    if selected_rows:
        st.session_state["selected_ticker"] = df.iloc[selected_rows[0]]["ticker"]
        st.switch_page("ticker_detail.py")
