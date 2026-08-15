import streamlit as st
import yfinance as yf
import pandas as pd

# --- APP CONFIGURATION ---
st.set_page_config(page_title="MF Dip Analyzer Pro", page_icon="📉", layout="wide")

# --- PREMIUM DARK THEME CSS ---
st.markdown(
    """
    <style>
    /* Main Background */
    .stApp {
        background: linear-gradient(180deg, #0b0f19 0%, #1a2235 100%);
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }
    
    /* Headings */
    h1, h2, h3 {
        color: #f8fafc !important;
        font-weight: 600;
    }
    
    /* Metric Cards */
    div[data-testid="stMetricValue"] {
        color: #f8fafc;
        font-size: 2rem;
    }
    div[data-testid="stMetricDelta"] {
        font-size: 1.2rem;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        color: #94a3b8;
        font-size: 1.1rem;
        border-bottom: 2px solid transparent;
    }
    .stTabs [aria-selected="true"] {
        color: #38bdf8 !important;
        border-bottom: 2px solid #38bdf8 !important;
    }
    
    /* Dataframes/Tables */
    .stDataFrame {
        background-color: #1e293b;
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #334155;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #38bdf8;
        color: #0f172a;
        border-radius: 6px;
        font-weight: 600;
        border: none;
        padding: 0.5rem 1rem;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #0ea5e9;
        transform: translateY(-1px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* Input Fields */
    .stTextInput>div>div>input {
        background-color: #1e293b;
        color: #f8fafc;
        border: 1px solid #334155;
        border-radius: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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
st.title("📉 Institutional Dip Analyzer")
st.caption("Automated Lumpsum Deployment System")

# 1. MARKET PULSE
st.subheader("Live Market Pulse")
idx_data = fetch_index_data()

# Styling metrics using columns
col1, col2, _ = st.columns([1, 1, 2])
with col1:
    st.metric("NIFTY 50", f"{idx_data['NIFTY 50']['value']:,.2f}", f"{idx_data['NIFTY 50']['change']:.2f}%")
with col2:
    st.metric("SENSEX", f"{idx_data['SENSEX']['value']:,.2f}", f"{idx_data['SENSEX']['change']:.2f}%")

st.divider()

if st.button("🔄 Execute Market Scan"):
    with st.spinner("Analyzing Top Holdings..."):
        all_tickers = set()
        for holdings in funds.values():
            all_tickers.update(holdings.keys())
        
        live_changes = fetch_live_data(all_tickers)
        
        fund_impacts = {}
        for fund_name, holdings in funds.items():
            impact = sum([live_changes.get(t, 0) * w for t, w in holdings.items()])
            fund_impacts[fund_name] = impact
            
        best_fund = min(fund_impacts, key=fund_impacts.get)
        best_impact = fund_impacts[best_fund]
        
        # 2. DEPLOYMENT TARGET
        st.subheader("🎯 System Recommendation")
        if best_impact >= 0:
            st.info("⚖️ **HOLD CASH.** Market conditions do not meet dip criteria today.")
        else:
            st.success(f"🔥 **ALLOCATE TO:** {best_fund}")
            st.write(f"Estimated drag from Top 10 holdings: **{best_impact:.2f}%**")
        
        st.divider()
        
        # 3. PORTFOLIO BREAKDOWN
        st.subheader("Portfolio Diagnostics")
        
        search_query = st.text_input("🔍 Filter by Stock (e.g., 'HDFC')").upper()
        
        tabs = st.tabs(list(funds.keys()))
        
        def color_returns(val):
            color = '#ef4444' if val < 0 else '#22c55e' # Vibrant red/green for dark mode
            return f'color: {color}; font-weight: 600;'

        for tab, (fund_name, holdings) in zip(tabs, funds.items()):
            with tab:
                df_data = []
                for ticker, weight in holdings.items():
                    stock_name = ticker.replace(".NS", "")
                    if search_query and search_query not in stock_name:
                        continue
                        
                    change = live_changes.get(ticker, 0.0)
                    df_data.append({
                        "Asset": stock_name,
                        "Allocation": weight * 100,
                        "Intraday Move": change,
                        "Net Drag/Lift": change * weight 
                    })
                
                if df_data:
                    df = pd.DataFrame(df_data)
                    df = df.sort_values(by="Allocation", ascending=False)
                    
                    # Apply premium styling to dataframe
                    styled_df = df.style.map(color_returns, subset=["Intraday Move", "Net Drag/Lift"]).format({
                        "Allocation": "{:.2f}%",
                        "Intraday Move": "{:.2f}%",
                        "Net Drag/Lift": "{:.3f}%"
                    })
                    
                    st.dataframe(styled_df, use_container_width=True, hide_index=True)
                else:
                    st.info(f"No matching assets found in {fund_name}.")
