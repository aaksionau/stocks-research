import pandas as pd
import streamlit as st

from stocks_research.repository import SnapshotRepository

st.title("Ticker Detail")

repository = SnapshotRepository()
tickers = sorted(s.ticker for s in repository.get_latest_snapshots())

if not tickers:
    st.info("No snapshots yet. Run the pipeline first: `uv run python -m stocks_research.pipeline`")
else:
    preselected = st.session_state.get("selected_ticker") or st.query_params.get("ticker")
    default_index = tickers.index(preselected) if preselected in tickers else 0

    ticker = st.selectbox("Ticker", tickers, index=default_index)
    st.session_state["selected_ticker"] = ticker
    st.query_params["ticker"] = ticker

    history = repository.get_ticker_history(ticker)
    df = pd.DataFrame([vars(s) for s in history]).sort_values("date")

    st.subheader(f"{ticker} — price & volume")
    by_date = df.set_index("date")
    st.line_chart(by_date[["close"]])
    st.bar_chart(by_date[["volume"]])

    st.subheader("Indicator history")
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

    st.subheader("AI commentary history")
    commentary_history = df[df["commentary"].notna()].sort_values("date", ascending=False)
    if commentary_history.empty:
        st.caption("No AI commentary recorded yet for this ticker.")
    else:
        for _, row in commentary_history.iterrows():
            st.markdown(f"**{row['date']}**")
            st.write(row["commentary"])
