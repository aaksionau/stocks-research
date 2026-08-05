import pandas as pd
import streamlit as st

from stocks_research.company.repository import CompanyProfileRepository
from stocks_research.market import signals
from stocks_research.market.repository import SnapshotRepository
from stocks_research.ui.theme import render_verdict_card, render_watchlist_metrics, trend_badge
from stocks_research.watchlist.repository import WatchlistRepository

st.title("⭐ Watchlist")

watchlist_repository = WatchlistRepository()
followed_tickers = watchlist_repository.get_followed_tickers()

if not followed_tickers:
    st.info('No tickers followed yet -- open a ticker\'s detail page and toggle "⭐ Follow" to add it here.')
else:
    histories = SnapshotRepository().get_ticker_histories(followed_tickers)
    profiles = CompanyProfileRepository().get_all_profiles()
    st.caption(f"Following {len(followed_tickers)} ticker(s) · click a ticker to open its full detail view.")

    for ticker in followed_tickers:
        history = histories[ticker]
        with st.container(border=True):
            header_cols = st.columns([2, 1, 1, 1, 1, 1])
            with header_cols[0]:
                st.markdown(f"#### [{ticker}](/ticker_detail?ticker={ticker})")
                if history:
                    trend_badge(history[-1].ma_trend)

            if header_cols[5].button("Unfollow", key=f"unfollow_{ticker}"):
                watchlist_repository.unfollow(ticker)
                st.rerun()

            if not history:
                header_cols[1].caption("No snapshot data yet.")
            else:
                latest = history[-1]
                render_watchlist_metrics(
                    header_cols[1:4], latest.close, latest.momentum_1d, latest.momentum_5d, latest.momentum_20d
                )
                signal = signals.evaluate(latest, profiles.get(ticker))
                render_verdict_card(header_cols[4], signal.verdict)
                df = pd.DataFrame([vars(s) for s in history]).sort_values("date").set_index("date")
                st.line_chart(df[["close"]])
