import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz
import requests
import time

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
    unsafe_allow_html=True,
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
        "WIPRO.NS": 0.014, "TECHM.NS": 0.013, "JSWSTEEL.NS": 0.013,
        "HINDALCO.NS": 0.013, "COALINDIA.NS": 0.013, "ONGC.NS": 0.012, "GRASIM.NS": 0.012,
        "ADANIPORTS.NS": 0.012, "DIVISLAB.NS": 0.012, "MARUTI.NS": 0.012, "NESTLEIND.NS": 0.012,
        "TATACONSUM.NS": 0.012, "INDUSINDBK.NS": 0.011, "DRREDDY.NS": 0.011, "HINDUNILVR.NS": 0.011,
        "SBILIFE.NS": 0.011, "HDFCLIFE.NS": 0.011, "BAJAJFINSV.NS": 0.010, "BPCL.NS": 0.010,
    },
    "Parag Parikh Flexi Cap": {
        "HDFCBANK.NS": 0.090, "ITC.NS": 0.080, "POWERGRID.NS": 0.065, "ICICIBANK.NS": 0.060,
        "BAJFINANCE.NS": 0.055, "MARUTI.NS": 0.050, "HCLTECH.NS": 0.045, "COALINDIA.NS": 0.040,
        "CDSL.NS": 0.035, "RELIANCE.NS": 0.030, "GOOGL": 0.060, "MSFT": 0.050, "AMZN": 0.045, "META": 0.040,
        "BAJAJ-AUTO.NS": 0.030, "HEROMOTOCO.NS": 0.025, "NESTLEIND.NS": 0.020, "BRITANNIA.NS": 0.020,
        "TATACONSUM.NS": 0.020, "EICHERMOT.NS": 0.015, "TVSMOTOR.NS": 0.015, "COLPAL.NS": 0.015,
        "HINDUNILVR.NS": 0.015, "DABUR.NS": 0.015, "PIDILITIND.NS": 0.015, "MARICO.NS": 0.015,
        "GODREJCP.NS": 0.015, "UBL.NS": 0.010,
    },
    "Helios Flexi Cap": {
        "ICICIBANK.NS": 0.080, "HDFCBANK.NS": 0.070, "SBIN.NS": 0.060, "RELIANCE.NS": 0.055,
        "LT.NS": 0.050, "ITC.NS": 0.045, "INFY.NS": 0.040, "TCS.NS": 0.035, "AXISBANK.NS": 0.030,
        "PAYTM.NS": 0.025, "TRENT.NS": 0.025, "INDIGO.NS": 0.025, "DIXON.NS": 0.025,
        "HAL.NS": 0.025, "BEL.NS": 0.025, "SWIGGY.NS": 0.020, "ZYDUSLIFE.NS": 0.020,
        "APOLLOHOSP.NS": 0.020, "MAXHEALTH.NS": 0.020, "POLYCAB.NS": 0.020, "KPITTECH.NS": 0.020,
        "TATAELXSI.NS": 0.020, "CYIENT.NS": 0.015, "PERSISTENT.NS": 0.015, "COFORGE.NS": 0.015,
        "TATACHEM.NS": 0.015, "SONACOMS.NS": 0.015, "CGPOWER.NS": 0.015, "KALYANKJIL.NS": 0.015,
        "DEVYANI.NS": 0.010, "SUZLON.NS": 0.010, "BSE.NS": 0.010, "MCX.NS": 0.010, "POLICYBZR.NS": 0.010,
    },
}

# --- OFFICIAL AMFI SCHEME CODES (Direct Growth Plans) ---
mf_amfi_codes = {
    "HDFC Flexi Cap Fund Direct Growth": "118955",
    "Parag Parikh Flexi Cap Fund Direct Growth": "122639",
    "Helios Flexi Cap Fund Direct Growth": "152135",
}

INVALID_YF_TICKERS = {
    "ZOMATO.NS",
    "MCDOWELL-N.NS",
    "TATAMOTORS.NS",
    "PAYTM.NS",
    "SWIGGY.NS",
    "MCX.NS",
    "POLICYBZR.NS",
    "KALYANKJIL.NS",
}


