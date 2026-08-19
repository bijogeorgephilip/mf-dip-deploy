import requests
import json
import time

print("📈 Initializing Groww-Native Mutual Fund Scraper...")

BASE_URL = "https://groww.in/v1/api/data/mf/web/v3/scheme/search/{}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json"
}

FUNDS_TO_SCRAPE = {
    "HDFC Flexi Cap Fund Direct Growth": "hdfc-equity-fund-direct-plan",
    "Parag Parikh Flexi Cap Fund Direct Growth": "parag-parikh-long-term-equity-fund-direct-growth",
    "Helios Flexi Cap Fund Direct Growth": "helios-flexi-cap-fund-direct-growth"
}

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
                search_id = item.get("search_id", "") # Groww's exact internal URL slug!
                
                if not company_name or "TREPS" in company_name or not search_id:
                    continue
                
                decimal_weight = round(float(weight_percentage) / 100, 4)
                
                # We save BOTH the slug (to scrape prices) and the name (for the UI)
                fund_dict[search_id] = {
                    "name": company_name,
                    "weight": decimal_weight
                }

            if fund_dict:
                final_holdings[fund_name] = fund_dict
                print(f"✅ Successfully scraped {len(fund_dict)} stocks for {fund_name}.")
                
        except Exception as e:
            print(f"❌ Error fetching {fund_name}: {e}")
            
        time.sleep(2) 

    return final_holdings

def main():
    print("-------------------------------------------------")
    scraped_data = scrape_fund_holdings()
    
    if scraped_data:
        with open("holdings.json", "w") as f:
            json.dump(scraped_data, f, indent=4)
        print("-------------------------------------------------")
        print("🎉 SUCCESS! holdings.json has been updated with Groww-Native data.")
    else:
        print("❌ FAILED to scrape any data.")

if __name__ == "__main__":
    main()
