import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz

# --- APP CONFIGURATION ---
st.set_page_config(page_title="MF Dip Analyzer Pro", page_icon="📉", layout="wide")

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

# --- EXPANDED MUTUAL FUND PORTFOLIO DATA (Normalized to ~100%) ---
funds = {
    "HDFC Flexi Cap": {
        "ICICIBANK.NS": 0.095, "HDFCBANK.NS": 0.075, "AXISBANK.NS": 0.065, "SBIN.NS": 0.055, 
        "KOTAKBANK.NS": 0.045, "BHARTIARTL.NS": 0.040, "LT.NS": 0.038, "CIPLA.NS": 0.035, 
        "HCLTECH.NS": 0.032, "RELIANCE.NS": 0.030, "INFY.NS": 0.028, "TCS.NS": 0.025, 
        "ITC.NS": 0.022, "BAJFINANCE.NS": 0.020, "NTPC.NS": 0.018, "SUNPHARMA.NS": 0.015, 
        "M&M.NS": 0.015, "TITAN.NS": 0.015, "ASIANPAINT.NS": 0.015, "TATASTEEL.NS": 0.015,
        "ULTRACEMCO.NS": 0.014, "POWERGRID.NS": 0.014, "BAJAJ-AUTO.NS": 0.014, 
        "TATAMOTORS.NS": 0.014, "WIPRO.NS": 0.014, "TECHM.NS": 0.013, "JSWSTEEL.NS": 0.013, 
        "HINDALCO.NS": 0.013, "COALINDIA.NS": 0.013, "ONGC.NS": 0.012, "GRASIM.NS": 0.012,
        "ADANIPORTS.NS": 0.012, "DIVISLAB.NS": 0.012, "MARUTI.NS": 0.012, "NESTLEIND.NS": 0.012,
        "TATACONSUM.NS": 0.012, "INDUSINDBK.NS": 0.011, "DRREDDY.NS": 0.011, "HINDUNILVR.NS": 0.011,
        "SBILIFE.NS": 0.011, "HDFCLIFE.NS": 0.011, "BAJAJFINSV.NS": 0.010, "BPCL.NS": 0.010
    },
    "Parag Parikh Flexi Cap": {
        "HDFCBANK.NS": 0.090, "ITC.NS": 0.080, "POWERGRID.NS": 0.065, "ICICIBANK.NS": 0.060, 
        "BAJFINANCE.NS": 0.055, "MARUTI.NS": 0.050, "HCLTECH.NS": 0.045, "COALINDIA.NS": 0.040, 
        "CDSL.NS": 0.035, "RELIANCE.NS": 0.030, "GOOGL": 0.060, "MSFT": 0.050, "AMZN": 0.045, "META": 0.040,
        "BAJAJ-AUTO.NS": 0.030, "HEROMOTOCO.NS": 0.025, "NESTLEIND.NS": 0.020, "BRITANNIA.NS": 0.020, 
        "TATACONSUM.NS": 0.020, "EICHERMOT.NS": 0.015, "TVSMOTOR.NS": 0.015, "COLPAL.NS": 0.015,
        "HINDUNILVR.NS": 0.015, "DABUR.NS": 0.015, "PIDILITIND.NS": 0.015, "MARICO.NS": 0.015,
        "GODREJCP.NS": 0.015, "UBL.NS": 0.010, "MCDOWELL-N.NS": 0.010
    },
    "Helios Flexi Cap": {
        "ICICIBANK.NS": 0.080, "HDFCBANK.NS": 0.070, "SBIN.NS": 0.060, "RELIANCE.NS": 0.055, 
        "LT.NS": 0.050, "ITC.NS": 0.045, "INFY.NS": 0.040, "TCS.NS": 0.035, "AXISBANK.NS": 0.030, 
        "ZOMATO.NS": 0.030, "PAYTM.NS": 0.025, "TRENT.NS": 0.025, "INDIGO.NS": 0.025, "DIXON.NS": 0.025,
        "HAL.NS": 0.025, "BEL.NS": 0.025, "SWIGGY.NS": 0.020, "ZYDUSLIFE.NS": 0.020, 
        "APOLLOHOSP.NS": 0.020, "MAXHEALTH.NS": 0.020, "POLYCAB.NS": 0.020, "KPITTECH.NS": 0.020, 
        "TATAELXSI.NS": 0.020, "CYIENT.NS": 0.015, "PERSISTENT.NS": 0.015, "COFORGE.NS": 0.015,
        "TATACHEM.NS": 0.015, "SONACOMS.NS": 0.015, "CGPOWER.NS": 0.015, "KALYANKJIL.NS": 0.015,
        "DEVYANI.NS": 0.010, "SUZLON.NS": 0.010, "BSE.NS": 0.010, "MCX.NS": 0.010, "POLICYBZR.NS": 0.010
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
                prev, curr = hist['Close'].iloc[-2], hist['Close'].iloc[-1]
                data[name] = {"value": curr, "change": ((curr - prev) / prev) * 100}
            else:
                data[name] = {"value": 0.0, "change": 0.0}
        except:
            data[name] = {"value": 0.0, "change": 0.0}
    return data

@st.cache_data(ttl=60)
def fetch_live_data(tickers):
    changes = {}
    valid_tickers = [t for t in tickers if t != "CASH"]
    try:
        # Bulk download and cleanly extract the 'Close' grid
        data = yf.download(valid_tickers, period="2d", progress=False)
        close_data = data['Close'] if len(valid_tickers) > 1 else data['Close'].to_frame(name=valid_tickers[0])
        
        for ticker in valid_tickers:
            try:
                hist = close_data[ticker].dropna()
                if len(hist) >= 2:
                    prev, curr = hist.iloc[-2], hist.iloc[-1]
                    changes[ticker] = ((curr - prev) / prev) * 100
                else:
                    changes[ticker] = 0.0
            except:
                changes[ticker] = 0.0
    except:
        for ticker in valid_tickers: changes[ticker] = 0.0
        
    changes["CASH"] = 0.0 # Safety buffer logic
    return changes

# --- MAIN UI ---
st.title("📉 MF Dip Analyzer Pro")

# Current Date & Time (IST)
ist_timezone = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(ist_timezone).strftime('%A, %d %b %Y | %I:%M %p IST')
st.caption(f"**Last Market Sync:** {current_time}")
st.markdown("Full-Weight Portfolio Execution & Market Heatmap Engine")

# 1. MARKET PULSE
idx_data = fetch_index_data()
col1, col2, _ = st.columns([1, 1, 2])
col1.metric("NIFTY 50", f"{idx_data['NIFTY 50']['value']:,.2f}", f"{idx_data['NIFTY 50']['change']:.2f}%")
col2.metric("SENSEX", f"{idx_data['SENSEX']['value']:,.2f}", f"{idx_data['SENSEX']['change']:.2f}%")
st.divider()

if st.button("EXECUTE FULL-PORTFOLIO SCAN"):
    with st.spinner("Downloading live data and executing NAV drop algorithms..."):
        all_tickers = set(t for fund in funds.values() for t in fund.keys())
        live_changes = fetch_live_data(all_tickers)
        
        fund_impacts = {}
        for fund_name, holdings in funds.items():
            fund_impacts[fund_name] = sum([live_changes.get(t, 0) * w for t, w in holdings.items()])
            
        best_fund = min(fund_impacts, key=fund_impacts.get)
        best_impact = fund_impacts[best_fund]
        
        # 2. DEPLOYMENT TARGET
        st.subheader("🎯 System Recommendation")
        if best_impact >= 0:
            st.info("⚖️ **HOLD CASH.** Based on total portfolio weighting, no significant dip detected.")
        else:
            st.success(f"🔥 **ALLOCATE TO:** {best_fund}")
            st.write(f"Estimated Total NAV Drop: **{best_impact:.2f}%**")
        st.divider()
        
        # 3. DIAGNOSTICS & HEATMAP VISUALIZATION
        st.subheader("Deep Diagnostics (Heatmap & Holdings)")
        search_query = st.text_input("🔍 Filter Table by Stock (e.g., 'HDFC')").upper()
        
        tabs = st.tabs(list(funds.keys()))
        def color_returns(val):
            color = '#f23645' if val < 0 else '#089981'
            return f'color: {color}; font-weight: 600;'

        for tab, (fund_name, holdings) in zip(tabs, funds.items()):
            with tab:
                df_data = []
                for ticker, weight in holdings.items():
                    stock_name = ticker.replace(".NS", "")
                    change = live_changes.get(ticker, 0.0)
                    df_data.append({
                        "Asset": stock_name,
                        "Allocation": weight * 100,
                        "Intraday Move": change,
                        "Net Drag/Lift": change * weight 
                    })
                
                df_full = pd.DataFrame(df_data).sort_values(by="Allocation", ascending=False)
                df_full['Portfolio'] = fund_name
                
                chart_col, table_col = st.columns([1.5, 1]) 
                
                with table_col:
                    st.markdown("**Complete Asset Ledger**")
                    if search_query:
                        df_display = df_full[df_full["Asset"].str.upper().str.contains(search_query)]
                    else:
                        df_display = df_full
                    
                    styled_df = df_display.style.map(color_returns, subset=["Intraday Move", "Net Drag/Lift"]).format({
                        "Allocation": "{:.2f}%", "Intraday Move": "{:.2f}%", "Net Drag/Lift": "{:.3f}%"
                    })
                    st.dataframe(styled_df, use_container_width=True, hide_index=True, height=500)
                
                with chart_col:
                    st.markdown("**Performance Heatmap**")
                    fig = px.treemap(
                        df_full, 
                        path=['Portfolio', 'Asset'], 
                        values='Allocation',
                        color='Intraday Move',
                        color_continuous_scale=['#f23645', '#1a2235', '#089981'],
                        color_continuous_midpoint=0
                    )
                    fig.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#e2e8f0'),
                        margin=dict(t=10, b=10, l=10, r=10),
                        coloraxis_colorbar=dict(title="% Change", tickformat=".1f")
                    )
                    fig.update_traces(
                        textinfo="label+value",
                        hovertemplate="<b>%{label}</b><br>Weight: %{value:.2f}%<br>Daily Change: %{color:.2f}%<extra></extra>"
                    )
                    st.plotly_chart(fig, use_container_width=True)
