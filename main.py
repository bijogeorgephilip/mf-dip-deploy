import streamlit as st
import yfinance as yf
import pandas as pd

# --- APP CONFIGURATION ---
# Switched to 'wide' layout for better dashboard visualization
st.set_page_config(page_title="MF Dip Analyzer Pro", page_icon="📉", layout="wide")

# --- MUTUAL FUND PORTFOLIO DATA (Top 10 Approx Weights) ---
funds = {
    "HDFC Flexi Cap": {
        "ICICIBANK.NS": 0.088, "HDFCBANK.NS": 0.065, "AXISBANK.NS": 0.052,
        "SBIN.NS": 0.048, "KOTAKBANK.NS": 0.035, "BHARTIARTL.NS": 0.032,
        "LT.NS": 0.030, "CIPLA.NS": 0.028, "HCLTECH.NS": 0.025, "RELIANCE.NS": 0.021
    },
    "Parag Parikh Flexi Cap": {
        "HDFCBANK.NS": 0.082, "ITC.NS": 0.071, "POWERGRID.NS": 0.055,
        "ICICIBANK.NS": 0.051, "BAJFINANCE.NS": 0.048, "MARUTI.NS": 0.042,
        "HCLTECH.NS": 0.040, "COALINDIA.NS": 0.035, "CDSL.NS": 0.031, "RELIANCE.NS": 0.020
    },
    "Helios Flexi Cap": {
        "ICICIBANK.NS": 0.055, "HDFCBANK.NS": 0.052, "SBIN.NS": 0.041,
        "RELIANCE.NS": 0.038, "LT.NS": 0.035, "ITC.NS": 0.032,
        "INFY.NS": 0.030, "TCS.NS": 0.028, "AXISBANK.NS": 0.025, "ZOMATO.NS": 0.020
    }
}

# --- FETCH LIVE DATA FUNCTIONS ---
@st.cache_data(ttl=60)
def fetch_index_data():
    indices = {"NIFTY 50": "^NSEI", "SENSEX": "^BSESN"}
    data = {}
    for name, ticker in indices.items():
        try:
            hist = yf.Ticker(ticker).history(period="2d")
            if len(hist) >= 2:
                prev = hist['Close'].iloc[0]
                curr = hist['Close'].iloc[-1]
                data[name] = {"value": curr, "change": ((curr - prev) / prev) * 100}
            else:
                data[name] = {"value": 0.0, "change": 0.0}
        except:
            data[name] = {"value": 0.0, "change": 0.0}
    return data

@st.cache_data(ttl=60)
def fetch_live_data(tickers):
    changes = {}
    for ticker in tickers:
        try:
            hist = yf.Ticker(ticker).history(period="2d")
            if len(hist) >= 2:
                prev = hist['Close'].iloc[0]
                curr = hist['Close'].iloc[-1]
                changes[ticker] = ((curr - prev) / prev) * 100
            else:
                changes[ticker] = 0.0
        except:
            changes[ticker] = 0.0
    return changes

# --- MAIN UI ---
st.title("📉 Mutual Fund Dip Analyzer Pro")
st.markdown("Automated Tranche Deployment Dashboard based on Live Underlying Assets.")

# 1. MARKET PULSE (Indices)
st.subheader("🌐 Live Market Pulse")
idx_data = fetch_index_data()
col1, col2, _ = st.columns([1, 1, 2]) # Keeps the boxes contained to the left

col1.metric("NIFTY 50", f"{idx_data['NIFTY 50']['value']:,.2f}", f"{idx_data['NIFTY 50']['change']:.2f}%")
col2.metric("SENSEX", f"{idx_data['SENSEX']['value']:,.2f}", f"{idx_data['SENSEX']['change']:.2f}%")

st.divider()

if st.button("🔄 Analyze Live Mutual Fund Dips"):
    with st.spinner("Crunching NSE data for Top 10 Holdings..."):
        
        # Aggregate all unique tickers
        all_tickers = set()
        for holdings in funds.values():
            all_tickers.update(holdings.keys())
        
        live_changes = fetch_live_data(all_tickers)
        
        # Calculate impacts
        fund_impacts = {}
        for fund_name, holdings in funds.items():
            impact = sum([live_changes.get(t, 0) * w for t, w in holdings.items()])
            fund_impacts[fund_name] = impact
            
        best_fund = min(fund_impacts, key=fund_impacts.get)
        best_impact = fund_impacts[best_fund]
        
        # 2. DEPLOYMENT RECOMMENDATION
        st.subheader("🎯 Deployment Target")
        if best_impact >= 0:
            st.warning("⚖️ **HOLD CASH.** All tracked funds are estimated flat or positive today.")
        else:
            st.success(f"🔥 **DEPLOY TO: {best_fund}** (Estimated Top 10 Impact: **{best_impact:.2f}%**)")
        
        st.divider()
        
        # 3. DEEP DIVE VISUALIZATIONS
        st.subheader("📊 Top 10 Holdings Breakdown")
        st.caption("See exactly which stocks are dragging your funds down today. Sorted by biggest losers.")
        
        # Create tabs for each fund
        tabs = st.tabs(list(funds.keys()))
        
        # Function to color negative red, positive green
        def color_returns(val):
            color = '#ff4b4b' if val < 0 else '#09ab3b'
            return f'color: {color}; font-weight: bold;'

        for tab, (fund_name, holdings) in zip(tabs, funds.items()):
            with tab:
                # Build Dataframe
                df_data = []
                for ticker, weight in holdings.items():
                    change = live_changes.get(ticker, 0.0)
                    df_data.append({
                        "Stock": ticker.replace(".NS", ""),
                        "Weight (%)": weight * 100,
                        "Today's Change (%)": change,
                        "Fund Impact": change * weight # How much this specific stock affects the fund today
                    })
                df = pd.DataFrame(df_data)
                
                # Sort by most negative change
                df = df.sort_values(by="Today's Change (%)", ascending=True)
                
                # Apply styles
                styled_df = df.style.map(color_returns, subset=["Today's Change (%)", "Fund Impact"]).format({
                    "Weight (%)": "{:.2f}%",
                    "Today's Change (%)": "{:.2f}%",
                    "Fund Impact": "{:.3f}%"
                })
                
                # Display table spanning full width
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
