import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz
import requests
import time
import json

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
    
    .fund-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    .fund-title { font-size: 1.2rem; color: #94a3b8; margin-bottom: 10px; font-weight: 600; }
    .fund-val-red { font-size: 2rem; color: #f23645; font-weight: 700; }
    .fund-val-green { font-size: 2rem; color: #089981; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True
)

# --- TICKER MAPPING & CLEANUP ---
TICKER_MAPPING = {
    "KVBANK.NS": "KARURVYSYA.NS",
    "ETERNAL.NS": "ZOMATO.NS"
}

INVALID_YF_TICKERS = {
    "ADITYAINFO.NS", 
    "ATHERENERGY.NS", 
    "last_updated",
    "description",
    "CASH"
}

# Ensure both variations of the HDFC name point to the correct code
mf_amfi_codes = {
    "HDFC Flexi Cap Direct Plan Growth": "118955",
    "HDFC Flexi Cap Fund Direct Growth": "118955", 
    "Parag Parikh Flexi Cap Fund Direct Growth": "122639",
    "Helios Flexi Cap Fund Direct Growth": "152135",
    "ICICI Prudential Aggressive Hybrid Fund Direct Growth": "120251",
    "Bandhan Small Cap Fund Direct Growth": "147946",
    "Invesco India Smallcap Fund Direct Growth": "145137"
}

# --- JSON LOADER (V2 Cache Buster) ---
@st.cache_data(ttl=3600)
def load_holdings_v2():
    try:
        with open("holdings.json", "r") as file:
            raw_data = json.load(file)
            
            standardized = {}
            for fund, holdings in raw_data.items():
                # EXPLICITLY NUKE METADATA
                if fund == "_metadata" or fund.startswith("_"):
                    continue
                
                std_holdings = {}
                if isinstance(holdings, dict):
                    for ticker, data in holdings.items():
                        # Silence unlisted stocks / IPOs
                        if ticker in INVALID_YF_TICKERS or ticker.startswith("_"):
                            continue
                        
                        clean_ticker = TICKER_MAPPING.get(ticker, ticker)
                        
                        if isinstance(data, dict):
                            std_holdings[clean_ticker] = {
                                "name": data.get("name", clean_ticker.replace(".NS", "")),
                                "weight": float(data.get("weight", 0.0))
                            }
                        elif isinstance(data, (int, float)):
                            std_holdings[clean_ticker] = {
                                "name": clean_ticker.replace(".NS", ""),
                                "weight": float(data)
                            }
                
                if std_holdings:
                    # Mathematically normalize weights to ensure they equal 100%
                    total_weight = sum([v["weight"] for v in std_holdings.values()])
                    if total_weight > 0:
                        for k in std_holdings:
                            std_holdings[k]["weight"] = std_holdings[k]["weight"] / total_weight
                    standardized[fund] = std_holdings
            return standardized
    except Exception as e:
        st.error(f"Error loading holdings: {e}")
        return {}

funds = load_holdings_v2()

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
    valid_tickers = [t for t in tickers if t not in INVALID_YF_TICKERS]
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
        
    return changes

# --- AMFI NAV LOGIC ---
@st.cache_data(ttl=3600)
def fetch_amfi_scheme_data(code):
    url = f"https://api.mfapi.in/mf/{code}"
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            payload = response.json()

            if not isinstance(payload, dict):
                return pd.DataFrame()

            raw_data = payload.get("data", [])
            if not isinstance(raw_data, list):
                return pd.DataFrame()

            df = pd.DataFrame(raw_data)
            if df.empty or "date" not in df.columns or "nav" not in df.columns:
                return pd.DataFrame()

            df = df[["date", "nav"]].copy()
            df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", dayfirst=True, errors="coerce")
            df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
            df = df.dropna(subset=["date", "nav"]).sort_values("date").reset_index(drop=True)
            return df if not df.empty else pd.DataFrame()
        except (requests.RequestException, ValueError, TypeError):
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))
                continue
            return pd.DataFrame()
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_historical_mf_data(period):
    df_list = []
    days_to_fetch = {"1mo": 30, "3mo": 90, "1y": 365, "5y": 1825}.get(period, 30)

    for name, code in mf_amfi_codes.items():
        try:
            df = fetch_amfi_scheme_data(code)
            if df.empty:
                continue

            max_date = df["date"].max()
            cutoff_date = max_date - pd.Timedelta(days=days_to_fetch)
            
            df = df[df["date"] >= cutoff_date]
            if df.empty:
                continue

            df = df.copy()
            df["Normalized"] = (df["nav"] / df["nav"].iloc[0]) * 100
            df["Fund"] = name
            df = df.rename(columns={"date": "Date"})
            df_list.append(df[["Date", "Normalized", "Fund"]])
        except Exception:
            continue

    if df_list:
        return pd.concat(df_list, ignore_index=True)
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_amfi_eod_data():
    eod_data = {}
    for name, code in mf_amfi_codes.items():
        try:
            df = fetch_amfi_scheme_data(code)
            if df.empty or len(df) < 2:
                eod_data[name] = {"nav": None, "change": None, "date": None, "ok": False}
                continue

            latest_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            latest_nav = float(latest_row["nav"])
            prev_nav = float(prev_row["nav"])

            change = ((latest_nav - prev_nav) / prev_nav) * 100 if prev_nav != 0 else None

            eod_data[name] = {
                "nav": latest_nav,
                "change": change,
                "date": latest_row["date"].strftime("%d-%b-%Y"),
                "ok": True,
            }
        except Exception:
            eod_data[name] = {"nav": None, "change": None, "date": None, "ok": False}
    return eod_data

