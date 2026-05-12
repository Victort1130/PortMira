import json
import os
import pandas as pd

from src.models import Asset

DEFAULT_PATH = "data/portfolio.json"
FALLBACK_PATH = "data/sample_portfolio.json"


def load_portfolio(filepath=None):
    """Read a portfolio JSON file and return its contents as a dict."""
    if filepath is None:
        filepath = DEFAULT_PATH if os.path.exists(DEFAULT_PATH) else FALLBACK_PATH

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[storage] File not found: {filepath}")
        return {}


def get_assets_df(portfolio):
    """Convert the assets list in a portfolio dict to a Pandas DataFrame."""
    assets = portfolio.get("assets", [])
    if not assets:
        return pd.DataFrame()
    return pd.DataFrame(assets)


def get_liabilities_df(portfolio):
    """Convert the liabilities list in a portfolio dict to a Pandas DataFrame."""
    liabilities = portfolio.get("liabilities", [])
    if not liabilities:
        return pd.DataFrame()
    return pd.DataFrame(liabilities)


def save_portfolio(portfolio, filepath=DEFAULT_PATH):
    """Write a portfolio dict back to a JSON file, creating directories as needed."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)
    print(f"[storage] Portfolio saved to {filepath}")


class Storage:
    """Simple Asset-object based storage (for standalone use outside the Streamlit app)."""

    def __init__(self, file_path="data.json"):
        self.file_path = file_path

    def save_all(self, assets: list[Asset]):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump([a.to_dict() for a in assets], f, indent=4, ensure_ascii=False)

    def load_all(self) -> list[Asset]:
        if not os.path.exists(self.file_path):
            return []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return [Asset(**item) for item in json.load(f)]
        except (json.JSONDecodeError, TypeError) as e:
            print(f"[Storage] read error: {e}")
            return []
