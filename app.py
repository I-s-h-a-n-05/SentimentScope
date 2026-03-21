import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from database.db import init_db, save_search, get_recent_searches, clear_history
from services.fetcher import fetch_news, fetch_trending, fetch_trending_india
from services.analyzer import analyze_all, extract_keywords, build_timeline

st.set_page_config(page_title="SentimentScope", page_icon="◈",
                   layout="wide", initial_sidebar_state="collapsed")

# ── Sentiment theme system ────────────────────────────────────────────────────
def get_theme(avg_score=None):
    """Returns CSS variable overrides based on current sentiment."""
    if avg_score is None:
        return {
            "glow": "rgba(79,122,255,0.15)", "glow2": "rgba(155,109,255,0.08)",
            "acc": "#4f7aff", "ac2": "#9b6dff",
            "card_border": "rgba(79,122,255,0.15)",
            "verdict_bg": "rgba(79,122,255,0.05)",
            "bg_tint": "#09090f", "label": "neutral"
        }
    if avg_score > 0.05:
        return {
            "glow": "rgba(30,217,122,0.18)", "glow2": "rgba(30,217,122,0.06)",
            "acc": "#1ed97a", "ac2": "#0fba62",
            "card_border": "rgba(30,217,122,0.2)",
            "verdict_bg": "rgba(30,217,122,0.06)",
            "bg_tint": "#080f0c", "label": "positive"
        }
    elif avg_score < -0.05:
        return {
            "glow": "rgba(240,64,96,0.18)", "glow2": "rgba(240,64,96,0.06)",
            "acc": "#f04060", "ac2": "#c42d4a",
            "card_border": "rgba(240,64,96,0.2)",
            "verdict_bg": "rgba(240,64,96,0.06)",
            "bg_tint": "#0f0809", "label": "negative"
        }
    else:
        return {
            "glow": "rgba(245,160,32,0.18)", "glow2": "rgba(245,160,32,0.06)",
            "acc": "#f5a020", "ac2": "#d4860a",
            "card_border": "rgba(245,160,32,0.2)",
            "verdict_bg": "rgba(245,160,32,0.06)",
            "bg_tint": "#0f0e08", "label": "neutral_warm"
        }

def inject_theme(avg_score=None):
    t = get_theme(avg_score)
    st.markdown(f"""
    <style>
    :root {{
        --acc:  {t['acc']};
        --ac2:  {t['ac2']};
        --glow: {t['glow']};
        --glow2: {t['glow2']};
        --card-border: {t['card_border']};
        --verdict-bg:  {t['verdict_bg']};
        --bg-tint: {t['bg_tint']};
    }}
    body, .stApp {{ background: var(--bg-tint) !important; transition: background 0.6s ease; }}
    .ss-card {{ border-color: var(--card-border) !important; transition: border-color 0.6s ease; }}
    div[data-testid="stButton"] button[kind="primary"] {{
        background: linear-gradient(135deg, var(--acc), var(--ac2)) !important;
    }}
    div[data-testid="stTabs"] button[aria-selected="true"] {{ color: var(--acc) !important; }}
    </style>
    """, unsafe_allow_html=True)

# ── Base CSS (static, loaded once) ───────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 0 !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { display: none; }

:root {
    --bg0: #09090f;
    --bg1: #0d1018;
    --bg2: #13161f;
    --bg3: #191c28;
    --bg4: #1f2233;
    --b:   rgba(255,255,255,0.07);
    --bh:  rgba(255,255,255,0.13);
    --t0:  #eef0f8;
    --t1:  #8f95b2;
    --t2:  #4a5070;
    --pos: #1ed97a;
    --neg: #f04060;
    --neu: #f5a020;
    --acc: #4f7aff;
    --ac2: #9b6dff;
    --glow: rgba(79,122,255,0.15);
}

/* ── Animations ── */
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes pulse-dot {
    0%,100% { opacity: 1; box-shadow: 0 0 0 0 var(--pos); }
    50%      { opacity: 0.5; box-shadow: 0 0 0 4px transparent; }
}
@keyframes score-in {
    from { opacity: 0; transform: scale(0.85); }
    to   { opacity: 0.07; transform: scale(1); }
}
@keyframes shimmer {
    0%   { background-position: -200% center; }
    100% { background-position: 200% center; }
}

/* ── Navbar ── */
.ss-nav {
    background: rgba(13,16,24,0.96);
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border-bottom: 1px solid var(--b);
    padding: 0 44px;
    height: 62px;
    display: flex;
    align-items: center;
    gap: 20px;
    position: sticky;
    top: 0;
    z-index: 999;
}
.ss-logo {
    font-size: 20px; font-weight: 700; color: var(--t0);
    letter-spacing: -0.5px; white-space: nowrap;
    display: flex; align-items: center; gap: 9px;
}
.ss-logo-mark {
    width: 28px; height: 28px; border-radius: 8px;
    background: linear-gradient(135deg, var(--acc), var(--ac2));
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; font-weight: 800;
    transition: background 0.6s ease;
}
.ss-divider { width: 1px; height: 22px; background: var(--b); }
.ss-tagline { font-size: 13px; color: var(--t2); }
.ss-live {
    margin-left: auto;
    display: flex; align-items: center; gap: 7px;
    font-size: 13px; font-weight: 600; color: var(--pos);
    font-family: 'JetBrains Mono', monospace;
}
.ss-live-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--pos);
    animation: pulse-dot 2s infinite;
}

/* ── Cards ── */
.ss-card {
    background: var(--bg2);
    border: 1px solid var(--b);
    border-radius: 14px;
    padding: 22px;
    margin-bottom: 16px;
    animation: fadeUp 0.4s ease both;
    transition: border-color 0.6s ease;
}
.ss-card:hover { border-color: var(--bh); }
.ss-ct {
    font-size: 12px; font-weight: 700; color: var(--t1);
    text-transform: uppercase; letter-spacing: 1px;
    margin-bottom: 16px; display: flex; align-items: center; gap: 10px;
}
.ss-ct::before {
    content: '';
    width: 3px; height: 14px; border-radius: 2px;
    background: var(--acc);
    display: inline-block;
    transition: background 0.6s ease;
}

