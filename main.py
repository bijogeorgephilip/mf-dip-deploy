import streamlit as st
import yfinance as yf
import pandas as pd

# --- APP CONFIGURATION ---
st.set_page_config(page_title="MF Dip Analyzer Pro", page_icon="📉", layout="wide")

# --- CUSTOM UI THEME ---
# Injects a sleek dark premium financial gradient background
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- MUTUAL FUND PORTFOLIO DATA (Top 10 Approx Weights) ---
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
            if len(hist)
