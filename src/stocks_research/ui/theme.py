import streamlit as st

APP_TITLE = "Stocks Research"

_CSS = """
<style>
/* Tighter top spacing, comfortable side gutters on small screens */
.block-container {
    padding-top: 2.5rem;
    padding-bottom: 3rem;
}
@media (max-width: 640px) {
    .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }
}

/* Metric cards */
div[data-testid="stMetric"] {
    background: var(--secondary-background-color);
    border: 1px solid var(--border-color, rgba(128, 128, 128, 0.25));
    border-radius: 0.75rem;
    padding: 0.9rem 1.1rem;
}
div[data-testid="stMetricLabel"] {
    font-size: 0.8rem;
    opacity: 0.75;
}

h1 {
    font-weight: 700 !important;
    letter-spacing: -0.02em;
}

button[data-testid="stTab"] {
    font-weight: 600;
}
</style>
"""

_TREND_BADGES = {
    "bullish": ("Bullish", ":material/trending_up:", "green"),
    "bearish": ("Bearish", ":material/trending_down:", "red"),
    "neutral": ("Neutral", ":material/trending_flat:", "gray"),
}

_VERDICT_BADGES = {
    "Strong Buy": (":material/thumb_up:", "green"),
    "Buy": (":material/thumb_up:", "blue"),
    "Hold": (":material/pause_circle:", "orange"),
    "Avoid": (":material/thumb_down:", "red"),
    "Insufficient Data": (":material/help:", "gray"),
}


def configure_app() -> None:
    """Set page config and inject shared styles. Call once, first, from app.py."""
    st.set_page_config(page_title=APP_TITLE, page_icon="📊", layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)


def trend_badge(trend: str) -> None:
    label, icon, color = _TREND_BADGES.get(trend, (trend.title(), None, "gray"))
    st.badge(label, icon=icon, color=color)


def verdict_badge(verdict: str) -> None:
    icon, color = _VERDICT_BADGES.get(verdict, (None, "gray"))
    st.badge(verdict, icon=icon, color=color)
