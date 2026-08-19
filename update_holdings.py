import requests
import json
import time

print("📈 Initializing Mutual Fund Holdings Scraper...")

# --- 1. GROWW API CONFIGURATION ---
BASE_URL = "https://groww.in/v1/api/data/mf/web/v3/scheme/search/{}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json"
}

# The specific URL slugs Groww uses for your 3 funds
# THE KEYS HERE ARE EXACTLY HOW YOU WANT THEM TO APPEAR IN YOUR APP
FUNDS_TO_SCRAPE = {
    "HDFC Flexi Cap Fund Direct Growth": "hdfc-equity-fund-direct-plan",
    "Parag Parikh Flexi Cap Fund Direct Growth": "parag-parikh-long-term-equity-fund-direct-growth",
    "Helios Flexi Cap Fund Direct Growth": "helios-flexi-cap-fund-direct-growth"
}

# --- 2. THE TICKER TRANSLATOR ---
# Groww gives us names like "State Bank of India". Yahoo Finance needs "SBIN.NS".
TICKER_MAP = {
    "HDFC Bank Ltd.": "HDFCBANK.NS",
    "ICICI Bank Ltd.": "ICICIBANK.NS",
    "State Bank of India": "SBIN.NS",
    "Reliance Industries Ltd.": "RELIANCE.NS",
    "Larsen & Toubro Ltd.": "LT.NS",
    "ITC Ltd.": "ITC.NS",
    "Infosys Ltd.": "INFY.NS",
    "Tata Consultancy Services Ltd.": "TCS.NS",
    "Axis Bank Ltd.": "AXISBANK.NS",
    "Bharti Airtel Ltd.": "BHARTIARTL.NS",
    "Bajaj Finance Ltd.": "BAJFINANCE.NS",
    "Maruti Suzuki India Ltd.": "MARUTI.NS",
    "Coal India Ltd.": "COALINDIA.NS",
    "Adani Ports & Special Economic Zone Ltd.": "ADANIPORTS.NS",
    "Alphabet Inc Class A": "GOOGL",
    "Microsoft Corp": "MSFT",
    "Amazon.com Inc": "AMZN",
    "Meta Platforms Inc": "META"
}

def guess_ticker(company_name):
    """If the company isn't in our dictionary, try to guess the Yahoo Ticker."""
    first_word = company_name.replace(" Ltd.", "").split()[0].upper()
    return f"{first_word}.NS"

def scrape_fund_holdings():
    final_holdings = {}

    for fund_name, slug in FUNDS_TO_SCRAPE.items():
        print(f"🔄 Fetching data for: {fund_name}...")
        url = BASE_URL.format(slug)
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            holdings_list = data.get("holdings", [])
            
            fund_dict = {}
            for item in holdings_list:
                company_name = item.get("company_name", "")
                weight_percentage = item.get("corpus_per", 0.0)
                
                if not company_name or "TREPS" in company_name or "Net Current Asset" in company_name:
                    continue
                
                decimal_weight = round(float(weight_percentage) / 100, 4)
                ticker = TICKER_MAP.get(company_name, guess_ticker(company_name))
                
                fund_dict[ticker] = decimal_weight

            if fund_dict:
                final_holdings[fund_name] = fund_dict
                print(f"✅ Successfully scraped {len(fund_dict)} stocks for {fund_name}.")
            else:
                print(f"⚠️ Warning: Found no valid stocks for {fund_name}.")
                
        except Exception as e:
            print(f"❌ Error fetching {fund_name}: {e}")
            
        time.sleep(2) 

    return final_holdings

def main():
    print("-------------------------------------------------")
    scraped_data = scrape_fund_holdings()
    
    if scraped_data:
        # Overwrite your holdings.json file automatically!
        with open("holdings.json", "w") as f:
            json.dump(scraped_data, f, indent=4)
        print("-------------------------------------------------")
        print("🎉 SUCCESS! holdings.json has been updated with the latest live data.")
    else:
        print("❌ FAILED to scrape any data. holdings.json was not modified.")

if __name__ == "__main__":
    main()
