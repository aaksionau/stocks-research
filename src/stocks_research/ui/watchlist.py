import pandas as pd
import streamlit as st

from stocks_research.market.repository import SnapshotRepository
from stocks_research.ui.theme import trend_badge
from stocks_research.watchlist.repository import WatchlistRepository

st.title("⭐ Watchlist")

watchlist_repository = WatchlistRepository()
followed_tickers = watchlist_repository.get_followed_tickers()

if not followed_tickers:
    st.info(
        "No tickers followed yet -- open a ticker's detail page and toggle \"⭐ Follow\" to add it here."
    )
else:
    snapshot_repository = SnapshotRepository()
    st.caption(f"Following {len(followed_tickers)} ticker(s) · click a ticker to open its full detail view.")

    for ticker in followed_tickers:
        history = snapshot_repository.get_ticker_history(ticker)
        with st.container(border=True):
            header_cols = st.columns([2, 1, 1, 1, 1])
            with header_cols[0]:
                st.markdown(f"#### [{ticker}](/ticker_detail?ticker={ticker})")
                if history:
                    trend_badge(history[-1].ma_trend)

            if not history:
                header_cols[1].caption("No snapshot data yet.")
            else:
                latest = history[-1]
                header_cols[1].metric(
                    "Close",
                    f"${latest.close:,.2f}",
                    delta=f"{latest.momentum_1d:+.2f}%" if latest.momentum_1d is not None else None,
                )
                header_cols[2].metric(
                    "5D", f"{latest.momentum_5d:+.2f}%" if latest.momentum_5d is not None else "N/A"
                )
                header_cols[3].metric(
                    "20D", f"{latest.momentum_20d:+.2f}%" if latest.momentum_20d is not None else "N/A"
                )

            if header_cols[4].button("Unfollow", key=f"unfollow_{ticker}"):
                watchlist_repository.unfollow(ticker)
                st.rerun()

            if history:
                df = pd.DataFrame([vars(s) for s in history]).sort_values("date").set_index("date")
                st.line_chart(df[["close"]])
