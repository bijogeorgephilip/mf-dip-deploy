import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz
import requests
import time
import json
import re
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

@st.cache_data(ttl=3600)
def load_holdings():
    try:
        with open("holdings.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        st.error("Holdings file not found. Please run update_holdings.py first.")
        return {}

funds = load_holdings()

# --- 100% GROWW-NATIVE SCRAPER (Replaces Yahoo Finance) ---
@st.cache_data(ttl=60)
def fetch_groww_index_data():
    indices = {"NIFTY 50": "nifty-50", "SENSEX": "sensex"}
    data = {}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    for name, slug in indices.items():
        try:
            url = f"https://groww.in/indices/{slug}"
            res = requests.get(url, headers=headers, timeout=5)
            # Scrape the background JSON injected by Groww
            change_match = re.search(r'"dayChangePerc":\s*([-\d\.]+)', res.text)
            val_match = re.search(r'"livePrice":\s*([-\d\.]+)', res.text)
            
            change = float(change_match.group(1)) if change_match else 0.0
            value = float(val_match.group(1)) if val_match else 0.0
            data[name] = {"value": value, "change": change, "ok": True}
        except Exception:
            data[name] = {"value": None, "change": None, "ok": False}
    return data

@st.cache_data(ttl=60)
def fetch_groww_live_stocks(slugs):
    changes = {}
    valid_slugs = [s for s in slugs if s]

    def scrape_stock(slug):
        url = f"https://groww.in/stocks/{slug}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        try:
            res = requests.get(url, headers=headers, timeout=5)
            # Scrape the dayChange percentage directly from the HTML source
            match = re.search(r'"dayChangePerc":\s*([-\d\.]+)', res.text)
            if match:
                return slug, float(match.group(1))
        except:
            pass
        return slug, None

    # Multi-threading: Fetches 10 stocks simultaneously instead of 1 by 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(scrape_stock, valid_slugs)

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
    market = fetch_groww_index_data()
    all_slugs = list(set(slug for holdings in funds.values() for slug in holdings.keys()))
    live_changes = fetch_groww_live_stocks(all_slugs)
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
            "Weighted Impact": round(weighted_impact, 2) if valid_components else None,
            "NAV": round(nav_data.get("nav", 0), 3) if nav_data.get("nav") else None,
            "NAV Change": round(nav_data.get("change", 0), 2) if nav_data.get("change") else None,
            "Signal": signal,
        })

    summary = pd.DataFrame(rows).sort_values("Weighted Impact", ascending=True)
    rec = summary.iloc[0] if not summary.empty else None
    return market, summary, rec, live_changes

# --- DASHBOARD UI ---
def main():
    st.title("📉 MF Dip Analyzer Pro (Groww Native)")
    st.caption("100% Yahoo-Free. Multi-threaded live scraping directly from Groww endpoints.")

    if st.button("Refresh data"):
        st.cache_data.clear()

    market, summary, rec, live_changes = compute_fund_summary()

    if not market or not market.get("NIFTY 50", {}).get("ok"):
        st.warning("Market data temporarily unavailable from Groww.")

    c1, c2, c3 = st.columns(3)
    nifty, sensex = market.get("NIFTY 50", {}), market.get("SENSEX", {})
    
    c1.metric("NIFTY 50", f"₹{nifty.get('value', 0):,.2f}", f"{nifty.get('change', 0):.2f}%")
    c2.metric("SENSEX", f"₹{sensex.get('value', 0):,.2f}", f"{sensex.get('change', 0):.2f}%")
    
    if rec is not None:
        c3.metric("Deployment Signal", rec["Signal"], f"{rec['Weighted Impact']:.2f}%")
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
            fig3 = px.pie(pd.DataFrame(donut_data), values='Weight', names='Stock', hole=0.4, template="plotly_dark")
            fig3.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig3, use_container_width=True)

    # Detailed Holdings Table
    st.divider()
    st.subheader("🔍 Live Impact Breakdown")
    cols = st.columns(len(funds))
    
    for idx, (fund_name, holdings) in enumerate(funds.items()):
        with cols[idx]:
            with st.expander(f"{fund_name}", expanded=True):
                rows = []
                for slug, data in holdings.items():
                    val = live_changes.get(slug)
                    rows.append({
                        "Stock": data["name"],
                        "Weight": data["weight"] * 100,
                        "Live Change": val,
                        "NAV Impact": (data["weight"] * val) if val is not None else 0.0
                    })
                
                df_stocks = pd.DataFrame(rows).sort_values("NAV Impact", ascending=True)
                st.dataframe(
                    df_stocks.style.format({"Weight": "{:.1f}%", "Live Change": "{:.2f}%", "NAV Impact": "{:.3f}%"}, na_rep="N/A"), 
                    hide_index=True, use_container_width=True
                )

if __name__ == "__main__":
    main()
