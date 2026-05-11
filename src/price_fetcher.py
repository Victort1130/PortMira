import requests
import json
import time

def fetch_market_data():
    print("💡 常見加密貨幣：bitcoin, ethereum, solana, dogecoin, ripple")
    crypto_input = input("👉 請輸入需要的加密貨幣 (用逗號分隔，按 Enter 預設為 bitcoin, ethereum)：")
    
    print("\n💡 常見法幣代碼：TWD, JPY, EUR, GBP, KRW")
    fiat_input = input("👉 請輸入需要的法幣匯率 (用逗號分隔，按 Enter 預設為 TWD, JPY)：")
    
    if crypto_input.strip() == "":
        target_cryptos = ["bitcoin", "ethereum"]
    else:
        target_cryptos = [c.strip().lower() for c in crypto_input.split(",")]

    if fiat_input.strip() == "":
        target_fiats = ["TWD", "JPY"]
    else:
        target_fiats = [f.strip().upper() for f in fiat_input.split(",")]

    market_data = {
        "fetch_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "crypto": {},
        "fiat": {}
    }

    try:
        print("\n⏳ 正在抓取加密貨幣價格...")
        crypto_ids = ",".join(target_cryptos)
        crypto_url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_ids}&vs_currencies=usd"
        
        crypto_res = requests.get(crypto_url, timeout=5)
        
        if crypto_res.status_code == 429:
            print("⚠️ 警告：觸發 API 速率限制 (Rate Limit)")
            fetched_cryptos = {}
        else:
            crypto_res.raise_for_status()
            fetched_cryptos = crypto_res.json()
        
        for c in target_cryptos:
            if c in fetched_cryptos and fetched_cryptos[c]:
                market_data["crypto"][c] = fetched_cryptos[c]
            else:
                print(f"⚠️ 找不到加密貨幣：{c} (名稱拼錯或無資料)")
                market_data["crypto"][c] = {"usd": "N/A"}
                
        print("✅ 加密貨幣抓取程序完成！")
    except Exception as e:
        print(f"❌ 加密貨幣抓取失敗: {e}")
        for c in target_cryptos:
            market_data["crypto"][c] = {"usd": "N/A"}

    try:
        print("⏳ 正在抓取最新外幣匯率...")
        fiat_url = "https://api.exchangerate-api.com/v4/latest/USD"
        fiat_res = requests.get(fiat_url, timeout=5)
        fiat_res.raise_for_status()
        all_rates = fiat_res.json().get("rates", {})
        
        for fiat in target_fiats:
            if fiat in all_rates:
                market_data["fiat"][fiat] = all_rates[fiat]
            else:
                print(f"⚠️ 找不到法幣代碼：{fiat} (名稱拼錯或無資料)")
                market_data["fiat"][fiat] = "N/A"
                
        print("✅ 外幣匯率抓取程序完成！")
    except Exception as e:
        print(f"❌ 外幣匯率抓取失敗: {e}")
        for fiat in target_fiats:
            market_data["fiat"][fiat] = "N/A"

    print("\n📊 === 即時市場報價 ===")
    
    for crypto, data in market_data["crypto"].items():
        usd_price = data.get('usd') if isinstance(data, dict) else data
        print(f"🔹 {crypto.capitalize()}: ${usd_price}")
        
    print("-" * 20) 
    
    for fiat, rate in market_data["fiat"].items():
        print(f"💵 1 USD = {rate} {fiat}")

    with open('latest_prices.json', 'w', encoding='utf-8') as f:
        json.dump(market_data, f, indent=4, ensure_ascii=False)
        
    print("\n📁 客製化資料已經完美存入 latest_prices.json！")

if __name__ == "__main__":
    fetch_market_data()
