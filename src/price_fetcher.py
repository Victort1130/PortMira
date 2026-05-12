import yfinance as yf
import requests


def fetch_stock_prices(tickers: list[str]) -> dict[str, float]:
    """Fetch latest price for each yfinance ticker. Returns {ticker: price}."""
    prices = {}
    for t in tickers:
        try:
            price = yf.Ticker(t).fast_info["last_price"]
            if price:
                prices[t] = float(price)
        except Exception as e:
            print(f"[price_fetcher] {t}: {e}")
    return prices


def fetch_crypto_prices(coin_ids: list[str], vs_currency: str = "usd") -> dict[str, float]:
    """Fetch current prices from CoinGecko. Returns {coin_id: price_in_vs_currency}."""
    if not coin_ids:
        return {}
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": ",".join(coin_ids), "vs_currencies": vs_currency}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 429:
            print("[price_fetcher] CoinGecko rate limit hit, skipping crypto prices")
            return {}
        r.raise_for_status()
        data = r.json()
        return {cid: data[cid][vs_currency] for cid in coin_ids if cid in data}
    except Exception as e:
        print(f"[price_fetcher] CoinGecko error: {e}")
        return {}


def fetch_prev_closes(tickers: list[str]) -> dict[str, float]:
    """Fetch previous close price for each yfinance ticker. Returns {ticker: prev_close}."""
    prev_closes = {}
    for t in tickers:
        try:
            prev_closes[t] = float(yf.Ticker(t).fast_info["previous_close"])
        except Exception as e:
            print(f"[price_fetcher] prev_close {t}: {e}")
    return prev_closes


def fetch_crypto_prev_closes(coin_ids: list[str]) -> dict[str, float]:
    """Estimate previous close for crypto using CoinGecko 24h change. Returns {coin_id: prev_close}."""
    if not coin_ids:
        return {}
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": ",".join(coin_ids), "vs_currencies": "usd", "include_24hr_change": "true"}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 429:
            return {}
        r.raise_for_status()
        data = r.json()
        prev_closes = {}
        for cid in coin_ids:
            if cid not in data:
                continue
            price = data[cid].get("usd", 0)
            change_pct = data[cid].get("usd_24h_change") or 0
            divisor = 1 + change_pct / 100
            if price and divisor:
                prev_closes[cid] = price / divisor
        return prev_closes
    except Exception as e:
        print(f"[price_fetcher] crypto prev_close error: {e}")
        return {}


def fetch_all_fx_rates(currencies: list[str], base_currency: str) -> dict[str, float]:
    """Fetch all FX rates in one request using exchangerate-api.com.

    Returns {currency: rate_to_base}, e.g. {"USD": 32.5, "TWD": 1.0} when base is TWD.
    """
    result: dict[str, float] = {base_currency: 1.0}
    foreign = [c for c in set(currencies) if c != base_currency]
    if not foreign:
        return result
    try:
        r = requests.get(
            f"https://api.exchangerate-api.com/v4/latest/{base_currency}",
            timeout=10,
        )
        r.raise_for_status()
        # api_rates["USD"] = how many USD per 1 TWD (e.g. 0.031)
        # we want: how many TWD per 1 USD = 1 / 0.031 ≈ 32.5
        api_rates = r.json().get("rates", {})
        for ccy in foreign:
            rate = api_rates.get(ccy)
            result[ccy] = (1.0 / rate) if rate else 1.0
        return result
    except Exception as e:
        print(f"[price_fetcher] FX batch error: {e}")
        return {ccy: 1.0 for ccy in currencies}
