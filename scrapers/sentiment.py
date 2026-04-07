"""
Sentiment analysis — keyword-based by default.
If GROQ_API_KEY is set, uses Groq AI for higher quality analysis.
"""
import os, json, re
from .assets import BULLISH_WORDS, BEARISH_WORDS

def keyword_sentiment(text: str) -> float:
    """Return sentiment score -1.0 (bearish) to +1.0 (bullish)."""
    t = text.lower()
    bull = sum(1 for w in BULLISH_WORDS if w in t)
    bear = sum(1 for w in BEARISH_WORDS if w in t)
    total = bull + bear
    if total == 0:
        return 0.0
    return round((bull - bear) / total, 3)

def sentiment_label(score: float) -> str:
    if score >= 0.3:  return "Bullish"
    if score <= -0.3: return "Bearish"
    return "Neutral"

def sentiment_color(score: float) -> str:
    if score >= 0.3:  return "green"
    if score <= -0.3: return "red"
    return "yellow"

def analyze_headlines_groq(headlines: list[str], api_key: str) -> list[float]:
    """Batch-analyze headlines with Groq. Returns list of scores."""
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        batch = "\n".join(f"{i+1}. {h}" for i, h in enumerate(headlines[:15]))
        prompt = (
            "Analyze the market sentiment of each headline. "
            "Reply ONLY with a JSON array of numbers, one per headline, "
            "where -1.0 = very bearish, 0 = neutral, 1.0 = very bullish.\n\n"
            f"Headlines:\n{batch}"
        )
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        match = re.search(r'\[.*?\]', raw, re.DOTALL)
        if match:
            scores = json.loads(match.group())
            return [max(-1.0, min(1.0, float(s))) for s in scores]
    except Exception as e:
        print(f"  [Groq sentiment] fallback to keyword: {e}")
    return [keyword_sentiment(h) for h in headlines]

def analyze_headlines(headlines: list[str]) -> list[dict]:
    """Analyze a list of headlines. Returns list of {text, score, label, color}."""
    api_key = os.environ.get("GROQ_API_KEY", "")
    if api_key:
        scores = analyze_headlines_groq(headlines, api_key)
    else:
        scores = [keyword_sentiment(h) for h in headlines]

    return [
        {
            "text": h,
            "score": scores[i],
            "label": sentiment_label(scores[i]),
            "color": sentiment_color(scores[i]),
        }
        for i, h in enumerate(headlines)
    ]
