import streamlit as st

overview = st.Page("overview.py", title="Overview", icon="📊", default=True)
ticker_detail = st.Page("ticker_detail.py", title="Ticker Detail", icon="🔍")

pg = st.navigation([overview, ticker_detail])
st.set_page_config(page_title="Stocks Research", layout="wide")
pg.run()