/* ── Verdict ── */
.ss-verdict {
    border-radius: 16px; padding: 28px 32px;
    margin-bottom: 20px;
    border: 1px solid var(--card-border, rgba(79,122,255,0.2));
    background: var(--verdict-bg, rgba(79,122,255,0.04));
    position: relative; overflow: hidden;
    animation: fadeUp 0.4s ease both;
    transition: background 0.6s ease, border-color 0.6s ease;
}
.ss-verdict::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, var(--acc), transparent);
    transition: background 0.6s ease;
}
.ss-v-kw {
    font-size: 10px; color: var(--t2); font-weight: 700;
    text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;
    font-family: 'JetBrains Mono', monospace;
}
.ss-v-label {
    font-size: 30px; font-weight: 700; letter-spacing: -0.8px; margin-bottom: 6px;
    background: linear-gradient(135deg, var(--acc), var(--ac2));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    transition: background 0.6s ease;
}
.ss-v-score {
    font-size: 15px; font-weight: 600; color: var(--t1);
    font-family: 'JetBrains Mono', monospace;
}
.ss-v-score strong {
    color: var(--acc); transition: color 0.6s ease;
}
.ss-v-ghost {
    position: absolute; right: 28px; top: 50%; transform: translateY(-50%);
    font-size: 72px; font-weight: 900; letter-spacing: -4px;
    color: white; pointer-events: none;
    animation: score-in 0.5s ease both;
    font-family: 'JetBrains Mono', monospace;
    background: linear-gradient(135deg, var(--acc), var(--ac2));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    opacity: 0.08;
}

/* ── Stats ── */
.ss-stats {
    display: grid; grid-template-columns: repeat(4,1fr);
    gap: 12px; margin-bottom: 20px;
}
.ss-stat {
    background: var(--bg2); border: 1px solid var(--b);
    border-radius: 12px; padding: 18px 20px;
    animation: fadeUp 0.4s ease both;
    transition: transform 0.15s, border-color 0.2s;
}
.ss-stat:hover { transform: translateY(-2px); border-color: var(--bh); }
.ss-sn {
    font-size: 32px; font-weight: 700; line-height: 1; margin-bottom: 5px;
    font-family: 'JetBrains Mono', monospace;
}
.ss-sl { font-size: 10px; color: var(--t2); font-weight: 700;
          text-transform: uppercase; letter-spacing: 0.8px; }
.sp .ss-sn { color: var(--pos); }
.sn .ss-sn { color: var(--neg); }
.su .ss-sn { color: var(--neu); }
.st .ss-sn { color: var(--acc); transition: color 0.6s ease; }

/* ── Articles ── */
.ss-art {
    padding: 14px 0; border-bottom: 1px solid var(--b);
    display: flex; align-items: flex-start; gap: 14px;
    transition: background 0.15s;
}
.ss-art:last-child { border-bottom: none; padding-bottom: 0; }
.ss-art-body { flex: 1; min-width: 0; }
.ss-art-title {
    font-size: 13px; font-weight: 500; color: var(--t0);
    text-decoration: none; line-height: 1.55; display: block; margin-bottom: 4px;
}
.ss-art-title:hover { color: var(--acc); }
.ss-art-meta {
    font-size: 11px; color: var(--t2);
    font-family: 'JetBrains Mono', monospace;
}
.ss-art-right { text-align: right; flex-shrink: 0; }
.ss-badge {
    display: inline-block; padding: 2px 8px; border-radius: 5px;
    font-size: 9px; font-weight: 800; letter-spacing: 0.8px; text-transform: uppercase;
}
.bp { background: rgba(30,217,122,0.12); color: var(--pos); }
.bn { background: rgba(240,64,96,0.12);  color: var(--neg); }
.bu { background: rgba(245,160,32,0.12); color: var(--neu); }
.ss-sc {
    font-size: 11px; color: var(--t2); margin-top: 3px;
    font-family: 'JetBrains Mono', monospace;
}

/* ── About ── */
.about-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 14px; margin: 20px 0; }
.about-card {
    background: var(--bg3); border: 1px solid var(--b);
    border-radius: 12px; padding: 20px;
    transition: border-color 0.2s, transform 0.15s;
}
.about-card:hover { border-color: var(--bh); transform: translateY(-2px); }
.about-icon { font-size: 18px; margin-bottom: 10px; }
.about-title { font-size: 13px; font-weight: 600; color: var(--t0); margin-bottom: 6px; }
.about-body { font-size: 12px; color: var(--t1); line-height: 1.65; }
.tier1-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 8px; margin-top: 14px; }
.tier1-chip {
    background: var(--bg3); border: 1px solid var(--b); border-radius: 6px;
    padding: 6px 10px; font-size: 11px; font-weight: 500;
    color: var(--t1); text-align: center;
}
.stack-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.stack-pill {
    background: var(--bg4); border: 1px solid var(--b); border-radius: 20px;
    padding: 4px 12px; font-size: 11px; font-weight: 600; color: var(--t1);
    font-family: 'JetBrains Mono', monospace;
}

/* ── History ── */
.hist-item {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 18px; background: var(--bg2); border: 1px solid var(--b);
    border-radius: 11px; margin-bottom: 8px;
    transition: border-color 0.15s, transform 0.15s;
}
.hist-item:hover { border-color: var(--bh); transform: translateX(2px); }
.hist-kw { font-size: 14px; font-weight: 600; color: var(--t0); margin-bottom: 3px; }
.hist-meta { font-size: 11px; color: var(--t2); font-family: 'JetBrains Mono', monospace; }
.ss-pill { display:inline-block; padding: 3px 10px; border-radius: 20px;
            font-size: 11px; font-weight: 600; }
.pp { background: rgba(30,217,122,0.1);  color: var(--pos); }
.pn { background: rgba(240,64,96,0.1);   color: var(--neg); }
.pu { background: rgba(245,160,32,0.1);  color: var(--neu); }

