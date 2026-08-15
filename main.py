import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# --- APP CONFIGURATION ---
st.set_page_config(page_title="MF Dip Analyzer Pro", page_icon="📉", layout="wide")

# --- PREMIUM TRADING TERMINAL THEME CSS ---
st.markdown(
    """
    <style>
    /* Main Background - Stock Chart Grid Style */
    .stApp {
        background-color: #0b0e14;
        background-image: 
            linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
        background-size: 30px 30px;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3 {
        color: #f8fafc !important;
        font-weight: 600;
        text-shadow: 0px 2px 4px rgba(0,0,0,0.5);
    }
    
    div[data-testid="stMetricValue"] {
        color: #ffffff;
        font-size: 2.2rem;
        font-weight: 700;
    }
    div[data-testid="stMetricDelta"] {
        font-size: 1.2rem;
        font-weight: 600;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        color: #64748b;
        font-size: 1.1rem;
        border-bottom: 2px solid transparent;
    }
    .stTabs [aria-selected="true"] {
        color: #e2e8f0 !important;
        border-bottom: 2px solid #38bdf8 !important;
    }
    
    .stDataFrame {
        background-color: rgba(30, 41, 59, 0.85);
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    
    .stButton>button {
        background-color: #2563eb;
        color: #ffffff;
        border-radius: 4px;
        font-weight: 600;
        border: 1px solid #1d4ed8;
        padding: 0.5rem 1.5rem;
        transition: all 0.2s ease;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .stButton>button:hover {
        background-color: #1d4ed8;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
    }
    
    .stTextInput>div>div>input {
        background-color: rgba(30, 41, 59, 0.8);
        color: #f8fafc;
        border: 1px solid #475569;
        border-radius: 4px;
    }
    .stTextInput>div>div>input:focus {
        border-color: #38bdf8;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- MUTUAL FUND PORTFOLIO DATA ---
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

col1, col2, _ = st.columns([1, 1, 2])
with col1:
    st.metric("NIFTY 50", f"{idx_data['NIFTY 50']['value']:,.2f}", f"{idx_data['NIFTY 50']['change']:.2f}%")
with col2:
    st.metric("SENSEX", f"{idx_data['SENSEX']['value']:,.2f}", f"{idx_data['SENSEX']['change']:.2f}%")

st.divider()

if st.button("EXECUTE MARKET SCAN"):
    with st.spinner("Analyzing Top Holdings & Generating Visuals..."):
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
        
        # 3. PORTFOLIO BREAKDOWN & VISUALIZATION
        st.subheader("Portfolio Diagnostics")
        
        search_query = st.text_input("🔍 Filter by Stock (e.g., 'HDFC')").upper()
        
        tabs = st.tabs(list(funds.keys()))
        
        def color_returns(val):
            color = '#f23645' if val < 0 else '#089981'
            return f'color: {color}; font-weight: 600;'

        for tab, (fund_name, holdings) in zip(tabs, funds.items()):
            with tab:
                # Build data for both Table and Chart
                df_data = []
                for ticker, weight in holdings.items():
                    stock_name = ticker.replace(".NS", "")
                    
                    # Ensure charting data is built even if filtered out of the table
                    change = live_changes.get(ticker, 0.0)
                    df_data.append({
                        "Asset": stock_name,
                        "Allocation": weight * 100,
                        "Intraday Move": change,
                        "Net Drag/Lift": change * weight 
                    })
                
                df_full = pd.DataFrame(df_data)
                df_full = df_full.sort_values(by="Allocation", ascending=False)
                
                # Setup Layout for Table (Left) and Chart (Right)
                chart_col, table_col = st.columns([1, 1])
                
                with table_col:
                    st.markdown("**Live Asset Impact (Top 10)**")
                    # Apply search filter only to the table
                    if search_query:
                        df_display = df_full[df_full["Asset"].str.contains(search_query)]
                    else:
                        df_display = df_full

                    if not df_display.empty:
                        styled_df = df_display.style.map(color_returns, subset=["Intraday Move", "Net Drag/Lift"]).format({
                            "Allocation": "{:.2f}%",
                            "Intraday Move": "{:.2f}%",
                            "Net Drag/Lift": "{:.3f}%"
                        })
                        st.dataframe(styled_df, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"No matching assets found in {fund_name}.")
                
                with chart_col:
                    st.markdown("**Allocation Visualizer**")
                    # Create Interactive Donut Chart using Plotly
                    fig = px.pie(
                        df_full, 
                        values='Allocation', 
                        names='Asset', 
                        hole=0.5, # Makes it a donut
                        color_discrete_sequence=px.colors.qualitative.Prism
                    )
                    
                    # Style chart for dark mode
                    fig.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#e2e8f0'),
                        margin=dict(t=0, b=0, l=0, r=0),
                        showlegend=False
                    )
                    
                    # Add hover info and text position
                    fig.update_traces(
                        textposition='inside', 
                        textinfo='percent+label',
                        hovertemplate="<b>%{label}</b><br>Weight: %{percent}<extra></extra>"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
