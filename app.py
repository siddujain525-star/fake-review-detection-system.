import streamlit as st
import joblib
import numpy as np
import pandas as pd
import os
from src.preprocess import clean_text
from scraper_test import scrape_amazon_reviews
from lime.lime_text import LimeTextExplainer
import streamlit.components.v1 as components
from sklearn.pipeline import make_pipeline

# --- PAGE CONFIG ---
st.set_page_config(page_title="AI Review Analyser", layout="wide", page_icon="🛡️")

# --- 1. CLOUD-SAFE LOAD MODEL & ASSETS ---
# Absolute pathing is required because the working directory on Streamlit Cloud can be inconsistent
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model", "fake_review_model.pkl")

@st.cache_resource
def load_model_assets():
    if not os.path.exists(MODEL_PATH):
        st.error(f"❌ Model file NOT found at: {MODEL_PATH}")
        st.stop()

    try:
        loaded_data = joblib.load(MODEL_PATH)
        # Check if pkl contains (model, vectorizer) tuple or single pipeline
        if isinstance(loaded_data, (tuple, list)) and len(loaded_data) == 2:
            return loaded_data[0], loaded_data[1]
        return loaded_data, None 
    except Exception as e:
        st.error(f"Internal Load Error: {e}")
        st.stop()

model, vectorizer = load_model_assets()

# Build pipeline for analysis
try:
    if vectorizer is not None:
        c = make_pipeline(vectorizer, model)
    else:
        c = model  # Assumes it was already a Pipeline
except Exception as e:
    st.error(f"Pipeline Creation Error: {e}")
    st.stop()

# --- 2. CORE ANALYSIS ENGINE ---
def run_analysis(review_text, rating=None):
    cleaned = clean_text(review_text)
    words = cleaned.split()
    
    if len(words) == 0:
        return None

    probs = c.predict_proba([cleaned])[0]
    prediction_index = np.argmax(probs) # 0 = Fake (CG), 1 = Real (OR)
    ai_real_confidence = probs[1] * 100
    
    unique_ratio = len(set(words)) / len(words)
    is_fake = (prediction_index == 0) or (unique_ratio < 0.15)
    
    # BEHAVIORAL ANALYSIS: Detecting "Intentional Misinformation"
    # Flags human-written text that has a mismatch between sentiment and rating
    intentional_malice = False
    if rating is not None:
        malicious_keywords = ['bad', 'worst', 'scam', 'fake', 'trash', 'waste', 'cheap', 'fraud']
        if prediction_index == 1 and rating <= 2.0 and any(kw in cleaned.lower() for kw in malicious_keywords):
            intentional_malice = True
        if prediction_index == 1 and rating >= 4.5 and "waste" in cleaned.lower():
            intentional_malice = True

    return {
        "is_fake": is_fake,
        "intentional": intentional_malice,
        "confidence": ai_real_confidence,
        "cleaned_text": cleaned
    }

# --- 3. UI LAYOUT ---
st.title("🛡️ AI Product Integrity System")
st.markdown("Enter a product name to analyze live reviews for bot-spam and intentional misinformation.")

tab1, tab2 = st.tabs(["📝 Single Review Check", "🌐 Global Product Analysis"])

with tab1:
    st.subheader("Manual Analysis")
    manual_review = st.text_area("Paste a review here:", height=150, key="manual_input")
    if st.button("Analyze Review", key="manual_btn"):
        if manual_review:
            res = run_analysis(manual_review)
            if res:
                if res["is_fake"]: st.error("### 🚩 VERDICT: FAKE")
                else: st.success("### ✅ VERDICT: GENUINE")
                st.metric("AI Confidence", f"{res['confidence']:.1f}%")

with tab2:
    st.subheader("Live Multi-Site Search")
    product_name = st.text_input("Enter Product Name (e.g. 'Logitech Mouse'):", key="p_name")

    if st.button("Search & Analyze Across Platforms", key="search_btn"):
        if product_name:
            with st.spinner(f"Scraping Amazon for '{product_name}'..."):
                scraped_data = scrape_amazon_reviews(product_name)
            
            if not scraped_data:
                st.error("No reviews found. Amazon may be blocking the request.")
                if os.path.exists("bot_check.png"):
                    st.image("bot_check.png", caption="Last Browser View: Check for CAPTCHA")
            else:
                total = len(scraped_data)
                fakes = 0
                malice = 0
                table_rows = []

                for item in scraped_data:
                    analysis = run_analysis(item['text'], rating=item['rating'])
                    if not analysis: continue
                    if analysis['is_fake']: fakes += 1
                    if analysis['intentional']: malice += 1
                    
                    table_rows.append({
                        "Rating": f"{item['rating']} ⭐",
                        "Review Snippet": item['text'][:80] + "...",
                        "AI Verdict": "🚩 FAKE" if analysis['is_fake'] else "✅ REAL",
                        "Behavioral Alert": "⚠️ MALICIOUS" if analysis['intentional'] else "Normal"
                    })

                st.divider()
                st.header(f"Trust Report for: {product_name}")
                col1, col2, col3 = st.columns(3)
                col1.metric("Reviews Analyzed", total)
                col2.metric("Authenticity Score", f"{int(((total-fakes)/total)*100)}%")
                col3.metric("Malicious Intent Found", malice)

                st.subheader("📑 Detailed Breakdown")
                st.table(pd.DataFrame(table_rows))
        else:
            st.warning("Please enter a product name.")
