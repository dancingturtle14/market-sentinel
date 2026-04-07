# Asset keyword lookup tables for mention detection
# SPOT ASSETS ONLY — no leveraged/futures/margin products

CRYPTO_ASSETS = {
    "BTC":  ["bitcoin", "btc", "$btc"],
    "ETH":  ["ethereum", "eth", "$eth", "ether"],
    "SOL":  ["solana", "sol", "$sol"],
    "BNB":  ["binance coin", "bnb", "$bnb"],
    "XRP":  ["xrp", "ripple", "$xrp"],
    "ADA":  ["cardano", "ada", "$ada"],
    "DOGE": ["dogecoin", "doge", "$doge"],
    "AVAX": ["avalanche", "avax", "$avax"],
    "LINK": ["chainlink", "link", "$link"],
    "TON":  ["toncoin", "ton", "$ton"],
    "DOT":  ["polkadot", "dot", "$dot"],
    "MATIC":["polygon", "matic", "$matic"],
    "UNI":  ["uniswap", "uni", "$uni"],
    "LTC":  ["litecoin", "ltc", "$ltc"],
    "ATOM": ["cosmos", "atom", "$atom"],
}

STOCK_ASSETS = {
    "NVDA": ["nvda", "nvidia", "$nvda"],
    "TSLA": ["tsla", "tesla", "$tsla"],
    "AAPL": ["aapl", "apple", "$aapl"],
    "MSFT": ["msft", "microsoft", "$msft"],
    "GOOGL":["googl", "google", "alphabet", "$googl"],
    "AMZN": ["amzn", "amazon", "$amzn"],
    "META": ["meta", "facebook", "$meta"],
    "AMD":  ["amd", "$amd"],
    "PLTR": ["pltr", "palantir", "$pltr"],
    "GME":  ["gme", "gamestop", "$gme"],
    "AMC":  ["amc", "$amc"],
    "MSTR": ["mstr", "microstrategy", "$mstr"],
    "COIN": ["coinbase", "$coin"],
    "SPY":  ["spy", "s&p 500", "s&p500", "sp500"],
    "QQQ":  ["qqq", "nasdaq", "$qqq"],
}

BULLISH_WORDS = [
    "surge", "rally", "soar", "jump", "gain", "rise", "bull", "moon",
    "pump", "breakout", "ath", "record high", "upside", "buy", "long",
    "accumulate", "bottom", "rebound", "recovery", "outperform", "beat",
    "strong", "positive", "growth", "boost", "spike"
]

BEARISH_WORDS = [
    "crash", "drop", "fall", "dump", "bear", "down", "sell", "decline",
    "collapse", "fear", "panic", "loss", "short", "correction", "plunge",
    "tumble", "sink", "weak", "negative", "risk", "warning", "miss",
    "underperform", "recession", "inflation", "selloff"
]
