"""
Reddit data — public JSON API with RSS fallback.
RSS is more cloud-IP-friendly (GitHub Actions); JSON gives richer data (scores/comments).
No API key required for either approach.
"""
import requests, re, xml.etree.ElementTree as ET
from collections import Counter
from .assets import CRYPTO_ASSETS, STOCK_ASSETS

# Reddit requires a descriptive User-Agent; datacenter IPs may still be rate-limited
HEADERS = {
    "User-Agent": "MarketSentinel/1.0 (sentiment dashboard; read-only; github.com/dancingturtle14/market-sentinel)"
}

CRYPTO_SUBS = ["CryptoCurrency", "Bitcoin", "ethereum", "solana", "CryptoMarkets"]
STOCK_SUBS  = ["wallstreetbets", "stocks", "investing", "StockMarket", "options"]

# Reddit Atom RSS namespace
_ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}


def _session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def _fetch_subreddit_json(sub: str, limit: int = 50) -> list[dict]:
    """Primary: Reddit JSON API — rich data but blocked on some cloud IPs."""
    url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}"
    try:
        r = _session().get(url, timeout=15, verify=False)
        r.raise_for_status()
        posts = r.json()["data"]["children"]
        return [
            {
                "title":    p["data"]["title"],
                "score":    p["data"]["score"],
                "comments": p["data"]["num_comments"],
                "url":      "https://reddit.com" + p["data"]["permalink"],
            }
            for p in posts
        ]
    except Exception as e:
        print(f"  [Reddit JSON] r/{sub} failed: {e}")
        return []


def _fetch_subreddit_rss(sub: str, limit: int = 25) -> list[dict]:
    """Fallback: Reddit Atom RSS — works on cloud IPs, no upvote/comment counts."""
    url = f"https://www.reddit.com/r/{sub}/hot.rss?limit={limit}"
    try:
        r = _session().get(url, timeout=15, verify=False)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        posts = []
        for entry in root.findall("a:entry", _ATOM_NS):
            title_el = entry.find("a:title", _ATOM_NS)
            link_el  = entry.find("a:link",  _ATOM_NS)
            title = title_el.text if title_el is not None else ""
            url   = (link_el.get("href", "") if link_el is not None else "")
            # Skip stickied mod posts
            if title and not title.startswith("[Mod]"):
                posts.append({"title": title, "score": 0, "comments": 0, "url": url})
        return posts
    except Exception as e:
        print(f"  [Reddit RSS]  r/{sub} failed: {e}")
        return []


def _fetch_subreddit(sub: str, limit: int = 50) -> list[dict]:
    """Try JSON first; fall back to RSS if JSON returns nothing."""
    posts = _fetch_subreddit_json(sub, limit)
    if not posts:
        print(f"  [Reddit] r/{sub}: JSON empty, trying RSS fallback…")
        posts = _fetch_subreddit_rss(sub, min(limit, 25))
    return posts


def _count_mentions(posts: list[dict], asset_map: dict) -> dict:
    counts = Counter()
    all_text = " ".join(p["title"].lower() for p in posts)
    for sym, kws in asset_map.items():
        for kw in kws:
            counts[sym] += len(re.findall(r"\b" + re.escape(kw) + r"\b", all_text))
    return dict(counts.most_common(10))


def _activity_score(posts: list[dict]) -> int:
    """Composite score from upvotes + comments (0 when from RSS fallback)."""
    total = sum(p["score"] + p["comments"] * 3 for p in posts[:20])
    if total == 0 and posts:
        # RSS fallback: estimate activity from post count (more posts = more active)
        return min(100, len(posts) * 4)
    return min(100, total // 100)


def fetch_crypto_reddit() -> list[dict]:
    results = []
    for sub in CRYPTO_SUBS:
        posts = _fetch_subreddit(sub)
        if not posts:
            continue
        top = sorted(posts, key=lambda x: x["score"], reverse=True)
        # If all scores are 0 (RSS fallback), just take first post
        top_post = top[0] if top else {}
        results.append({
            "subreddit":       f"r/{sub}",
            "mentions":        _count_mentions(posts, CRYPTO_ASSETS),
            "activity_score":  _activity_score(posts),
            "top_post":        top_post.get("title", ""),
            "top_post_url":    top_post.get("url", ""),
            "top_post_score":  top_post.get("score", 0),
        })
    return results


def fetch_stock_reddit() -> list[dict]:
    results = []
    for sub in STOCK_SUBS:
        posts = _fetch_subreddit(sub)
        if not posts:
            continue
        top = sorted(posts, key=lambda x: x["score"], reverse=True)
        top_post = top[0] if top else {}
        results.append({
            "subreddit":       f"r/{sub}",
            "mentions":        _count_mentions(posts, STOCK_ASSETS),
            "activity_score":  _activity_score(posts),
            "top_post":        top_post.get("title", ""),
            "top_post_url":    top_post.get("url", ""),
            "top_post_score":  top_post.get("score", 0),
        })
    return results
