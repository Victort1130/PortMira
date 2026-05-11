這個想法太棒了！要把 Dashboard 做得好用，當然不能把幣種寫死。

CoinGecko API 其實非常聰明，它的網址允許我們一次傳入多個加密貨幣的名稱（用逗號隔開）。所以我們只需要把使用者輸入的清單，組合成一個長字串塞進網址裡就可以了！

這一次，我們把加密貨幣與法幣匯率都做成可以讓使用者自由輸入的格式。請將 price_fetcher.py 替換成以下最終完美版：

Python
import requests
import json
import time

def fetch_market_data():
    # ==========================================
    # 0. 接收使用者輸入：動態選擇加密貨幣與法幣
    # ==========================================
    print("💡 常見加密貨幣：bitcoin, ethereum, solana, dogecoin, ripple")
    crypto_input = input("👉 請輸入需要的加密貨幣 (用逗號分隔，按 Enter 預設為 bitcoin, ethereum)：")
    
    print("\n💡 常見法幣代碼：TWD, JPY, EUR, GBP, KRW")
    fiat_input = input("👉 請輸入需要的法幣匯率 (用逗號分隔，按 Enter 預設為 TWD, JPY)：")

    # 處理加密貨幣清單 (CoinGecko 的 ID 必須是小寫)
    if crypto_input.strip() == "":
        target_cryptos = ["bitcoin", "ethereum"]
    else:
        target_cryptos = [c.strip().lower() for c in crypto_input.split(",")]

    # 處理法幣清單 (ExchangeRate 的代碼必須是大寫)
    if fiat_input.strip() == "":
        target_fiats = ["TWD", "JPY"]
    else:
        target_fiats = [f.strip().upper() for f in fiat_input.split(",")]

    market_data = {
        "fetch_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "crypto": {},
        "fiat": {}
    }

    # ==========================================
    # 1. 動態抓取加密貨幣價格
    # ==========================================
    try:
        print("\n⏳ 正在抓取加密貨幣價格...")
        # 魔法在這裡！我們用 ",".join() 把清單變成 "bitcoin,solana" 這種格式塞進網址
        crypto_ids = ",".join(target_cryptos)
        crypto_url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_ids}&vs_currencies=usd"
        
        crypto_res = requests.get(crypto_url)
        crypto_res.raise_for_status()
        
        # 把 API 回傳的結果存起來
        fetched_cryptos = crypto_res.json()
        
        # 檢查使用者輸入的幣種有沒有真的抓到
        for c in target_cryptos:
            if c in fetched_cryptos:
                market_data["crypto"][c] = fetched_cryptos[c]
            else:
                print(f"⚠️ 找不到加密貨幣：{c} (可能是名稱拼錯了)")
                
        print("✅ 加密貨幣抓取成功！")
    except Exception as e:
        print(f"❌ 加密貨幣抓取失敗: {e}")

    # ==========================================
    # 2. 動態抓取外幣匯率
    # ==========================================
    try:
        print("⏳ 正在抓取最新外幣匯率...")
        fiat_url = "https://api.exchangerate-api.com/v4/latest/USD"
        fiat_res = requests.get(fiat_url)
        fiat_res.raise_for_status()
        all_rates = fiat_res.json().get("rates", {})
        
        for fiat in target_fiats:
            if fiat in all_rates:
                market_data["fiat"][fiat] = all_rates[fiat]
            else:
                print(f"⚠️ 找不到法幣代碼：{fiat}")
                
        print("✅ 外幣匯率抓取成功！")
    except Exception as e:
        print(f"❌ 外幣匯率抓取失敗: {e}")

    # ==========================================
    # 3. 顯示結果並存檔
    # ==========================================
    print("\n📊 === 即時市場報價 ===")
    
    # 動態印出加密貨幣 (.capitalize() 會讓第一個字母變成大寫，看起來比較漂亮)
    for crypto, data in market_data["crypto"].items():
        print(f"🔹 {crypto.capitalize()}: ${data.get('usd', 'N/A')}")
        
    print("-" * 20) # 分隔線
    
    # 動態印出法幣匯率
    for fiat, rate in market_data["fiat"].items():
        print(f"💵 1 USD = {rate} {fiat}")

    with open('latest_prices.json', 'w', encoding='utf-8') as f:
        json.dump(market_data, f, indent=4, ensure_ascii=False)
        
    print("\n📁 客製化資料已經完美存入 latest_prices.json！")

if __name__ == "__main__":
    fetch_market_data()
