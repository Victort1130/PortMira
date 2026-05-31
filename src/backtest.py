import yfinance as yf
import pandas as pd
from datetime import date, datetime
from typing import Optional

from src.price_fetcher import fetch_all_fx_rates

CRYPTO_TICKER_MAP = {
    "bitcoin": "BTC-USD", "ethereum": "ETH-USD", "binancecoin": "BNB-USD",
    "cardano": "ADA-USD", "solana": "SOL-USD", "ripple": "XRP-USD",
    "polkadot": "DOT-USD", "dogecoin": "DOGE-USD", "avalanche-2": "AVAX-USD",
    "chainlink": "LINK-USD", "uniswap": "UNI-USD", "litecoin": "LTC-USD",
    "stellar": "XLM-USD", "monero": "XMR-USD",
}


def _get_ticker(asset: dict) -> Optional[str]:
    cat = asset.get("category", "")
    ticker = asset.get("ticker", "")
    if cat == "crypto":
        return CRYPTO_TICKER_MAP.get(ticker.lower(), f"{ticker.upper()}-USD")
    elif cat in ("stock", "stock_tw", "etf"):
        return ticker
    elif cat == "commodity":
        return ticker
    return None


def calc_max_drawdown(values: list) -> float:
    if not values:
        return 0.0
    peak = 0.0
    max_dd = 0.0
    for v in values:
        if v <= 0:
            continue  # skip zero/gap days
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd


def run_backtest(assets: list, start_date: str, end_date: str, base_currency: str, benchmark: Optional[str] = "SPY") -> dict:
    """
    assets: list of asset dicts from portfolio.json
    Returns dict with dates, portfolio_values, benchmark_values, metrics, asset_returns.
    """
    # Filter assets with tickers
    backtest_assets = []
    skipped = []
    for a in assets:
        t = _get_ticker(a)
        if t:
            backtest_assets.append({**a, "_ticker": t})
        else:
            skipped.append(a.get("name", "?"))

    if not backtest_assets:
        return {"error": "沒有可回測的資產（需要有代碼的股票、ETF 或加密貨幣）", "skipped": skipped}

    # Convert every asset's value into base_currency using current FX rates.
    # (Historical FX is not fetched; a constant rate keeps the curve in one
    #  currency, consistent with how the dashboard values the portfolio.)
    _currencies = [a.get("currency", base_currency) for a in backtest_assets]
    fx_rates = fetch_all_fx_rates(_currencies, base_currency)
    for a in backtest_assets:
        a["_fx"] = fx_rates.get(a.get("currency", base_currency), 1.0)

    tickers_to_fetch = [a["_ticker"] for a in backtest_assets]
    if benchmark:
        tickers_to_fetch.append(benchmark)

    try:
        raw = yf.download(tickers_to_fetch, start=start_date, end=end_date, auto_adjust=True, progress=False)
    except Exception as e:
        return {"error": f"價格下載失敗：{e}"}

    if raw.empty:
        return {"error": "無法取得歷史資料，請確認日期範圍"}

    close = raw["Close"] if "Close" in raw.columns else raw
    if isinstance(close, pd.Series):
        close = close.to_frame(name=tickers_to_fetch[0])

    # Calculate portfolio daily value
    dates = close.index.strftime("%Y-%m-%d").tolist()
    portfolio_values = []
    for dt in close.index:
        total = 0.0
        for a in backtest_assets:
            t = a["_ticker"]
            qty = float(a.get("quantity", 0))
            if t in close.columns and not pd.isna(close.loc[dt, t]):
                total += qty * float(close.loc[dt, t]) * a["_fx"]
        portfolio_values.append(total)

    # Benchmark values (normalized to same starting value as portfolio)
    benchmark_values = None
    if benchmark and benchmark in close.columns:
        bm_series = close[benchmark].dropna()
        if not bm_series.empty and portfolio_values:
            # Find first portfolio value > 0 to avoid scaling benchmark to zero
            first_valid_idx = next((i for i, v in enumerate(portfolio_values) if v > 0), None)
            if first_valid_idx is not None:
                first_valid_pv = portfolio_values[first_valid_idx]
                first_valid_dt = close.index[first_valid_idx]
                # Find the benchmark price at (or nearest after) first_valid_dt
                bm_at_start = bm_series[bm_series.index >= first_valid_dt]
                if not bm_at_start.empty and float(bm_at_start.iloc[0]) != 0:
                    scale = first_valid_pv / float(bm_at_start.iloc[0])
                    bm_aligned = []
                    for dt in close.index:
                        if dt in bm_series.index and not pd.isna(bm_series[dt]):
                            bm_aligned.append(float(bm_series[dt]) * scale)
                        else:
                            bm_aligned.append(None)
                    benchmark_values = bm_aligned

    # Metrics
    valid_values = [v for v in portfolio_values if v > 0]
    if len(valid_values) >= 2:
        total_return = (valid_values[-1] - valid_values[0]) / valid_values[0] if valid_values[0] > 0 else 0.0
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        years = (end_dt - start_dt).days / 365.25
        cagr = (valid_values[-1] / valid_values[0]) ** (1 / years) - 1 if years > 0 and valid_values[0] > 0 else 0.0
        max_dd = calc_max_drawdown(portfolio_values)
    else:
        total_return = cagr = max_dd = 0.0

    # Per-asset returns
    asset_returns = []
    for a in backtest_assets:
        t = a["_ticker"]
        if t in close.columns:
            series = close[t].dropna()
            if len(series) >= 2:
                ret = (float(series.iloc[-1]) - float(series.iloc[0])) / float(series.iloc[0])
                asset_returns.append({"name": a.get("name", t), "ticker": t, "return": ret})

    return {
        "dates": dates,
        "portfolio_values": portfolio_values,
        "benchmark_values": benchmark_values,
        "total_return": total_return,
        "cagr": cagr,
        "max_drawdown": max_dd,
        "asset_returns": sorted(asset_returns, key=lambda x: x["return"], reverse=True),
        "skipped": skipped,
        "benchmark": benchmark,
    }
