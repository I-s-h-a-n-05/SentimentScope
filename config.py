import os
from dotenv import load_dotenv

load_dotenv()

try:
    import streamlit as st
    NEWS_API_KEY     = st.secrets.get("NEWS_API_KEY", os.getenv("NEWS_API_KEY", ""))
    GUARDIAN_API_KEY = st.secrets.get("GUARDIAN_API_KEY", os.getenv("GUARDIAN_API_KEY", ""))
except Exception:
    NEWS_API_KEY     = os.getenv("NEWS_API_KEY", "")
    GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY", "")

NEWS_FETCH_LIMIT    = 30
VADER_AMBIGUITY_LOW  = -0.2
VADER_AMBIGUITY_HIGH =  0.2
ROBERTA_MODEL = "cardiffnlp/twitter-roberta-base-sentiment"