def sanitize_portfolio_tickers(portfolio):
    sanitized = {}
    for fund_name, holdings in portfolio.items():
        cleaned = {ticker: weight for ticker, weight in holdings.items() if ticker and ticker not in INVALID_YF_TICKERS}
        if cleaned:
            sanitized[fund_name] = cleaned
    return sanitized


def is_valid_yf_ticker(ticker):
    if not ticker or ticker in INVALID_YF_TICKERS:
        return False
    try:
        info = yf.Ticker(ticker).fast_info
        return info is not None and getattr(info, "lastPrice", None) is not None
    except Exception:
        return False


funds = sanitize_portfolio_tickers(funds)


@st.cache_data(ttl=60)
def fetch_index_data():
    indices = {"NIFTY 50": "^NSEI", "SENSEX": "^BSESN"}
    data = {}
    for name, ticker in indices.items():
        try:
            hist = yf.Ticker(ticker).history(period="2d")
            if len(hist) >= 2:
                prev, curr = hist["Close"].iloc[-2], hist["Close"].iloc[-1]
                if prev and curr:
                    data[name] = {
                        "value": float(curr),
                        "change": ((curr - prev) / prev) * 100,
                        "ok": True,
                    }
                    continue
        except Exception:
            pass

        data[name] = {"value": None, "change": None, "ok": False}
    return data


@st.cache_data(ttl=60)
def fetch_live_data(tickers):
    changes = {}
    valid_tickers = []

    for ticker in tickers:
        if not ticker or ticker == "CASH" or ticker in INVALID_YF_TICKERS:
            continue
        if is_valid_yf_ticker(ticker):
            valid_tickers.append(ticker)

    if not valid_tickers:
        return {"CASH": 0.0, "_status": "no_valid_tickers"}

    try:
        data = yf.download(valid_tickers, period="2d", progress=False, auto_adjust=True)
        if data.empty:
            raise ValueError("Empty Yahoo Finance response")

        close_data = data["Close"] if len(valid_tickers) > 1 else data["Close"].to_frame(name=valid_tickers[0])
                for ticker in valid_tickers:
                    try:
                        # FIX: Check if the column actually exists in the downloaded data!
                        if ticker not in close_data.columns:
                            changes[ticker] = None
                            continue
                        
                        hist = close_data[ticker].dropna()
                        if len(hist) >= 2:
                            prev, curr = hist.iloc[-2], hist.iloc[-1]
                            changes[ticker] = ((curr - prev) / prev) * 100 if prev else 0.0
                        else:
                            changes[ticker] = None
                    except Exception:
                        changes[ticker] = None

    changes["CASH"] = 0.0
    changes["_status"] = "ok" if any(v is not None for v in changes.values()) else "failed"
    return changes


@st.cache_data(ttl=3600)
def fetch_amfi_scheme_data(code):
    """Fetch and normalize a single AMFI fund series into a date/nav DataFrame."""
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
    hist_data = pd.DataFrame()
    days_to_fetch = {"1mo": 30, "3mo": 90, "1y": 365, "5y": 1825}.get(period, 30)

    for name, code in mf_amfi_codes.items():
        try:
            df = fetch_amfi_scheme_data(code)
            if df.empty:
                continue

            cutoff_date = get_ist_now() - pd.Timedelta(days=days_to_fetch)
            df = df[df["date"] >= cutoff_date.tz_localize(None)]
            if df.empty:
                continue

            df = df.copy()
            df["Normalized"] = (df["nav"] / df["nav"].iloc[0]) * 100
            df["Fund"] = name
            df = df.rename(columns={"date": "Date"})
            hist_data = pd.concat([hist_data, df[["Date", "Normalized", "Fund"]]], ignore_index=True)
        except Exception:
            continue

    return hist_data


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
            latest_nav = safe_float(latest_row["nav"])
            prev_nav = safe_float(prev_row["nav"])

            if prev_nav == 0:
                change = None
            else:
                change = ((latest_nav - prev_nav) / prev_nav) * 100

            eod_data[name] = {
                "nav": latest_nav,
                "change": change,
                "date": latest_row["date"].strftime("%d-%b-%Y"),
                "ok": True,
            }
        except Exception:
            eod_data[name] = {"nav": None, "change": None, "date": None, "ok": False}
    return eod_data


