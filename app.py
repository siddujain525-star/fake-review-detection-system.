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

import os

# --- 1. LOAD MODEL & ASSETS ---
# This ensures we find the folder regardless of where the server runs from
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model", "fake_review_model.pkl")

@st.cache_resource
def load_model_assets():
    if not os.path.exists(MODEL_PATH):
        # This will show up in your Streamlit logs
        st.error(f"File not found: {MODEL_PATH}")
        return None, None

    try:
        # Load the saved object
        loaded_data = joblib.load(MODEL_PATH)
        
        # DEBUG: If your pkl has (model, vectorizer) as a tuple/list
        if isinstance(loaded_data, (tuple, list)) and len(loaded_data) == 2:
            return loaded_data[0], loaded_data[1]
        
        # If your pkl IS the model and you load vectorizer separately, 
        # or if it's a single pipeline object:
        return loaded_data, None 
        
    except Exception as e:
        st.error(f"Internal Load Error: {e}")
        return None, None

# Initialize
model, vectorizer = load_model_assets()

# If loading failed, stop the app gracefully so you can see the error
if model is None:
    st.warning("⚠️ Model could not be initialized. Check your 'model/' folder on GitHub.")
    st.stop()

# Create the pipeline for LIME
# If your 'model' already includes the vectorizer (a scikit-learn Pipeline), 
# you don't need make_pipeline.
try:
    if vectorizer is not None:
        c = make_pipeline(vectorizer, model)
    else:
        # Assuming the loaded model is already a Pipeline
        c = model 
except Exception as e:
    st.error(f"Pipeline Creation Error: {e}")
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
