# SentimentScope — Real-Time NLP Sentiment Intelligence

> Analyze public sentiment on any topic across thousands of live news sources. Built with a hybrid VADER + RoBERTa NLP pipeline, multi-source data aggregation, and a sentiment-reactive UI.

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32-red?style=flat-square)
![NLP](https://img.shields.io/badge/NLP-VADER%20%2B%20RoBERTa-purple?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## What it does

Enter any keyword and SentimentScope fetches live news articles from multiple sources, runs them through a two-stage NLP pipeline, and renders an interactive dashboard showing sentiment breakdown, trends over time, top keywords, and the most sentiment-charged articles.

The UI theme itself reacts to the results — green for positive coverage, red for negative, amber for mixed.

---

## Features

| Feature | Description |
|---|---|
| **Hybrid NLP pipeline** | VADER scores first (fast, local). Ambiguous results escalate to RoBERTa transformer via HuggingFace Inference API |
| **Multi-source aggregation** | Pulls from NewsAPI + The Guardian API + 6 RSS feeds (Times of India, NDTV, The Hindu, Al Jazeera, BBC, Dawn) |
| **Sentiment-reactive UI** | Entire color theme adapts dynamically based on sentiment result |
| **Compare mode** | Side-by-side sentiment comparison of two topics with overlaid timelines |
| **Trending tab** | Live global headlines + Trending in India section from Indian RSS feeds |
| **Dual timeline chart** | Article volume + sentiment score stacked — shows if coverage spikes are positive or negative |
| **CSV export** | Download full analysis as structured CSV |
| **Search history** | SQLite-backed search history with re-run support |
| **Tier-1 filter** | Filter to high-credibility sources only (Reuters, BBC, Bloomberg, Guardian, etc.) |

---

## Tech stack

```
Frontend       Streamlit + custom CSS (Inter + JetBrains Mono)
NLP Layer 1    VADER Sentiment (vaderSentiment)
NLP Layer 2    cardiffnlp/twitter-roberta-base-sentiment via HuggingFace Inference API
Data Sources   NewsAPI · The Guardian API · RSS feeds (feedparser)
Visualization  Plotly (bar, pie, scatter, subplot)
Storage        SQLite via Python sqlite3
Language       Python 3.11
```

---

## Architecture

```
User input (keyword)
        │
        ▼
┌─────────────────────────────────┐
│         Multi-source Fetcher     │
│  NewsAPI + Guardian + RSS feeds  │
│  → deduplicate → sort by date    │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│       Hybrid NLP Pipeline        │
│  1. VADER (fast, local)          │
│  2. If ambiguous → RoBERTa API   │
│  → final_score + sentiment_label │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│         SQLite Storage           │
│  searches + articles tables      │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│      Streamlit Dashboard         │
│  Verdict · Stats · Charts        │
│  Keywords · Articles · Export    │
└─────────────────────────────────┘
```

---

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/YOURUSERNAME/SentimentScope.git
cd SentimentScope
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Get API keys (both free)
- **NewsAPI**: Register at [newsapi.org](https://newsapi.org) — free tier, 100 requests/day
- **Guardian API**: Register at [open-platform.theguardian.com](https://open-platform.theguardian.com/access/guardian-api) — free, unlimited

### 4. Configure secrets
Create `.streamlit/secrets.toml`:
```toml
NEWS_API_KEY = "your_newsapi_key"
GUARDIAN_API_KEY = "your_guardian_key"
HF_API_KEY = ""
```

Or create a `.env` file:
```
NEWS_API_KEY=your_newsapi_key
GUARDIAN_API_KEY=your_guardian_key
```

### 5. Run
```bash
streamlit run app.py
```

---

## Project structure

```
SentimentScope/
├── app.py                  # Streamlit UI — all tabs, charts, theme system
├── config.py               # Environment variable loading
├── requirements.txt
├── services/
│   ├── fetcher.py          # Multi-source news fetching (NewsAPI + Guardian + RSS)
│   └── analyzer.py         # VADER + RoBERTa hybrid pipeline
└── database/
    └── db.py               # SQLite setup, save/retrieve search history
```

---

## Screenshots

<img width="1919" height="877" alt="image" src="https://github.com/user-attachments/assets/d176a4a0-38c4-46cd-b824-30a90f7de130" />
<img width="1919" height="847" alt="image" src="https://github.com/user-attachments/assets/73a71d53-a5e6-45b0-8d3d-3a615113ab6e" />
<img width="1919" height="857" alt="image" src="https://github.com/user-attachments/assets/b2c0c641-46d5-418b-8236-04d87710bb52" />
<img width="1919" height="852" alt="image" src="https://github.com/user-attachments/assets/a56a765f-e296-44de-b019-9819ded058ac" />
<img width="1919" height="849" alt="image" src="https://github.com/user-attachments/assets/9254fd40-39cb-411f-be44-ecbc45747ad7" />
<img width="1919" height="870" alt="image" src="https://github.com/user-attachments/assets/da27308a-0eaf-4c6b-8bef-676ae96af316" />
<img width="1919" height="825" alt="image" src="https://github.com/user-attachments/assets/c1e3b588-2430-4ae5-a6b6-5e7eca18bc79" />
<img width="1919" height="867" alt="image" src="https://github.com/user-attachments/assets/84eeb97a-901a-41ed-9ad7-d7168506b71b" />


---

## Live demo

> [sentimentscope.streamlit.app](https://sentimentscope.streamlit.app) 

---

## Notes on data coverage

SentimentScope aggregates from international English-language news sources. Coverage is strongest for:
- Global tech companies (Tesla, Apple, OpenAI, Nvidia)
- Major public figures (Elon Musk, Trump, Modi)
- Indian topics via RSS (NDTV, Times of India, The Hindu)
- Global events (climate change, Bitcoin, AI regulation)

NewsAPI free tier returns up to 30 articles per search from the past 7 days.

---

## License

MIT
