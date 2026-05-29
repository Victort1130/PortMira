import yfinance as yf
import pandas as pd
import numpy as np
from typing import Optional

CRYPTO_TICKER_MAP = {
    "bitcoin": "BTC-USD", "ethereum": "ETH-USD", "binancecoin": "BNB-USD",
    "cardano": "ADA-USD", "solana": "SOL-USD", "ripple": "XRP-USD",
    "dogecoin": "DOGE-USD", "avalanche-2": "AVAX-USD",
}


def _to_yf_ticker(asset: dict) -> Optional[str]:
    cat = asset.get("category", "")
    ticker = (asset.get("ticker") or "").strip()
    if not ticker:
        return None
    if cat == "crypto":
        return CRYPTO_TICKER_MAP.get(ticker.lower(), f"{ticker.upper()}-USD")
    elif cat in ("stock", "stock_tw", "etf", "commodity"):
        return ticker
    return None


def calc_rsi(prices: pd.Series, period: int = 14) -> Optional[float]:
    """Return the latest RSI value (0-100). Returns None if insufficient data."""
    if len(prices) < period + 1:
        return None
    delta = prices.diff().dropna()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float('nan'))
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return round(float(val), 1) if not pd.isna(val) else None


def calc_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Return (macd_line, signal_line, histogram) latest values. Returns (None,None,None) if insufficient."""
    if len(prices) < slow + signal:
        return None, None, None
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line

    def _val(s):
        v = s.iloc[-1]
        return round(float(v), 4) if not pd.isna(v) else None

    return _val(macd_line), _val(signal_line), _val(hist)


def rsi_context(rsi: Optional[float]) -> str:
    """Return brief factual context for RSI value."""
    if rsi is None:
        return ""
    if rsi >= 70:
        return "短期偏超買"
    elif rsi <= 30:
        return "短期偏超賣"
    elif rsi >= 60:
        return "偏強"
    elif rsi <= 40:
        return "偏弱"
    return "中性"


def macd_context(macd: Optional[float], signal: Optional[float], hist: Optional[float]) -> str:
    """Return brief factual MACD context."""
    if macd is None or signal is None or hist is None:
        return ""
    if hist > 0 and macd > signal:
        return "MACD 多頭排列"
    elif hist < 0 and macd < signal:
        return "MACD 空頭排列"
    elif hist > 0:
        return "動能轉強"
    else:
        return "動能轉弱"


def fetch_ohlcv(ticker: str, period_days: int = 90) -> pd.DataFrame:
    """Fetch OHLCV data for a ticker. Returns DataFrame with columns:
    date, open, high, low, close, volume. Returns empty DataFrame on error.
    """
    try:
        tf = yf.Ticker(ticker)
        hist = tf.history(period=f"{period_days}d", auto_adjust=True)
        if hist.empty:
            return pd.DataFrame()
        hist = hist.reset_index()
        # Normalize column names
        hist.columns = [c.lower() for c in hist.columns]
        # Keep only needed columns
        needed = ["date", "open", "high", "low", "close", "volume"]
        available = [c for c in needed if c in hist.columns]
        df = hist[available].copy()
        # Ensure date is tz-naive
        if "date" in df.columns:
            if hasattr(df["date"].dtype, "tz") and df["date"].dtype.tz is not None:
                df["date"] = df["date"].dt.tz_localize(None)
        return df
    except Exception:
        return pd.DataFrame()


def calc_sma(closes: list, period: int) -> list:
    """Simple moving average. Returns list with None for the first period-1 items."""
    result = []
    for i in range(len(closes)):
        if i < period - 1:
            result.append(None)
        else:
            window = closes[i - period + 1: i + 1]
            valid = [v for v in window if v is not None]
            result.append(sum(valid) / len(valid) if len(valid) == period else None)
    return result


def calc_bollinger(closes: list, period: int = 20) -> tuple:
    """Bollinger Bands. Returns (upper, mid, lower) as lists with None for first period-1 items."""
    mid = calc_sma(closes, period)
    upper = []
    lower = []
    for i in range(len(closes)):
        if mid[i] is None:
            upper.append(None)
            lower.append(None)
        else:
            window = closes[i - period + 1: i + 1]
            valid = [v for v in window if v is not None]
            if len(valid) == period:
                std = float(np.std(valid, ddof=0))
                upper.append(mid[i] + 2 * std)
                lower.append(mid[i] - 2 * std)
            else:
                upper.append(None)
                lower.append(None)
    return upper, mid, lower


def calc_portfolio_sharpe(enriched_df: pd.DataFrame, fx_rates: dict) -> Optional[float]:
    """Compute annualized Sharpe ratio (risk-free rate = 0) from portfolio daily returns.

    Uses daily_change_pct weighted by market_value if available.
    Falls back to cost_basis/market_value assuming 1-year hold.
    Returns None if insufficient data.
    """
    try:
        df = enriched_df.copy()
        if "market_value" not in df.columns:
            return None
        df["market_value"] = pd.to_numeric(df["market_value"], errors="coerce")
        total_mv = df["market_value"].sum()
        if total_mv <= 0:
            return None

        if "daily_change_pct" in df.columns:
            df["daily_change_pct"] = pd.to_numeric(df["daily_change_pct"], errors="coerce")
            valid = df[df["daily_change_pct"].notna()].copy()
            if len(valid) < 2:
                return None
            # Weight each asset's daily return by market_value
            weights = valid["market_value"] / valid["market_value"].sum()
            portfolio_return = float((valid["daily_change_pct"] / 100 * weights).sum())
            # Use cross-sectional std as a proxy — limited but workable for single-day
            # Better: compute weighted std of individual returns
            returns_arr = (valid["daily_change_pct"] / 100).values
            weights_arr = weights.values
            weighted_mean = float(np.average(returns_arr, weights=weights_arr))
            variance = float(np.average((returns_arr - weighted_mean) ** 2, weights=weights_arr))
            daily_std = float(np.sqrt(variance))
            if daily_std == 0:
                return None
            annualized_return = weighted_mean * 252
            annualized_std = daily_std * np.sqrt(252)
            return round(annualized_return / annualized_std, 3)

        # Fallback: use unrealized P&L as a proxy for 1-year return
        if "unrealized_pl_pct" in df.columns:
            df["unrealized_pl_pct"] = pd.to_numeric(df["unrealized_pl_pct"], errors="coerce")
            valid = df[df["unrealized_pl_pct"].notna() & (df["market_value"] > 0)].copy()
            if len(valid) < 2:
                return None
            weights = valid["market_value"] / valid["market_value"].sum()
            returns_arr = (valid["unrealized_pl_pct"] / 100).values
            weights_arr = weights.values
            weighted_mean = float(np.average(returns_arr, weights=weights_arr))
            variance = float(np.average((returns_arr - weighted_mean) ** 2, weights=weights_arr))
            std = float(np.sqrt(variance))
            if std == 0:
                return None
            return round(weighted_mean / std, 3)
        return None
    except Exception:
        return None


def calc_portfolio_beta(tickers_weights: dict) -> Optional[float]:
    """Compute portfolio beta vs SPY.

    tickers_weights: {yf_ticker: market_value_weight (raw, will be normalised)}
    Returns beta or None if insufficient data.
    """
    if not tickers_weights:
        return None
    try:
        all_tickers = list(tickers_weights.keys()) + ["SPY"]
        raw = yf.download(
            all_tickers,
            period="3mo",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        if raw.empty or "Close" not in raw.columns:
            return None

        close_df = raw["Close"]
        if "SPY" not in close_df.columns:
            return None

        spy_returns = close_df["SPY"].pct_change().dropna()
        total_weight = sum(tickers_weights.values())
        if total_weight <= 0:
            return None

        portfolio_returns = None
        for ticker, weight in tickers_weights.items():
            if ticker not in close_df.columns:
                continue
            ret = close_df[ticker].pct_change().dropna()
            normalised = weight / total_weight
            aligned = ret.reindex(spy_returns.index).fillna(0)
            if portfolio_returns is None:
                portfolio_returns = aligned * normalised
            else:
                portfolio_returns = portfolio_returns + aligned * normalised

        if portfolio_returns is None or len(portfolio_returns) < 10:
            return None

        cov_matrix = np.cov(portfolio_returns.values, spy_returns.values)
        beta = cov_matrix[0, 1] / cov_matrix[1, 1]
        return round(float(beta), 3)
    except Exception:
        return None


def fetch_indicators_batch(assets: list) -> dict:
    """
    Fetch technical indicators for all assets with tickers.
    Returns {asset_id: {"rsi": float, "rsi_ctx": str, "macd": float, "signal": float, "hist": float, "macd_ctx": str}}
    """
    ticker_map = {}  # yf_ticker -> list[asset_id]
    for a in assets:
        t = _to_yf_ticker(a)
        if t:
            ticker_map.setdefault(t, []).append(a["id"])

    if not ticker_map:
        return {}

    try:
        raw = yf.download(
            list(ticker_map.keys()),
            period="3mo",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception:
        return {}

    if raw.empty:
        return {}

    # Handle single vs multi ticker
    tickers_list = list(ticker_map.keys())
    if len(tickers_list) == 1:
        # Single ticker: Close is a Series, convert to DataFrame
        if "Close" in raw.columns:
            close_series = raw["Close"]
            if hasattr(close_series, "columns"):
                close_df = close_series
            else:
                close_df = close_series.to_frame(name=tickers_list[0])
        else:
            return {}
    else:
        if "Close" in raw.columns:
            close_df = raw["Close"]
        else:
            return {}

    results = {}
    for yf_ticker, asset_ids in ticker_map.items():
        if yf_ticker not in close_df.columns:
            continue
        prices = close_df[yf_ticker].dropna()
        rsi = calc_rsi(prices)
        macd, sig, hist = calc_macd(prices)
        indicator_data = {
            "rsi": rsi,
            "rsi_ctx": rsi_context(rsi),
            "macd": macd,
            "signal": sig,
            "hist": hist,
            "macd_ctx": macd_context(macd, sig, hist),
        }
        for asset_id in asset_ids:
            results[asset_id] = indicator_data
    return results
