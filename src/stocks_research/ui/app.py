import streamlit as st

from stocks_research.market.repository import SnapshotRepository
from stocks_research.news.repository import NewsRepository


@st.cache_resource
def _ensure_schema() -> None:
    # Pages query these tables directly without creating them -- normally fine
    # since the batch pipelines create them on their first run, but a fresh
    # deploy of the web UI ahead of (or without) a pipeline run would otherwise
    # hard-crash a page with UndefinedTable instead of showing "no data yet".
    SnapshotRepository().ensure_schema()
    NewsRepository().ensure_schema()


_ensure_schema()

overview = st.Page("overview.py", title="Overview", icon="📊", default=True)
ticker_detail = st.Page("ticker_detail.py", title="Ticker Detail", icon="🔍")
trends = st.Page("trends.py", title="Trends", icon="📈")
news_trends = st.Page("news_trends.py", title="News Trends", icon="📰")

pg = st.navigation([overview, ticker_detail, trends, news_trends], position="top")
st.set_page_config(page_title="Stocks Research", layout="wide")
pg.run()
