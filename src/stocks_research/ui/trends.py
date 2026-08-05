import pandas as pd
import streamlit as st

from stocks_research.company.profile import CompanyProfile
from stocks_research.company.repository import CompanyProfileRepository
from stocks_research.market.repository import SnapshotRepository
from stocks_research.market.trends import DEFAULT_WINDOW_DAYS, MAX_WINDOW_DAYS, TrendSummary, summarize_buy_signal_trends

st.title("Trends Over Time")


@st.cache_data(ttl=300)
def _get_all_profiles() -> dict[str, CompanyProfile]:
    # Company profiles only change on a (much less frequent) manual pipeline run,
    # so caching avoids re-fetching all ~500 rows on every slider drag.
    return CompanyProfileRepository().get_all_profiles()


@st.cache_data(ttl=300)
def _load_trend_summaries(days: int) -> list[TrendSummary]:
    # Recomputing evaluate() over the full history (600K+ rows) takes 70+ seconds; caching
    # per window size keeps repeat slider drags to the same value effectively instant.
    rows = SnapshotRepository().get_recent_indicator_rows(days)
    return summarize_buy_signal_trends(rows, _get_all_profiles(), days=days)


repository = SnapshotRepository()
available_days = repository.get_distinct_date_count()

if available_days == 0:
    st.info("No snapshots yet. Run the pipeline first: `uv run python -m stocks_research.market.pipeline`")
else:
    max_days = min(available_days, MAX_WINDOW_DAYS)
    st.caption(
        "Which tickers have trended toward a Buy signal recently -- recomputed using today's "
        "fundamentals, so this reflects current valuation/quality applied to past price action, "
        "not what Overview showed on that day."
    )

    if max_days <= 1:
        st.caption("Only one day of data so far -- the window slider needs at least two.")
        days = max_days
    else:
        days = st.slider(
            "Days to consider",
            min_value=1,
            max_value=max_days,
            value=min(DEFAULT_WINDOW_DAYS, max_days),
        )

    summaries = _load_trend_summaries(days)

    if not summaries:
        st.info("No tickers trended toward a Buy signal in the selected window.")
    else:
        df = pd.DataFrame([vars(t) for t in summaries])

        kpi_cols = st.columns(3)
        kpi_cols[0].metric("Tickers Trending", len(df))
        kpi_cols[1].metric("Days Considered", summaries[0].days_considered)
        kpi_cols[2].metric("Avg Buy Signal Days", f"{df['buy_signal_count'].mean():.1f}")

        st.caption(f"Top tickers by Buy Signal frequency over the last {summaries[0].days_considered} day(s).")
        st.bar_chart(df.set_index("ticker")["buy_signal_count"].head(20))

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "buy_signal_count": st.column_config.NumberColumn(
                    "Buy Signal Days",
                    help=(
                        "Days in the window with a Strong Buy/Buy verdict, recomputed using today's "
                        "fundamentals -- not an archived historical record."
                    ),
                ),
                "strong_buy_count": st.column_config.NumberColumn("Strong Buy Days"),
                "last_buy_date": st.column_config.DateColumn("Last Buy Signal"),
            },
        )
