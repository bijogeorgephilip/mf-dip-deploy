import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import pytz
import requests
import yfinance as yf
import json
import concurrent.futures
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote

# --- ATTEMPT TO LOAD NLP ENGINE ---
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

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

# --- CLEANED OFFICIAL AMFI SCHEME CODES ---
mf_amfi_codes = {
    "HDFC Flexi Cap Fund Direct Growth": "118955",
    "Parag Parikh Flexi Cap Fund Direct Growth": "122639",
    "Helios Flexi Cap Fund Direct Growth": "152135",
}

# --- HTTP SESSION CREATOR ---
def get_custom_session():
    """Creates a custom requests session with browser headers to prevent Yahoo 401 blocks."""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    })
    return session

def standardize_holdings(raw_funds):
    standardized = {}
    for fund, holdings in raw_funds.items():
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
        st.error("Holdings file not found. Please ensure holdings.json is available.")
        return {}
    except json.JSONDecodeError:
        st.error("Error reading holdings.json. Ensure it is valid JSON.")
        return {}

funds = load_holdings()

# --- YFINANCE DATA SCRAPERS ---
@st.cache_data(ttl=60)
def fetch_yahoo_index_data():
    indices = {"NIFTY 50": "^NSEI", "SENSEX": "^BSESN"}
    data = {}
    session = get_custom_session()
    
    for name, ticker in indices.items():
        try:
            tkr = yf.Ticker(ticker, session=session)
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
    stock_data = {}
    valid_tickers = [t for t in tickers if t]
    session = get_custom_session()

    def get_stock_info(ticker):
        try:
            tkr = yf.Ticker(ticker, session=session)
            hist = tkr.history(period="5d").dropna(subset=['Close'])
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                latest = hist['Close'].iloc[-1]
                change = ((latest - prev_close) / prev_close) * 100
                if pd.isna(change):
                    return ticker, {"price": float(latest), "change": None}
                return ticker, {"price": float(latest), "change": float(change)}
        except:
            pass
        return ticker, {"price": 0.0, "change": None}

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        results = executor.map(get_stock_info, valid_tickers)

    for ticker, info in results:
        stock_data[ticker] = info
    return stock_data

@st.cache_data(ttl=14400)
def fetch_stock_fundamentals(tickers):
    fund_data = {}
    valid_tickers = [t for t in tickers if t]
    session = get_custom_session()

    def get_fundamentals(ticker):
        try:
            time.sleep(0.2)
            tkr = yf.Ticker(ticker, session=session)
            info = tkr.info or {}
            pe = info.get("trailingPE") or info.get("forwardPE")
            pb = info.get("priceToBook")
            roe = info.get("returnOnEquity")
            target_mean = info.get("targetMeanPrice")
            target_high = info.get("targetHighPrice")
            target_low = info.get("targetLowPrice")
            
            return ticker, {
                "pe": float(pe) if pe and pe > 0 else None,
                "pb": float(pb) if pb and pb > 0 else None,
                "roe": float(roe) * 100 if roe else None,
                "target_mean": float(target_mean) if target_mean else None,
                "target_high": float(target_high) if target_high else None,
                "target_low": float(target_low) if target_low else None
            }
        except:
            pass
        return ticker, {"pe": None, "pb": None, "roe": None, "target_mean": None, "target_high": None, "target_low": None}

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(get_fundamentals, valid_tickers)

    for ticker, data in results:
        fund_data[ticker] = data
    return fund_data

@st.cache_data(ttl=14400)
def fetch_news_sentiment(ticker_names):
    """Fetches news headlines from Google News RSS and analyzes sentiment with VADER."""
    sentiment_data = {}
    if not VADER_AVAILABLE:
        return sentiment_data

    analyzer = SentimentIntensityAnalyzer()

    def get_sentiment(ticker, name):
        try:
            query = f"{name} stock India"
            url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=5)
            
            headlines = []
            total_score = 0.0
            
            if response.status_code == 200:
                root = ET.fromstring(response.text)
                for item in root.findall('.//item')[:5]:
                    title_elem = item.find('title')
                    title = title_elem.text if title_elem is not None else ""
                    
                    link_elem = item.find('link')
                    link = link_elem.text if link_elem is not None else "#"
                    
                    source_elem = item.find('source')
                    source = source_elem.text if source_elem is not None else "News"
                    
                    if title:
                        score = analyzer.polarity_scores(title)['compound']
                        total_score += score
                        headlines.append({"title": title, "publisher": source, "score": score, "link": link})
            
            avg_score = total_score / len(headlines) if headlines else 0.0
            
            if avg_score > 0.05: label = "Bullish"
            elif avg_score < -0.05: label = "Bearish"
            else: label = "Neutral"
            
            return ticker, {"score": avg_score, "label": label, "headlines": headlines}
        except Exception:
            return ticker, {"score": 0.0, "label": "Neutral", "headlines": []}

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(get_sentiment, tkr, name) for tkr, name in ticker_names.items()]
        for future in concurrent.futures.as_completed(futures):
            ticker, data = future.result()
            sentiment_data[ticker] = data
            
    return sentiment_data

