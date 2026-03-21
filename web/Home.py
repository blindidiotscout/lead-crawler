"""
Lead Crawler - Streamlit Web Frontend
Multi-Page App für Lead-Generierung und Analyse
"""

import streamlit as st
from pathlib import Path

# Page config (must be first Streamlit command)
st.set_page_config(
    page_title="Lead Crawler",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS für besseres Styling
st.markdown("""
<style>
    .main {
        padding: 1rem 2rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3rem;
        font-weight: bold;
    }
    .lead-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 4px solid #4CAF50;
    }
    .score-high { color: #4CAF50; font-weight: bold; }
    .score-medium { color: #FF9800; font-weight: bold; }
    .score-low { color: #f44336; font-weight: bold; }
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 1rem;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Session State initialisieren
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'last_search' not in st.session_state:
    st.session_state.last_search = None
if 'settings' not in st.session_state:
    from lead_crawler.config import get_settings
    st.session_state.settings = get_settings()

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/search.png", width=60)
    st.title("🔍 Lead Crawler")
    st.markdown("---")
    st.markdown("**Made with ❤️ in Austria**")
    st.markdown("*WKO-Daten | LLM: Ollama*")
    
    # Quick Stats
    if st.session_state.search_results:
        st.markdown("---")
        st.markdown("**📊 Letzte Suche**")
        st.metric("Gefunden", len(st.session_state.search_results))

# Hauptbereich - Startseite
st.markdown("""
<div style='text-align: center; padding: 3rem 1rem;'>
    <h1>🎯 Lead Crawler</h1>
    <h3>Automatisierte Lead-Generierung für KMU in Österreich</h3>
    <p style='font-size: 1.2rem; color: #666; margin-top: 2rem;'>
        Finde und analysiere Unternehmen mit KI-gestützter Branchenerkennung
    </p>
</div>
""", unsafe_allow_html=True)

# Feature Cards
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div style='background: #f0f2f6; border-radius: 10px; padding: 1.5rem; text-align: center;'>
        <h2>📍</h2>
        <h4>Geografische Suche</h4>
        <p>PLZ + Radius Suche über ganz Österreich</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style='background: #f0f2f6; border-radius: 10px; padding: 1.5rem; text-align: center;'>
        <h2>🤖</h2>
        <h4>KI-Analyse</h4>
        <p>LLM-basierte Branchenerkennung via Ollama</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div style='background: #f0f2f6; border-radius: 10px; padding: 1.5rem; text-align: center;'>
        <h2>📊</h2>
        <h4>Lead Scoring</h4>
        <p>Qualitätsbewertung von Unternehmen</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Quick Stats
if st.session_state.search_results:
    st.subheader("📈 Letzte Suche")
    results = st.session_state.search_results
    
    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
    
    with metrics_col1:
        st.metric("Gefunden", len(results))
    with metrics_col2:
        websites = sum(1 for r in results if r.get('website'))
        st.metric("Mit Website", websites)
    with metrics_col3:
        llm_analyzed = sum(1 for r in results if r.get('llm_analysis'))
        st.metric("LLM-Analysiert", llm_analyzed)
    with metrics_col4:
        cached = sum(1 for r in results if r.get('llm_cached'))
        st.metric("Aus Cache", cached)
else:
    st.info("ℹ️ Starte eine Suche auf der 🔎 Suche-Seite um Ergebnisse zu sehen")

# Footer
st.markdown("---")
st.caption("Lead Crawler v2.0 | WKO-Daten | LLM: Ollama | Made with Streamlit")