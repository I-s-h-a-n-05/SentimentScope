import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "sentimentscope.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_articles INTEGER,
            positive_count INTEGER,
            negative_count INTEGER,
            neutral_count INTEGER,
            avg_score REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            search_id INTEGER,
            title TEXT,
            source TEXT,
            published_at TEXT,
            url TEXT,
            sentiment_label TEXT,
            vader_score REAL,
            roberta_score REAL,
            final_score REAL,
            FOREIGN KEY (search_id) REFERENCES searches(id)
        )
    """)
    conn.commit()
    conn.close()

def save_search(keyword, results):
    conn = get_connection()
    cursor = conn.cursor()
    labels = [r["sentiment_label"] for r in results]
    pos = labels.count("positive")
    neg = labels.count("negative")
    neu = labels.count("neutral")
    scores = [r["final_score"] for r in results]
    avg = round(sum(scores) / len(scores), 4) if scores else 0
    cursor.execute("""
        INSERT INTO searches (keyword, total_articles, positive_count, negative_count, neutral_count, avg_score)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (keyword, len(results), pos, neg, neu, avg))
    search_id = cursor.lastrowid
    for r in results:
        cursor.execute("""
            INSERT INTO articles (search_id, title, source, published_at, url, sentiment_label, vader_score, roberta_score, final_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (search_id, r.get("title"), r.get("source"), r.get("published_at"),
              r.get("url"), r.get("sentiment_label"), r.get("vader_score"),
              r.get("roberta_score"), r.get("final_score")))
    conn.commit()
    conn.close()
    return search_id

def get_recent_searches(limit=20):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT keyword, searched_at, total_articles, positive_count, negative_count, neutral_count, avg_score
        FROM searches ORDER BY searched_at DESC LIMIT ?
    """, (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def clear_history():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM articles")
    cursor.execute("DELETE FROM searches")
    conn.commit()
    conn.close()