def get_ist_now():
    return datetime.now(pytz.timezone("Asia/Kolkata"))


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def compute_fund_summary():
    market = fetch_index_data()
    live_changes = fetch_live_data([ticker for holdings in funds.values() for ticker in holdings.keys()])
    amfi = fetch_amfi_eod_data()

    rows = []
    for fund_name, holdings in funds.items():
        weighted_impact = 0.0
        valid_components = 0

        for ticker, weight in holdings.items():
            change = live_changes.get(ticker)
            if change is None:
                continue
            weighted_impact += weight * float(change)
            valid_components += 1

        nav_snapshot = amfi.get(fund_name, {})
        fund_nav = nav_snapshot.get("nav")
        nav_change = nav_snapshot.get("change")

        signal = "Buy" if valid_components and weighted_impact < -0.5 else "Hold Cash"

        rows.append({
            "Fund": fund_name,
            "Weighted Impact": round(weighted_impact, 2) if valid_components else None,
            "NAV": round(fund_nav, 3) if fund_nav is not None else None,
            "NAV Change": round(nav_change, 2) if nav_change is not None else None,
            "Signal": signal,
        })

    summary = pd.DataFrame(rows).sort_values("Weighted Impact", ascending=True, na_position="last")
    recommendation = summary.iloc[0] if not summary.empty else None
    return market, summary, recommendation


def main():
    st.title("📉 MF Dip Analyzer Pro")
    st.caption("Entry logic for flexi-cap deployment based on weighted market dip exposure.")

    if st.button("Refresh data"):
        st.cache_data.clear()

    market, summary, recommendation = compute_fund_summary()

    has_market_data = any(item.get("ok", False) for item in market.values()) if market else False
    if not has_market_data:
        st.warning("Market data is temporarily unavailable. Yahoo Finance is not responding right now.")
        st.stop()

    nifty = market.get("NIFTY 50", {"value": None, "change": None})
    sensex = market.get("SENSEX", {"value": None, "change": None})

    c1, c2, c3 = st.columns(3)
    with c1:
        if nifty["value"] is None:
            st.metric("NIFTY 50", "N/A", "N/A")
        else:
            st.metric("NIFTY 50", f"₹{nifty['value']:,.2f}", f"{nifty['change']:.2f}%")
    with c2:
        if sensex["value"] is None:
            st.metric("SENSEX", "N/A", "N/A")
        else:
            st.metric("SENSEX", f"₹{sensex['value']:,.2f}", f"{sensex['change']:.2f}%")
    with c3:
        if recommendation is not None and recommendation["Weighted Impact"] is not None:
            st.metric("Deployment Signal", recommendation["Signal"], f"{recommendation['Weighted Impact']:.2f}%")
        else:
            st.metric("Deployment Signal", "Hold Cash", "0.00%")

    if recommendation is not None and recommendation["Weighted Impact"] is not None:
        st.info(
            f"Best opportunity: {recommendation['Fund']} with a weighted impact of {recommendation['Weighted Impact']:.2f}% — "
            f"recommended action: {recommendation['Signal']}."
        )

    st.subheader("Fund comparison")
    chart_df = summary.copy()
    chart_df["Signal Color"] = chart_df["Signal"].map({"Buy": "#f23645", "Hold Cash": "#38bdf8"})
    fig = px.bar(
        chart_df,
        x="Fund",
        y="Weighted Impact",
        color="Signal",
        color_discrete_map={"Buy": "#f23645", "Hold Cash": "#38bdf8"},
        title="Weighted market impact by fund",
    )
    fig.update_layout(xaxis_title="Fund", yaxis_title="Impact (%)", template="plotly_dark")
    st.plotly_chart(fig, width='stretch')

    st.subheader("Live fund snapshot")
    display_df = summary[["Fund", "Weighted Impact", "NAV", "NAV Change", "Signal"]].copy()
    display_df = display_df.rename(
        columns={
            "Weighted Impact": "Weighted impact (%)",
            "NAV": "NAV",
            "NAV Change": "NAV change (%)",
        }
    )
    st.dataframe(display_df, width='stretch', hide_index=True)

    with st.expander("Portfolio logic"):
        st.markdown(
            """
            This dashboard compares the live weighted movement of the underlying stocks inside each flexi-cap portfolio.
            The fund with the most negative weighted impact is highlighted as the current deployment candidate.
            """
        )


if __name__ == "__main__":
    main()