# --- AMFI NAV LOGIC ---
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

# --- COLOR FORMATTING FUNCTIONS ---
def style_negative_positive(val):
    if isinstance(val, (int, float)):
        if val > 0: return 'color: #00c853;'
        elif val < 0: return 'color: #ff4b4b;'
        else: return 'color: #808495;'
    return ''

def style_signal(val):
    if val == "Strong Buy": return 'color: #ff4b4b; font-weight: 700;'
    elif val == "Medium Buy": return 'color: #f59e0b; font-weight: 700;'
    elif val == "Hold Cash": return 'color: #00c853; font-weight: 700;'
    return ''

def style_sentiment(val):
    if val == "Bullish": return 'color: #00c853; font-weight: 700;'
    elif val == "Bearish": return 'color: #ff4b4b; font-weight: 700;'
    elif val == "Neutral": return 'color: #808495; font-weight: 700;'
    return ''

# --- COMPUTATION ENGINE ---
def compute_fund_summary(strong_thresh, medium_thresh):
    market = fetch_yahoo_index_data()
    
    all_tickers_names = {}
    for holdings in funds.values():
        for ticker, data in holdings.items():
            all_tickers_names[ticker] = data["name"]
            
    all_tickers = list(all_tickers_names.keys())
    
    stock_info_dict = fetch_yahoo_live_stocks(all_tickers)
    fundamentals_dict = fetch_stock_fundamentals(all_tickers)
    sentiment_dict = fetch_news_sentiment(all_tickers_names)
    amfi = fetch_amfi_eod_data()

    rows = []
    peer_rows = []
    fund_sentiment_rows = []
    
    for fund_name, holdings in funds.items():
        weighted_impact = 0.0
        valid_components = 0
        
        weighted_pe = 0.0
        weighted_pb = 0.0
        weighted_roe = 0.0
        weighted_upside = 0.0
        weighted_sentiment = 0.0
        
        weight_pe_cov = 0.0
        weight_pb_cov = 0.0
        weight_roe_cov = 0.0
        weight_target_cov = 0.0
        weight_sentiment_cov = 0.0

        for ticker, data in holdings.items():
            info = stock_info_dict.get(ticker, {})
            fund_stats = fundamentals_dict.get(ticker, {})
            sent_stats = sentiment_dict.get(ticker, {})
            
            w = data["weight"]
            change = info.get("change")
            price = info.get("price", 0.0)
            
            if change is not None and pd.notna(change):
                weighted_impact += w * float(change)
                valid_components += 1

            if fund_stats.get("pe"):
                weighted_pe += w * fund_stats["pe"]
                weight_pe_cov += w
            if fund_stats.get("pb"):
                weighted_pb += w * fund_stats["pb"]
                weight_pb_cov += w
            if fund_stats.get("roe"):
                weighted_roe += w * fund_stats["roe"]
                weight_roe_cov += w
            if fund_stats.get("target_mean") and price > 0:
                upside = ((fund_stats["target_mean"] - price) / price) * 100
                weighted_upside += w * upside
                weight_target_cov += w
                
            if "score" in sent_stats:
                weighted_sentiment += w * sent_stats["score"]
                weight_sentiment_cov += w

        nav_data = amfi.get(fund_name, {})
        prev_nav = nav_data.get("nav", 0.0) or 0.0
        estimated_intraday_nav = prev_nav * (1 + (weighted_impact / 100)) if prev_nav else 0.0
        
        if not valid_components: signal = "Hold Cash"
        elif weighted_impact <= strong_thresh: signal = "Strong Buy"
        elif weighted_impact <= medium_thresh: signal = "Medium Buy"
        else: signal = "Hold Cash"

        rows.append({
            "Fund": fund_name,
            "Prev NAV": round(prev_nav, 3),
            "Est. Intraday NAV": round(estimated_intraday_nav, 3),
            "Est. NAV Change (%)": round(weighted_impact, 2) if valid_components else 0.0,
            "NAV Date": nav_data.get("date", "N/A"),
            "Signal": signal,
        })

        peer_rows.append({
            "Fund": fund_name,
            "Weighted P/E": round(weighted_pe / weight_pe_cov, 1) if weight_pe_cov > 0 else None,
            "Weighted P/B": round(weighted_pb / weight_pb_cov, 2) if weight_pb_cov > 0 else None,
            "Weighted ROE (%)": round(weighted_roe / weight_roe_cov, 2) if weight_roe_cov > 0 else None,
            "Target Fair Upside (%)": round(weighted_upside / weight_target_cov, 2) if weight_target_cov > 0 else None,
            "Valuation Coverage (%)": round(weight_target_cov * 100, 1)
        })
        
        if weight_sentiment_cov > 0:
            final_sent_score = weighted_sentiment / weight_sentiment_cov
            if final_sent_score > 0.05: f_label = "Bullish"
            elif final_sent_score < -0.05: f_label = "Bearish"
            else: f_label = "Neutral"
        else:
            final_sent_score = 0.0
            f_label = "N/A"
            
        fund_sentiment_rows.append({
            "Fund": fund_name,
            "Aggregated Score": round(final_sent_score, 3),
            "Fund Sentiment": f_label
        })

    summary = pd.DataFrame(rows).sort_values("Est. NAV Change (%)", ascending=True)
    peer_df = pd.DataFrame(peer_rows)
    fund_sent_df = pd.DataFrame(fund_sentiment_rows)
    rec = summary.iloc[0] if not summary.empty else None
    return market, summary, rec, stock_info_dict, fundamentals_dict, sentiment_dict, peer_df, fund_sent_df

