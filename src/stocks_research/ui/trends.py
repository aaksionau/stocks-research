import pandas as pd
import streamlit as st

from stocks_research.repository import SnapshotRepository
from stocks_research.trends import DEFAULT_WINDOW_DAYS, summarize_trends

st.title("Trends Over Time")

snapshots = SnapshotRepository().get_all_snapshots()

if not snapshots:
    st.info("No snapshots yet. Run the pipeline first: `uv run python -m stocks_research.pipeline`")
else:
    available_days = len({s.date for s in snapshots})
    days = st.slider(
        "Days to consider",
        min_value=1,
        max_value=available_days,
        value=min(DEFAULT_WINDOW_DAYS, available_days),
    )

    summaries = summarize_trends(snapshots, days=days)

    if not summaries:
        st.info("No tickers were flagged in the selected window.")
    else:
        df = pd.DataFrame([vars(t) for t in summaries])

        st.caption(
            f"{len(df)} ticker(s) flagged at least once across the last "
            f"{summaries[0].days_considered} day(s) of data."
        )

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
