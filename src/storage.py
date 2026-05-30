import json
import os
import pandas as pd

from src.models import Asset

DEFAULT_PATH = "data/portfolio.json"
_EMPTY_PORTFOLIO = {"assets": [], "liabilities": [], "scenarios": [], "meta": {"last_updated": ""}}

EXPENSES_FILE = "data/expenses.json"
BUDGETS_FILE  = "data/budgets.json"
CARDS_FILE    = "data/cards.json"


def load_portfolio(filepath=None):
    """Read a portfolio JSON file and return its contents as a dict."""
    if filepath is None:
        filepath = DEFAULT_PATH

    if not os.path.exists(filepath):
        return _EMPTY_PORTFOLIO.copy()

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[storage] Error reading {filepath}: {e}")
        return _EMPTY_PORTFOLIO.copy()


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


def get_scenarios(portfolio: dict) -> list:
    return portfolio.get("scenarios", [])


def save_scenario(portfolio: dict, scenario: dict, filepath: str = DEFAULT_PATH) -> None:
    if "scenarios" not in portfolio:
        portfolio["scenarios"] = []
    ids = [s["id"] for s in portfolio["scenarios"]]
    if scenario["id"] in ids:
        portfolio["scenarios"][ids.index(scenario["id"])] = scenario
    else:
        portfolio["scenarios"].append(scenario)
    save_portfolio(portfolio, filepath)


def delete_scenario(portfolio: dict, scenario_id: str, filepath: str = DEFAULT_PATH) -> None:
    portfolio["scenarios"] = [s for s in portfolio.get("scenarios", []) if s["id"] != scenario_id]
    save_portfolio(portfolio, filepath)


def save_portfolio(portfolio, filepath=DEFAULT_PATH):
    """Write a portfolio dict back to a JSON file, creating directories as needed."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)
    print(f"[storage] Portfolio saved to {filepath}")


def load_expenses() -> list:
    if not os.path.exists(EXPENSES_FILE):
        return []
    with open(EXPENSES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_expenses(expenses: list) -> None:
    os.makedirs(os.path.dirname(EXPENSES_FILE), exist_ok=True)
    with open(EXPENSES_FILE, "w", encoding="utf-8") as f:
        json.dump(expenses, f, ensure_ascii=False, indent=2)


def load_budgets() -> list:
    if not os.path.exists(BUDGETS_FILE):
        return []
    with open(BUDGETS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_budgets(budgets: list) -> None:
    os.makedirs(os.path.dirname(BUDGETS_FILE), exist_ok=True)
    with open(BUDGETS_FILE, "w", encoding="utf-8") as f:
        json.dump(budgets, f, ensure_ascii=False, indent=2)


def load_cards() -> list:
    if not os.path.exists(CARDS_FILE):
        return []
    with open(CARDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cards(cards: list) -> None:
    os.makedirs(os.path.dirname(CARDS_FILE), exist_ok=True)
    with open(CARDS_FILE, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)


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
