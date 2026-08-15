import streamlit as st
import yfinance as yf
import pandas as pd

# --- APP CONFIGURATION ---
st.set_page_config(page_title="MF Dip Analyzer", page_icon="📉", layout="centered")

# --- MUTUAL FUND PORTFOLIO DATA ---
# Weights are represented as decimals (e.g., 0.09 = 9%)
# .NS suffix is required by Yahoo Finance for Indian NSE stocks
funds = {
    "HDFC Flexi Cap": {
        "ICICIBANK.NS": 0.09,
        "HDFCBANK.NS": 0.07,
        "SBIN.NS": 0.04,
        "RELIANCE.NS": 0.02,
        "ITC.NS": 0.00
    },
    "Parag Parikh Flexi Cap": {
        "HDFCBANK.NS": 0.08,
        "ITC.NS": 0.07,
        "ICICIBANK.NS": 0.05,
        "RELIANCE.NS": 0.00,
        "SBIN.NS": 0.00
    },
    "Helios Flexi Cap": {
        "ICICIBANK.NS": 0.05,
        "HDFCBANK.NS": 0.05,
        "RELIANCE.NS": 0.03,
        "SBIN.NS": 0.03,
        "ITC.NS": 0.00
    }
}

# --- FETCH LIVE DATA FUNCTION ---
@st.cache_data(ttl=60) # Caches data for 60 seconds so it doesn't spam the API
def fetch_live_data(tickers):
    changes = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            # Fetch last 2 days to calculate % change from yesterday's close
            hist = stock.history(period="2d")
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[0]
                current = hist['Close'].iloc[-1]
                pct_change = ((current - prev_close) / prev_close) * 100
            else:
                pct_change = 0.0
            changes[ticker] = pct_change
        except Exception:
            changes[ticker] = 0.0
    return changes

# --- MAIN UI ---
st.title("📉 Mutual Fund Dip Analyzer")
st.markdown("Check live market data to find the optimal Flexi Cap fund for today's lumpsum deployment.")

if st.button("🔄 Fetch Live Market Data"):
    with st.spinner("Pulling live NSE data..."):
        # 1. Get unique list of all stocks across all funds
        all_tickers = set()
        for fund_holdings in funds.values():
            all_tickers.update(fund_holdings.keys())

        # 2. Fetch live percentage changes
        live_changes = fetch_live_data(all_tickers)

        # 3. Display individual stock performances
        st.subheader("📊 Heavyweight Stock Performance")
        cols = st.columns(len(all_tickers))
        for i, (ticker, change) in enumerate(live_changes.items()):
            color = "🔴" if change < 0 else "🟢"
            cols[i].metric(label=ticker.replace(".NS", ""), value=f"{change:.2f}%")

        st.divider()

        # 4. Calculate Fund Impacts
        fund_impacts = {}
        for fund_name, holdings in funds.items():
            impact = 0.0
            for ticker, weight in holdings.items():
                impact += live_changes[ticker] * weight
            fund_impacts[fund_name] = impact

        # 5. Find the Winner (The most negative impact)
        best_fund = min(fund_impacts, key=fund_impacts.get)
        best_impact = fund_impacts[best_fund]

        st.subheader("🎯 Deployment Recommendation")

        if best_impact >= 0:
            st.warning("⚖️ **HOLD CASH.** All tracked funds are estimated to be flat or positive today. No dip detected.")
        else:
            st.success(f"🔥 **DEPLOY TO: {best_fund}**")
            st.info(f"It has the deepest estimated dip today at **{best_impact:.2f}%** based on its top holdings.")

        # 6. Show all fund estimates
        st.subheader("📋 Estimated Impact per Fund")
        for fund, impact in fund_impacts.items():
            st.write(f"**{fund}:** {impact:.2f}%")

st.markdown("---")
st.caption("Data provided by Yahoo Finance (~15 min delay). Run this check at 1:50 PM before 3:00 PM cutoff.")
