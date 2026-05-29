import pandas as pd
from datetime import date
from src.models import STOCK_CATEGORIES, CRYPTO_CATEGORIES, COMMODITY_CATEGORIES
from src.price_fetcher import (
    fetch_stock_prices,
    fetch_prev_closes,
    fetch_all_fx_rates,
)

# All auto-priced categories go through yfinance (crypto uses BTC-USD format)
_YF_CATEGORIES = STOCK_CATEGORIES | CRYPTO_CATEGORIES | COMMODITY_CATEGORIES


def build_prices(assets_df: pd.DataFrame) -> dict[str, float]:
    """Fetch market prices for all auto-priced assets. Returns {ticker: price}."""
    tickers = (
        assets_df[assets_df["category"].isin(_YF_CATEGORIES) & assets_df["ticker"].notna()]["ticker"]
        .tolist()
    )
    return fetch_stock_prices(tickers) if tickers else {}


def build_prev_closes(assets_df: pd.DataFrame) -> dict[str, float]:
    """Fetch previous close prices for daily change calculation. Returns {ticker: prev_close}."""
    tickers = (
        assets_df[assets_df["category"].isin(_YF_CATEGORIES) & assets_df["ticker"].notna()]["ticker"]
        .tolist()
    )
    return fetch_prev_closes(tickers) if tickers else {}


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


def calc_asset_cagr(market_value: float, cost_basis: float, purchase_date_str) -> float | None:
    """Annualized return (CAGR) for a single asset. Returns None if data is missing or invalid."""
    if not purchase_date_str or cost_basis <= 0 or market_value <= 0:
        return None
    try:
        if isinstance(purchase_date_str, date):
            purchase = purchase_date_str
        else:
            purchase = date.fromisoformat(str(purchase_date_str))
    except (ValueError, TypeError):
        return None
    years = (date.today() - purchase).days / 365.25
    if years < 0.01:
        return None
    return (market_value / cost_basis) ** (1.0 / years) - 1.0


def calc_portfolio_cagr(enriched_df: pd.DataFrame) -> float | None:
    """Portfolio CAGR using earliest purchase_date and aggregate values.
    Only includes assets that have purchase_date set.
    """
    if "purchase_date" not in enriched_df.columns:
        return None
    df = enriched_df[enriched_df["purchase_date"].notna() & (enriched_df["purchase_date"] != "")].copy()
    if df.empty:
        return None
    try:
        earliest = min(
            date.fromisoformat(str(d)) if not isinstance(d, date) else d
            for d in df["purchase_date"]
        )
    except (ValueError, TypeError):
        return None
    years = (date.today() - earliest).days / 365.25
    if years < 0.01:
        return None
    total_mv = float(df["market_value"].sum())
    total_cb = float(df["cost_basis"].sum())
    if total_cb <= 0 or total_mv <= 0:
        return None
    return (total_mv / total_cb) ** (1.0 / years) - 1.0


def add_cagr_column(enriched_df: pd.DataFrame) -> pd.DataFrame:
    """Add per-asset cagr column to enriched_df if purchase_date is present."""
    df = enriched_df.copy()
    if "purchase_date" not in df.columns:
        return df
    df["cagr"] = df.apply(
        lambda row: calc_asset_cagr(
            float(row["market_value"]) if pd.notna(row.get("market_value")) else 0.0,
            float(row["cost_basis"]) if pd.notna(row.get("cost_basis")) else 0.0,
            row.get("purchase_date"),
        ),
        axis=1,
    )
    return df


