import requests
import feedparser
from newsapi import NewsApiClient
from datetime import datetime, timedelta
from config import NEWS_API_KEY
import os

newsapi = NewsApiClient(api_key=NEWS_API_KEY)
GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY", "")

NEWS_FETCH_LIMIT = 30

DATE_RANGES = {
    "1 day":   1,
    "1 week":  7,
    "2 weeks": 14,
    "1 month": 28,
}

TIER1_SOURCES = {
    "reuters", "associated-press", "bbc-news", "bloomberg",
    "the-wall-street-journal", "financial-times", "npr",
    "the-guardian-uk", "al-jazeera-english", "techcrunch",
    "the-verge", "wired", "ars-technica", "fortune",
    "business-insider", "cnbc", "cnn", "the-washington-post"
}

# ── RSS feed registry ─────────────────────────────────────────────────────────
RSS_FEEDS = {
    # Indian sources
    "Times of India":   "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "The Hindu":        "https://www.thehindu.com/feeder/default.rss",
    "NDTV":             "https://feeds.feedburner.com/ndtvnews-top-stories",
    "Hindustan Times":  "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
    "India Today":      "https://www.indiatoday.in/rss/home",
    # Global / Middle East / Asia
    "Al Jazeera":       "https://www.aljazeera.com/xml/rss/all.xml",
    "BBC World":        "http://feeds.bbci.co.uk/news/world/rss.xml",
    "South China Morning Post": "https://www.scmp.com/rss/91/feed",
    "Dawn (Pakistan)":  "https://www.dawn.com/feeds/home",
}

def _parse_rss_date(entry):
    """Extract published date string from RSS entry."""
    for field in ("published", "updated", "created"):
        val = getattr(entry, field, None)
        if val:
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(val)
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                pass
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def _is_within_days(pub_str, days):
    """Check if article is within the requested date range."""
    try:
        pub = datetime.strptime(pub_str[:19], "%Y-%m-%dT%H:%M:%S")
        return (datetime.utcnow() - pub).days <= days
    except Exception:
        return True  # include if can't parse

def _keyword_matches_title(title, keyword):
    """
    Title-only strict matching — if the keyword isn't in the headline,
    the article is not about that topic.
    - Exact phrase match (case-insensitive)
    - Multi-word: all words must appear as whole words in title
    """
    import re
    title_lower = title.lower().strip()
    keyword_lower = keyword.lower().strip()

    # Exact phrase in title
    if keyword_lower in title_lower:
        return True

    # Multi-word: every word must be a whole-word match in title
    words = keyword_lower.split()
    if len(words) > 1:
        return all(
            bool(re.search(r'\b' + re.escape(w) + r'\b', title_lower))
            for w in words
        )

    # Single word: whole-word match only
    return bool(re.search(r'\b' + re.escape(keyword_lower) + r'\b', title_lower))

def fetch_rss(keyword, days=7):
    """
    Fetch articles matching keyword from all RSS feeds.
    Returns list of article dicts.
    """
    results = []
    seen_titles = set()

    for source_name, url in RSS_FEEDS.items():
        try:
            resp = requests.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            }, timeout=8)
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:40]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "").strip()
                link = entry.get("link", "")

                if not title or title in seen_titles:
                    continue

                # Title-only matching — keyword must be in the headline
                if not _keyword_matches_title(title, keyword):
                    continue

                pub_str = _parse_rss_date(entry)
                if not _is_within_days(pub_str, days):
                    continue

                seen_titles.add(title)
                results.append({
                    "title": title,
                    "source": source_name,
                    "published_at": pub_str,
                    "url": link,
                    "text": f"{title}. {summary[:300]}".strip(),
                    "source_type": "rss"
                })
        except Exception as e:
            print(f"[RSS Error] {source_name}: {e}")

    return results

def fetch_guardian(keyword, days=7):
    """
    Fetch from The Guardian API — excellent global + UK coverage.
    Returns list of article dicts.
    """
    if not GUARDIAN_API_KEY:
        return []
    try:
        from_date = (datetime.now() - timedelta(days=min(days, 28))).strftime("%Y-%m-%d")
        # Use quoted phrase for multi-word keywords for stricter matching
        query = f'"{keyword}"' if ' ' in keyword else keyword

        resp = requests.get(
            "https://content.guardianapis.com/search",
            params={
                "q": query,
                "from-date": from_date,
                "order-by": "newest",
                "page-size": 30,
                "show-fields": "trailText,headline,bodyText",
                "api-key": GUARDIAN_API_KEY,
            },
            timeout=8
        )
        if resp.status_code != 200:
            print(f"[Guardian Error] {resp.status_code}: {resp.text[:200]}")
            return []

        articles = []
        for item in resp.json().get("response", {}).get("results", []):
            fields = item.get("fields", {})
            title = fields.get("headline") or item.get("webTitle", "")
            trail = fields.get("trailText", "")
            pub = item.get("webPublicationDate", "")
            url = item.get("webUrl", "")
            if not title:
                continue
            # Title-only relevance check
            if not _keyword_matches_title(title, keyword):
                continue
            articles.append({
                "title": title,
                "source": "The Guardian",
                "published_at": pub,
                "url": url,
                "text": f"{title}. {trail}".strip(),
                "source_type": "guardian"
            })
        return articles
    except Exception as e:
        print(f"[Guardian Error] {e}")
        return []