/* ── Trending ── */
.trend-item {
    display: flex; align-items: flex-start; gap: 14px;
    padding: 14px 0; border-bottom: 1px solid var(--b);
}
.trend-item:last-child { border-bottom: none; }
.trend-num {
    font-size: 20px; font-weight: 800; color: var(--b);
    min-width: 30px; line-height: 1.4;
    font-family: 'JetBrains Mono', monospace;
}
.trend-body { flex: 1; }
.trend-title {
    font-size: 13px; font-weight: 500; color: var(--t0);
    text-decoration: none; line-height: 1.5; display: block; margin-bottom: 3px;
}
.trend-title:hover { color: var(--acc); }
.trend-src { font-size: 11px; color: var(--t2); }

/* ── Theme indicator ── */
.theme-bar {
    height: 2px;
    background: linear-gradient(90deg, var(--acc), var(--ac2), transparent);
    margin-bottom: 0;
    transition: background 0.6s ease;
}

/* ── Loading overlay ── */
.ss-loading {
    padding: 48px 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 28px;
}
.ss-loading-bars {
    display: flex;
    align-items: flex-end;
    gap: 5px;
    height: 48px;
}
.ss-loading-bars span {
    display: inline-block;
    width: 5px;
    border-radius: 3px;
    background: var(--acc);
    animation: bar-dance 1.1s ease-in-out infinite;
    transition: background 0.6s ease;
}
.ss-loading-bars span:nth-child(1) { height: 20px; animation-delay: 0s; }
.ss-loading-bars span:nth-child(2) { height: 36px; animation-delay: 0.1s; }
.ss-loading-bars span:nth-child(3) { height: 48px; animation-delay: 0.2s; }
.ss-loading-bars span:nth-child(4) { height: 28px; animation-delay: 0.3s; }
.ss-loading-bars span:nth-child(5) { height: 40px; animation-delay: 0.4s; }
.ss-loading-bars span:nth-child(6) { height: 20px; animation-delay: 0.5s; }
.ss-loading-bars span:nth-child(7) { height: 32px; animation-delay: 0.6s; }
@keyframes bar-dance {
    0%, 100% { transform: scaleY(0.4); opacity: 0.4; }
    50%       { transform: scaleY(1);   opacity: 1; }
}
.ss-loading-steps {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-width: 260px;
}
.ss-loading-step {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 13px;
    font-family: 'JetBrains Mono', monospace;
    color: var(--t2);
    transition: color 0.3s;
}
.ss-loading-step.active { color: var(--t0); }
.ss-loading-step.done   { color: var(--pos); }
.ss-step-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--t2); flex-shrink: 0;
    transition: background 0.3s;
}
.ss-loading-step.active .ss-step-dot {
    background: var(--acc);
    animation: pulse-dot 0.8s infinite;
}
.ss-loading-step.done .ss-step-dot { background: var(--pos); }
.ss-loading-kw {
    font-size: 22px;
    font-weight: 700;
    color: var(--t0);
    letter-spacing: -0.5px;
    font-family: 'JetBrains Mono', monospace;
}
.ss-loading-kw span {
    background: linear-gradient(135deg, var(--acc), var(--ac2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    transition: background 0.6s;
}

/* ── Footer ── */
.ss-footer {
    border-top: 1px solid var(--b); padding: 18px 44px;
    display: flex; justify-content: space-between; align-items: center;
    background: var(--bg1); margin-top: 48px;
}
.ss-fl { font-size: 12px; color: var(--t2); font-family: 'JetBrains Mono', monospace; }
.ss-fr { display: flex; gap: 6px; flex-wrap: wrap; }
.ss-fc {
    font-size: 10px; font-weight: 700; padding: 3px 9px;
    border-radius: 5px; background: var(--bg3);
    border: 1px solid var(--b); color: var(--t2);
    text-transform: uppercase; letter-spacing: 0.5px;
    font-family: 'JetBrains Mono', monospace;
}

/* ── Streamlit overrides ── */
div[data-testid="stTextInput"] input {
    background: var(--bg2) !important; border: 1px solid var(--b) !important;
    border-radius: 10px !important; color: var(--t0) !important;
    font-size: 14px !important; padding: 11px 15px !important;
    font-family: 'Inter', sans-serif !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: var(--acc) !important;
    box-shadow: 0 0 0 3px var(--glow, rgba(79,122,255,0.12)) !important;
}
div[data-testid="stButton"] button {
    border-radius: 10px !important; font-weight: 600 !important;
    font-size: 13px !important; font-family: 'Inter', sans-serif !important;
    transition: all 0.2s !important;
}
div[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, var(--acc), var(--ac2)) !important;
    border: none !important;
}
div[data-testid="stButton"] button[kind="primary"]:hover {
    opacity: 0.88 !important; transform: translateY(-1px) !important;
}
div[data-testid="stSelectbox"] > div,
div[data-testid="stSelectbox"] > div > div {
    background: var(--bg2) !important;
    border: 1px solid var(--b) !important;
    border-radius: 10px !important;
    color: var(--t0) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    transition: border-color 0.2s !important;
    cursor: pointer !important;
}
div[data-testid="stSelectbox"] > div:hover {
    border-color: var(--acc) !important;
}
div[data-testid="stSelectbox"] svg {
    color: var(--t2) !important;
}
div[data-baseweb="popover"] ul {
    background: var(--bg2) !important;
    border: 1px solid var(--bh) !important;
    border-radius: 10px !important;
    padding: 6px !important;
    font-family: 'JetBrains Mono', monospace !important;
}
div[data-baseweb="popover"] li {
    border-radius: 7px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    color: var(--t1) !important;
    padding: 8px 12px !important;
    transition: background 0.15s !important;
}
div[data-baseweb="popover"] li:hover,
div[data-baseweb="popover"] li[aria-selected="true"] {
    background: var(--bg3) !important;
    color: var(--acc) !important;
}
div[data-testid="stDownloadButton"] button {
    background: var(--bg3) !important; border: 1px solid var(--b) !important;
    color: var(--t1) !important; border-radius: 10px !important;
    font-size: 12px !important;
}
div[data-testid="stCheckbox"] label { color: var(--t1) !important; font-size: 13px !important; }
div[data-testid="stButton"] button[kind="secondary"] {
    background: var(--bg3) !important;
    border: 1px solid var(--b) !important;
    color: var(--t2) !important;
    font-size: 12px !important;
}
div[data-testid="stButton"] button[kind="secondary"]:hover {
    border-color: var(--acc) !important;
    color: var(--t1) !important;
}
div[data-testid="stTabs"] button {
    font-family: 'Inter', sans-serif !important; font-weight: 600 !important;
    font-size: 15px !important;
    padding: 10px 20px !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--acc) !important;
}
div[data-testid="stAlert"] { border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)

