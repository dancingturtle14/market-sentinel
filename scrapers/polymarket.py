"""
Polymarket public API — no key required.
Fetches top markets by 24h volume, split into crypto and finance/other.
"""
import requests, json

API = "https://gamma-api.polymarket.com/markets"
HEADERS = {"User-Agent": "MarketSentinelBot/1.0"}

SPORTS_EXCLUDE = [
    " vs. ", " vs ", "o/u ", "spread", "moneyline", "over/under",
    "nba", "nfl", "mlb", "nhl", "nba", "fifa", "epl", "champions league",
    "super bowl", "world cup", "playoffs", "championship", "tournament",
    "match winner", "first goal", "halftime", "innings", "quarter",
]

CRYPTO_KEYWORDS = [
    "bitcoin", "btc", "ethereum", "eth", "crypto", "solana", "sol",
    "xrp", "ripple", "coinbase", "binance", "defi", "nft", "altcoin",
    "blockchain", "stablecoin", "halving", "memecoin", "doge", "bnb",
    "price of bitcoin", "price of eth", "above $", "below $"
]
STOCK_KEYWORDS = [
    "stock", "equity", "fed", "rate", "recession", "gdp", "inflation",
    "s&p", "nasdaq", "dow", "trump", "tariff", "trade", "earnings",
    "ipo", "merger", "tesla", "nvidia", "apple", "microsoft", "amazon",
    "google", "meta", "economy", "market", "interest rate", "cpi",
    "unemployment", "payroll", "xi jinping", "china", "sanction"
]

def _categorize(title: str) -> str:
    t = title.lower()
    if any(kw in t for kw in SPORTS_EXCLUDE):
        return "other"
    if any(kw in t for kw in CRYPTO_KEYWORDS):
        return "crypto"
    if any(kw in t for kw in STOCK_KEYWORDS):
        return "finance"
    return "other"

def fetch_polymarket(limit: int = 100) -> dict:
    crypto, finance, other = [], [], []
    try:
        r = requests.get(
            API,
            params={"limit": limit, "active": "true", "order": "volume24hr", "ascending": "false"},
            headers=HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        markets = r.json()

        for m in markets:
            title   = m.get("question") or m.get("title") or ""
            vol_raw = m.get("volume24hr") or m.get("volume") or 0
            volume  = float(str(vol_raw).split()[0]) if vol_raw else 0
            prices_raw = m.get("outcomePrices", '["0.5","0.5"]')
            try:
                # API returns a JSON string, e.g. '["0.65","0.35"]'
                if isinstance(prices_raw, str):
                    prices_raw = json.loads(prices_raw)
                yes_bid = float(prices_raw[0]) if prices_raw else 0.5
            except (ValueError, TypeError, json.JSONDecodeError):
                yes_bid = 0.5
            # Skip fully resolved markets (0% or 100%)
            if yes_bid <= 0.02 or yes_bid >= 0.98:
                continue
            item = {
                "title":     title,
                "volume_24h": round(volume),
                "yes_price":  round(yes_bid, 2),
                "category":   _categorize(title),
            }
            if item["category"] == "crypto":
                crypto.append(item)
            elif item["category"] == "finance":
                finance.append(item)
            else:
                other.append(item)
    except Exception as e:
        print(f"  [Polymarket] failed: {e}")

    return {
        "crypto":  sorted(crypto,  key=lambda x: x["volume_24h"], reverse=True)[:8],
        "finance": sorted(finance, key=lambda x: x["volume_24h"], reverse=True)[:8],
    }
