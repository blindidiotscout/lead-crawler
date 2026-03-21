"""
Settings Page - Einstellungen
Konfiguration des Lead Crawlers
"""

from pathlib import Path

import streamlit as st

from lead_crawler.config import get_settings

# Page config
st.set_page_config(
    page_title="Einstellungen - Lead Crawler",
    page_icon="⚙️",
    layout="wide"
)

# Settings laden
settings = get_settings()

st.title("⚙️ Einstellungen")

# Tabs für verschiedene Kategorien
tab1, tab2, tab3, tab4 = st.tabs(["🔧 Allgemein", "🤖 LLM", "💾 Cache", "ℹ️ System"])

with tab1:
    st.subheader("🔧 Allgemeine Einstellungen")

    general_col1, general_col2 = st.columns(2)

    with general_col1:
        st.markdown("**Crawler-Einstellungen**")

        max_workers = st.slider(
            "Max. parallele Requests",
            min_value=1,
            max_value=10,
            value=settings.crawler.max_workers if hasattr(settings.crawler, 'max_workers') else 3
        )

        request_timeout = st.slider(
            "Request Timeout (Sekunden)",
            min_value=10,
            max_value=120,
            value=settings.crawler.timeout if hasattr(settings.crawler, 'timeout') else 30
        )

        user_agent = st.text_input(
            "User-Agent",
            value=settings.crawler.user_agent if hasattr(settings.crawler, 'user_agent') else "LeadCrawler/2.0"
        )

    with general_col2:
        st.markdown("**PLZ-Einstellungen**")

        plz_db_path = st.text_input(
            "PLZ-Datenbank Pfad",
            value=str(settings.plz.db_path) if hasattr(settings.plz, 'db_path') else "data/plz_austria.db"
        )

        default_radius = st.slider(
            "Standard-Radius (km)",
            min_value=5,
            max_value=50,
            value=20
        )

with tab2:
    st.subheader("🤖 LLM-Einstellungen")

    llm_col1, llm_col2 = st.columns(2)

    with llm_col1:
        st.markdown("**Ollama Konfiguration**")

        ollama_url = st.text_input(
            "Ollama URL",
            value=settings.ollama.url if hasattr(settings, 'ollama') else "http://192.168.178.123:11434"
        )

        ollama_model = st.selectbox(
            "Standard-Modell",
            ["qwen2.5:7b", "qwen3.5:397b-cloud", "llama3.2:3b", "mistral:7b"],
            index=0
        )

        llm_timeout = st.slider(
            "LLM Timeout (Sekunden)",
            min_value=30,
            max_value=600,
            value=settings.ollama.timeout if hasattr(settings.ollama, 'timeout') else 300
        )

        retry_attempts = st.slider(
            "Retry-Versuche",
            min_value=1,
            max_value=5,
            value=settings.ollama.retry_attempts if hasattr(settings.ollama, 'retry_attempts') else 3
        )

    with llm_col2:
        st.markdown("**Analyse-Einstellungen**")

        analyze_websites = st.toggle(
            "Websites standardmäßig analysieren",
            value=True
        )

        use_cache = st.toggle(
            "Cache für LLM-Ergebnisse nutzen",
            value=True
        )

        max_words = st.slider(
            "Max. Wörter für Website-Text",
            min_value=100,
            max_value=5000,
            value=1000
        )

with tab3:
    st.subheader("💾 Cache-Einstellungen")

    cache_col1, cache_col2 = st.columns(2)

    with cache_col1:
        st.markdown("**Cache-Konfiguration**")

        cache_enabled = st.toggle("Cache aktivieren", value=True)

        cache_db_path = st.text_input(
            "Cache-Datenbank Pfad",
            value=str(settings.cache.db_path) if hasattr(settings, 'cache') else "data/analysis_cache.db"
        )

        cache_ttl = st.slider(
            "Cache TTL (Tage)",
            min_value=1,
            max_value=90,
            value=settings.cache.ttl_days if hasattr(settings.cache, 'ttl_days') else 30
        )

    with cache_col2:
        st.markdown("**Cache-Statistiken**")

        # Cache-Statistiken (simuliert)
        st.metric("Cache-Einträge", "0", help="Aktuell im Cache")
        st.metric("Cache-Größe", "0 MB", help="Gespeicherte Daten")
        st.metric("Cache-Hit-Rate", "N/A", help="Trefferquote")

        st.markdown("---")

        if st.button("🗑️ Cache leeren"):
            try:
                from lead_crawler.services.cache import get_cache
                cache = get_cache()
                cache.clear()
                st.success("✅ Cache geleert!")
            except Exception as e:
                st.error(f"❌ Fehler: {str(e)}")

        if st.button("📊 Cache-Statistiken aktualisieren"):
            try:
                from lead_crawler.services.cache import get_cache
                cache = get_cache()
                stats = cache.get_stats()
                st.metric("Cache-Einträge", stats.get('total_entries', 0))
                st.metric("Cache-Größe", f"{stats.get('db_size_mb', 0):.2f} MB")
            except Exception as e:
                st.error(f"❌ Fehler: {str(e)}")

with tab4:
    st.subheader("ℹ️ System-Information")

    info_col1, info_col2 = st.columns(2)

    with info_col1:
        st.markdown("**Projekt**")
        st.write("Version: 2.0.0")
        st.write("Datenquelle: WKO (wirtschaftskammer.at)")
        st.write("LLM: Ollama (lokal)")
        st.write("Branch: refactoring")

        st.markdown("---")
        st.markdown("**Abhängigkeiten**")
        st.write("✅ FastAPI")
        st.write("✅ Streamlit")
        st.write("✅ Scrapy")
        st.write("✅ Pydantic")

    with info_col2:
        st.markdown("**Status**")
        st.write("🟢 Crawler: Bereit")
        st.write(f"🟢 LLM: {ollama_url}")
        st.write(f"🟢 Cache: Aktiv ({cache_ttl} Tage)")

        st.markdown("---")
        st.markdown("**Dateien**")

        # Pfade anzeigen
        if Path(cache_db_path).exists():
            st.write(f"✅ Cache-DB: {cache_db_path}")
        else:
            st.write("❌ Cache-DB: Nicht gefunden")

        if Path(plz_db_path).exists():
            st.write(f"✅ PLZ-DB: {plz_db_path}")
        else:
            st.write("❌ PLZ-DB: Nicht gefunden")

    # Environment-Variablen
    st.markdown("---")
    st.subheader("🔐 Environment-Variablen")

    show_env = st.toggle("Environment-Variablen anzeigen", value=False)

    if show_env:
        import os
        env_vars = [
            "OLLAMA_URL",
            "OLLAMA_MODEL",
            "CACHE_DB_PATH",
            "PLZ_DB_PATH"
        ]

        for var in env_vars:
            value = os.getenv(var, "Nicht gesetzt")
            # Mask sensitive values
            if "KEY" in var or "SECRET" in var:
                value = "***" if value else "Nicht gesetzt"
            st.write(f"`{var}`: {value}")

# Speichern-Button
st.markdown("---")

save_col1, save_col2 = st.columns(2)

with save_col1:
    if st.button("💾 Einstellungen speichern"):
        st.info("ℹ️ Einstellungen werden in der .env-Datei gespeichert")
        # In echter Implementation: .env schreiben

with save_col2:
    if st.button("🔄 Auf Standard zurücksetzen"):
        st.info("ℹ️ Einstellungen auf Standardwerte zurückgesetzt")
        # In echter Implementation: .env zurücksetzen
