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

# --- CLEANED OFFICIAL AMFI SCHEME CODES (Single source of truth to avoid chart duplication) ---
mf_amfi_codes = {
    "HDFC Flexi Cap Fund Direct Growth": "118955",
    "Parag Parikh Flexi Cap Fund Direct Growth": "122639",
    "Helios Flexi Cap Fund Direct Growth": "152135",
}

def standardize_holdings(raw_funds):
    """Ensures holdings are formatted correctly. Keys are read directly as Yahoo Tickers."""
    standardized = {}
    for fund, holdings in raw_funds.items():
        # Standardize fund name to match official long names if short names are used
        clean_fund_name = fund
        if fund == "HDFC Flexi Cap": clean_fund_name = "HDFC Flexi Cap Fund Direct Growth"
        elif fund == "Parag Parikh Flexi Cap": clean_fund_name = "Parag Parikh Flexi Cap Fund Direct Growth"
        elif fund == "Helios Flexi Cap": clean_fund_name = "Helios Flexi Cap Fund Direct Growth"
        
        std_holdings = {}
        if isinstance(holdings, dict):
            for ticker, data in holdings.items():
                if isinstance(data, dict):
                    std_holdings[ticker] = {
                        "name": data.get("name", ticker),
                        "weight": float(data.get("weight", 0.0))
                    }
                elif isinstance(data, (int, float)):
                    std_holdings[ticker] = {"name": ticker, "weight": float(data)}
                else:
                    std_holdings[ticker] = {"name": str(data), "weight": 0.0}
        standardized[clean_fund_name] = std_holdings
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
            hist = tkr.history(period="5d").dropna(subset=['Close'])
            
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                latest = hist['Close'].iloc[-1]
                change = ((latest - prev_close) / prev_close) * 100
                data[name] = {"value": float(latest), "change": float(change), "ok": True}
            else:
                data[name] = {"value": 0.0, "change": 0.0, "ok": False}
        except Exception:
            data[name] = {"value": 0.0, "change": 0.0, "ok": False}
            
    return data

@st.cache_data(ttl=60)
def fetch_yahoo_live_stocks(tickers):
    changes = {}
    valid_tickers = [t for t in tickers if t]

    def get_stock_change(ticker):
        try:
            tkr = yf.Ticker(ticker)
            hist = tkr.history(period="5d").dropna(subset=['Close'])
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                latest = hist['Close'].iloc[-1]
                change = ((latest - prev_close) / prev_close) * 100
                
                if pd.isna(change):
                    return ticker, None
                return ticker, float(change)
        except:
            pass
        return ticker, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(get_stock_change, valid_tickers)

    for ticker, change in results:
        changes[ticker] = change

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
        if not df.empty and len(df) >= 1:
            latest = df.iloc[-1]["nav"]
            eod[name] = {"nav": latest, "date": df.iloc[-1]["date"].strftime("%d-%m-%Y")}
        else:
            eod[name] = {"nav": None, "date": "N/A"}
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
    all_tickers = list(set(ticker for holdings in funds.values() for ticker in holdings.keys()))
    live_changes = fetch_yahoo_live_stocks(all_tickers)
    amfi = fetch_amfi_eod_data()

    rows = []
    for fund_name, holdings in funds.items():
        weighted_impact = 0.0
        valid_components = 0

        for ticker, data in holdings.items():
            change = live_changes.get(ticker)
            if change is not None and pd.notna(change):
                weighted_impact += data["weight"] * float(change)
                valid_components += 1

        nav_data = amfi.get(fund_name, {})
        prev_nav = nav_data.get("nav", 0.0) or 0.0
        
        estimated_intraday_nav = prev_nav * (1 + (weighted_impact / 100)) if prev_nav else 0.0
        
        if not valid_components: signal = "Hold Cash"
        elif weighted_impact <= -0.50: signal = "Strong Buy"
        elif weighted_impact <= -0.25: signal = "Medium Buy"
        else: signal = "Hold Cash"

        rows.append({
            "Fund": fund_name,
            "Prev NAV": round(prev_nav, 3),
            "Est. Intraday NAV": round(estimated_intraday_nav, 3),
            "Est. NAV Change (%)": round(weighted_impact, 2) if valid_components else 0.0,
            "NAV Date": nav_data.get("date", "N/A"),
            "Signal": signal,
        })

    summary = pd.DataFrame(rows).sort_values("Est. NAV Change (%)", ascending=True)
    rec = summary.iloc[0] if not summary.empty else None
    return market, summary, rec, live_changes

# --- DASHBOARD UI ---
def main():
    st.title("📉 MF Dip Analyzer Pro (1:30 PM Execution Engine)")
    st.caption("Predicts same-day NAV changes using live stock weights for optimal intraday dip-buying.")

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
        impact = rec['Est. NAV Change (%)']
        impact_str = f"{impact:.2f}%" if pd.notna(impact) else "N/A"
        
        c3.metric("Deployment Signal", rec["Signal"], impact_str)
        st.info(f"Top Opportunity: **{rec['Fund']}** | Action: **{rec['Signal']}** (Est. Intraday Move: {impact_str})")

    # --- MUTUAL FUND INTRADAY NAV PREDICTION TABLE ---
    st.divider()
    st.subheader("📌 1:30 PM Intraday NAV Projections")
    nav_table_df = summary[["Fund", "Prev NAV", "Est. Intraday NAV", "Est. NAV Change (%)", "NAV Date", "Signal"]].copy()
    nav_table_df = nav_table_df.drop_duplicates(subset=["Fund"])
    st.dataframe(
        nav_table_df.style.format({"Prev NAV": "₹{:.3f}", "Est. Intraday NAV": "₹{:.3f}", "Est. NAV Change (%)": "{:.2f}%"}, na_rep="N/A"),
        hide_index=True, use_container_width=True
    )

    # Bar Chart
    st.divider()
    chart_df = summary.drop_duplicates(subset=["Fund"]).copy()
    cmap = {"Strong Buy": "#f23645", "Medium Buy": "#f59e0b", "Hold Cash": "#38bdf8"}
    fig = px.bar(chart_df, x="Fund", y="Est. NAV Change (%)", color="Signal", color_discrete_map=cmap, title="Estimated Intraday NAV Drop (%)")
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
    st.subheader("🔍 Live Stock Impact Breakdown")
    cols = st.columns(len(funds) if funds else 1)
    
    for idx, (fund_name, holdings) in enumerate(funds.items()):
        with cols[idx]:
            with st.expander(f"{fund_name}", expanded=True):
                rows = []
                for ticker, data in holdings.items():
                    val = live_changes.get(ticker)
                    display_change = float(val) if pd.notna(val) else 0.0
                    
                    if pd.isna(val):
                        st.caption(f"⚠️ Market data unavailable for '{ticker}' today.")

                    rows.append({
                        "Stock": data["name"],
                        "Weight": data["weight"] * 100,
                        "Live Change": display_change,
                        "NAV Impact": (data["weight"] * display_change)
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
