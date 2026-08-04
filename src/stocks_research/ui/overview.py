import pandas as pd
import streamlit as st

from stocks_research.repository import SnapshotRepository

st.title("Overview")

snapshots = SnapshotRepository().get_latest_snapshots()

if not snapshots:
    st.info("No snapshots yet. Run the pipeline first: `uv run python -m stocks_research.pipeline`")
else:
    df = pd.DataFrame([vars(s) for s in snapshots]).sort_values("ticker")

    filter_cols = st.columns([2, 2, 1, 1])
    ticker_filter = filter_cols[0].text_input("Filter by ticker")
    trend_filter = filter_cols[1].multiselect(
        "Filter by MA trend", options=sorted(df["ma_trend"].unique()), default=[]
    )
    flagged_only = filter_cols[2].checkbox("Flagged only")
    bearish_flagged_only = filter_cols[3].checkbox("Bearish + flagged")

    if ticker_filter:
        df = df[df["ticker"].str.contains(ticker_filter, case=False)]
    if trend_filter:
        df = df[df["ma_trend"].isin(trend_filter)]
    if flagged_only:
        df = df[df["flagged"]]
    if bearish_flagged_only:
        df = df[df["flagged"] & (df["ma_trend"] == "bearish")]

    df = df.sort_values(["flagged", "score"], ascending=[False, False])

    st.caption(
        f"{len(df)} of {len(snapshots)} tickers ({df['flagged'].sum()} flagged) "
        "· Select a row to open that ticker's drill-down view."
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
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "flagged": st.column_config.TextColumn("Flagged", width="small"),
            "score": st.column_config.ProgressColumn(
                "Score", format="%.2f", min_value=0, max_value=max(score_max, 1.0)
            ),
            "ma_trend": st.column_config.TextColumn("MA Trend"),
            "volume_ratio": st.column_config.TextColumn("Vol Ratio"),
            "commentary": st.column_config.TextColumn("AI Commentary", width="large"),
        },
    )

    selected_rows = event.selection.rows if event and event.selection else []
    if selected_rows:
        st.session_state["selected_ticker"] = df.iloc[selected_rows[0]]["ticker"]
        st.switch_page("ticker_detail.py")
