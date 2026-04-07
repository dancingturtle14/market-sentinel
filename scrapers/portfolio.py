"""
Portfolio tracker for specific ETFs.
Fetches prices, technicals, dividend info, and generates outlook signals.
Spot ETFs only — no leverage, no derivatives.
"""
import yfinance as yf
import pandas as pd

HOLDINGS = {
    "BKHY":  {"name": "BlackRock High Yield Bond",       "type": "Bond Income"},
    "XYLD":  {"name": "Global X S&P 500 Covered Call",   "type": "Covered Call Income"},
    "JEPQ":  {"name": "JPMorgan Nasdaq Equity Premium",   "type": "Equity Income"},
    "SCHD":  {"name": "Schwab US Dividend Equity",        "type": "Dividend Growth"},
    "QQQM":  {"name": "Invesco Nasdaq 100",               "type": "Growth"},
}

def _calc_rsi(closes: pd.Series, period: int = 14) -> float:
    delta = closes.diff().dropna()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, 1e-9)
    rsi   = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 1) if not rsi.empty else 50.0

def _signal(closes: pd.Series, rsi: float) -> dict:
    """Composite outlook from multiple technical signals. Returns score + reasons."""
    sma20 = closes.rolling(20).mean()
    sma50 = closes.rolling(50).mean()
    price = float(closes.iloc[-1])

    # Each signal tracked individually: +1 bullish, -1 bearish, 0 neutral
    signals = []
    reasons = []

    # 1. Price vs SMA20
    if price > float(sma20.iloc[-1]):
        signals.append(1)
        reasons.append("Price above 20-day moving average ↑")
    else:
        signals.append(-1)
        reasons.append("Price below 20-day moving average ↓")

    # 2. SMA20 vs SMA50 (golden/death cross)
    if float(sma20.iloc[-1]) > float(sma50.iloc[-1]):
        signals.append(1)
        reasons.append("Short-term trend above long-term (bullish cross) ↑")
    else:
        signals.append(-1)
        reasons.append("Short-term trend below long-term (bearish cross) ↓")

    # 3. RSI — extra weight at extremes
    if rsi < 30:
        signals.extend([1, 1])   # oversold = strong bullish signal
        reasons.append(f"RSI {rsi} — Oversold zone, historically signals a bounce ↑")
    elif rsi > 70:
        signals.extend([-1, -1]) # overbought = strong bearish signal
        reasons.append(f"RSI {rsi} — Overbought zone, historically signals a pullback ↓")
    elif rsi < 45:
        signals.append(-1)
        reasons.append(f"RSI {rsi} — Below neutral, mild downward pressure ↓")
    elif rsi > 55:
        signals.append(1)
        reasons.append(f"RSI {rsi} — Above neutral, mild upward momentum ↑")
    else:
        signals.append(0)
        reasons.append(f"RSI {rsi} — In neutral range (45–55)")

    # 4. 5-day momentum
    if len(closes) >= 6:
        mom5 = (price - float(closes.iloc[-6])) / float(closes.iloc[-6]) * 100
        if mom5 > 1.5:
            signals.append(1)
            reasons.append(f"5-day momentum +{mom5:.1f}% — short-term buying pressure ↑")
        elif mom5 < -1.5:
            signals.append(-1)
            reasons.append(f"5-day momentum {mom5:.1f}% — short-term selling pressure ↓")
        else:
            signals.append(0)
            reasons.append(f"5-day momentum {mom5:+.1f}% — consolidating sideways →")

    # 5. 1-month trend
    if len(closes) >= 22:
        mom1m = (price - float(closes.iloc[-22])) / float(closes.iloc[-22]) * 100
        if mom1m > 3:
            signals.append(1)
            reasons.append(f"1-month return +{mom1m:.1f}% — sustained uptrend ↑")
        elif mom1m < -3:
            signals.append(-1)
            reasons.append(f"1-month return {mom1m:.1f}% — sustained downtrend ↓")
        else:
            signals.append(0)
            reasons.append(f"1-month return {mom1m:+.1f}% — range-bound")

    # Composite score and confidence from signal agreement
    score      = sum(signals)
    bull_count = signals.count(1)
    bear_count = signals.count(-1)
    dominant   = max(bull_count, bear_count)
    total      = len(signals)

    # Confidence = how many signals agree on the dominant direction
    if dominant >= total - 1:          # all or all-but-one agree
        confidence = "High"
    elif dominant >= round(total * 0.6):  # 60%+ agree
        confidence = "Medium"
    else:
        confidence = "Low"

    # Label
    if score >= 3:
        label, color = "Bullish",      "green"
    elif score <= -3:
        label, color = "Bearish",      "red"
    elif score >= 1:
        label, color = "Mild Bullish", "green"
    elif score <= -1:
        label, color = "Mild Bearish", "red"
    else:
        label, color = "Neutral",      "yellow"

    return {
        "label":      label,
        "color":      color,
        "score":      score,
        "bull_count": bull_count,
        "bear_count": bear_count,
        "total":      total,
        "confidence": confidence,
        "reasons":    reasons,
    }


def fetch_portfolio() -> list[dict]:
    symbols = list(HOLDINGS.keys())
    results = []

    try:
        # Bulk download 3 months history
        hist = yf.download(symbols, period="3mo", auto_adjust=True, progress=False)
        closes_all = hist["Close"]
        volumes_all = hist.get("Volume", pd.DataFrame())
    except Exception as e:
        print(f"  [Portfolio] yfinance download failed: {e}")
        return []

    for sym, meta in HOLDINGS.items():
        try:
            closes = closes_all[sym].dropna()
            if len(closes) < 10:
                continue

            price     = float(closes.iloc[-1])
            prev      = float(closes.iloc[-2])
            chg_1d    = round((price - prev) / prev * 100, 2)
            chg_1w    = round((price - float(closes.iloc[-6])) / float(closes.iloc[-6]) * 100, 2) if len(closes) >= 6 else None
            chg_1m    = round((price - float(closes.iloc[-22])) / float(closes.iloc[-22]) * 100, 2) if len(closes) >= 22 else None
            high_3m   = round(float(closes.max()), 2)
            low_3m    = round(float(closes.min()), 2)
            rsi       = _calc_rsi(closes)
            outlook   = _signal(closes, rsi)

            # Dividend & extra info via Ticker.info
            div_yield = None
            last_div  = None
            week52_high = None
            week52_low  = None
            try:
                info        = yf.Ticker(sym).info
                div_yield   = info.get("trailingAnnualDividendYield") or info.get("dividendYield")
                if div_yield:
                    # yfinance may return decimal (0.073) or percent (7.3) depending on version
                    div_yield = round(div_yield * 100 if div_yield < 1 else div_yield, 2)
                last_div    = info.get("lastDividendValue")
                week52_high = info.get("fiftyTwoWeekHigh")
                week52_low  = info.get("fiftyTwoWeekLow")
            except Exception:
                pass

            results.append({
                "symbol":       sym,
                "name":         meta["name"],
                "type":         meta["type"],
                "price_usd":    round(price, 2),
                "change_1d":    chg_1d,
                "change_1w":    chg_1w,
                "change_1m":    chg_1m,
                "high_3m":      high_3m,
                "low_3m":       low_3m,
                "week52_high":  week52_high,
                "week52_low":   week52_low,
                "rsi":          rsi,
                "div_yield":    div_yield,
                "last_div":     round(last_div, 4) if last_div else None,
                "outlook":      outlook,
            })

        except Exception as e:
            print(f"  [Portfolio] {sym} failed: {e}")

    return results
