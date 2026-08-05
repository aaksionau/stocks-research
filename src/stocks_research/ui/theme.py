import pandas as pd
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
    "Strong Buy": ("🟢", ":material/thumb_up:", "green"),
    "Buy": ("🔵", ":material/thumb_up:", "blue"),
    "Hold": ("🟡", ":material/pause_circle:", "orange"),
    "Avoid": ("🔴", ":material/thumb_down:", "red"),
    "Insufficient Data": ("⚪", ":material/help:", "gray"),
}

_BADGE_COLOR_RGB = {
    "green": (46, 160, 67),
    "blue": (59, 130, 246),
    "orange": (245, 158, 11),
    "red": (226, 59, 59),
    "gray": (139, 139, 139),
}

_SENTIMENT_DIRECTION_LABELS = {
    "rising": "📈 Rising",
    "falling": "📉 Falling",
    "flat": "➡️ Flat",
}


def configure_app() -> None:
    """Set page config and inject shared styles. Call once, first, from app.py."""
    st.set_page_config(page_title=APP_TITLE, page_icon="📊", layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)


def trend_badge(trend: str) -> None:
    label, icon, color = _TREND_BADGES.get(trend, (trend.title(), None, "gray"))
    st.badge(label, icon=icon, color=color)


def verdict_badge(verdict: str) -> None:
    _emoji, icon, color = _VERDICT_BADGES.get(verdict, ("⚪", None, "gray"))
    st.badge(verdict, icon=icon, color=color)


def verdict_label(verdict: str) -> str:
    """Plain-text emoji + verdict, for contexts (e.g. dataframe cells) that can't render st.badge."""
    emoji, _icon, _color = _VERDICT_BADGES.get(verdict, ("⚪", None, "gray"))
    return f"{emoji} {verdict}"


def render_price_metrics(cols, close: float, momentum_1d, momentum_5d, momentum_20d) -> None:
    """Close/5D/20D metric tiles shared by Ticker Detail's header and the Watchlist cards.

    Momentum args accept None or NaN (pd.notna handles both) since callers source them
    from either a DataFrame row or an IndicatorSnapshot dataclass.
    """
    cols[0].metric(
        "Close",
        f"${close:,.2f}",
        delta=f"{momentum_1d:+.2f}%" if pd.notna(momentum_1d) else None,
    )
    cols[1].metric("5D", f"{momentum_5d:+.2f}%" if pd.notna(momentum_5d) else "N/A")
    cols[2].metric("20D", f"{momentum_20d:+.2f}%" if pd.notna(momentum_20d) else "N/A")


def _colored_metric_card(col, label: str, value: str, is_positive: bool | None, delta: str | None = None) -> None:
    """Metric card whose background tints green/red by sign, with an optional delta pinned to the right.

    Used by the Watchlist, which (unlike Ticker Detail's render_price_metrics) wants each
    block color-coded and the Close block's up/down change shown beside the value rather than below it.
    """
    if is_positive is None:
        bg, border = "var(--secondary-background-color)", "rgba(128, 128, 128, 0.25)"
    elif is_positive:
        bg, border = "rgba(46, 160, 67, 0.15)", "rgba(46, 160, 67, 0.4)"
    else:
        bg, border = "rgba(226, 59, 59, 0.15)", "rgba(226, 59, 59, 0.4)"

    delta_html = ""
    if delta is not None:
        arrow = "▲" if is_positive else "▼"
        delta_color = "#2ea043" if is_positive else "#e23b3b"
        delta_html = f'<div style="color:{delta_color}; font-weight:600; font-size:0.95rem;">{arrow} {delta}</div>'

    col.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center;
                    background:{bg}; border:1px solid {border}; border-radius:0.75rem;
                    padding:0.9rem 1.1rem;">
            <div>
                <div style="font-size:0.8rem; opacity:0.75;">{label}</div>
                <div style="font-size:1.5rem; font-weight:600;">{value}</div>
            </div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_watchlist_metrics(cols, close: float, momentum_1d, momentum_5d, momentum_20d) -> None:
    """Close/5D/20D cards for the Watchlist: color-coded by sign, Close's change shown to the right."""
    close_positive = bool(momentum_1d >= 0) if pd.notna(momentum_1d) else None
    _colored_metric_card(
        cols[0],
        "Close",
        f"${close:,.2f}",
        close_positive,
        delta=f"{momentum_1d:+.2f}%" if pd.notna(momentum_1d) else None,
    )

    for col, label, momentum in zip(cols[1:], ("5D", "20D"), (momentum_5d, momentum_20d)):
        positive = bool(momentum >= 0) if pd.notna(momentum) else None
        _colored_metric_card(col, label, f"{momentum:+.2f}%" if pd.notna(momentum) else "N/A", positive)


def render_verdict_card(col, verdict: str) -> None:
    """Buy Signal card for the Watchlist, tinted to match the same verdict colors as verdict_badge."""
    _emoji, _icon, color_name = _VERDICT_BADGES.get(verdict, ("⚪", None, "gray"))
    r, g, b = _BADGE_COLOR_RGB.get(color_name, _BADGE_COLOR_RGB["gray"])
    bg, border = f"rgba({r}, {g}, {b}, 0.15)", f"rgba({r}, {g}, {b}, 0.4)"

    col.markdown(
        f"""
        <div style="background:{bg}; border:1px solid {border}; border-radius:0.75rem;
                    padding:0.9rem 1.1rem;">
            <div style="font-size:0.8rem; opacity:0.75;">Buy Signal</div>
            <div style="font-size:1.25rem; font-weight:600;">{verdict_label(verdict)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sentiment_direction_label(direction: str) -> str:
    """Plain-text emoji + direction, for contexts (e.g. dataframe cells) that can't render st.badge."""
    return _SENTIMENT_DIRECTION_LABELS.get(direction, direction.title())
