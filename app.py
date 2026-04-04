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

# --- 1. LOAD MODEL & ASSETS ---
@st.cache_resource
def load_model():
    # Update path if your model is in a different folder
    return joblib.load("model/fake_review_model.pkl")

try:
    model, vectorizer = load_model()
    # Create a pipeline for LIME and easier predicting
    c = make_pipeline(vectorizer, model)
except Exception as e:
    st.error(f"Model Load Error: {e}. Check if 'model/fake_review_model.pkl' exists.")
    st.stop()

# --- 2. CORE ANALYSIS ENGINE ---
def run_analysis(review_text, rating=None):
    cleaned = clean_text(review_text)
    words = cleaned.split()
    
    if len(words) == 0:
        return None

    # AI Prediction
    probs = c.predict_proba([cleaned])[0]
    prediction_index = np.argmax(probs) # 0 = Fake (CG), 1 = Real (OR)
    ai_real_confidence = probs[1] * 100
    
    # Heuristics (Uniqueness & Length)
    unique_ratio = len(set(words)) / len(words)
    avg_word_len = sum(len(w) for w in words) / len(words)

    # Final Verdict Logic
    # Flag as fake if AI says so OR if text is extremely repetitive
    is_fake = (prediction_index == 0) or (unique_ratio < 0.15)
    
    # --- BEHAVIORAL ANALYSIS (Intentional Misinformation) ---
    intentional_malice = False
    if rating is not None:
        malicious_keywords = ['bad', 'worst', 'scam', 'fake', 'trash', 'waste', 'cheap', 'fraud']
        # Scenario: Human-written (Real) but 1-star rating with aggressive hate speech
        if prediction_index == 1 and rating <= 2.0 and any(kw in cleaned.lower() for kw in malicious_keywords):
            intentional_malice = True
        # Scenario: Human-written (Real) but 5-star rating using 'waste' (Sarcasm)
        if prediction_index == 1 and rating >= 4.5 and "waste" in cleaned.lower():
            intentional_malice = True

    return {
        "is_fake": is_fake,
        "intentional": intentional_malice,
        "confidence": ai_real_confidence,
        "unique_ratio": unique_ratio,
        "avg_word_len": avg_word_len,
        "prediction_index": prediction_index,
        "cleaned_text": cleaned
    }

# --- 3. UI HEADER ---
st.title("🛡️ AI Product Integrity System")
st.markdown("Detecting computer-generated spam and intentional human misinformation.")

tab1, tab2 = st.tabs(["📝 Single Review Check", "🔍 Live Product Analysis"])

# --- TAB 1: MANUAL INPUT ---
with tab1:
    st.subheader("Analyze a Single Review")
    manual_review = st.text_area("Paste a review here:", height=150, key="manual_input")
    
    if st.button("Analyze Review", key="manual_btn"):
        if manual_review:
            res = run_analysis(manual_review)
            if res:
                col1, col2 = st.columns(2)
                with col1:
                    if res["is_fake"]:
                        st.error("### 🚩 VERDICT: FAKE / SUSPICIOUS")
                    else:
                        st.success("### ✅ VERDICT: GENUINE")
                
                with col2:
                    st.metric("AI Real Confidence", f"{res['confidence']:.1f}%")
                
                # Visual Explanation (LIME)
                with st.expander("🔍 See Feature Importance (LIME)"):
                    explainer = LimeTextExplainer(class_names=['Fake', 'Real'])
                    exp = explainer.explain_instance(res["cleaned_text"], c.predict_proba, num_features=10)
                    components
