import pandas as pd
import streamlit as st

from stocks_research.market.repository import SnapshotRepository
from stocks_research.market.trends import DEFAULT_WINDOW_DAYS, summarize_trends

st.title("Trends Over Time")

repository = SnapshotRepository()
available_days = repository.get_distinct_date_count()

if available_days == 0:
    st.info("No snapshots yet. Run the pipeline first: `uv run python -m stocks_research.market.pipeline`")
else:
    st.caption("Which tickers have been flagged most often over a recent window of days.")

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

    summaries = summarize_trends(repository.get_recent_flag_rows(days), days=days)

    if not summaries:
        st.info("No tickers were flagged in the selected window.")
    else:
        df = pd.DataFrame([vars(t) for t in summaries])

        kpi_cols = st.columns(3)
        kpi_cols[0].metric("Tickers Flagged", len(df))
        kpi_cols[1].metric("Days Considered", summaries[0].days_considered)
        kpi_cols[2].metric("Avg Score (flagged)", f"{df['avg_score'].mean():.2f}")

        st.caption(f"Top tickers by how often they were flagged in the last {summaries[0].days_considered} day(s).")
        st.bar_chart(df.set_index("ticker")["flag_count"].head(20))

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "flag_count": st.column_config.NumberColumn("Times Flagged"),
                "avg_score": st.column_config.NumberColumn("Avg Score", format="%.2f"),
                "last_flagged_date": st.column_config.DateColumn("Last Flagged"),
            },
        )