init_db()

# ── Inject default theme ──────────────────────────────────────────────────────
avg_score_state = st.session_state.get("last_avg", None)
inject_theme(avg_score_state)

# ── Plotly base ───────────────────────────────────────────────────────────────
def pl_base(acc="#4f7aff"):
    return dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#4a5070", family="JetBrains Mono, monospace", size=10),
        margin=dict(t=12, b=12, l=8, r=8),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", zeroline=False,
                   showline=False, tickfont_size=9),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", zeroline=False,
                   showline=False, tickfont_size=9),
    )

POS, NEG, NEU = "#1ed97a", "#f04060", "#f5a020"

def verdict_cls(avg): return "vp" if avg > 0.05 else "vn" if avg < -0.05 else "vu"
def pill_cls(avg):    return "pp" if avg > 0.05 else "pn" if avg < -0.05 else "pu"
def badge_cls(l):     return {"positive":"bp","negative":"bn","neutral":"bu"}.get(l,"bu")
def verdict_str(avg): return "Mostly Positive" if avg > 0.05 else "Mostly Negative" if avg < -0.05 else "Mixed / Neutral"
def acc_color(avg):   return POS if avg > 0.05 else NEG if avg < -0.05 else NEU

def render_dual_timeline(results):
    """Dual-panel chart: top = article volume, bottom = sentiment score."""
    tl = build_timeline(results)
    if len(tl) < 2:
        return None
    df = pd.DataFrame(tl)
    sent_colors = [POS if s > 0.05 else NEG if s < -0.05 else NEU for s in df["avg_score"]]
    acc = acc_color(st.session_state.get("last_avg", 0))

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.38, 0.62],
        subplot_titles=["Article volume", "Sentiment score"]
    )
    # Volume bars
    fig.add_trace(go.Bar(
        x=df["date"], y=df["count"],
        marker_color=acc, marker_opacity=0.5,
        name="Articles",
        hovertemplate="<b>%{x}</b><br>%{y} articles<extra></extra>"
    ), row=1, col=1)
    # Sentiment bars
    fig.add_trace(go.Bar(
        x=df["date"], y=df["avg_score"],
        marker_color=sent_colors, marker_opacity=0.82,
        name="Sentiment",
        hovertemplate="<b>%{x}</b><br>Score: %{y:.3f}<extra></extra>"
    ), row=2, col=1)
    # Zero line on sentiment
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.08)",
                  line_width=1, row=2, col=1)

    layout = pl_base(acc)
    layout.update(dict(
        height=340, showlegend=False,
        xaxis2=dict(gridcolor="rgba(255,255,255,0.04)", zeroline=False,
                    showline=False, tickfont_size=9),
        yaxis2=dict(gridcolor="rgba(255,255,255,0.04)", zeroline=False,
                    showline=False, tickfont_size=9),
    ))
    # Style subplot titles
    for ann in fig.layout.annotations:
        ann.font.size = 10
        ann.font.color = "#4a5070"
        ann.font.family = "JetBrains Mono, monospace"

    fig.update_layout(**layout)
    return fig

def render_pie(pos, neu, neg, height=210):
    fig = go.Figure(go.Pie(
        labels=["Positive", "Neutral", "Negative"], values=[pos, neu, neg],
        hole=0.6, marker_colors=[POS, NEU, NEG],
        textinfo="percent", textfont_size=10,
        hovertemplate="<b>%{label}</b><br>%{value} articles<extra></extra>"
    ))
    fig.update_layout(**pl_base(), height=height, showlegend=True,
        legend=dict(orientation="v", x=0.78, y=0.5, font_size=10,
                    font_family="JetBrains Mono, monospace"))
    return fig

def render_articles(results, limit=12):
    top = sorted(results, key=lambda x: abs(x["final_score"]), reverse=True)[:limit]
    html = ""
    for a in top:
        lbl = a["sentiment_label"]
        sc = a["final_score"]
        sign = "+" if sc > 0 else ""
        date = a.get("published_at", "")[:10]
        html += f"""
        <div class="ss-art">
          <div class="ss-art-body">
            <a href="{a['url']}" target="_blank" class="ss-art-title">{a['title']}</a>
            <div class="ss-art-meta">{a['source']} · {date}</div>
          </div>
          <div class="ss-art-right">
            <span class="ss-badge {badge_cls(lbl)}">{lbl}</span>
            <div class="ss-sc">{sign}{sc:.4f}</div>
          </div>
        </div>"""
    return f'<div class="ss-card">{html}</div>'

def run_analysis(keyword, days, tier1):
    """Fetch + analyze + save. Returns results list or None."""
    loading_placeholder = st.empty()

    steps = [
        ("Fetching live news articles", False, False),
        ("Running VADER sentiment scoring", False, False),
        ("Escalating ambiguous text to RoBERTa", False, False),
        ("Building insights & timeline", False, False),
    ]

    def render_loading(current_step):
        rows = ""
        for i, (label, _, _) in enumerate(steps):
            if i < current_step:
                cls = "done"
                icon = "✓"
            elif i == current_step:
                cls = "active"
                icon = "→"
            else:
                cls = ""
                icon = "·"
            rows += f'''<div class="ss-loading-step {cls}">
                <div class="ss-step-dot"></div>
                <span style="min-width:16px;opacity:0.6">{icon}</span>
                {label}
            </div>'''

        loading_placeholder.markdown(f'''
        <div class="ss-loading">
          <div class="ss-loading-kw">Analyzing <span>"{keyword}"</span></div>
          <div class="ss-loading-bars">
            <span></span><span></span><span></span><span></span>
            <span></span><span></span><span></span>
          </div>
          <div class="ss-loading-steps">{rows}</div>
        </div>''', unsafe_allow_html=True)

    render_loading(0)
    articles = fetch_news(keyword, tier1_only=tier1, days=days)

    if not articles:
        loading_placeholder.empty()
        st.error("No articles found. Try a broader keyword or disable Tier-1 filter.")
        return None

    render_loading(1)
    import time; time.sleep(0.3)
    render_loading(2)
    results = analyze_all(articles)

    if not results:
        loading_placeholder.empty()
        st.error("Analysis failed.")
        return None

    render_loading(3)
    import time; time.sleep(0.2)
    save_search(keyword, results)
    loading_placeholder.empty()
    return results