def calc_rebalance(enriched_df: pd.DataFrame, tolerance_pct: float = 5.0) -> pd.DataFrame:
    """Compute rebalancing actions based on target_pct column (values in 0–100 range).

    tolerance_pct: acceptable deviation in percentage points (e.g. 5 means target±5% = hold).
    Returns DataFrame sorted by absolute delta, with columns:
    name, ticker, category, market_value, current_pct, target_pct, target_range,
    delta_value, delta_units, action
    """
    if "target_pct" not in enriched_df.columns:
        return pd.DataFrame()
    df = enriched_df.copy()
    df["target_pct"] = pd.to_numeric(df["target_pct"], errors="coerce")
    df = df[df["target_pct"].notna() & (df["target_pct"] > 0)].copy()
    if df.empty:
        return pd.DataFrame()

    total_value = float(enriched_df["market_value"].sum())
    if total_value <= 0:
        return pd.DataFrame()

    df["current_pct"] = df["market_value"] / total_value * 100
    df["target_value"] = total_value * df["target_pct"] / 100
    df["delta_value"] = df["target_value"] - df["market_value"]
    def _delta_units(row) -> float:
        price_in_base = float(row.get("current_price", 0) or 0) * float(row.get("fx_rate", 1) or 1)
        if price_in_base <= 0:
            return float("nan")
        return row["delta_value"] / price_in_base

    df["delta_units"] = df.apply(_delta_units, axis=1)

    def _bounds(row):
        lo = row.get("target_min_pct")
        hi = row.get("target_max_pct")
        tgt = row["target_pct"]
        lo = float(lo) if pd.notna(lo) and lo != "" else tgt - tolerance_pct
        hi = float(hi) if pd.notna(hi) and hi != "" else tgt + tolerance_pct
        return lo, hi

    def _action(row) -> str:
        lo, hi = _bounds(row)
        if row["current_pct"] < lo:
            return "買入 Buy"
        if row["current_pct"] > hi:
            return "賣出 Sell"
        return "持有 Hold"

    def _range_str(row) -> str:
        lo, hi = _bounds(row)
        return f"{max(0, lo):.0f}% – {hi:.0f}%"

    df["action"] = df.apply(_action, axis=1)
    df["target_range"] = df.apply(_range_str, axis=1)

    cols = ["name", "ticker", "category", "market_value", "current_pct", "target_pct",
            "target_range", "delta_value", "delta_units", "action"]
    return df[[c for c in cols if c in df.columns]].sort_values(
        "delta_value", key=abs, ascending=False
    ).reset_index(drop=True)


def apply_scenario(
    enriched_df: pd.DataFrame,
    liabilities_df: pd.DataFrame | None,
    fx_rates: dict[str, float],
    category_shocks: dict[str, float],
    fx_shocks: dict[str, float],
) -> tuple[pd.DataFrame, float, float, float]:
    """Apply price and FX shocks and return (scenario_df, total_assets, total_liabilities, net_worth).

    category_shocks: {category: decimal_change} e.g. {"stock": -0.20}
    fx_shocks: {currency: decimal_change} e.g. {"USD": 0.05} means USD strengthens 5% vs base
    """
    if liabilities_df is None:
        liabilities_df = pd.DataFrame()

    df = enriched_df.copy()

    new_fx = {ccy: rate * (1.0 + fx_shocks.get(ccy, 0.0)) for ccy, rate in fx_rates.items()}

    df["scenario_price"] = df.apply(
        lambda row: float(row["current_price"]) * (1.0 + category_shocks.get(row["category"], 0.0)),
        axis=1,
    )
    df["scenario_fx"] = df["currency"].apply(lambda c: new_fx.get(c, fx_rates.get(c, 1.0)))
    df["scenario_value"] = df["quantity"] * df["scenario_price"] * df["scenario_fx"]

    total_assets = float(df["scenario_value"].sum())

    if liabilities_df.empty:
        total_liabilities = 0.0
    else:
        liab = liabilities_df.copy()
        liab["scenario_fx"] = liab["currency"].apply(lambda c: new_fx.get(c, fx_rates.get(c, 1.0)))
        total_liabilities = float((liab["amount"] * liab["scenario_fx"]).sum())

    return df, total_assets, total_liabilities, total_assets - total_liabilities


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
