import streamlit as st

from stocks_research.news.data import NewsArticle
from stocks_research.news.trends import DEFAULT_WINDOW_DAYS


def days_window_slider(articles: list[NewsArticle]) -> int:
    """Renders the "Days to consider" window slider, or a caption when there's under two days of data."""
    available_days = len({a.published_at.date() for a in articles})
    if available_days <= 1:
        st.caption("Only one day of data so far -- the window slider needs at least two.")
        return available_days

    return st.slider(
        "Days to consider",
        min_value=1,
        max_value=available_days,
        value=min(DEFAULT_WINDOW_DAYS, available_days),
    )
