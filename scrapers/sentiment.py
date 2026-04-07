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

def analyze_headlines_groq(headlines: list[str], api_key: str) -> list[float]:  # kept for compat
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

def _ai_generate(prompt: str) -> str | None:
    """Try Gemini first, then Groq. Returns text or None."""
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    groq_key   = os.environ.get("GROQ_API_KEY", "")

    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            return resp.text.strip()
        except Exception as e:
            print(f"  [Gemini] {e}")

    if groq_key:
        try:
            from groq import Groq
            resp = Groq(api_key=groq_key).chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"  [Groq] {e}")

    return None


def generate_summary(topic: str, data_text: str) -> dict:
    """Generate a one-paragraph Bullish/Bearish/Mixed summary. Gemini → Groq → keywords."""
    if not data_text.strip():
        return {"outlook": "Mixed", "summary": "Insufficient data to generate a summary."}

    prompt = (
        f"You are a concise financial analyst. Based on the following {topic} data, "
        "write exactly ONE paragraph summarizing the overall market sentiment. "
        "Start with 'Bullish:', 'Bearish:', or 'Mixed:' followed by specific reasons. "
        "Mention numbers and names where available. Max 80 words.\n\n"
        f"Data:\n{data_text}"
    )
    text = _ai_generate(prompt)

    if text:
        outlook = "Mixed"
        if text.lower().startswith("bullish"):  outlook = "Bullish"
        elif text.lower().startswith("bearish"): outlook = "Bearish"
        return {"outlook": outlook, "summary": text}

    # Keyword fallback
    bull = sum(1 for w in BULLISH_WORDS if w in data_text.lower())
    bear = sum(1 for w in BEARISH_WORDS if w in data_text.lower())
    if bull > bear * 1.5:   outlook, prefix = "Bullish", "Bullish"
    elif bear > bull * 1.5: outlook, prefix = "Bearish", "Bearish"
    else:                   outlook, prefix = "Mixed",   "Mixed"
    return {
        "outlook": outlook,
        "summary": f"{prefix}: {bull} bullish vs {bear} bearish signals detected across {topic} data.",
    }


def analyze_headlines(headlines: list[str]) -> list[dict]:
    """Analyze headlines. Tries Gemini → Groq → keywords."""
    batch = "\n".join(f"{i+1}. {h}" for i, h in enumerate(headlines[:15]))
    prompt = (
        "Analyze the market sentiment of each headline. "
        "Reply ONLY with a JSON array of numbers, one per headline, "
        "where -1.0 = very bearish, 0 = neutral, 1.0 = very bullish.\n\n"
        f"Headlines:\n{batch}"
    )
    scores = None
    text = _ai_generate(prompt)
    if text:
        try:
            m = re.search(r'\[.*?\]', text, re.DOTALL)
            if m:
                scores = [max(-1.0, min(1.0, float(s))) for s in json.loads(m.group())]
        except Exception:
            pass
    if scores is None:
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
