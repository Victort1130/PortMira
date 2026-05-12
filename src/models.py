from dataclasses import dataclass, asdict
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
CASH_CATEGORIES = frozenset({"cash"})
MANUAL_CATEGORIES = frozenset({"other"})
AUTO_PRICE_CATEGORIES = STOCK_CATEGORIES | CRYPTO_CATEGORIES


if __name__ == "__main__":
    my_asset = Asset(id=1, name="台積電", category="股票", amount=500, cost_basis=650.0, currency="TWD", note="長期持有")
    print(my_asset)
    print(my_asset.to_dict())
