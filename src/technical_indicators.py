import yfinance as yf
import pandas as pd
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
