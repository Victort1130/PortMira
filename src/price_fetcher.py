import requests
import json
import time

def fetch_price():
    
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"
    
    try:
        print("⏳ 正在上網抓取最新價格...")
        
        response = requests.get(url)
        response.raise_for_status() 
        
        
        price_data = response.json() 
        
        
        price_data["fetch_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        print("✅ 抓取成功！目前的價格是：")
        print(f"Bitcoin: ${price_data['bitcoin']['usd']}")
        print(f"Ethereum: ${price_data['ethereum']['usd']}")
        
        
        with open('latest_prices.json', 'w', encoding='utf-8') as f:
            json.dump(price_data, f, indent=4)
            
        print("📁 資料已經完美存入 latest_prices.json 囉！")
            
    except Exception as e:

        print(f"❌ 抓取失敗，發生錯誤: {e}")

if __name__ == "__main__":
    fetch_price()
