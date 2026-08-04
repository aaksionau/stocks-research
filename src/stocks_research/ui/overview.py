import pandas as pd
import streamlit as st

from stocks_research.repository import SnapshotRepository

st.set_page_config(page_title="Stocks Research — Overview", layout="wide")
st.title("Overview")

snapshots = SnapshotRepository().get_latest_snapshots()

if not snapshots:
    st.info("No snapshots yet. Run the pipeline first: `uv run python -m stocks_research.pipeline`")
else:
    df = pd.DataFrame([vars(s) for s in snapshots]).sort_values("ticker")

    ticker_filter = st.text_input("Filter by ticker")
    trend_filter = st.multiselect(
        "Filter by MA trend", options=sorted(df["ma_trend"].unique()), default=[]
    )

    if ticker_filter:
        df = df[df["ticker"].str.contains(ticker_filter, case=False)]
    if trend_filter:
        df = df[df["ma_trend"].isin(trend_filter)]

    st.caption(f"{len(df)} of {len(snapshots)} tickers")
    st.dataframe(df, use_container_width=True, hide_index=True)
