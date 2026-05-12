import pandas as pd
from src.models import STOCK_CATEGORIES, CRYPTO_CATEGORIES
from src.price_fetcher import (
    fetch_stock_prices,
    fetch_crypto_prices,
    fetch_prev_closes,
    fetch_crypto_prev_closes,
    fetch_all_fx_rates,
)


def build_prices(assets_df: pd.DataFrame) -> dict[str, float]:
    """Fetch market prices for all auto-priced assets. Returns {ticker: price}."""
    prices: dict[str, float] = {}

    stock_tickers = (
        assets_df[assets_df["category"].isin(STOCK_CATEGORIES) & assets_df["ticker"].notna()]["ticker"]
        .tolist()
    )
    if stock_tickers:
        prices.update(fetch_stock_prices(stock_tickers))

    crypto_ids = (
        assets_df[(assets_df["category"] == "crypto") & assets_df["ticker"].notna()]["ticker"]
        .tolist()
    )
    if crypto_ids:
        prices.update(fetch_crypto_prices(crypto_ids, vs_currency="usd"))

    return prices


def build_prev_closes(assets_df: pd.DataFrame) -> dict[str, float]:
    """Fetch previous close prices for daily change calculation. Returns {ticker: prev_close}."""
    prev_closes: dict[str, float] = {}

    stock_tickers = (
        assets_df[assets_df["category"].isin(STOCK_CATEGORIES) & assets_df["ticker"].notna()]["ticker"]
        .tolist()
    )
    if stock_tickers:
        prev_closes.update(fetch_prev_closes(stock_tickers))

    crypto_ids = (
        assets_df[(assets_df["category"] == "crypto") & assets_df["ticker"].notna()]["ticker"]
        .tolist()
    )
    if crypto_ids:
        prev_closes.update(fetch_crypto_prev_closes(crypto_ids))

    return prev_closes


def build_fx_rates(
    assets_df: pd.DataFrame,
    liabilities_df: pd.DataFrame,
    base_currency: str,
) -> dict[str, float]:
    """Return {currency: rate_to_base} for all currencies in the portfolio."""
    all_currencies: set[str] = set()
    if not assets_df.empty and "currency" in assets_df.columns:
        all_currencies |= set(assets_df["currency"].tolist())
    if not liabilities_df.empty and "currency" in liabilities_df.columns:
        all_currencies |= set(liabilities_df["currency"].tolist())
    return fetch_all_fx_rates(list(all_currencies), base_currency)


def enrich_assets(
    assets_df: pd.DataFrame,
    prices: dict[str, float],
    fx_rates: dict[str, float],
    base_currency: str = "TWD",
    prev_closes: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Add market_value, cost_basis, unrealized_pl, unrealized_pl_pct, daily_change_pct columns."""
    df = assets_df.copy()

    def _current_price(row) -> float:
        if row["category"] == "cash":
            return 1.0
        ticker = row.get("ticker")
        if ticker and ticker in prices:
            return float(prices[ticker])
        return float(row["cost_per_unit"])

    df["current_price"] = df.apply(_current_price, axis=1)
    df["fx_rate"] = df["currency"].apply(lambda c: fx_rates.get(c, 1.0))

    df["market_value"] = df["quantity"] * df["current_price"] * df["fx_rate"]
    df["cost_basis"] = df["quantity"] * df["cost_per_unit"] * df["fx_rate"]
    df["unrealized_pl"] = df["market_value"] - df["cost_basis"]
    df["unrealized_pl_pct"] = (
        df["unrealized_pl"] / df["cost_basis"].replace(0, float("nan")) * 100
    )

    if prev_closes:
        def _daily_change(row) -> float:
            ticker = row.get("ticker")
            if ticker and ticker in prev_closes and prev_closes[ticker]:
                return (row["current_price"] - prev_closes[ticker]) / prev_closes[ticker] * 100
            return float("nan")
        df["daily_change_pct"] = df.apply(_daily_change, axis=1)

    return df


def calc_net_worth(
    enriched_df: pd.DataFrame,
    liabilities_df: pd.DataFrame,
    fx_rates: dict[str, float],
) -> tuple[float, float, float]:
    """Return (total_assets, total_liabilities, net_worth) in base currency."""
    total_assets = float(enriched_df["market_value"].sum()) if not enriched_df.empty else 0.0

    if liabilities_df.empty:
        total_liabilities = 0.0
    else:
        liab = liabilities_df.copy()
        liab["fx_rate"] = liab["currency"].apply(lambda c: fx_rates.get(c, 1.0))
        total_liabilities = float((liab["amount"] * liab["fx_rate"]).sum())

    return total_assets, total_liabilities, total_assets - total_liabilities


def get_alerts(enriched_df: pd.DataFrame, threshold_pct: float) -> pd.DataFrame:
    """Return assets whose daily price moved by more than threshold_pct (absolute)."""
    if "daily_change_pct" not in enriched_df.columns:
        return pd.DataFrame()
    mask = enriched_df["daily_change_pct"].abs() >= threshold_pct
    return enriched_df[mask & enriched_df["daily_change_pct"].notna()][
        ["name", "category", "current_price", "daily_change_pct", "market_value"]
    ].copy()


def calc_margin_ratio(
    enriched_df: pd.DataFrame,
    liabilities_df: pd.DataFrame,
    fx_rates: dict[str, float],
) -> tuple[float, float, float]:
    """Return (total_assets, margin_loan_total, maintenance_ratio_pct) in base currency.

    融資維持率 = 總市值 / 融資金額 × 100%  (warning threshold: 130%)
    """
    total_assets = float(enriched_df["market_value"].sum()) if not enriched_df.empty else 0.0

    if liabilities_df.empty:
        return total_assets, 0.0, float("inf")

    margin = liabilities_df[liabilities_df["category"] == "margin_loan"].copy()
    if margin.empty:
        return total_assets, 0.0, float("inf")

    margin["fx_rate"] = margin["currency"].apply(lambda c: fx_rates.get(c, 1.0))
    margin_total = float((margin["amount"] * margin["fx_rate"]).sum())
    ratio = (total_assets / margin_total * 100) if margin_total else float("inf")
    return total_assets, margin_total, ratio


def calc_monthly_interest(
    liabilities_df: pd.DataFrame,
    fx_rates: dict[str, float],
) -> tuple[pd.DataFrame, float]:
    """Return (per-liability interest DataFrame, total monthly interest) in base currency."""
    if liabilities_df.empty:
        return pd.DataFrame(), 0.0

    df = liabilities_df.copy()
    df["fx_rate"] = df["currency"].apply(lambda c: fx_rates.get(c, 1.0))
    df["amount_base"] = df["amount"] * df["fx_rate"]
    df["monthly_interest"] = df["amount_base"] * df["annual_rate"] / 12

    result = df[["name", "category", "amount_base", "annual_rate", "monthly_interest"]].copy()
    return result, float(df["monthly_interest"].sum())
