"""
Reddit data — OAuth API (primary) → public JSON → RSS fallback.

GitHub Actions IPs are blocked by Reddit's public JSON/RSS endpoints.
The fix: application-only OAuth (free, no user login needed).

Setup: add REDDIT_CLIENT_ID + REDDIT_CLIENT_SECRET to GitHub Secrets.
Register a free "script" app at https://www.reddit.com/prefs/apps
"""
import os, re, requests, xml.etree.ElementTree as ET
from collections import Counter
from .assets import CRYPTO_ASSETS, STOCK_ASSETS

REDDIT_CLIENT_ID     = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")

HEADERS = {
    "User-Agent": "MarketSentinel/1.0 (read-only sentiment dashboard; github.com/dancingturtle14/market-sentinel)"
}
_ATOM_NS     = {"a": "http://www.w3.org/2005/Atom"}
_oauth_token = None   # cached per process run

CRYPTO_SUBS = ["CryptoCurrency", "Bitcoin", "ethereum", "solana", "CryptoMarkets"]
STOCK_SUBS  = ["wallstreetbets", "stocks", "investing", "StockMarket", "options"]


# ── OAuth ────────────────────────────────────────────────────────────────────

def _get_oauth_token() -> str | None:
    """Fetch an application-only OAuth token from Reddit (free, no user login)."""
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        return None
    try:
        r = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": HEADERS["User-Agent"]},
            timeout=12,
            verify=False,
        )
        r.raise_for_status()
        token = r.json().get("access_token")
        if token:
            print("  [Reddit OAuth] token obtained")
        return token
    except Exception as e:
        print(f"  [Reddit OAuth] token failed: {e}")
        return None


def _fetch_subreddit_oauth(sub: str, limit: int = 50) -> list[dict]:
    global _oauth_token
    if _oauth_token is None:
        _oauth_token = _get_oauth_token()
    if not _oauth_token:
        return []
    url = f"https://oauth.reddit.com/r/{sub}/hot?limit={limit}"
    try:
        r = requests.get(
            url,
            headers={**HEADERS, "Authorization": f"Bearer {_oauth_token}"},
            timeout=15, verify=False,
        )
        if r.status_code == 401:
            _oauth_token = None   # token expired, will retry next subreddit
            return []
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
        print(f"  [Reddit OAuth] r/{sub} failed: {e}")
        return []


# ── Public fallbacks ─────────────────────────────────────────────────────────

def _fetch_subreddit_json(sub: str, limit: int = 50) -> list[dict]:
    url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
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
    url = f"https://www.reddit.com/r/{sub}/hot.rss?limit={limit}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        posts = []
        for entry in root.findall("a:entry", _ATOM_NS):
            title_el = entry.find("a:title", _ATOM_NS)
            link_el  = entry.find("a:link",  _ATOM_NS)
            title = title_el.text if title_el is not None else ""
            href  = link_el.get("href", "") if link_el is not None else ""
            if title and not title.startswith("[Mod]"):
                posts.append({"title": title, "score": 0, "comments": 0, "url": href})
        return posts
    except Exception as e:
        print(f"  [Reddit RSS]  r/{sub} failed: {e}")
        return []


def _fetch_subreddit(sub: str, limit: int = 50) -> list[dict]:
    """Priority: OAuth (most reliable from cloud) → JSON → RSS."""
    if REDDIT_CLIENT_ID:
        posts = _fetch_subreddit_oauth(sub, limit)
        if posts:
            return posts
        print(f"  [Reddit] OAuth failed for r/{sub}, trying public JSON…")
    posts = _fetch_subreddit_json(sub, limit)
    if posts:
        return posts
    print(f"  [Reddit] JSON empty for r/{sub}, trying RSS…")
    return _fetch_subreddit_rss(sub, min(limit, 25))


# ── Helpers ──────────────────────────────────────────────────────────────────

def _count_mentions(posts: list[dict], asset_map: dict) -> dict:
    counts = Counter()
    all_text = " ".join(p["title"].lower() for p in posts)
    for sym, kws in asset_map.items():
        for kw in kws:
            counts[sym] += len(re.findall(r"\b" + re.escape(kw) + r"\b", all_text))
    return dict(counts.most_common(10))


def _activity_score(posts: list[dict]) -> int:
    total = sum(p["score"] + p["comments"] * 3 for p in posts[:20])
    if total == 0 and posts:
        return min(100, len(posts) * 4)   # RSS fallback: estimate from post count
    return min(100, total // 100)


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_crypto_reddit() -> list[dict]:
    results = []
    for sub in CRYPTO_SUBS:
        posts = _fetch_subreddit(sub)
        if not posts:
            continue
        top = max(posts, key=lambda x: x["score"], default={})
        results.append({
            "subreddit":      f"r/{sub}",
            "mentions":       _count_mentions(posts, CRYPTO_ASSETS),
            "activity_score": _activity_score(posts),
            "top_post":       top.get("title", ""),
            "top_post_url":   top.get("url", ""),
            "top_post_score": top.get("score", 0),
        })
    return results


def fetch_stock_reddit() -> list[dict]:
    results = []
    for sub in STOCK_SUBS:
        posts = _fetch_subreddit(sub)
        if not posts:
            continue
        top = max(posts, key=lambda x: x["score"], default={})
        results.append({
            "subreddit":      f"r/{sub}",
            "mentions":       _count_mentions(posts, STOCK_ASSETS),
            "activity_score": _activity_score(posts),
            "top_post":       top.get("title", ""),
            "top_post_url":   top.get("url", ""),
            "top_post_score": top.get("score", 0),
        })
    return results
