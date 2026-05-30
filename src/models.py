from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional


@dataclass
class Asset:
    id: int
    name: str
    category: str
    amount: float
    cost_basis: float
    currency: str
    note: Optional[str] = ""
    last_updated: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self):
        return asdict(self)


# Category constants used by calculations.py
STOCK_CATEGORIES = frozenset({"stock", "stock_tw", "etf"})
CRYPTO_CATEGORIES = frozenset({"crypto"})
COMMODITY_CATEGORIES = frozenset({"commodity"})
CASH_CATEGORIES = frozenset({"cash"})
MANUAL_CATEGORIES = frozenset({"other"})
AUTO_PRICE_CATEGORIES = STOCK_CATEGORIES | CRYPTO_CATEGORIES | COMMODITY_CATEGORIES

COMMODITY_TICKERS = {
    "GC=F": "黃金 Gold",
    "CL=F": "WTI 原油 Crude Oil",
    "SI=F": "白銀 Silver",
    "HG=F": "銅 Copper",
    "NG=F": "天然氣 Natural Gas",
    "PL=F": "鉑金 Platinum",
    "ZW=F": "小麥 Wheat",
    "ZC=F": "玉米 Corn",
}


EXPENSE_CATEGORIES = ["餐飲", "交通", "訂閱服務", "娛樂", "投資支出", "醫療", "購物", "其他"]
BUDGET_PERIODS     = ["月", "雙週", "週"]
CARD_NETWORKS      = ["Visa", "Mastercard", "JCB", "UnionPay", "Amex", "其他"]
CARD_TYPES         = ["credit", "debit"]
CARD_TYPE_DISPLAY  = {"credit": "信用卡", "debit": "簽帳金融卡"}


@dataclass
class PaymentCard:
    id: str
    card_name: str
    bank: str
    network: str          # from CARD_NETWORKS
    card_tier: str
    last_four: str
    card_type: str        # "credit" or "debit"
    linked_liability_id: Optional[str] = None
    is_default: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass
class Expense:
    id: str
    date: str  # "YYYY-MM-DD"
    category: str
    amount: float
    currency: str
    note: str = ""
    payment_card_id: Optional[str] = None


@dataclass
class Budget:
    id: str
    category: str  # expense category or "總計"
    amount: float
    currency: str
    period: str  # "月", "雙週", "週"
    alert_threshold: float = 0.6


if __name__ == "__main__":
    my_asset = Asset(id=1, name="台積電", category="股票", amount=500, cost_basis=650.0, currency="TWD", note="長期持有")
    print(my_asset)
    print(my_asset.to_dict())
