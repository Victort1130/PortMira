import requests
import json
import time

def fetch_market_data():
    # ==========================================
    # 0. 接收使用者輸入：動態選擇幣種
    # ==========================================
    print("💡 常見法幣代碼：TWD (台幣), JPY (日圓), EUR (歐元), GBP (英鎊), KRW (韓元)")
    user_input = input("👉 請輸入你需要的匯率代碼 (用逗號分隔，直接按 Enter 則預設為 TWD, JPY)：")

    # 處理使用者的輸入：
    # 如果甚麼都沒打，就給預設值
    if user_input.strip() == "":
        target_fiats = ["TWD", "JPY"]
    else:
        # 把輸入的字串用逗號切開，清掉多餘空白，並且全部轉成大寫
        target_fiats = [currency.strip().upper() for currency in user_input.split(",")]

    market_data = {
        "fetch_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "crypto": {},
        "fiat": {}
    }

    # ==========================================
    # 1. 抓取加密貨幣價格 (不變)
    # ==========================================
    try:
        print("\n⏳ 正在抓取加密貨幣價格...")
        crypto_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"
        crypto_res = requests.get(crypto_url)
        crypto_res.raise_for_status()
        market_data["crypto"] = crypto_res.json()
        print("✅ 加密貨幣抓取成功！")
    except Exception as e:
        print(f"❌ 加密貨幣抓取失敗: {e}")

    # ==========================================
    # 2. 抓取外幣匯率 (根據使用者選擇過濾)
    # ==========================================
    try:
        print("⏳ 正在抓取最新外幣匯率...")
        fiat_url = "https://api.exchangerate-api.com/v4/latest/USD"
        fiat_res = requests.get(fiat_url)
        fiat_res.raise_for_status()
        all_rates = fiat_res.json().get("rates", {})
        
        # 迴圈檢查使用者要的幣種有沒有在 API 回傳的資料裡
        for fiat in target_fiats:
            if fiat in all_rates:
                market_data["fiat"][fiat] = all_rates[fiat]
            else:
                print(f"⚠️ 找不到幣種代碼：{fiat} (將忽略此項目)")
                
        print("✅ 外幣匯率抓取成功！")
    except Exception as e:
        print(f"❌ 外幣匯率抓取失敗: {e}")

    # ==========================================
    # 3. 顯示結果並存檔
    # ==========================================
    print("\n📊 === 即時市場報價 ===")
    print(f"🔹 Bitcoin (BTC): ${market_data['crypto'].get('bitcoin', {}).get('usd', 'N/A')}")
    print(f"🔹 Ethereum (ETH): ${market_data['crypto'].get('ethereum', {}).get('usd', 'N/A')}")
    
    # 動態印出使用者選擇的匯率
    for fiat, rate in market_data["fiat"].items():
        print(f"💵 1 USD = {rate} {fiat}")

    with open('latest_prices.json', 'w', encoding='utf-8') as f:
        json.dump(market_data, f, indent=4, ensure_ascii=False)
        
    print("\n📁 客製化資料已經完美存入 latest_prices.json！")

if __name__ == "__main__":
    fetch_market_data()
