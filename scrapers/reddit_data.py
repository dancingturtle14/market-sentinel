"""
Reddit data via public JSON API — no API key required.
Counts asset mentions and calculates community activity scores.
"""
import requests, re, ssl
from requests.adapters import HTTPAdapter
from collections import Counter
from .assets import CRYPTO_ASSETS, STOCK_ASSETS

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

def _session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s

CRYPTO_SUBS = ["CryptoCurrency", "Bitcoin", "ethereum", "solana", "CryptoMarkets"]
STOCK_SUBS  = ["wallstreetbets", "stocks", "investing", "StockMarket", "options"]

def _fetch_subreddit(sub: str, limit: int = 50) -> list[dict]:
    url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}"
    try:
        sess = _session()
        r = sess.get(url, timeout=15, verify=False)
        r.raise_for_status()
        posts = r.json()["data"]["children"]
        return [
            {
                "title": p["data"]["title"],
                "score": p["data"]["score"],
                "comments": p["data"]["num_comments"],
                "url": "https://reddit.com" + p["data"]["permalink"],
            }
            for p in posts
        ]
    except Exception as e:
        print(f"  [Reddit] r/{sub} failed: {e}")
        return []

def _count_mentions(posts: list[dict], asset_map: dict) -> dict:
    counts = Counter()
    all_text = " ".join(p["title"].lower() for p in posts)
    for sym, kws in asset_map.items():
        for kw in kws:
            counts[sym] += len(re.findall(r'\b' + re.escape(kw) + r'\b', all_text))
    return dict(counts.most_common(10))

def _activity_score(posts: list[dict]) -> int:
    """Composite score: upvotes + comments, normalized."""
    total = sum(p["score"] + p["comments"] * 3 for p in posts[:20])
    return min(100, total // 100)

def fetch_crypto_reddit() -> list[dict]:
    results = []
    for sub in CRYPTO_SUBS:
        posts = _fetch_subreddit(sub)
        if not posts:
            continue
        top = sorted(posts, key=lambda x: x["score"], reverse=True)
        results.append({
            "subreddit": f"r/{sub}",
            "mentions": _count_mentions(posts, CRYPTO_ASSETS),
            "activity_score": _activity_score(posts),
            "top_post": top[0]["title"] if top else "",
            "top_post_url": top[0]["url"] if top else "",
            "top_post_score": top[0]["score"] if top else 0,
        })
    return results

def fetch_stock_reddit() -> list[dict]:
    results = []
    for sub in STOCK_SUBS:
        posts = _fetch_subreddit(sub)
        if not posts:
            continue
        top = sorted(posts, key=lambda x: x["score"], reverse=True)
        results.append({
            "subreddit": f"r/{sub}",
            "mentions": _count_mentions(posts, STOCK_ASSETS),
            "activity_score": _activity_score(posts),
            "top_post": top[0]["title"] if top else "",
            "top_post_url": top[0]["url"] if top else "",
            "top_post_score": top[0]["score"] if top else 0,
        })
    return results
