from scraper_test import scrape_amazon_reviews  # Ensure this function now accepts a NAME, not a URL
import streamlit as st
import joblib
import numpy as np
from src.preprocess import clean_text
from lime.lime_text import LimeTextExplainer
import streamlit.components.v1 as components
from sklearn.pipeline import make_pipeline

st.set_page_config(page_title="AI Review Analyser", layout="wide")

# 1. Load Model
@st.cache_resource
def load_model():
    return joblib.load("model/fake_review_model.pkl")

try:
    model, vectorizer = load_model()
    c = make_pipeline(vectorizer, model)
except Exception as e:
    st.error(f"Model Load Error: {e}. Ensure 'model/fake_review_model.pkl' exists.")

st.title("🛡️ AI Product Integrity System")

# --- REUSABLE ANALYSIS FUNCTION ---
def run_analysis(review_text, rating=None):
    cleaned = clean_text(review_text)
    words = cleaned.split()
    
    if len(words) == 0:
        return {"status": "Invalid", "is_fake": False}

    probs = c.predict_proba([cleaned])[0]
    prediction_index = np.argmax(probs)
    ai_confidence = probs[1] * 100 # Prob of being "Real"
    
    unique_ratio = len(set(words)) / len(words)
    avg_word_length = sum(len(word) for word in words) / len(words) if len(words) > 0 else 0

    # Hybrid Logic: AI Verdict + Heuristics
    is_fake = (prediction_index == 0) or (unique_ratio < 0.15)
    
    # NEW: Intentional Misinformation Check (Behavioral Analysis)
    intentional_flag = False
    if rating is not None:
        # If AI says it's written naturally (Real), but it's 1-star and uses 'trash/scam' 
        # it might be a competitor's intentional negative review.
        if prediction_index == 1 and rating <= 1.5 and any(word in cleaned for word in ['bad', 'worst', 'scam']):
            intentional_flag = True

    return {
        "is_fake": is_fake,
        "intentional": intentional_flag,
        "ai_confidence": ai_confidence,
        "unique_ratio": unique_ratio,
        "avg_len": avg_word_length,
        "prediction": prediction_index
    }

# --- UI LAYOUT TABS ---
tab1, tab2 = st.tabs(["📝 Single Review Check", "🔍 Multi-Site Product Search"])

# TAB 1: Manual Check (Kept for your debugging)
with tab1:
    st.subheader("Manual Analysis")
    manual_review = st.text_area("Paste review here:", height=100, key="manual_area")
    if st.button("Analyze", key="manual_btn"):
        if manual_review:
            res = run_analysis(manual_review)
            if res["is_fake"]: st.error("🚩 VERDICT: FAKE")
            else: st.success("✅ VERDICT: REAL")
            # ... (LIME code here remains the same as your original)

# --- TAB 2: LIVE PRODUCT SEARCH (THE MAIN UPDATE) ---
with tab2:
    st.subheader("🌐 Global Product Analysis")
    # Change: Now asking for Product Name
    product_name = st.text_input("Enter Product Name (e.g. 'iPhone 15 Pro' or 'Boat Airdopes')", key="p_name_input")

    if st.button("Search & Analyze Across Platforms", key="search_btn"):
        if product_name:
            with st.spinner(f"Searching and analyzing reviews for '{product_name
