"""
RSS news scraper — no API key required.
Fetches crypto and stock news from major outlets.
"""
import feedparser, re
from datetime import datetime, timezone
from .assets import CRYPTO_ASSETS, STOCK_ASSETS

CRYPTO_FEEDS = [
    ("CoinDesk",      "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt",       "https://decrypt.co/feed"),
    ("CryptoSlate",   "https://cryptoslate.com/feed/"),
]

STOCK_FEEDS = [
    ("Reuters",     "https://feeds.reuters.com/reuters/businessNews"),
    ("CNBC",        "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_topstories"),
    ("Yahoo Fin",   "https://finance.yahoo.com/news/rssindex"),
]

HEADERS = {"User-Agent": "MarketSentinelBot/1.0 (research dashboard)"}

def _parse_feed(name: str, url: str, max_items: int = 10) -> list[dict]:
    items = []
    try:
        feed = feedparser.parse(url, request_headers=HEADERS)
        for entry in feed.entries[:max_items]:
            title = entry.get("title", "").strip()
            link  = entry.get("link", "")
            pub   = entry.get("published", entry.get("updated", ""))
            if title:
                items.append({"title": title, "url": link, "source": name, "published": pub})
    except Exception as e:
        print(f"  [RSS] {name} failed: {e}")
    return items

def _detect_assets(text: str, asset_map: dict) -> list[str]:
    t = text.lower()
    return [sym for sym, kws in asset_map.items() if any(kw in t for kw in kws)]

def fetch_crypto_news() -> list[dict]:
    articles = []
    for name, url in CRYPTO_FEEDS:
        articles.extend(_parse_feed(name, url))
    for a in articles:
        a["assets"] = _detect_assets(a["title"], CRYPTO_ASSETS)
    return articles[:30]

def fetch_stock_news() -> list[dict]:
    articles = []
    for name, url in STOCK_FEEDS:
        articles.extend(_parse_feed(name, url))
    for a in articles:
        a["assets"] = _detect_assets(a["title"], STOCK_ASSETS)
    return articles[:30]
