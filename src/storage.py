import json
import os
from models import Asset

class Storage:
    def __init__(self, file_path="data.json"):
        self.file_path = file_path

    def save_all(self, assets: list[Asset]):
        """將資產清單存入 JSON 檔案"""
        with open(self.file_path, "w", encoding="utf-8") as f:
            # 將每個 Asset 物件轉為字典，再存入 JSON
            json_data = [a.to_dict() for a in assets]
            json.dump(json_data, f, indent=4, ensure_ascii=False)
        print(f"--- 成功將資料存入 {self.file_path} ---")

    def load_all(self) -> list[Asset]:
        """從 JSON 檔案讀取資產資料並轉回物件清單"""
        if not os.path.exists(self.file_path):
            print(f"--- 找不到 {self.file_path}，回傳空清單 ---")
            return []
        
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 將字典格式轉回 Asset 物件
                return [Asset(**item) for item in data]
        except (json.JSONDecodeError, TypeError) as e:
            print(f"--- 讀取失敗: {e} ---")
            return []

# ==========================================
# 測試區塊：測試讀取與存入功能
# ==========================================
if __name__ == "__main__":
    print("--- 正在測試 storage.py 的讀寫功能 ---")
    
    # 1. 準備一些測試資料
    test_data = [
        Asset(id=1, name="美金現金", category="外幣", amount=5000, cost_basis=32.1, currency="USD"),
        Asset(id=2, name="比特幣", category="加密貨幣", amount=0.01, cost_basis=2000000, currency="TWD")
    ]

    # 2. 建立儲存物件並存檔
    my_storage = Storage("test_data.json")
    my_storage.save_all(test_data)

    # 3. 測試讀取功能
    loaded_assets = my_storage.load_all()
    
    print("\n[讀取到的資料內容]")
    for asset in loaded_assets:
        print(f"名稱: {asset.name}, 數量: {asset.amount} {asset.currency}")

    print("\n--- 測試結束！請檢查你的資料夾內是否多了 test_data.json ---")
