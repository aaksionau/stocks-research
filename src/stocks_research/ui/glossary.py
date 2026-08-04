import streamlit as st

st.title("Glossary")
st.caption("What the numbers and labels around this app actually mean.")

st.header("Price & momentum")

with st.container(border=True):
    st.markdown("**Close**")
    st.write("The ticker's most recent closing price.")

with st.container(border=True):
    st.markdown("**Momentum (1D / 5D / 20D)**")
    st.write(
        "The percentage change in close price over the last 1, 5, or 20 trading days. "
        "`momentum_5d = (close_today - close_5_days_ago) / close_5_days_ago * 100`. "
        "Positive means the price rose over that window, negative means it fell."
    )

st.header("Trend")

with st.container(border=True):
    st.markdown("**MA 50 / MA 200**")
    st.write(
        "The simple moving average of the close price over the last 50 or 200 trading days -- "
        "a smoothed-out view of the price that filters out day-to-day noise."
    )

with st.container(border=True):
    st.markdown("**MA Trend**")
    st.write(
        "Compares MA 50 to MA 200 to classify the medium-term trend: "
        "**Bullish** when MA 50 is above MA 200, **Bearish** when it's below, "
        "**Neutral** when they're equal or one can't be computed yet "
        "(needs 200 days of price history)."
    )

with st.container(border=True):
    st.markdown("**Above MA50 %**")
    st.write(
        "How far the current close is above (positive) or below (negative) its own 50-day "
        "moving average, as a percentage: `(close - MA50) / MA50 * 100`."
    )

st.header("Volume")

with st.container(border=True):
    st.markdown("**Volume**")
    st.write("Number of shares traded on the most recent day.")

with st.container(border=True):
    st.markdown("**Vol Ratio**")
    st.write(
        "Today's volume divided by the 20-day average volume. A ratio around 1.0 is normal "
        "trading activity; the 🔥 marker in the Overview table highlights ratios of 2.0 or "
        "higher -- roughly double the usual volume, often a sign something is moving the stock."
    )

st.header("Score & flagging")

with st.container(border=True):
    st.markdown("**Score**")
    st.write(
        "A single number combining three signals -- 20-day momentum, distance above/below the "
        "50-day moving average, and volume excess -- each converted to a z-score (how many "
        "standard deviations it is from that day's average across all tracked tickers) and "
        "summed. Higher scores mean a ticker stands out more from the pack that day; the score "
        "has no fixed range and is only meaningful relative to other tickers on the same day."
    )

with st.container(border=True):
    st.markdown("**Flagged**")
    st.write("The 30 tickers with the highest score on a given day are marked as flagged (🚩).")

with st.container(border=True):
    st.markdown("**AI Commentary**")
    st.write(
        "A short, auto-generated plain-language summary of a flagged ticker's day, produced by "
        "an LLM from that day's indicators. It's descriptive, not investment advice."
    )

st.header("News sentiment")

with st.container(border=True):
    st.markdown("**Sentiment score**")
    st.write(
        "An LLM rates each news headline about a ticker from -1 (very negative) to +1 (very "
        "positive), with 0 being neutral."
    )

with st.container(border=True):
    st.markdown("**Avg Sentiment**")
    st.write("The mean sentiment score across all articles in the selected day window.")

with st.container(border=True):
    st.markdown("**Direction**")
    st.write(
        "Compares the average sentiment of the first half of the window to the second half: "
        "**Rising** if it's meaningfully more positive recently, **Falling** if meaningfully "
        "more negative, otherwise **Flat**."
    )

st.header("Trends page")

with st.container(border=True):
    st.markdown("**Times Flagged**")
    st.write("How many days, within the selected window, a ticker was among that day's 30 flagged tickers.")

with st.container(border=True):
    st.markdown("**Avg Score (flagged)**")
    st.write("A ticker's average score across only the days it was flagged within the window.")