def fetch_newsapi(keyword, tier1_only=False, days=7):
    """Fetch from NewsAPI (primarily Western/English news)."""
    try:
        days = min(days, 28)
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        sources = ",".join(TIER1_SOURCES) if tier1_only else None
        kwargs = dict(
            q=keyword, from_param=from_date, language="en",
            sort_by="publishedAt", page_size=NEWS_FETCH_LIMIT
        )
        if sources:
            kwargs["sources"] = sources
        response = newsapi.get_everything(**kwargs)
        return _parse_newsapi(response, keyword=keyword)
    except Exception as e:
        print(f"[NewsAPI Error] {e}")
        return []

def _parse_newsapi(response, keyword=None):
    articles = []
    for article in response.get("articles", []):
        title = article.get("title") or ""
        description = article.get("description") or ""
        if "[Removed]" in title or not title:
            continue
        # Post-filter: keyword must appear in title
        if keyword and not _keyword_matches_title(title, keyword):
            continue
        articles.append({
            "title": title,
            "source": article.get("source", {}).get("name", "Unknown"),
            "published_at": article.get("publishedAt", ""),
            "url": article.get("url", ""),
            "text": f"{title}. {description}".strip(),
            "source_type": "newsapi"
        })
    return articles

def fetch_news(keyword, tier1_only=False, days=7):
    """
    Multi-source fetch: NewsAPI + Guardian API + RSS feeds.
    Deduplicates by title similarity.
    Returns merged, deduplicated list sorted by date.
    """
    newsapi_results  = fetch_newsapi(keyword, tier1_only=tier1_only, days=days)
    guardian_results = fetch_guardian(keyword, days=days)
    rss_results      = fetch_rss(keyword, days=days)

    # Merge all sources
    all_articles = newsapi_results + guardian_results + rss_results

    # Deduplicate by normalized title
    seen = set()
    deduped = []
    for a in all_articles:
        key = a["title"].lower()[:60].strip()
        if key not in seen:
            seen.add(key)
            deduped.append(a)

    # Sort by date descending
    def sort_key(a):
        pub = a.get("published_at", "")
        return pub[:19] if pub else ""

    deduped.sort(key=sort_key, reverse=True)

    print(f"[Fetcher] {keyword}: {len(newsapi_results)} NewsAPI + "
          f"{len(guardian_results)} Guardian + {len(rss_results)} RSS = "
          f"{len(deduped)} total (after dedup)")

    return deduped

def fetch_trending():
    """Fetch today's top headlines from NewsAPI."""
    try:
        response = newsapi.get_top_headlines(language="en", page_size=10)
        articles = []
        for a in response.get("articles", []):
            title = a.get("title") or ""
            if "[Removed]" in title or not title:
                continue
            articles.append({
                "title": title,
                "source": a.get("source", {}).get("name", ""),
                "url": a.get("url", "")
            })
        return articles
    except Exception as e:
        print(f"[Trending Error] {e}")
        return []

INDIA_RSS_FEEDS = {
    "Times of India":  "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "The Hindu":       "https://www.thehindu.com/feeder/default.rss",
    "NDTV":            "https://feeds.feedburner.com/ndtvnews-top-stories",
    "Hindustan Times": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
    "India Today":     "https://www.indiatoday.in/rss/home",
    "News18":          "https://www.news18.com/rss/india.xml",
}

def fetch_trending_india(limit=12):
    """
    Fetch top headlines from Indian RSS sources.
    Returns deduplicated list sorted by recency.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, */*"
    }
    articles = []
    seen = set()

    for source_name, url in INDIA_RSS_FEEDS.items():
        try:
            resp = requests.get(url, headers=headers, timeout=6)
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:8]:
                title = (entry.get("title") or "").strip()
                link  = entry.get("link", "")
                if not title or title in seen:
                    continue
                seen.add(title)
                pub = _parse_rss_date(entry)
                articles.append({
                    "title":  title,
                    "source": source_name,
                    "url":    link,
                    "published_at": pub
                })
        except Exception as e:
            print(f"[India RSS] {source_name}: {e}")

    # Sort by date descending, return top N
    articles.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    return articles[:limit]