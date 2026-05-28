import feedparser
import yfinance as yf
from datetime import datetime
from typing import Optional

# Free RSS feeds
RSS_FEEDS = {
    "macro": [
        ("美聯儲 Fed", "https://www.federalreserve.gov/feeds/press_monetary.xml"),
        ("財政部 Treasury", "https://home.treasury.gov/system/files/rss/press-releases.xml"),
        ("Yahoo Finance 財經", "https://finance.yahoo.com/rss/topfinstories"),
    ],
    "market": [
        ("CNBC 市場", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
        ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines"),
        ("Guardian 商業", "https://www.theguardian.com/business/rss"),
    ],
}

# Keyword sentiment
_POSITIVE_WORDS = {"升息", "增長", "復甦", "強勁", "超預期", "創高", "買入", "升評", "盈餘", "獲利", "漲", "上漲", "強"}
_NEGATIVE_WORDS = {"降息", "衰退", "崩盤", "下跌", "不及預期", "虧損", "裁員", "破產", "賣出", "降評", "跌", "下跌", "弱"}
_EN_POSITIVE = {"rise", "surge", "gain", "beat", "strong", "growth", "rally", "upgrade", "profit"}
_EN_NEGATIVE = {"fall", "drop", "miss", "weak", "recession", "decline", "crash", "downgrade", "loss", "tariff"}


def sentiment_label(text: str) -> str:
    text_lower = text.lower()
    words = set(text_lower.split())
    pos = sum(1 for w in _POSITIVE_WORDS if w in text_lower) + sum(1 for w in _EN_POSITIVE if w in words)
    neg = sum(1 for w in _NEGATIVE_WORDS if w in text_lower) + sum(1 for w in _EN_NEGATIVE if w in words)
    if pos > neg:
        return "🟢"
    elif neg > pos:
        return "🔴"
    return "⚪"


def _parse_feed(url: str, limit: int = 8) -> list:
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:limit]:
            title = getattr(entry, "title", "")
            link  = getattr(entry, "link", "#")
            pub   = getattr(entry, "published", "")
            items.append({
                "title":     title,
                "link":      link,
                "published": pub,
                "sentiment": sentiment_label(title),
            })
        return items
    except Exception:
        return []


def fetch_macro_news(limit: int = 8) -> list:
    items = []
    for name, url in RSS_FEEDS["macro"]:
        for item in _parse_feed(url, limit=5):
            item["source"] = name
            items.append(item)
    return items[:limit]


def fetch_market_news(limit: int = 10) -> list:
    items = []
    for name, url in RSS_FEEDS["market"]:
        for item in _parse_feed(url, limit=5):
            item["source"] = name
            items.append(item)
    return items[:limit]


def fetch_stock_news(tickers: list, limit_per_ticker: int = 3) -> list:
    """Use yfinance to get news for given tickers."""
    all_news = []
    for ticker in tickers[:6]:  # limit to 6 tickers to avoid slow load
        try:
            t = yf.Ticker(ticker)
            for item in (t.news or [])[:limit_per_ticker]:
                # yfinance >=0.2.x wraps news inside {'id':..., 'content':{...}}
                content = item.get("content", item)
                title = content.get("title") or item.get("title", "")
                link  = (
                    content.get("canonicalUrl", {}).get("url")
                    or item.get("link", "#")
                    or "#"
                )
                source = (
                    content.get("provider", {}).get("displayName")
                    or item.get("publisher", "")
                )
                pub_date_raw = content.get("pubDate") or ""
                if not pub_date_raw and item.get("providerPublishTime"):
                    try:
                        pub_date_raw = datetime.fromtimestamp(
                            item["providerPublishTime"]
                        ).strftime("%Y-%m-%d %H:%M")
                    except Exception:
                        pub_date_raw = ""
                all_news.append({
                    "title":     title,
                    "link":      link,
                    "published": pub_date_raw,
                    "source":    source,
                    "ticker":    ticker,
                    "sentiment": sentiment_label(title),
                })
        except Exception:
            continue
    return all_news
