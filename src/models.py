from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

@dataclass
class Asset:
    id: int                # 唯一識別碼 (例如: 1, 2, 3)
    name: str              # 資產名稱 (例如: 台積電, 美金現金, 比特幣)
    category: str          # 類別 (例如: 股票, 外幣, 加密貨幣, 房地產)
    amount: float          # 持有數量 (例如: 1000, 0.5)
    cost_basis: float      # 每單位買入成本 (例如: 600.5)
    currency: str          # 幣別 (例如: TWD, USD)
    note: Optional[str] = "" # 備註 (選填)
    last_updated: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self):
        """將物件轉換為字典格式，這是為了方便 storage.py 存成 JSON 檔案"""
        return asdict(self)

# ==========================================
# 測試區塊：當你直接執行這個檔案 (models.py) 時會跑這裡
# ==========================================
if __name__ == "__main__":
    print("--- 正在測試 models.py 的資料結構 ---")
    
    # 1. 建立一個範例資產
    my_asset = Asset(
        id=1,
        name="台積電",
        category="股票",
        amount=500,
        cost_basis=650.0,
        currency="TWD",
        note="長期持有"
    )

    # 2. 印出資產物件，確認格式正確
    print("\n[成功建立資產物件]")
    print(my_asset)

    # 3. 測試轉換成字典的功能
    asset_dict = my_asset.to_dict()
    print("\n[成功轉換成字典格式]")
    print(asset_dict)
    
    print("\n--- 測試結束，一切正常！ ---")
