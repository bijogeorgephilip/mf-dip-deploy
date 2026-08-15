# 📉 Mutual Fund Dip Analyzer

A lightweight, automated Python web application built with Streamlit to execute a mathematically driven, emotionless "Nifty Dip" deployment strategy for Flexi Cap Mutual Funds.

## 🎯 The Purpose
This tool was built to solve a specific problem: **Eliminating the stress of active stock picking and intraday trading.** Instead of staring at a brokerage screen all day, this application automates the decision-making process for deploying lumpsum cash tranches. By tracking the real-time performance of the underlying heavyweight stocks inside specific mutual funds, it calculates exactly which fund is offering the deepest discounted Net Asset Value (NAV) on any given market day.

## 🧠 The Core Strategy (The Manifesto)
This tool strictly follows a disciplined 5-year wealth creation architecture:
1. **The Time Check:** Run the app strictly at **1:50 PM** (before the 3:00 PM mutual fund cut-off).
2. **The Dip Signal:** Confirm the Nifty 50 is trading in the red. 
3. **The Calculation:** The app pulls live NSE data for the top 5 heavyweights of each tracked Flexi Cap fund and multiplies it by their portfolio weightage.
4. **The Execution:** Deploy one lumpsum tranche (e.g., ₹10,000) directly into the fund highlighted by the app as having the most negative daily impact.
5. **The Golden Rule:** Close the app, close the broker, and enjoy the rest of the day.

## ⚙️ Features
* **Real-Time NSE Data:** Uses `yfinance` to fetch live stock market data with a standard ~15-minute delay.
* **Dynamic Weighting:** Calculates exact fund impact based on current portfolio allocations of HDFC Flexi Cap, Parag Parikh Flexi Cap, and Helios Flexi Cap.
* **Deployment Recommendation:** Automatically outputs a clear "Buy" or "Hold Cash" signal based on the math.
* **Mobile Friendly:** Built on Streamlit to be accessed instantly via a smartphone web browser.

## 🚀 How to Run Locally

1. **Install Dependencies:**
   Ensure you have Python installed, then run:
   ```bash
   pip install streamlit yfinance pandas