# ── Navbar ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="ss-nav">
  <div class="ss-logo">
    <div class="ss-logo-mark">◈</div>
    Sentiment<span style="color:var(--acc);transition:color 0.6s">Scope</span>
  </div>
  <div class="ss-divider"></div>
  <div class="ss-tagline">NLP Intelligence Platform</div>
  <div class="ss-live">
    <div class="ss-live-dot"></div>
    LIVE
  </div>
</div>
""", unsafe_allow_html=True)

# ── Theme bar (reacts to sentiment) ──────────────────────────────────────────
st.markdown('<div class="theme-bar"></div>', unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_analyze, tab_compare, tab_trending, tab_history, tab_about = st.tabs([
    "  Analyze  ", "  Compare  ", "  Trending  ", "  History  ", "  About  "
])

# ════════════════════════════════════════════════════════════════════
# TAB 1 — ANALYZE
# ════════════════════════════════════════════════════════════════════
with tab_analyze:
    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([5, 1.2, 1])
    with c1:
        keyword = st.text_input("kw",
            placeholder='Enter any topic — "Tesla", "climate change", "GPT-5"…',
            label_visibility="collapsed", key="kw_main")
    with c2:
        tier1 = st.checkbox("Tier-1 only", value=False, key="t1_main")
    with c3:
        run = st.button("Analyze →", type="primary", use_container_width=True, key="btn_main")

    st.markdown("""
    <div style="font-size:11px;color:var(--t2);margin:6px 0 10px;font-family:JetBrains Mono,monospace">
    ⓘ NewsAPI covers English-language international news — best for global companies, public figures, major events & technologies
    </div>""", unsafe_allow_html=True)

    ex_cols = st.columns(6)
    for i, ex in enumerate(["Tesla", "OpenAI", "Bitcoin", "Apple", "SpaceX", "Climate change"]):
        if ex_cols[i].button(ex, key=f"ex_{ex}", use_container_width=True):
            st.session_state["run_kw"] = ex
            st.rerun()

    if "run_kw" in st.session_state:
        keyword = st.session_state.pop("run_kw")
        run = True

    if run and keyword.strip():
        results = run_analysis(keyword.strip(), 7, tier1)
        if results:
            labels = [r["sentiment_label"] for r in results]
            pos = labels.count("positive")
            neg = labels.count("negative")
            neu = labels.count("neutral")
            total = len(results)
            avg = round(sum(r["final_score"] for r in results) / total, 4)

            # Store for theme reactivity
            st.session_state["last_avg"] = avg
            inject_theme(avg)

            acc = acc_color(avg)
            vc = verdict_cls(avg)
            src_lbl = "Tier-1 sources" if tier1 else "All sources"

            # Verdict
            st.markdown(f"""
            <div class="ss-verdict">
              <div class="ss-v-kw">"{keyword.strip()}" · {total} articles · {src_lbl}</div>
              <div class="ss-v-label">{verdict_str(avg)}</div>
              <div class="ss-v-score">avg score &nbsp;<strong>{avg:+.4f}</strong></div>
              <div class="ss-v-ghost">{avg:+.2f}</div>
            </div>""", unsafe_allow_html=True)

            # Stats
            st.markdown(f"""
            <div class="ss-stats">
              <div class="ss-stat sp"><div class="ss-sn">{pos}</div><div class="ss-sl">Positive · {pos/total*100:.0f}%</div></div>
              <div class="ss-stat su"><div class="ss-sn">{neu}</div><div class="ss-sl">Neutral · {neu/total*100:.0f}%</div></div>
              <div class="ss-stat sn"><div class="ss-sn">{neg}</div><div class="ss-sl">Negative · {neg/total*100:.0f}%</div></div>
              <div class="ss-stat st"><div class="ss-sn">{total}</div><div class="ss-sl">Articles analyzed</div></div>
            </div>""", unsafe_allow_html=True)

            # Source breakdown
            source_counts = {}
            for r in results:
                st_type = r.get("source_type", "newsapi")
                label = {"newsapi": "NewsAPI", "guardian": "The Guardian", "rss": "RSS feeds"}.get(st_type, st_type)
                source_counts[label] = source_counts.get(label, 0) + 1
            if len(source_counts) > 1:
                src_str = " &nbsp;·&nbsp; ".join(
                    f'<span style="color:var(--t1)">{v}</span> <span style="color:var(--t2)">{k}</span>'
                    for k, v in sorted(source_counts.items(), key=lambda x: -x[1])
                )
                st.markdown(f'<div style="font-size:11px;color:var(--t2);margin-bottom:16px;font-family:JetBrains Mono,monospace">Sources: {src_str}</div>', unsafe_allow_html=True)

            # Charts
            ch1, ch2 = st.columns([1, 2])
            with ch1:
                st.markdown('<div class="ss-card"><div class="ss-ct">Sentiment breakdown</div>', unsafe_allow_html=True)
                st.plotly_chart(render_pie(pos, neu, neg), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            with ch2:
                st.markdown('<div class="ss-card"><div class="ss-ct">Volume + sentiment over time</div>', unsafe_allow_html=True)
                fig_dual = render_dual_timeline(results)
                if fig_dual:
                    st.plotly_chart(fig_dual, use_container_width=True)
                else:
                    st.caption("All articles published on the same day — timeline not available.")
                st.markdown('</div>', unsafe_allow_html=True)

            # Keywords
            kws = extract_keywords(results, top_n=30)
            if kws:
                kw_df = pd.DataFrame(list(kws.items()), columns=["word","count"]).sort_values("count").tail(20)
                fig_kw = go.Figure(go.Bar(
                    x=kw_df["count"], y=kw_df["word"], orientation="h",
                    marker_color=acc, marker_opacity=0.7,
                    hovertemplate="<b>%{y}</b> · %{x} mentions<extra></extra>"
                ))
                fig_kw.update_layout(**pl_base(acc), height=320, bargap=0.32)
                st.markdown('<div class="ss-card"><div class="ss-ct">Top keywords</div>', unsafe_allow_html=True)
                st.plotly_chart(fig_kw, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # Articles + export
            df_exp = pd.DataFrame([{
                "title": a["title"], "source": a["source"],
                "published_at": a.get("published_at","")[:10], "url": a["url"],
                "sentiment": a["sentiment_label"],
                "vader_score": a["vader_score"], "final_score": a["final_score"]
            } for a in results])

            hc1, hc2 = st.columns([4, 1])
            with hc1:
                st.markdown('<div class="ss-ct" style="margin-bottom:12px">Top articles by sentiment strength</div>', unsafe_allow_html=True)
            with hc2:
                st.download_button("↓ Export CSV",
                    data=df_exp.to_csv(index=False).encode(),
                    file_name=f"sentimentscope_{keyword.strip().replace(' ','_')}.csv",
                    mime="text/csv", use_container_width=True)
            st.markdown(render_articles(results), unsafe_allow_html=True)

    elif run:
        st.warning("Please enter a keyword.")
    else:
        theme_hint = ""
        if avg_score_state is not None:
            theme_hint = f'<div style="font-size:11px;color:var(--t2);margin-top:6px;font-family:JetBrains Mono,monospace">Theme reactive · last score: {avg_score_state:+.4f}</div>'
        st.markdown(f"""
        <div style="text-align:center;padding:64px 0;color:var(--t2)">
          <div style="font-size:32px;opacity:0.1;margin-bottom:14px;font-weight:800">◈</div>
          <div style="font-size:15px;font-weight:600;color:var(--t1);margin-bottom:6px">Enter a keyword to begin</div>
          <div style="font-size:12px">The UI theme will adapt to the sentiment of your results</div>
          {theme_hint}
        </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════