# --- COLOR FORMATTING ---
def style_negative_positive(val):
    if isinstance(val, (int, float)):
        if val > 0: return 'color: #00c853;'
        elif val < 0: return 'color: #ff4b4b;'
        else: return 'color: #808495;'
    return ''

# --- MAIN UI ---
st.title("📉 Institutional Dip Analyzer Pro")

ist_timezone = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(ist_timezone).strftime('%A, %d %b %Y | %I:%M %p IST')
st.caption(f"**Last Market Sync:** {current_time}")
st.markdown("Full-Weight Portfolio Execution & Market Heatmap Engine")

if st.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.rerun()

# 1. MARKET PULSE
idx_data = fetch_index_data()
col1, col2, _ = st.columns([1, 1, 2])
col1.metric("NIFTY 50", f"{idx_data['NIFTY 50']['value']:,.2f}", f"{idx_data['NIFTY 50']['change']:.2f}%")
col2.metric("SENSEX", f"{idx_data['SENSEX']['value']:,.2f}", f"{idx_data['SENSEX']['change']:.2f}%")
st.divider()

with st.spinner("Downloading live data and executing NAV drop algorithms..."):
    all_tickers = set(t for fund in funds.values() for t in fund.keys())
    live_changes = fetch_live_data(all_tickers)
    
    fund_impacts = {}
    for fund_name, holdings in funds.items():
        # Using dict architecture: data["weight"]
        fund_impacts[fund_name] = sum([live_changes.get(t, 0) * data["weight"] for t, data in holdings.items()])
        
    if fund_impacts:
        best_fund = min(fund_impacts, key=fund_impacts.get)
        best_impact = fund_impacts[best_fund]
        
        # 2. DEPLOYMENT TARGET
        st.subheader("🎯 System Recommendation")
        if best_impact >= 0:
            st.info("⚖️ **HOLD CASH.** Based on total portfolio weighting, no significant dip detected.")
        else:
            st.success(f"🔥 **ALLOCATE TO:** {best_fund}")
            st.write(f"Estimated Total NAV Drop: **{best_impact:.2f}%**")
            
        # --- FUND COMPARISON DASHBOARD ---
        st.write("---")
        st.subheader("📊 Cross-Fund Comparison")
        st.caption("Side-by-side view of all tracked NAV impacts.")
        
        comp_cols = st.columns(3) # Grouped nicely
        
        for i, (fund_name, impact) in enumerate(fund_impacts.items()):
            col_idx = i % 3
            val_class = "fund-val-red" if impact < 0 else "fund-val-green"
            sign = "+" if impact > 0 else ""
            
            comp_cols[col_idx].markdown(
                f"""
                <div class="fund-card" style="margin-bottom: 20px;">
                    <div class="fund-title">{fund_name}</div>
                    <div class="{val_class}">{sign}{impact:.2f}%</div>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
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
                for ticker, data in holdings.items():
                    stock_name = data["name"]
                    weight = data["weight"]
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
                    
                    df_display_clean = df_display.drop(columns=['Portfolio'])
                    
                    styled_df = df_display_clean.style.map(color_returns, subset=["Intraday Move", "Net Drag/Lift"]).format({
                        "Allocation": "{:.2f}%", "Intraday Move": "{:.2f}%", "Net Drag/Lift": "{:.3f}%"
                    })
                    st.dataframe(styled_df, use_container_width=True, hide_index=True, height=450)
                
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

        # --- GRID LAYOUT INDIVIDUAL HOLDINGS BREAKDOWN ---
        st.divider()
        st.subheader("🔍 Individual Fund Holdings Breakdown")
        
        fund_items = list(funds.items())
        
        # Wrapped in a 3-column loop to prevent squishing!
        for i in range(0, len(fund_items), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(fund_items):
                    f_name, f_holdings = fund_items[i + j]
                    with cols[j]:
                        with st.expander(f"{f_name} Stocks", expanded=True):
                            stock_rows = []
                            advancers = 0
                            decliners = 0
                            
                            for ticker, data in f_holdings.items():
                                val = live_changes.get(ticker)
                                
                                display_change = float(val) if pd.notna(val) else 0.0
                                if display_change > 0: advancers += 1
                                elif display_change < 0: decliners += 1
                                
                                impact = (data["weight"] * display_change)
                                
                                stock_rows.append({
                                    "Stock": data["name"],
                                    "Weight": data["weight"] * 100,
                                    "Live Change": display_change,
                                    "NAV Impact": impact
                                })
                            
                            st.caption(f"📈 Advancing: **{advancers}** | 📉 Declining: **{decliners}**")
                            
                            df_stocks = pd.DataFrame(stock_rows).sort_values("NAV Impact", ascending=True)
                            
                            st.dataframe(
                                df_stocks.style.format({
                                    "Weight": "{:.1f}%", 
                                    "Live Change": "{:.2f}%",
                                    "NAV Impact": "{:.3f}%"
                                }, na_rep="N/A").map(style_negative_positive, subset=["Live Change", "NAV Impact"]), 
                                use_container_width=True, 
                                hide_index=True
                            )
