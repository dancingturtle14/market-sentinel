"""
Crypto Fear & Greed Index from alternative.me — no key required.
Also fetches top coin prices from CoinGecko free API.
"""
import requests

HEADERS = {"User-Agent": "MarketSentinelBot/1.0"}

def fetch_fear_greed() -> dict:
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=2", headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()["data"]
        current = data[0]
        previous = data[1] if len(data) > 1 else data[0]
        return {
            "value":          int(current["value"]),
            "label":          current["value_classification"],
            "previous_value": int(previous["value"]),
            "previous_label": previous["value_classification"],
        }
    except Exception as e:
        print(f"  [FearGreed] failed: {e}")
        return {"value": 50, "label": "Neutral", "previous_value": 50, "previous_label": "Neutral"}

def fetch_crypto_prices(symbols: list[str] = None) -> list[dict]:
    if symbols is None:
        symbols = ["bitcoin","ethereum","solana","binancecoin","ripple",
                   "cardano","dogecoin","avalanche-2","chainlink","toncoin"]
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={
                "vs_currency": "usd",
                "ids": ",".join(symbols),
                "order": "market_cap_desc",
                "per_page": 15,
                "price_change_percentage": "24h",
            },
            headers=HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        coins = r.json()
        return [
            {
                "symbol":        c["symbol"].upper(),
                "name":          c["name"],
                "price_usd":     c["current_price"],
                "change_24h":    round(c.get("price_change_percentage_24h") or 0, 2),
                "market_cap":    c.get("market_cap", 0),
                "volume_24h":    c.get("total_volume", 0),
            }
            for c in coins
        ]
    except Exception as e:
        print(f"  [CoinGecko] failed: {e}")
        return []