# --- DASHBOARD UI ---
def main():
    st.title("📉 MF Dip Analyzer Pro")
    st.caption("Live Execution Engine & Fundamental Analytics: Intraday Dip Detection, Fair Value Estimation & Sentiment NLP.")

    if not VADER_AVAILABLE:
        st.warning("⚠️ VADER Sentiment NLP Library is not installed. Please run `pip install vaderSentiment` to enable News Sentiment features.")

    # --- MAIN INTERFACE SETTINGS & TIMESTAMP ---
    with st.expander("⚙️ Execution Settings & System Status", expanded=True):
        col_set1, col_set2, col_set3 = st.columns(3)
        
        with col_set1:
            strong_thresh = st.slider(
                "Strong Buy Trigger (%)", 
                min_value=-3.0, max_value=0.0, value=-0.50, step=0.05,
                help="Set the percentage drop required to flag a 'Strong Buy'."
            )
        with col_set2:
            medium_thresh = st.slider(
                "Medium Buy Trigger (%)", 
                min_value=-1.5, max_value=0.0, value=-0.25, step=0.05,
                help="Set the percentage drop for a 'Medium Buy'."
            )
        with col_set3:
            ist_time = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%I:%M:%S %p')
            st.metric("Last Data Fetch (IST)", ist_time, help="The exact time live market prices were refreshed.")
            if st.button("🔄 Force Refresh Data", width="stretch", help="Click to pull the latest stock prices, fundamentals, and news."):
                st.cache_data.clear()
                st.rerun()

    # Engine Call
    market, summary, rec, stock_info_dict, fundamentals_dict, sentiment_dict, peer_df, fund_sent_df = compute_fund_summary(strong_thresh, medium_thresh)

    if not market or not market.get("NIFTY 50", {}).get("ok"):
        st.warning("Market indices temporarily unavailable. Yahoo Finance API may be rate-limiting.")

    c1, c2, c3 = st.columns(3)
    nifty, sensex = market.get("NIFTY 50", {}), market.get("SENSEX", {})
    
    c1.metric("NIFTY 50", f"₹{nifty.get('value', 0):,.2f}", f"{nifty.get('change', 0):.2f}%", help="Live benchmark value for the Nifty 50 Index.")
    c2.metric("SENSEX", f"₹{sensex.get('value', 0):,.2f}", f"{sensex.get('change', 0):.2f}%", help="Live benchmark value for the Sensex Index.")
    
    if rec is not None:
        impact = rec['Est. NAV Change (%)']
        impact_str = f"{impact:.2f}%" if pd.notna(impact) else "N/A"
        
        c3.metric(
            "Top Opportunity Signal", 
            rec["Signal"], 
            impact_str, 
            help="The fund with the steepest estimated intraday dip right now."
        )
        
        # --- PREMIUM ALERT BANNER ---
        signal_val = rec['Signal']
        banner_color = "#ff4b4b" if signal_val == "Strong Buy" else "#f59e0b" if signal_val == "Medium Buy" else "#00c853"
        bg_color = "rgba(255, 75, 75, 0.15)" if signal_val == "Strong Buy" else "rgba(245, 158, 11, 0.15)" if signal_val == "Medium Buy" else "rgba(0, 200, 83, 0.12)"
        icon = "🚨" if signal_val == "Strong Buy" else "⚡" if signal_val == "Medium Buy" else "🛡️"
        
        st.markdown(f"""
        <div style="border: 1px solid {banner_color}; background-color: {bg_color}; padding: 22px; border-radius: 12px; text-align: center; margin: 20px 0;">
            <h2 style="color: {banner_color}; margin: 0; padding-bottom: 6px; font-size: 2.1rem; font-weight: 700;">
                {icon} {signal_val.upper()}
            </h2>
            <div style="font-size: 1.35rem; color: #f8fafc; font-weight: 500;">
                Target Fund: <strong>{rec['Fund']}</strong>
            </div>
            <div style="font-size: 1.15rem; color: #94a3b8; margin-top: 6px;">
                Estimated Intraday Move: <span style="color: {banner_color}; font-weight: bold; font-size: 1.25rem;">{impact_str}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- MUTUAL FUND INTRADAY NAV PREDICTION TABLE ---
    st.divider()
    st.subheader("📌 Live Intraday NAV Projections")
    nav_table_df = summary[["Fund", "Prev NAV", "Est. Intraday NAV", "Est. NAV Change (%)", "NAV Date", "Signal"]].copy()
    nav_table_df = nav_table_df.drop_duplicates(subset=["Fund"])
    
    styled_summary = nav_table_df.style.format({
        "Prev NAV": "₹{:.3f}", 
        "Est. Intraday NAV": "₹{:.3f}", 
        "Est. NAV Change (%)": "{:.2f}%"
    }, na_rep="N/A").map(
        style_negative_positive, subset=["Est. NAV Change (%)"]
    ).map(
        style_signal, subset=["Signal"]
    )
    
    st.dataframe(
        styled_summary, 
        hide_index=True, 
        width="stretch",
        column_config={
            "Prev NAV": st.column_config.Column(help="The official AMFI End-Of-Day NAV from the previous trading session."),
            "Est. Intraday NAV": st.column_config.Column(help="Projected live NAV estimated using constituent real-time prices."),
            "Est. NAV Change (%)": st.column_config.Column(help="Estimated percentage move of the fund's NAV right now."),
            "Signal": st.column_config.Column(help="Actionable deployment recommendation.")
        }
    )

    # --- ANALYTICS & FUNDAMENTAL SUITE ---
    st.divider()
    st.subheader("📊 Quantitative & Fundamental Analytics Suite")
    t1, t2, t3, t4, t5 = st.tabs([
        "Intraday Dip Chart", 
        "Peer Fundamentals & Intrinsic Upside", 
        "Intrinsic Valuation Explorer", 
        "Holdings Breakdown",
        "News & Sentiment NLP"
    ])
    
    with t1:
        chart_df = summary.drop_duplicates(subset=["Fund"]).copy()
        cmap = {"Strong Buy": "#ff4b4b", "Medium Buy": "#f59e0b", "Hold Cash": "#00c853"}
        fig = px.bar(chart_df, x="Fund", y="Est. NAV Change (%)", color="Signal", color_discrete_map=cmap, title="Estimated Live NAV Drop (%)")
        fig.update_layout(template="plotly_dark")
        st.plotly_chart(fig, width="stretch")

        hist_df = fetch_historical_mf_data()
        if not hist_df.empty:
            fig2 = px.line(hist_df, x="Date", y="Normalized", color="Fund", template="plotly_dark", title="30-Day Historical NAV Performance (Normalized to 100)")
            st.plotly_chart(fig2, width="stretch")

    with t2:
        st.caption("Cross-fund fundamental comparison based on portfolio weighted metrics from institutional equity analysts.")
        st.dataframe(
            peer_df.style.format({
                "Weighted P/E": "{:.1f}x",
                "Weighted P/B": "{:.2f}x",
                "Weighted ROE (%)": "{:.2f}%",
                "Target Fair Upside (%)": "{:.2f}%",
                "Valuation Coverage (%)": "{:.1f}%"
            }, na_rep="N/A").map(style_negative_positive, subset=["Target Fair Upside (%)"]),
            hide_index=True,
            width="stretch",
            column_config={
                "Weighted P/E": st.column_config.Column(help="Portfolio Price-to-Earnings Ratio. Lower indicates better relative value."),
                "Weighted P/B": st.column_config.Column(help="Portfolio Price-to-Book Ratio."),
                "Weighted ROE (%)": st.column_config.Column(help="Return on Equity: Measures the profitability and capital efficiency of the fund's underlying companies."),
                "Target Fair Upside (%)": st.column_config.Column(help="Weighted upside potential to 12-month institutional analyst consensus target prices."),
                "Valuation Coverage (%)": st.column_config.Column(help="Percentage of the portfolio that has active analyst price target coverage.")
            }
        )

    with t3:
        st.caption("Deep-dive into individual stock fair value targets, analyst price bands, and fundamental health ratios.")
        selected_analysis_fund = st.selectbox("Select Fund to Analyze:", list(funds.keys()), key="fund_analysis_select")
        fund_stocks = funds.get(selected_analysis_fund, {})
        
        if fund_stocks:
            val_rows = []
            for ticker, data in fund_stocks.items():
                info = stock_info_dict.get(ticker, {})
                f_stats = fundamentals_dict.get(ticker, {})
                price = info.get("price", 0.0)
                mean_t = f_stats.get("target_mean")
                
                upside = ((mean_t - price) / price) * 100 if (mean_t and price > 0) else None
                
                val_rows.append({
                    "Stock": data["name"],
                    "Current Price": price,
                    "Target Mean": mean_t,
                    "Target Low": f_stats.get("target_low"),
                    "Target High": f_stats.get("target_high"),
                    "Fair Upside (%)": upside,
                    "P/E": f_stats.get("pe"),
                    "P/B": f_stats.get("pb"),
                    "ROE (%)": f_stats.get("roe")
                })
            
            val_df = pd.DataFrame(val_rows).sort_values("Fair Upside (%)", ascending=False)
            st.dataframe(
                val_df.style.format({
                    "Current Price": "₹{:.2f}",
                    "Target Mean": "₹{:.2f}",
                    "Target Low": "₹{:.2f}",
                    "Target High": "₹{:.2f}",
                    "Fair Upside (%)": "{:.2f}%",
                    "P/E": "{:.1f}x",
                    "P/B": "{:.2f}x",
                    "ROE (%)": "{:.2f}%"
                }, na_rep="N/A").map(style_negative_positive, subset=["Fair Upside (%)"]),
                hide_index=True,
                width="stretch",
                column_config={
                    "Fair Upside (%)": st.column_config.Column(help="Potential return to institutional mean consensus fair value target."),
                    "Target Low": st.column_config.Column(help="Conservative bear-case target price."),
                    "Target High": st.column_config.Column(help="Optimistic bull-case target price.")
                }
            )

    with t4:
        selected_fund = st.selectbox("Select Fund for Portfolio Weighting:", list(funds.keys()), key="fund_breakdown_select")
        holdings_data = funds.get(selected_fund, {})
        if holdings_data:
            donut_data = [{"Stock": v["name"], "Weight": v["weight"]} for k, v in holdings_data.items()]
            if donut_data:
                fig3 = px.pie(pd.DataFrame(donut_data), values='Weight', names='Stock', hole=0.4, template="plotly_dark")
                fig3.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig3, width="stretch")

    with t5:
        st.caption("Live AI Sentiment Analysis based on recent news headlines from Google News RSS.")
        
        if VADER_AVAILABLE:
            st.dataframe(
                fund_sent_df.style.map(style_sentiment, subset=["Fund Sentiment"]), 
                hide_index=True, 
                width="stretch",
                column_config={
                    "Aggregated Score": st.column_config.Column(help="Weighted sum of polarity scores (-1.0 to 1.0) for the fund's underlying stocks."),
                    "Fund Sentiment": st.column_config.Column(help="Overall tone of the media coverage for the fund's portfolio.")
                }
            )
            
            st.markdown("### Top Individual Stock Movers (News Driven)")
            selected_sent_fund = st.selectbox("Select Fund for News Breakdown:", list(funds.keys()), key="fund_sent_select")
            fund_stocks_sent = funds.get(selected_sent_fund, {})
            
            if fund_stocks_sent:
                sent_rows = []
                for ticker, data in fund_stocks_sent.items():
                    s_stats = sentiment_dict.get(ticker, {})
                    sent_rows.append({
                        "Stock": data["name"],
                        "Weight": data["weight"] * 100,
                        "NLP Polarity": s_stats.get("score", 0.0),
                        "Sentiment": s_stats.get("label", "Neutral")
                    })
                
                s_df = pd.DataFrame(sent_rows).sort_values("NLP Polarity", ascending=False)
                st.dataframe(
                    s_df.style.format({
                        "Weight": "{:.1f}%",
                        "NLP Polarity": "{:.3f}"
                    }).map(style_sentiment, subset=["Sentiment"]),
                    hide_index=True,
                    width="stretch"
                )
                
                # Display Actual Headlines inside Expander
                st.markdown("#### Read Underlying Headlines")
                for ticker, data in fund_stocks_sent.items():
                    s_stats = sentiment_dict.get(ticker, {})
                    headlines = s_stats.get("headlines", [])
                    if headlines:
                        with st.expander(f"📰 {data['name']} ({s_stats.get('label', 'Neutral')})"):
                            for h in headlines:
                                emoji = "🟢" if h['score'] > 0.05 else "🔴" if h['score'] < -0.05 else "⚪"
                                st.markdown(f"{emoji} **[{h['publisher']}]** [{h['title']}]({h['link']}) (Score: {h['score']:.2f})")
        else:
            st.error("Please run `pip install vaderSentiment` to enable News & Sentiment Analytics.")

    # --- DETAILED HOLDINGS TABLE ---
    st.divider()
    st.subheader("🔍 Live Stock Impact Breakdown")
    cols = st.columns(len(funds) if funds else 1)
    
    for idx, (fund_name, holdings) in enumerate(funds.items()):
        with cols[idx]:
            with st.expander(f"{fund_name}", expanded=True):
                rows = []
                advancers = 0
                decliners = 0
                
                for ticker, data in holdings.items():
                    info = stock_info_dict.get(ticker, {})
                    val = info.get("change")
                    price = info.get("price", 0.0)
                    
                    display_change = float(val) if pd.notna(val) else 0.0
                    
                    if display_change > 0: advancers += 1
                    elif display_change < 0: decliners += 1
                    
                    if pd.isna(val):
                        st.caption(f"⚠️ Market data unavailable for '{ticker}'.")

                    rows.append({
                        "Stock": data["name"],
                        "Price": price,
                        "Weight": data["weight"] * 100,
                        "Live Change": display_change,
                        "NAV Impact": (data["weight"] * display_change)
                    })
                
                st.caption(f"📈 Advancing: **{advancers}** | 📉 Declining: **{decliners}**", help="Market breadth indicator: Shows how many tracked stocks in this fund are currently trading positive vs negative.")
                
                df_stocks = pd.DataFrame(rows).sort_values("Weight", ascending=False)
                
                if not df_stocks.empty:
                    styled_stocks = df_stocks.style.format({
                        "Price": "₹{:.2f}", 
                        "Weight": "{:.1f}%", 
                        "Live Change": "{:.2f}%", 
                        "NAV Impact": "{:.3f}%"
                    }, na_rep="N/A").map(style_negative_positive, subset=["Live Change", "NAV Impact"])
                    
                    st.dataframe(
                        styled_stocks, 
                        hide_index=True, 
                        width="stretch",
                        column_config={
                            "Price": st.column_config.Column(help="The Last Traded Price (LTP) on the exchange."),
                            "Weight": st.column_config.Column(help="The percentage allocation in the fund."),
                            "Live Change": st.column_config.Column(help="The real-time percentage change today."),
                            "NAV Impact": st.column_config.Column(help="Calculated as (Weight × Live Change). Net drag/lift on fund NAV today.")
                        }
                    )
                else:
                    st.write("No stock data available.")

if __name__ == "__main__":
    main()
