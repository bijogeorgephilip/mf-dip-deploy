import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz
import requests

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
    .fund-card { background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 20px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3); }
    .fund-title { font-size: 1.2rem; color: #94a3b8; margin-bottom: 10px; font-weight: 600; }
    .fund-val-red { font-size: 2rem; color: #f23645; font-weight: 700; }
    .fund-val-green { font-size: 2rem; color: #089981; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True
)

# --- MUTUAL FUND PORTFOLIO DATA (LIVE INTRADAY PREDICTOR WEIGHTS) ---
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

# --- OFFICIAL AMFI SCHEME CODES (Direct Growth Plans) ---
mf_amfi_codes = {
    "HDFC Flexi Cap": "119063",
    "Parag Parikh Flexi Cap": "122639",
    "Helios Flexi Cap": "152263"
}

# --- DATA FETCHING FUNCTIONS ---
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
    changes["CASH"] = 0.0
    return changes

@st.cache_data(ttl=3600)
def fetch_historical_mf_data(period):
    """Fetches OFFICIAL historical NAV data directly from AMFI via mfapi.in"""
    hist_data = pd.DataFrame()
    days_to_fetch = {"1mo": 30, "3mo": 90, "1y": 365, "5y": 1825}.get(period, 30)
    
    for name, code in mf_amfi_codes.items():
        try:
            url = f"https://api.mfapi.in/mf/{code}"
            response = requests.get(url).json()
            
            if response.get("status") == "SUCCESS":
                data = response.get("data", [])
                df = pd.DataFrame(data)
                
                df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
                df['nav'] = pd.to_numeric(df['nav'])
                df = df.sort_values('date')
                
                cutoff_date = datetime.now() - pd.Timedelta(days=days_to_fetch)
                df = df[df['date'] >= cutoff_date]
                
                if not df.empty:
                    df['Normalized'] = (df['nav'] / df['nav'].iloc[0]) * 100
                    df['Fund'] = name
                    df = df.rename(columns={"date": "Date"})
                    hist_data = pd.concat([hist_data, df[['Date', 'Normalized', 'Fund']]])
        except Exception as e:
            pass # Fails gracefully if AMFI is down
            
    return hist_data

@st.cache_data(ttl=3600)
def fetch_amfi_eod_data():
    """Fetches official EOD NAV, previous EOD NAV, and calculates EOD change from AMFI via mfapi.in"""
    eod_data = {}
    for name, code in mf_amfi_codes.items():
        try:
            url = f"https://api.mfapi.in/mf/{code}"
            response = requests.get(url).json()
            
            if response.get("status") == "SUCCESS":
                data = response.get("data", [])
                if len(data) >= 2:
                    df = pd.DataFrame(data)
                    df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
                    df['nav'] = pd.to_numeric(df['nav'])
                    df = df.sort_values('date') # Sort oldest first
                    
                    latest_row = df.iloc[-1]
                    prev_row = df.iloc[-2]
                    
                    latest_nav = latest_row['nav']
                    prev_nav = prev_row['nav']
                    latest_date = latest_row['date'].strftime('%d-%b-%Y')
                    
                    change = ((latest_nav - prev_nav) / prev_nav) * 100
                    eod_data[name] = {
                        "nav": latest_nav,
                        "change": change,
                        "date": latest_date
                    }
        except Exception as e:
            pass # Fails gracefully if AMFI is down
    return eod_data

# --- MAIN UI ---
st.title("📉 Institutional Dip Analyzer Pro")

ist_timezone = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(ist_timezone).strftime('%A, %d %b %Y | %I:%M %p IST')
st.caption(f"**Last Market Sync:** {current_time}")

# --- SECTION 1: LIVE INTRADAY ANALYZER ---
st.header("1. Intraday Deployment Engine")
st.markdown("Scan live underlying assets to find the deepest intraday NAV discount for lumpsum deployment.")

idx_data = fetch_index_data()
col1, col2, _ = st.columns([1, 1, 2])
col1.metric("NIFTY 50", f"{idx_data['NIFTY 50']['value']:,.2f}", f"{idx_data['NIFTY 50']['change']:.2f}%")
col2.metric("SENSEX", f"{idx_data['SENSEX']['value']:,.2f}", f"{idx_data['SENSEX']['change']:.2f}%")

if st.button("EXECUTE FULL-PORTFOLIO SCAN"):
    with st.spinner("Downloading live data and executing NAV drop algorithms..."):
        all_tickers = set(t for fund in funds.values() for t in fund.keys())
        live_changes = fetch_live_data(all_tickers)
        
        fund_impacts = {}
        for fund_name, holdings in funds.items():
            fund_impacts[fund_name] = sum([live_changes.get(t, 0) * w for t, w in holdings.items()])
            
        best_fund = min(fund_impacts, key=fund_impacts.get)
        best_impact = fund_impacts[best_fund]
        
        st.subheader("🎯 System Recommendation")
        if best_impact >= 0:
            st.info("⚖️ **HOLD CASH.** Based on total portfolio weighting, no significant dip detected.")
        else:
            st.success(f"🔥 **ALLOCATE TO:** {best_fund}")
            st.write(f"Estimated Total NAV Drop: **{best_impact:.2f}%**")
            
        st.write("---")
        st.subheader("📊 Cross-Fund Comparison")
        comp_cols = st.columns(len(funds))
        for i, (fund_name, impact) in enumerate(fund_impacts.items()):
            val_class = "fund-val-red" if impact < 0 else "fund-val-green"
            sign = "+" if impact > 0 else ""
            comp_cols[i].markdown(
                f"<div class='fund-card'><div class='fund-title'>{fund_name}</div><div class='{val_class}'>{sign}{impact:.2f}%</div></div>", 
                unsafe_allow_html=True
            )
            
        st.divider()
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
                    df_data.append({"Asset": stock_name, "Allocation": weight * 100, "Intraday Move": change, "Net Drag/Lift": change * weight})
                
                df_full = pd.DataFrame(df_data).sort_values(by="Allocation", ascending=False)
                df_full['Portfolio'] = fund_name
                
                chart_col, table_col = st.columns([1.5, 1]) 
                with table_col:
                    st.markdown("**Complete Asset Ledger**")
                    df_display = df_full[df_full["Asset"].str.upper().str.contains(search_query)] if search_query else df_full
                    styled_df = df_display.drop(columns=['Portfolio']).style.map(color_returns, subset=["Intraday Move", "Net Drag/Lift"]).format({"Allocation": "{:.2f}%", "Intraday Move": "{:.2f}%", "Net Drag/Lift": "{:.3f}%"})
                    st.dataframe(styled_df, use_container_width=True, hide_index=True, height=500)
                
                with chart_col:
                    st.markdown("**Performance Heatmap**")
                    fig = px.treemap(df_full, path=['Portfolio', 'Asset'], values='Allocation', color='Intraday Move', color_continuous_scale=['#f23645', '#1a2235', '#089981'], color_continuous_midpoint=0)
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'), margin=dict(t=10, b=10, l=10, r=10), coloraxis_colorbar=dict(title="% Change", tickformat=".1f"))
                    fig.update_traces(textinfo="label+value", hovertemplate="<b>%{label}</b><br>Weight: %{value:.2f}%<br>Daily Change: %{color:.2f}%<extra></extra>")
                    st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- SECTION 2: MACRO HISTORICAL TRACKER ---
st.header("2. Historical NAV Performance Tracker")
st.markdown("Track the actual, long-term compounded growth of your funds using official AMFI data.")

# --- OFFICIAL AMFI EOD SNAPSHOT ---
st.subheader("📊 Official End-Of-Day NAV & Daily Change")
with st.spinner("Fetching official AMFI EOD NAVs..."):
    amfi_eod = fetch_amfi_eod_data()
    if amfi_eod:
        comp_cols = st.columns(len(funds))
        for i, (fund_name, info) in enumerate(amfi_eod.items()):
            val_class = "fund-val-red" if info['change'] < 0 else "fund-val-green"
            sign = "+" if info['change'] > 0 else ""
            comp_cols[i].markdown(
                f"""
                <div class='fund-card'>
                    <div class='fund-title'>{fund_name}</div>
                    <div style='font-size: 1.15rem; color: #e2e8f0; margin-bottom: 8px;'>EOD NAV: <b>₹{info['nav']:.4f}</b></div>
                    <div class='{val_class}'>{sign}{info['change']:.2f}%</div>
                    <div style='font-size: 0.8rem; color: #64748b; margin-top: 8px;'>As of: {info['date']}</div>
                </div>
                """, 
                unsafe_allow_html=True
            )
    else:
        st.warning("Could not fetch official EOD data from AMFI.")

st.write("---")

period = st.radio("Select Timeframe:", ["1mo", "3mo", "1y", "5y"], horizontal=True, format_func=lambda x: {"1mo":"1 Month", "3mo":"3 Months", "1y":"1 Year", "5y":"5 Years"}[x])

with st.spinner("Fetching official AMFI mutual fund NAVs..."):
    hist_df = fetch_historical_mf_data(period)
    
    if not hist_df.empty:
        line_fig = px.line(
            hist_df, 
            x='Date', # Set X-Axis to Date from AMFI
            y='Normalized', 
            color='Fund',
            color_discrete_sequence=['#38bdf8', '#fbbf24', '#a78bfa']
        )
        
        line_fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e2e8f0'),
            xaxis=dict(title="", showgrid=False),
            yaxis=dict(title="Normalized Return (%)", showgrid=True, gridcolor='#334155'),
            legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified"
        )
        
        line_fig.update_traces(line=dict(width=3))
        
        st.plotly_chart(line_fig, use_container_width=True)
        st.caption("Chart data is normalized to 100 at the start of the period to allow direct percentage comparison between funds with different NAV prices.")
    else:
        st.warning("Could not fetch historical data at this time. AMFI servers might be busy.")