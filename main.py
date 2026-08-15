import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# --- APP CONFIGURATION ---
st.set_page_config(page_title="MF Dip Analyzer", page_icon="📉", layout="wide")

# --- PREMIUM TRADING TERMINAL THEME CSS ---
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0b0e14;
        background-image: 
            linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
        background-size: 30px 30px;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }
    h1, h2, h3 { color: #f8fafc !important; font-weight: 600; text-shadow: 0px 2px 4px rgba(0,0,0,0.5); }
    div[data-testid="stMetricValue"] { color: #ffffff; font-size: 2.2rem; font-weight: 700; }
    div[data-testid="stMetricDelta"] { font-size: 1.2rem; font-weight: 600; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] { height: 50px; color: #64748b; font-size: 1.1rem; border-bottom: 2px solid transparent; }
    .stTabs [aria-selected="true"] { color: #e2e8f0 !important; border-bottom: 2px solid #38bdf8 !important; }
    .stDataFrame { background-color: rgba(30, 41, 59, 0.85); border-radius: 8px; padding: 10px; border: 1px solid #334155; }
    .stButton>button { background-color: #2563eb; color: #ffffff; border-radius: 4px; font-weight: 600; border: 1px solid #1d4ed8; padding: 0.5rem 1.5rem; transition: all 0.2s ease; text-transform: uppercase; letter-spacing: 0.5px; }
    .stButton>button:hover { background-color: #1d4ed8; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4); }
    .stTextInput>div>div>input { background-color: rgba(30, 41, 59, 0.8); color: #f8fafc; border: 1px solid #475569; border-radius: 4px; }
    </style>
    """,
    unsafe_allow_html=True
)

# --- FULL MUTUAL FUND PORTFOLIO DATA (Adding up to 100% Weight) ---
# Tickers like "NIFTY_MIDCAP" or "CASH" are proxy trackers for the "tail" of the fund
funds = {
    "HDFC Flexi Cap": {
        "ICICIBANK.NS": 0.088, "HDFCBANK.NS": 0.065, "AXISBANK.NS": 0.052,
        "SBIN.NS": 0.048, "KOTAKBANK.NS": 0.035, "BHARTIARTL.NS": 0.032,
        "LT.NS": 0.030, "CIPLA.NS": 0.028, "HCLTECH.NS": 0.025, "RELIANCE.NS": 0.021,
        "INFY.NS": 0.018, "TCS.NS": 0.015, "ITC.NS": 0.012, "BAJFINANCE.NS": 0.010,
        "^NSEMDCP50": 0.400, # Proxy for the 40% mid/small cap tail
        "CASH": 0.121 # Remaining balance
    },
    "Parag Parikh Flexi Cap": {
        "HDFCBANK.NS": 0.082, "ITC.NS": 0.071, "POWERGRID.NS": 0.055,
        "ICICIBANK.NS": 0.051, "BAJFINANCE.NS": 0.048, "MARUTI.NS": 0.042,
        "HCLTECH.NS": 0.040, "COALINDIA.NS": 0.035, "CDSL.NS": 0.031, "RELIANCE.NS": 0.020,
        "GOOGL": 0.060, "MSFT": 0.050, "AMZN": 0.045, "META": 0.040, # US Tech Exposure
        "^NSEI": 0.180, # Proxy for other standard Indian equities
        "CASH": 0.150 # Famous PPFC high cash/arbitrage buffer
    },
    "Helios Flexi Cap": {
        "ICICIBANK.NS": 0.055, "HDFCBANK.NS": 0.052, "SBIN.NS": 0.041,
        "RELIANCE.NS": 0.038, "LT.NS": 0.035, "ITC.NS": 0.032,
        "INFY.NS": 0.030, "TCS.NS": 0.028, "AXISBANK.NS": 0.025, "ZOMATO.NS": 0.020,
        "PAYTM.NS": 0.015, "TRENT.NS": 0.012, "INDIGO.NS": 0.010, "DIXON.NS": 0.009,
        "HAL.NS": 0.008, "BEL.NS": 0.007,
        "^NSEMDCP50": 0.500, # Heavy mid/small thematic tail
        "CASH": 0.083
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
                prev, curr = hist['Close'].iloc[0], hist['Close'].iloc[-1]
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
        if ticker == "CASH":
            changes[ticker] = 0.0 # Cash doesn't drop in a market crash
            continue
            
        try:
            hist = yf.Ticker(ticker).history(period="2d")
            if len(hist) >= 2:
                prev, curr = hist['Close'].iloc[0], hist['Close'].iloc[-1]
                changes[ticker] = ((curr - prev) / prev) * 100
            else:
                changes[ticker] = 0.0
        except:
            changes[ticker] = 0.0
    return changes

# --- MAIN UI ---
st.title("📉 MP Dip Analyzer")
st.caption("Full-Weight Portfolio Simulation")

# 1. MARKET PULSE
idx_data = fetch_index_data()
col1, col2, _ = st.columns([1, 1, 2])
col1.metric("NIFTY 50", f"{idx_data['NIFTY 50']['value']:,.2f}", f"{idx_data['NIFTY 50']['change']:.2f}%")
col2.metric("SENSEX", f"{idx_data['SENSEX']['value']:,.2f}", f"{idx_data['SENSEX']['change']:.2f}%")
st.divider()

if st.button("EXECUTE FULL-PORTFOLIO SCAN"):
    with st.spinner("Crunching 100% NAV equivalents..."):
        all_tickers = set(t for fund in funds.values() for t in fund.keys())
        live_changes = fetch_live_data(all_tickers)
        
        fund_impacts = {}
        for fund_name, holdings in funds.items():
            fund_impacts[fund_name] = sum([live_changes.get(t, 0) * w for t, w in holdings.items()])
            
        best_fund = min(fund_impacts, key=fund_impacts.get)
        best_impact = fund_impacts[best_fund]
        
        st.subheader("🎯 System Recommendation")
        if best_impact >= 0:
            st.info("⚖️ **HOLD CASH.** Based on 100% portfolio weighting, no significant dip detected.")
        else:
            st.success(f"🔥 **ALLOCATE TO:** {best_fund}")
            st.write(f"Estimated Total NAV Drop: **{best_impact:.2f}%**")
        st.divider()
        
        st.subheader("Deep Diagnostics (100% Allocation Mapping)")
        search_query = st.text_input("🔍 Filter by Stock (e.g., 'HDFC')").upper()
        
        tabs = st.tabs(list(funds.keys()))
        def color_returns(val):
            color = '#f23645' if val < 0 else '#089981'
            return f'color: {color}; font-weight: 600;'

        for tab, (fund_name, holdings) in zip(tabs, funds.items()):
            with tab:
                df_data = []
                for ticker, weight in holdings.items():
                    # Clean up proxy names for the user interface
                    if ticker == "^NSEMDCP50": stock_name = "Other Mid/Small Cap Basket"
                    elif ticker == "^NSEI": stock_name = "Other Large Cap Basket"
                    elif ticker == "CASH": stock_name = "Cash & Arbitrage Buffer"
                    else: stock_name = ticker.replace(".NS", "")
                    
                    change = live_changes.get(ticker, 0.0)
                    df_data.append({
                        "Asset": stock_name,
                        "Allocation": weight * 100,
                        "Intraday Move": change,
                        "Net Drag/Lift": change * weight 
                    })
                
                df_full = pd.DataFrame(df_data).sort_values(by="Allocation", ascending=False)
                chart_col, table_col = st.columns([1, 1.2])
                
                with table_col:
                    if search_query:
                        df_display = df_full[df_full["Asset"].str.upper().str.contains(search_query)]
                    else:
                        df_display = df_full
                    
                    styled_df = df_display.style.map(color_returns, subset=["Intraday Move", "Net Drag/Lift"]).format({
                        "Allocation": "{:.2f}%", "Intraday Move": "{:.2f}%", "Net Drag/Lift": "{:.3f}%"
                    })
                    st.dataframe(styled_df, use_container_width=True, hide_index=True)
                
                with chart_col:
                    fig = px.pie(df_full, values='Allocation', names='Asset', hole=0.6,
                               color_discrete_sequence=px.colors.qualitative.Bold)
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                    font=dict(color='#e2e8f0'), margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
                    fig.update_traces(textposition='inside', textinfo='percent+label',
                                    hovertemplate="<b>%{label}</b><br>Weight: %{percent}<extra></extra>")
                    st.plotly_chart(fig, use_container_width=True)
