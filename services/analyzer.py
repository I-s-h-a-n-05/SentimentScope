from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from config import VADER_AMBIGUITY_LOW, VADER_AMBIGUITY_HIGH
from collections import Counter, defaultdict
import requests
import os
import re

vader = SentimentIntensityAnalyzer()

HF_API_URL = "https://api-inference.huggingface.co/models/cardiffnlp/twitter-roberta-base-sentiment-latest"
HF_API_KEY = os.getenv("HF_API_KEY", "")


def _roberta_sentiment(text):
    headers = {"Authorization": f"Bearer {HF_API_KEY}"} if HF_API_KEY else {}
    try:
        response = requests.post(
            HF_API_URL,
            headers=headers,
            json={"inputs": text[:512]},
            timeout=8
        )
        if response.status_code != 200:
            return None, None
        result = response.json()
        if not result or not isinstance(result, list):
            return None, None
        scores = result[0] if isinstance(result[0], list) else result
        label_map = {"negative": -1, "neutral": 0, "positive": 1}

        def normalize(raw):
            raw = raw.lower()
            if "neg" in raw: return "negative"
            if "pos" in raw: return "positive"
            return "neutral"

        best = max(scores, key=lambda x: x["score"])
        label = normalize(best["label"])
        compound = sum(label_map[normalize(s["label"])] * s["score"] for s in scores)
        return label, round(compound, 4)
    except Exception as e:
        print(f"[Analyzer] HuggingFace API error: {e}")
        return None, None


def analyze_single(text):
    vader_scores = vader.polarity_scores(text)
    vader_compound = vader_scores["compound"]
    vader_ambiguous = VADER_AMBIGUITY_LOW < vader_compound < VADER_AMBIGUITY_HIGH

    roberta_score = None
    roberta_label = None
    if vader_ambiguous:
        roberta_label, roberta_score = _roberta_sentiment(text)

    if roberta_score is not None:
        final_score = roberta_score
        final_label = roberta_label
    else:
        final_score = vader_compound
        if vader_compound >= 0.05:
            final_label = "positive"
        elif vader_compound <= -0.05:
            final_label = "negative"
        else:
            final_label = "neutral"

    return {
        "vader_score": round(vader_compound, 4),
        "roberta_score": roberta_score,
        "final_score": round(final_score, 4),
        "sentiment_label": final_label
    }


def analyze_all(articles):
    results = []
    for article in articles:
        text = article.get("text") or article.get("title") or ""
        if not text:
            continue
        sentiment = analyze_single(text)
        results.append({**article, **sentiment})
    return results


def extract_keywords(articles, top_n=40):
    stopwords = {
        "the","a","an","and","or","but","in","on","at","to","for","of","with",
        "is","was","are","were","be","been","has","have","had","it","its","that",
        "this","as","by","from","not","he","she","they","we","you","i","my","his",
        "her","their","our","will","can","could","would","may","might","do","did",
        "does","into","more","than","about","after","new","says","said","over",
        "up","out","before","between","through","during","while","just","also"
    }
    word_counts = Counter()
    for article in articles:
        title = article.get("title", "").lower()
        words = re.findall(r'\b[a-z]{4,}\b', title)
        for word in words:
            if word not in stopwords:
                word_counts[word] += 1
    return dict(word_counts.most_common(top_n))


def build_timeline(articles):
    """
    Smart grouping:
    - 3+ unique days  -> group by day
    - 1-2 unique days -> group by 2-hour blocks
    - same hour       -> group by 30-min blocks
    Always returns at least 2 points if data exists.
    """
    daily = defaultdict(list)
    for article in articles:
        pub = article.get("published_at", "")
        if pub:
            daily[pub[:10]].append(article["final_score"])

    if len(daily) >= 3:
        return [
            {"date": date, "avg_score": round(sum(s)/len(s), 4), "count": len(s)}
            for date, s in sorted(daily.items())
        ]

    # Try 2-hour blocks
    blocks2h = defaultdict(list)
    for article in articles:
        pub = article.get("published_at", "")
        if pub and len(pub) >= 13:
            try:
                hour = int(pub[11:13])
                block = (hour // 2) * 2
                label = f"{pub[:10]} {block:02d}:00"
                blocks2h[label].append(article["final_score"])
            except Exception:
                pass
    if len(blocks2h) >= 2:
        return [
            {"date": dt, "avg_score": round(sum(s)/len(s), 4), "count": len(s)}
            for dt, s in sorted(blocks2h.items())
        ]

    # Try 30-min blocks
    blocks30m = defaultdict(list)
    for article in articles:
        pub = article.get("published_at", "")
        if pub and len(pub) >= 16:
            try:
                hour = int(pub[11:13])
                minute = int(pub[14:16])
                block = (minute // 30) * 30
                label = f"{pub[:10]} {hour:02d}:{block:02d}"
                blocks30m[label].append(article["final_score"])
            except Exception:
                pass
    if len(blocks30m) >= 2:
        return [
            {"date": dt, "avg_score": round(sum(s)/len(s), 4), "count": len(s)}
            for dt, s in sorted(blocks30m.items())
        ]

    # Last resort: individual articles sorted by time
    individual = []
    for article in articles:
        pub = article.get("published_at", "")
        if pub and len(pub) >= 16:
            individual.append({"date": pub[:16], "avg_score": article["final_score"], "count": 1})
    if len(individual) >= 2:
        return sorted(individual, key=lambda x: x["date"])

    return [
        {"date": date, "avg_score": round(sum(s)/len(s), 4), "count": len(s)}
        for date, s in sorted(daily.items())
    ]