# TAB 2 — COMPARE
# ════════════════════════════════════════════════════════════════════
with tab_compare:
    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
    st.markdown('<p style="color:var(--t1);font-size:13px;margin-bottom:16px">Compare two topics — sentiment, volume, trends, and top articles side by side.</p>', unsafe_allow_html=True)

    cc1, cc2, cc3 = st.columns([3, 3, 1])
    with cc1: kw1 = st.text_input("Topic A", placeholder="e.g. Tesla", key="cmp1")
    with cc2: kw2 = st.text_input("Topic B", placeholder="e.g. BYD",   key="cmp2")
    with cc3:
        st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
        cmp_run = st.button("Compare →", type="primary", use_container_width=True, key="btn_cmp")

    st.markdown("""
    <div style="font-size:11px;color:var(--t2);margin-bottom:16px;font-family:JetBrains Mono,monospace;
    padding:10px 14px;background:var(--bg3);border-radius:8px;border:1px solid var(--b)">
    ⓘ &nbsp;NewsAPI covers English-language international news.
    Works best with: companies (Tesla, Apple), public figures (Elon Musk), global events, technologies (AI, Bitcoin).
    Regional or niche topics may return few or no results.
    </div>""", unsafe_allow_html=True)

    if cmp_run and kw1.strip() and kw2.strip():
        with st.spinner(f"Analyzing '{kw1}' and '{kw2}'…"):
            a1 = fetch_news(kw1.strip(), days=days)
            a2 = fetch_news(kw2.strip(), days=days)
            r1 = analyze_all(a1) if a1 else []
            r2 = analyze_all(a2) if a2 else []

        if not r1 and not r2:
            st.error("No articles found for either keyword. NewsAPI covers primarily English-language international news — try broader or globally recognized topics like company names, world leaders, or major events.")
            st.stop()
        if not r1:
            st.warning(f"No articles found for '{kw1}'. Showing results for '{kw2}' only.")
        if not r2:
            st.warning(f"No articles found for '{kw2}'. Showing results for '{kw1}' only.")

        def get_stats(r):
            if not r: return 0,0,0,0,0.0
            lb = [x["sentiment_label"] for x in r]
            sc = [x["final_score"] for x in r]
            return lb.count("positive"),lb.count("neutral"),lb.count("negative"),len(r),round(sum(sc)/len(sc),4)

        p1,n1,g1,t1_,avg1 = get_stats(r1)
        p2,n2,g2,t2_,avg2 = get_stats(r2)

        # Verdicts
        vc1, vc2 = st.columns(2)
        for col, kw, avg, pos, neu, neg, total in [
            (vc1, kw1, avg1, p1, n1, g1, t1_),
            (vc2, kw2, avg2, p2, n2, g2, t2_)
        ]:
            with col:
                st.markdown(f"""
                <div class="ss-verdict">
                  <div class="ss-v-kw">"{kw}" · {total} articles</div>
                  <div class="ss-v-label">{verdict_str(avg)}</div>
                  <div class="ss-v-score">avg score <strong>{avg:+.4f}</strong></div>
                  <div class="ss-v-ghost">{avg:+.2f}</div>
                </div>
                <div class="ss-stats" style="grid-template-columns:repeat(3,1fr)">
                  <div class="ss-stat sp"><div class="ss-sn">{pos}</div><div class="ss-sl">Positive</div></div>
                  <div class="ss-stat su"><div class="ss-sn">{neu}</div><div class="ss-sl">Neutral</div></div>
                  <div class="ss-stat sn"><div class="ss-sn">{neg}</div><div class="ss-sl">Negative</div></div>
                </div>""", unsafe_allow_html=True)

        # Overlaid timeline
        tl1 = build_timeline(r1)
        tl2 = build_timeline(r2)
        if tl1 or tl2:
            st.markdown('<div class="ss-card"><div class="ss-ct">Overlaid sentiment timeline</div>', unsafe_allow_html=True)
            fig_cmp = go.Figure()
            if tl1:
                d1 = pd.DataFrame(tl1)
                fig_cmp.add_trace(go.Scatter(
                    x=d1["date"], y=d1["avg_score"], name=kw1,
                    line=dict(color="#4f7aff", width=2.5),
                    fill="tozeroy", fillcolor="rgba(79,122,255,0.06)",
                    hovertemplate=f"<b>{kw1}</b> · %{{x}}<br>%{{y:.3f}}<extra></extra>"
                ))
            if tl2:
                d2 = pd.DataFrame(tl2)
                fig_cmp.add_trace(go.Scatter(
                    x=d2["date"], y=d2["avg_score"], name=kw2,
                    line=dict(color="#9b6dff", width=2.5),
                    fill="tozeroy", fillcolor="rgba(155,109,255,0.06)",
                    hovertemplate=f"<b>{kw2}</b> · %{{x}}<br>%{{y:.3f}}<extra></extra>"
                ))
            fig_cmp.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.07)", line_width=1)
            fig_cmp.update_layout(**pl_base(), height=240,
                legend=dict(orientation="h", y=1.1, x=0, font_size=10))
            st.plotly_chart(fig_cmp, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Breakdown pies
        pc1, pc2 = st.columns(2)
        for col, kw, pos, neu, neg in [(pc1,kw1,p1,n1,g1),(pc2,kw2,p2,n2,g2)]:
            with col:
                st.markdown(f'<div class="ss-card"><div class="ss-ct">{kw} breakdown</div>', unsafe_allow_html=True)
                st.plotly_chart(render_pie(pos, neu, neg, 200), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

        # Articles side by side
        ac1, ac2 = st.columns(2)
        with ac1:
            st.markdown(f'<div class="ss-ct" style="margin-bottom:10px">Articles — {kw1}</div>', unsafe_allow_html=True)
            st.markdown(render_articles(r1, 8) if r1 else '<p style="color:var(--t2);font-size:12px">No articles.</p>', unsafe_allow_html=True)
        with ac2:
            st.markdown(f'<div class="ss-ct" style="margin-bottom:10px">Articles — {kw2}</div>', unsafe_allow_html=True)
            st.markdown(render_articles(r2, 8) if r2 else '<p style="color:var(--t2);font-size:12px">No articles.</p>', unsafe_allow_html=True)

    elif cmp_run:
        st.warning("Please enter both keywords.")
    else:
        st.markdown("""
        <div style="text-align:center;padding:48px 0;color:var(--t2)">
          <div style="font-size:13px;color:var(--t1)">Enter two topics above to compare</div>
          <div style="font-size:11px;margin-top:6px;font-family:JetBrains Mono,monospace">
            Tesla vs BYD &nbsp;·&nbsp; OpenAI vs Google &nbsp;·&nbsp; iPhone vs Android
          </div>
        </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════
# TAB 3 — TRENDING
# ════════════════════════════════════════════════════════════════════
with tab_trending:
    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)

    # Fetch both in parallel-ish
    with st.spinner("Fetching live headlines…"):
        trending_global = fetch_trending()
        trending_india  = fetch_trending_india()

    col_g, col_i = st.columns(2)

    # ── Global trending ───────────────────────────────────────────────────────
    with col_g:
        st.markdown('<div class="ss-card">', unsafe_allow_html=True)
        st.markdown('<div class="ss-ct">Breaking globally</div>', unsafe_allow_html=True)
        if trending_global:
            for i, t in enumerate(trending_global):
                tc1, tc2 = st.columns([5, 1])
                with tc1:
                    num = f"0{i+1}" if i < 9 else str(i+1)
                    st.markdown(f"""
                    <div class="trend-item">
                      <div class="trend-num">{num}</div>
                      <div class="trend-body">
                        <a href="{t['url']}" target="_blank" class="trend-title">{t['title']}</a>
                        <div class="trend-src">{t['source']}</div>
                      </div>
                    </div>""", unsafe_allow_html=True)
                with tc2:
                    kw_chip = " ".join(t["title"].split()[:3])
                    if st.button("Analyze →", key=f"trg_{i}", use_container_width=True):
                        st.session_state["run_kw"] = kw_chip
                        st.rerun()
        else:
            st.caption("Could not fetch global headlines.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── India trending ────────────────────────────────────────────────────────
    with col_i:
        st.markdown('<div class="ss-card">', unsafe_allow_html=True)
        st.markdown('<div class="ss-ct" style="color:#ff6b35">Trending in India 🇮🇳</div>', unsafe_allow_html=True)
        if trending_india:
            for i, t in enumerate(trending_india):
                tc1, tc2 = st.columns([5, 1])
                with tc1:
                    num = f"0{i+1}" if i < 9 else str(i+1)
                    st.markdown(f"""
                    <div class="trend-item">
                      <div class="trend-num">{num}</div>
                      <div class="trend-body">
                        <a href="{t['url']}" target="_blank" class="trend-title">{t['title']}</a>
                        <div class="trend-src" style="color:#ff6b35;opacity:0.7">{t['source']}</div>
                      </div>
                    </div>""", unsafe_allow_html=True)
                with tc2:
                    kw_chip = " ".join(t["title"].split()[:3])
                    if st.button("Analyze →", key=f"tri_{i}", use_container_width=True):
                        st.session_state["run_kw"] = kw_chip
                        st.rerun()
        else:
            st.markdown("""
            <div style="padding:24px 0;text-align:center;color:var(--t2);font-size:12px">
              Indian news sources unavailable.<br>
              <span style="font-size:11px">Times of India · NDTV · The Hindu · Hindustan Times</span>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════
# TAB 4 — HISTORY
# ════════════════════════════════════════════════════════════════════
with tab_history:
    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
    recent = get_recent_searches(limit=20)

    hdr1, hdr2 = st.columns([4, 1])
    with hdr1:
        st.markdown(f'<p style="color:var(--t1);font-size:13px">{len(recent)} recent searches</p>', unsafe_allow_html=True)
    with hdr2:
        if st.button("🗑 Clear all", use_container_width=True, key="clear_hist"):
            clear_history()
            st.success("History cleared.")
            st.rerun()

    if recent:
        for idx, s in enumerate(recent):
            avg = s["avg_score"]
            hc1, hc2 = st.columns([5, 1])
            with hc1:
                st.markdown(f"""
                <div class="hist-item">
                  <div>
                    <div class="hist-kw">{s['keyword']}</div>
                    <div class="hist-meta">
                      {s['searched_at'][:16]} &nbsp;·&nbsp; {s['total_articles']} articles &nbsp;·&nbsp;
                      {s['positive_count']}↑ {s['neutral_count']}→ {s['negative_count']}↓
                    </div>
                  </div>
                  <span class="ss-pill {pill_cls(avg)}">{verdict_str(avg).split()[1]} · {avg:+.3f}</span>
                </div>""", unsafe_allow_html=True)
            with hc2:
                if st.button("Re-run", key=f"h_{idx}", use_container_width=True):
                    st.session_state["run_kw"] = s["keyword"]
                    st.rerun()
    else:
        st.markdown("""
        <div style="text-align:center;padding:48px 0;color:var(--t2);font-size:13px">
          No searches yet.
        </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════
# TAB 5 — ABOUT
# ════════════════════════════════════════════════════════════════════
with tab_about:
    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="ss-card">
      <div class="ss-ct">What is SentimentScope?</div>
      <p style="font-size:14px;color:var(--t1);line-height:1.8;margin:0">
        SentimentScope is a real-time NLP sentiment intelligence platform that analyzes public
        perception across thousands of live news sources. Enter any topic and get instant,
        AI-powered insight into whether the media narrative is positive, negative, or neutral.
        The interface theme itself reacts to your results — green for positive coverage,
        red for negative, amber for mixed.
      </p>
    </div>
    <div class="about-grid">
      <div class="about-card">
        <div class="about-icon">⚡</div>
        <div class="about-title">Hybrid NLP pipeline</div>
        <div class="about-body">VADER scores first — fast, local, no API needed.
        For ambiguous results, RoBERTa (fine-tuned on 124M tweets) escalates the
        classification for higher accuracy.</div>
      </div>
      <div class="about-card">
        <div class="about-icon">🎨</div>
        <div class="about-title">Sentiment-reactive UI</div>
        <div class="about-body">The entire interface theme adapts to your results in real time.
        Positive sentiment shifts the palette warm-green. Negative turns it red-slate.
        Mixed gives an amber tone.</div>
      </div>
      <div class="about-card">
        <div class="about-icon">⚖</div>
        <div class="about-title">Compare mode</div>
        <div class="about-body">Pit two topics head-to-head — overlaid sentiment timelines,
        side-by-side breakdowns, and top articles from each source. Ideal for brand
        or policy comparisons.</div>
      </div>
      <div class="about-card">
        <div class="about-icon">📈</div>
        <div class="about-title">Dual timeline</div>
        <div class="about-body">Every analysis shows two charts stacked: article volume
        per day (how much coverage) + sentiment score per day. Together they reveal
        whether spikes in coverage are positive or negative.</div>
      </div>
      <div class="about-card">
        <div class="about-icon">◑</div>
        <div class="about-title">Flexible date ranges</div>
        <div class="about-body">Choose from 1 day, 1 week, 2 weeks, or 1 month
        of live news. Note: NewsAPI free tier provides up to 28 days of history
        with up to 30 articles per search.</div>
      </div>
      <div class="about-card">
        <div class="about-icon">↓</div>
        <div class="about-title">CSV export</div>
        <div class="about-body">Download every analyzed article with title, source,
        date, VADER score, and final sentiment score as a clean CSV for further
        analysis in Excel or Python.</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="ss-card">
      <div class="ss-ct">Data sources</div>
      <p style="font-size:13px;color:var(--t1);line-height:1.7;margin:0 0 12px">
        SentimentScope pulls from <strong style="color:var(--t0)">three independent sources</strong>
        and merges them into a single deduplicated feed — giving you broader, more diverse coverage
        than any single API alone.
      </p>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px">
        <div class="about-card">
          <div class="about-title">NewsAPI</div>
          <div class="about-body">English-language international news from 150,000+ sources. Strong on Western, tech, and finance coverage.</div>
        </div>
        <div class="about-card">
          <div class="about-title">The Guardian API</div>
          <div class="about-body">Free structured API from The Guardian. Excellent global, political, and long-form journalism coverage.</div>
        </div>
        <div class="about-card">
          <div class="about-title">RSS Feeds</div>
          <div class="about-body">Direct feeds from Times of India, The Hindu, NDTV, Al Jazeera, Dawn, SCMP — adds Indian, Asian & Middle Eastern perspectives.</div>
        </div>
      </div>
      <div class="ss-ct" style="margin-top:8px">Tier-1 filter sources</div>
      <p style="font-size:13px;color:var(--t1);line-height:1.7;margin:0 0 12px">
        When "Tier-1 only" is enabled, results are filtered to high-credibility publications only.
      </p>
      <div class="tier1-grid">
        <div class="tier1-chip">Reuters</div><div class="tier1-chip">Associated Press</div>
        <div class="tier1-chip">BBC News</div><div class="tier1-chip">Bloomberg</div>
        <div class="tier1-chip">The Guardian</div><div class="tier1-chip">Financial Times</div>
        <div class="tier1-chip">Wall Street Journal</div><div class="tier1-chip">NPR</div>
        <div class="tier1-chip">TechCrunch</div><div class="tier1-chip">The Verge</div>
        <div class="tier1-chip">Wired</div><div class="tier1-chip">Ars Technica</div>
        <div class="tier1-chip">Fortune</div><div class="tier1-chip">Business Insider</div>
        <div class="tier1-chip">CNBC</div><div class="tier1-chip">Washington Post</div>
      </div>
    </div>
    <div class="ss-card">
      <div class="ss-ct">Tech stack</div>
      <div class="stack-row">
        <span class="stack-pill">Streamlit</span>
        <span class="stack-pill">VADER Sentiment</span>
        <span class="stack-pill">RoBERTa (cardiffnlp)</span>
        <span class="stack-pill">HuggingFace API</span>
        <span class="stack-pill">NewsAPI</span>
        <span class="stack-pill">Plotly</span>
        <span class="stack-pill">Pandas</span>
        <span class="stack-pill">SQLite</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="ss-footer">
  <div class="ss-fl">◈ SentimentScope · Built with Python · © 2026</div>
  <div class="ss-fr">
    <span class="ss-fc">VADER</span><span class="ss-fc">RoBERTa</span>
    <span class="ss-fc">NewsAPI</span><span class="ss-fc">Plotly</span>
    <span class="ss-fc">SQLite</span>
  </div>
</div>
""", unsafe_allow_html=True)