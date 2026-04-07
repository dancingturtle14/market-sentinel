#!/usr/bin/env python3
"""
Market Sentinel — data update orchestrator.
Runs all scrapers and writes data/market_data.json.
Safe to run repeatedly; gracefully handles partial failures.

POLICY: Spot assets only. No leverage, futures, margin, or derivatives data.
"""
import sys, os, json
from datetime import datetime, timezone
from collections import Counter

# Ensure scrapers package is importable
sys.path.insert(0, os.path.dirname(__file__))

from scrapers.news_rss    import fetch_crypto_news, fetch_stock_news
from scrapers.reddit_data import fetch_crypto_reddit, fetch_stock_reddit
from scrapers.polymarket  import fetch_polymarket
from scrapers.fear_greed  import fetch_fear_greed, fetch_crypto_prices
from scrapers.stocks_data import fetch_stock_prices, fetch_market_indices, market_mood_score
from scrapers.sentiment   import analyze_headlines, sentiment_label, sentiment_color
from scrapers.assets      import CRYPTO_ASSETS, STOCK_ASSETS

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "market_data.json")


def aggregate_mentions(reddit_data: list[dict]) -> list[dict]:
    """Sum mentions across all subreddits, return sorted list."""
    totals = Counter()
    for sub in reddit_data:
        for sym, cnt in sub.get("mentions", {}).items():
            totals[sym] += cnt
    return [{"symbol": s, "mentions": c} for s, c in totals.most_common(10)]


def enrich_crypto_mentions(mentions: list[dict], prices: list[dict]) -> list[dict]:
    price_map = {p["symbol"]: p for p in prices}
    result = []
    for m in mentions:
        p = price_map.get(m["symbol"], {})
        result.append({
            "symbol":     m["symbol"],
            "mentions":   m["mentions"],
            "price_usd":  p.get("price_usd"),
            "change_24h": p.get("change_24h"),
        })
    return result


def enrich_stock_mentions(mentions: list[dict], prices: list[dict]) -> list[dict]:
    price_map = {p["symbol"]: p for p in prices}
    result = []
    for m in mentions:
        p = price_map.get(m["symbol"], {})
        result.append({
            "symbol":     m["symbol"],
            "mentions":   m["mentions"],
            "price_usd":  p.get("price_usd"),
            "change_24h": p.get("change_24h"),
        })
    return result


def run():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Market Sentinel update starting...")
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)

    # ── Crypto ──────────────────────────────────────────────────────────
    print("  Fetching crypto news...")
    crypto_news_raw = fetch_crypto_news()
    crypto_headlines = [a["title"] for a in crypto_news_raw[:15]]
    crypto_analyzed  = analyze_headlines(crypto_headlines)
    crypto_news_out  = []
    for i, a in enumerate(crypto_news_raw[:15]):
        s = crypto_analyzed[i] if i < len(crypto_analyzed) else {"score": 0, "label": "Neutral", "color": "yellow"}
        crypto_news_out.append({
            "title":     a["title"],
            "source":    a["source"],
            "url":       a["url"],
            "published": a["published"],
            "assets":    a.get("assets", []),
            "sentiment": s["label"],
            "score":     s["score"],
            "color":     s["color"],
        })
    crypto_avg_score = (
        round(sum(n["score"] for n in crypto_news_out) / len(crypto_news_out), 3)
        if crypto_news_out else 0
    )

    print("  Fetching Fear & Greed...")
    fear_greed = fetch_fear_greed()

    print("  Fetching crypto prices...")
    crypto_prices = fetch_crypto_prices()

    print("  Fetching crypto Reddit...")
    crypto_reddit = fetch_crypto_reddit()
    crypto_mentions_raw = aggregate_mentions(crypto_reddit)
    crypto_mentions = enrich_crypto_mentions(crypto_mentions_raw, crypto_prices)

    # ── Stocks ──────────────────────────────────────────────────────────
    print("  Fetching stock news...")
    stock_news_raw = fetch_stock_news()
    stock_headlines = [a["title"] for a in stock_news_raw[:15]]
    stock_analyzed  = analyze_headlines(stock_headlines)
    stock_news_out  = []
    for i, a in enumerate(stock_news_raw[:15]):
        s = stock_analyzed[i] if i < len(stock_analyzed) else {"score": 0, "label": "Neutral", "color": "yellow"}
        stock_news_out.append({
            "title":     a["title"],
            "source":    a["source"],
            "url":       a["url"],
            "published": a["published"],
            "assets":    a.get("assets", []),
            "sentiment": s["label"],
            "score":     s["score"],
            "color":     s["color"],
        })
    stock_avg_score = (
        round(sum(n["score"] for n in stock_news_out) / len(stock_news_out), 3)
        if stock_news_out else 0
    )

    print("  Fetching stock prices & indices...")
    stock_prices   = fetch_stock_prices()
    indices        = fetch_market_indices()
    mood_score     = market_mood_score(indices)

    print("  Fetching stock Reddit...")
    stock_reddit = fetch_stock_reddit()
    stock_mentions_raw = aggregate_mentions(stock_reddit)
    stock_mentions = enrich_stock_mentions(stock_mentions_raw, stock_prices)

    # ── Polymarket ──────────────────────────────────────────────────────
    print("  Fetching Polymarket...")
    poly = fetch_polymarket()

    # ── Assemble output ─────────────────────────────────────────────────
    output = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "crypto": {
            "fear_greed":      fear_greed,
            "prices":          crypto_prices[:12],
            "top_mentioned":   crypto_mentions[:10],
            "news":            crypto_news_out,
            "news_sentiment":  {
                "score": crypto_avg_score,
                "label": sentiment_label(crypto_avg_score),
                "color": sentiment_color(crypto_avg_score),
            },
            "polymarket":      poly["crypto"],
            "reddit":          crypto_reddit,
        },
        "stocks": {
            "indices":         indices,
            "market_mood":     {
                "score": mood_score,
                "label": sentiment_label(mood_score),
                "color": sentiment_color(mood_score),
            },
            "prices":          stock_prices,
            "top_mentioned":   stock_mentions[:10],
            "news":            stock_news_out,
            "news_sentiment":  {
                "score": stock_avg_score,
                "label": sentiment_label(stock_avg_score),
                "color": sentiment_color(stock_avg_score),
            },
            "polymarket":      poly["finance"],
            "reddit":          stock_reddit,
        },
    }

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  [OK] Saved to {DATA_PATH}")
    print(f"  Crypto F&G: {fear_greed['value']} ({fear_greed['label']})")
    print(f"  Market mood: {mood_score} ({sentiment_label(mood_score)})")
    print(f"  Crypto news sentiment: {crypto_avg_score}")
    print(f"  Stock news sentiment: {stock_avg_score}")


if __name__ == "__main__":
    run()
