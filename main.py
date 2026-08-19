import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz
import requests
import yfinance as yf
import time
import json
import concurrent.futures

# --- APP CONFIGURATION ---
st.set_page_config(page_title="MF Dip Analyzer Pro", page_icon="📉", layout="wide")

# --- PREMIUM TRADING TERMINAL THEME CSS ---
st.markdown(
    """
    <style>
    .stApp { background-color: #0b0e14; background-image: linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px); background-size: 30px 30px; color: #e2e8f0; font-family: 'Inter', sans-serif; }
    h1, h2, h3 { color: #f8fafc !important; font-weight: 600; text-shadow: 0px 2px 4px rgba(0,0,0,0.5); }
    div[data-testid="stMetricValue"] { color: #ffffff; font-size: 2.2rem; font-weight: 700; }
    div[data-testid="stMetricDelta"] { font-size: 1.2rem; font-weight: 600; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] { height: 50px; color: #64748b; font-size: 1.1rem; border-bottom: 2px solid transparent; }
    .stTabs [aria-selected="true"] { color: #e2e8f0 !important; border-bottom: 2px solid #38bdf8 !important; }
    .stDataFrame { background-color: rgba(30, 41, 59, 0.85); border-radius: 8px; padding: 10px; border: 1px solid #334155; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- OFFICIAL AMFI SCHEME CODES ---
mf_amfi_codes = {
    "HDFC Flexi Cap Fund Direct Growth": "118955",
    "Parag Parikh Flexi Cap Fund Direct Growth": "122639",
    "Helios Flexi Cap Fund Direct Growth": "152135",
}

# --- GROWW SLUG TO YAHOO TICKER AUTO-TRANSLATOR ---
def slug_to_ticker(slug):
    """
    Converts a Groww URL slug to a Yahoo Finance NSE ticker.
    Adds common mappings, and attempts to guess the rest.
    """
    slug = str(slug).lower().strip()
    
    # Common overrides for slugs that don't match standard patterns
    overrides = {
        "reliance-industries": "RELIANCE.NS",
        "hdfc-bank": "HDFCBANK.NS",
        "icici-bank": "ICICIBANK.NS",
        "infosys": "INFY.NS",
        "tata-consultancy-services": "TCS.NS",
        "itc": "ITC.NS",
        "larsen-toubro": "LT.NS",
        "bajaj-finance": "BAJFINANCE.NS",
        "bharti-airtel": "BHARTIARTL.NS",
        "state-bank-of-india": "SBIN.NS",
        "kotak-mahindra-bank": "KOTAKBANK.NS",
        "axis-bank": "AXISBANK.NS",
        "hindustan-unilever": "HINDUNILVR.NS",
        "mahindra-mahindra": "M&M.NS",
        "maruti-suzuki-india": "MARUTI.NS",
        "hcl-technologies": "HCLTECH.NS",
        "sun-pharmaceutical-industries": "SUNPHARMA.NS",
        "tata-motors": "TATAMOTORS.NS",
        "titan-company": "TITAN.NS",
        "power-grid-corporation-of-india": "POWERGRID.NS",
        "bajaj-finserv": "BAJAJFINSV.NS",
        "coal-india": "COALINDIA.NS",
    }
    
    if slug in overrides:
        return overrides[slug]
    
    # Fallback guesser: remove hyphens, uppercase, append .NS
    guessed_ticker = slug.replace("-", "").upper() + ".NS"
    return guessed_ticker

def standardize_holdings(raw_funds):
    """Ensures holdings are formatted correctly regardless of the JSON structure."""
    standardized = {}
    for fund, holdings in raw_funds.items():
        std_holdings = {}
        if isinstance(holdings, dict):
            for slug, data in holdings.items():
                if isinstance(data, dict):
                    std_holdings[slug] = {
                        "name": data.get("name", slug),
                        "weight": float(data.get("weight", 0.0))
                    }
                elif isinstance(data, (int, float)):
                    std_holdings[slug] = {"name": slug, "weight": float(data)}
                else:
                    std_holdings[slug] = {"name": str(data), "weight": 0.0}
        standardized[fund] = std_holdings
    return standardized

@st.cache_data(ttl=3600)
def load_holdings():
    try:
        with open("holdings.json", "r") as file:
            raw_data = json.load(file)
            return standardize_holdings(raw_data)
    except FileNotFoundError:
        st.error("Holdings file not found. Please run update_holdings.py first.")
        return {}
    except json.JSONDecodeError:
        st.error("Error reading holdings.json. Ensure it is valid JSON.")
        return {}

funds = load_holdings()

# --- YFINANCE DATA SCRAPER ---
@st.cache_data(ttl=60)
def fetch_yahoo_index_data():
    indices = {"NIFTY 50": "^NSEI", "SENSEX": "^BSESN"}
    data = {}
    
    for name, ticker in indices.items():
        try:
            tkr = yf.Ticker(ticker)
            hist = tkr.history(period="2d")
            
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                latest = hist['Close'].iloc[-1]
                change = ((latest - prev_close) / prev_close) * 100
                data[name] = {"value": latest, "change": change, "ok": True}
            else:
                data[name] = {"value": 0.0, "change": 0.0, "ok": False}
        except Exception:
            data[name] = {"value": 0.0, "change": 0.0, "ok": False}
            
    return data

@st.cache_data(ttl=60)
def fetch_yahoo_live_stocks(slugs):
    changes = {}
    valid_slugs = [s for s in slugs if s]

    def get_stock_change(slug):
        ticker = slug_to_ticker(slug)
        try:
            tkr = yf.Ticker(ticker)
            hist = tkr.history(period="2d")
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                latest = hist['Close'].iloc[-1]
                change = ((latest - prev_close) / prev_close) * 100
                return slug, change
        except:
            pass
        return slug, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(get_stock_change, valid_slugs)

    for slug, change in results:
        changes[slug] = change

    changes["_status"] = "ok" if any(v is not None for v in changes.values()) else "failed"
    return changes

# --- EXISTING AMFI NAV LOGIC ---
@st.cache_data(ttl=3600)
def fetch_amfi_scheme_data(code):
    url = f"https://api.mfapi.in/mf/{code}"
    try:
        res = requests.get(url, timeout=10).json()
        df = pd.DataFrame(res.get("data", []))
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
            df["nav"] = pd.to_numeric(df["nav"])
            return df.sort_values("date").reset_index(drop=True)
    except:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_amfi_eod_data():
    eod = {}
    for name, code in mf_amfi_codes.items():
        df = fetch_amfi_scheme_data(code)
        if not df.empty and len(df) >= 2:
            latest, prev = df.iloc[-1]["nav"], df.iloc[-2]["nav"]
            eod[name] = {"nav": latest, "change": ((latest - prev) / prev) * 100}
        else:
            eod[name] = {"nav": None, "change": None}
    return eod

@st.cache_data(ttl=3600)
def fetch_historical_mf_data(period="1mo"):
    df_list = []
    for name, code in mf_amfi_codes.items():
        df = fetch_amfi_scheme_data(code)
        if not df.empty:
            cutoff = df["date"].max() - pd.Timedelta(days=30)
            df = df[df["date"] >= cutoff].copy()
            df["Normalized"] = (df["nav"] / df["nav"].iloc[0]) * 100
            df["Fund"] = name
            df_list.append(df.rename(columns={"date": "Date"}))
    return pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()

# --- COMPUTATION ENGINE ---
def compute_fund_summary():
    market = fetch_yahoo_index_data()
    all_slugs = list(set(slug for holdings in funds.values() for slug in holdings.keys()))
    live_changes = fetch_yahoo_live_stocks(all_slugs)
    amfi = fetch_amfi_eod_data()

    rows = []
    for fund_name, holdings in funds.items():
        weighted_impact = 0.0
        valid_components = 0

        for slug, data in holdings.items():
            change = live_changes.get(slug)
            if change is not None:
                weighted_impact += data["weight"] * float(change)
                valid_components += 1

        nav_data = amfi.get(fund_name, {})
        
        if not valid_components: signal = "Hold Cash"
        elif weighted_impact <= -0.50: signal = "Strong Buy"
        elif weighted_impact <= -0.25: signal = "Medium Buy"
        else: signal = "Hold Cash"

        rows.append({
            "Fund": fund_name,
            "Weighted Impact": round(weighted_impact, 2) if valid_components else 0.0,
            "NAV": round(nav_data.get("nav", 0), 3) if nav_data.get("nav") else None,
            "NAV Change": round(nav_data.get("change", 0), 2) if nav_data.get("change") else None,
            "Signal": signal,
        })

    summary = pd.DataFrame(rows).sort_values("Weighted Impact", ascending=True)
    rec = summary.iloc[0] if not summary.empty else None
    return market, summary, rec, live_changes

# --- DASHBOARD UI ---
def main():
    st.title("📉 MF Dip Analyzer Pro (yfinance Edition)")
    st.caption("Powered by Yahoo Finance API. Robust server-side fetching with Auto-Slug translation.")

    if st.button("Refresh data"):
        st.cache_data.clear()

    market, summary, rec, live_changes = compute_fund_summary()

    if not market or not market.get("NIFTY 50", {}).get("ok"):
        st.warning("Market indices temporarily unavailable. Yahoo Finance API may be rate-limiting.")

    c1, c2, c3 = st.columns(3)
    nifty, sensex = market.get("NIFTY 50", {}), market.get("SENSEX", {})
    
    c1.metric("NIFTY 50", f"₹{nifty.get('value', 0):,.2f}", f"{nifty.get('change', 0):.2f}%")
    c2.metric("SENSEX", f"₹{sensex.get('value', 0):,.2f}", f"{sensex.get('change', 0):.2f}%")
    
    if rec is not None:
        impact = rec['Weighted Impact']
        impact_str = f"{impact:.2f}%" if pd.notna(impact) else "N/A"
        
        c3.metric("Deployment Signal", rec["Signal"], impact_str)
        st.info(f"Top Opportunity: **{rec['Fund']}** | Action: **{rec['Signal']}**")

    # Bar Chart
    chart_df = summary.copy()
    cmap = {"Strong Buy": "#f23645", "Medium Buy": "#f59e0b", "Hold Cash": "#38bdf8"}
    fig = px.bar(chart_df, x="Fund", y="Weighted Impact", color="Signal", color_discrete_map=cmap)
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    # Analytics Tabs
    st.divider()
    st.subheader("📊 Advanced Analytics")
    t1, t2 = st.tabs(["Historical NAV", "Holdings Breakdown"])
    
    with t1:
        hist_df = fetch_historical_mf_data()
        if not hist_df.empty:
            fig2 = px.line(hist_df, x="Date", y="Normalized", color="Fund", template="plotly_dark")
            st.plotly_chart(fig2, use_container_width=True)
            
    with t2:
        selected_fund = st.selectbox("Select Fund:", list(funds.keys()))
        holdings_data = funds.get(selected_fund, {})
        if holdings_data:
            donut_data = [{"Stock": v["name"], "Weight": v["weight"]} for k, v in holdings_data.items()]
            if donut_data:
                fig3 = px.pie(pd.DataFrame(donut_data), values='Weight', names='Stock', hole=0.4, template="plotly_dark")
                fig3.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No holdings data to display for this fund.")

    # Detailed Holdings Table
    st.divider()
    st.subheader("🔍 Live Impact Breakdown")
    cols = st.columns(len(funds) if funds else 1)
    
    for idx, (fund_name, holdings) in enumerate(funds.items()):
        with cols[idx]:
            with st.expander(f"{fund_name}", expanded=True):
                rows = []
                for slug, data in holdings.items():
                    val = live_changes.get(slug)
                    
                    # Notify user if the auto-translator failed for a specific stock
                    display_change = val if val is not None else 0.0
                    if val is None:
                        st.caption(f"⚠️ Could not map '{slug}' to NSE ticker.")

                    rows.append({
                        "Stock": data["name"],
                        "Weight": data["weight"] * 100,
                        "Live Change": display_change,
                        "NAV Impact": (data["weight"] * display_change) if display_change is not None else 0.0
                    })
                
                df_stocks = pd.DataFrame(rows).sort_values("NAV Impact", ascending=True)
                if not df_stocks.empty:
                    st.dataframe(
                        df_stocks.style.format({"Weight": "{:.1f}%", "Live Change": "{:.2f}%", "NAV Impact": "{:.3f}%"}, na_rep="N/A"), 
                        hide_index=True, use_container_width=True
                    )
                else:
                    st.write("No stock data available.")

if __name__ == "__main__":
    main()
