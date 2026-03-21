"""
Lead Crawler - Streamlit Web Frontend
UI für Lead-Generierung und Analyse
"""

import streamlit as st
import sys
import json
import csv
import io
from datetime import datetime
from pathlib import Path

# Füge Projekt-Root zum Path hinzu (für 'src' imports)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from plz_radius import PLZDatabase, PLZRadiusService
from scraper import run_spider, run_spider_radius
from enhanced_scraper import run_enhanced_spider
from scoring import ScoringEngine

# Page config
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

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/search.png", width=60)
    st.title("🔍 Lead Crawler")
    st.markdown("---")
    
    # Navigation
    page = st.radio(
        "Navigation",
        ["🏠 Startseite", "🔎 Suche", "📊 Analyse", "⚙️ Einstellungen"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("**Made with ❤️ in Austria**")
    st.markdown("*WKO-Daten | LLM: Ollama*")

# Session State initialisieren
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'last_search' not in st.session_state:
    st.session_state.last_search = None

# Hauptbereich
if page == "🏠 Startseite":
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

elif page == "🔎 Suche":
    st.title("🔎 Unternehmenssuche")
    
    # Suchparameter
    st.subheader("Suchparameter")
    
    search_col1, search_col2, search_col3 = st.columns(3)
    
    with search_col1:
        plz_input = st.text_input("📮 PLZ", placeholder="z.B. 2351", max_chars=4)
    
    with search_col2:
        radius_km = st.slider("📍 Radius (km)", min_value=0, max_value=50, value=10)
    
    with search_col3:
        bundesland = st.selectbox("🏛️ Bundesland", [
            "Alle", "Wien", "Niederösterreich", "Oberösterreich", 
            "Steiermark", "Tirol", "Kärnten", "Salzburg", 
            "Burgenland", "Vorarlberg"
        ])
    
    # Optionen
    st.markdown("---")
    options_col1, options_col2 = st.columns(2)
    
    with options_col1:
        use_llm = st.toggle("🤖 LLM-Analyse aktivieren", value=True, 
                          help="Analysiert Websites mit lokalem LLM (Ollama)")
        if use_llm:
            llm_model = st.selectbox("LLM-Modell", ["qwen2.5:7b", "llama3.2:3b"])
    
    with options_col2:
        analyze_websites = st.toggle("🌐 Websites crawlen", value=True,
                                   help="Extrahiert Text von Unternehmenswebsites")
        max_companies = st.slider("Max. Unternehmen", 5, 100, 30)
    
    # Suche-Button
    st.markdown("---")
    
    search_disabled = not plz_input or len(plz_input) != 4
    
    if search_disabled:
        st.info("ℹ️ Gib eine 4-stellige PLZ ein um die Suche zu starten")
    
    if st.button("🚀 Suche starten", disabled=search_disabled, type="primary"):
        if len(plz_input) == 4 and plz_input.isdigit():
            with st.spinner("🔍 Suche läuft... Dies kann einige Minuten dauern"):
                try:
                    # PLZ validieren
                    plz_db = PLZDatabase()
                    coords = plz_db.get_plz(plz_input)
                    
                    if not coords:
                        st.error(f"❌ PLZ {plz_input} nicht gefunden")
                    else:
                        st.info(f"📍 {coords.ort}, {coords.bundesland}")
                        
                        # Spider ausführen
                        if use_llm:
                            results = run_enhanced_spider(
                                plz=plz_input,
                                use_llm=True,
                                llm_model=llm_model,
                                analyze_websites=analyze_websites
                            )
                        else:
                            results = run_spider_radius(
                                center_plz=plz_input,
                                radius_km=radius_km
                            )
                        
                        # Duplikate entfernen
                        seen = set()
                        unique_results = []
                        for r in results:
                            key = r.get('name', '') + r.get('plz', '') + r.get('ort', '')
                            if key not in seen:
                                seen.add(key)
                                unique_results.append(r)
                        
                        st.session_state.search_results = unique_results
                        st.session_state.last_search = {
                            'plz': plz_input,
                            'radius': radius_km,
                            'bundesland': bundesland,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        st.success(f"✅ {len(unique_results)} Unternehmen gefunden!")
                        
                except Exception as e:
                    st.error(f"❌ Fehler bei der Suche: {str(e)}")
        else:
            st.error("❌ Bitte gib eine gültige 4-stellige PLZ ein")
    
    # Ergebnisse anzeigen
    if st.session_state.search_results:
        st.markdown("---")
        st.subheader(f"📋 Ergebnisse ({len(st.session_state.search_results)})")
        
        # Filter
        filter_col1, filter_col2 = st.columns(2)
        
        with filter_col1:
            # Branchen-Filter
            branches = list(set([
                r.get('branche', 'Unbekannt') 
                for r in st.session_state.search_results 
                if r.get('branche')
            ]))
            selected_branch = []
            if branches:
                selected_branch = st.multiselect("🏭 Branche filtern", branches)
        
        with filter_col2:
            # Website-Filter
            has_website_filter = st.checkbox("Nur mit Website", value=False)
        
        # Ergebnisse filtern
        filtered_results = st.session_state.search_results
        if selected_branch:
            filtered_results = [r for r in filtered_results if r.get('branche') in selected_branch]
        if has_website_filter:
            filtered_results = [r for r in filtered_results if r.get('website')]
        
        # Als Tabelle anzeigen
        if filtered_results:
            display_data = []
            for r in filtered_results:
                row = {
                    'Name': r.get('name', 'N/A'),
                    'Ort': f"{r.get('plz', '')} {r.get('ort', '')}",
                    'Branche': r.get('branche', 'N/A')[:30] + '...' if len(r.get('branche', '')) > 30 else r.get('branche', 'N/A'),
                    'Website': '✅' if r.get('website') else '❌',
                    'LLM': '✅' if r.get('llm_analysis') else '❌'
                }
                
                # Scoring hinzufügen wenn vorhanden
                if 'score_total' in r:
                    row['Score'] = f"{r['score_total']}/100"
                
                display_data.append(row)
            
            st.dataframe(
                display_data,
                use_container_width=True,
                hide_index=True
            )
            
            # Einzelne Unternehmen anzeigen
            st.markdown("---")
            st.subheader("🔍 Details")
            
            company_names = [r.get('name', 'Unbekannt') for r in filtered_results]
            selected_company = st.selectbox("Unternehmen auswählen", company_names)
            
            if selected_company:
                company = next((r for r in filtered_results if r.get('name') == selected_company), None)
                if company:
                    with st.container():
                        st.markdown(f"""
                        <div class='lead-card'>
                            <h3>{company.get('name', 'N/A')}</h3>
                            <p>📍 {company.get('strasse', '')}, {company.get('plz', '')} {company.get('ort', '')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        detail_col1, detail_col2 = st.columns(2)
                        
                        with detail_col1:
                            st.markdown("**📞 Kontakt**")
                            st.write(f"Tel: {company.get('telefon', 'N/A')}")
                            st.write(f"Email: {company.get('email', 'N/A')}")
                            
                            if company.get('website'):
                                st.markdown(f"**🌐 [Website]({company['website']})**")
                        
                        with detail_col2:
                            st.markdown("**🏢 Branche**")
                            st.write(company.get('branche', 'N/A'))
                            
                            if company.get('llm_analysis'):
                                llm = company['llm_analysis']
                                st.markdown("**🤖 LLM-Analyse**")
                                st.write(f"Branche: {llm.get('branch', 'N/A')}")
                                st.write(f"Services: {', '.join(llm.get('services', []))[:50]}...")
                                st.write(f"Confidence: {llm.get('confidence', 0):.0%}")
            
            # Export Buttons
            st.markdown("---")
            export_col1, export_col2 = st.columns(2)
            
            with export_col1:
                if st.button("📥 Als CSV exportieren"):
                    try:
                        output = io.StringIO()
                        if filtered_results:
                            # CSV Header
                            fieldnames = ['name', 'strasse', 'plz', 'ort', 'bundesland', 
                                        'telefon', 'email', 'website', 'branche']
                            if filtered_results[0].get('llm_analysis'):
                                fieldnames.extend(['llm_branch', 'llm_services', 'llm_confidence'])
                            
                            writer = csv.DictWriter(output, fieldnames=fieldnames)
                            writer.writeheader()
                            
                            for r in filtered_results:
                                row = {k: r.get(k, '') for k in ['name', 'strasse', 'plz', 'ort', 
                                                                  'bundesland', 'telefon', 'email', 
                                                                  'website', 'branche']}
                                if r.get('llm_analysis'):
                                    llm = r['llm_analysis']
                                    row['llm_branch'] = llm.get('branch', '')
                                    row['llm_services'] = ', '.join(llm.get('services', []))
                                    row['llm_confidence'] = llm.get('confidence', 0)
                                writer.writerow(row)
                            
                            st.download_button(
                                label="⬇️ CSV herunterladen",
                                data=output.getvalue(),
                                file_name=f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                mime="text/csv"
                            )
                    except Exception as e:
                        st.error(f"Export fehlgeschlagen: {e}")
            
            with export_col2:
                if st.button("📥 Als JSON exportieren"):
                    try:
                        json_str = json.dumps(filtered_results, indent=2, ensure_ascii=False)
                        st.download_button(
                            label="⬇️ JSON herunterladen",
                            data=json_str,
                            file_name=f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
                    except Exception as e:
                        st.error(f"Export fehlgeschlagen: {e}")

elif page == "📊 Analyse":
    st.title("📊 Analyse & Statistiken")
    
    if not st.session_state.search_results:
        st.info("ℹ️ Starte zuerst eine Suche um Statistiken zu sehen")
    else:
        results = st.session_state.search_results
        
        # Metriken
        st.subheader("📈 Übersicht")
        
        metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
        
        with metrics_col1:
            with st.container():
                st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
                st.metric("Gefunden", len(results))
                st.markdown("</div>", unsafe_allow_html=True)
        
        with metrics_col2:
            websites = sum(1 for r in results if r.get('website'))
            st.metric("Mit Website", f"{websites} ({websites/len(results)*100:.0f}%)")
        
        with metrics_col3:
            llm_done = sum(1 for r in results if r.get('llm_analysis'))
            st.metric("LLM-Analysiert", f"{llm_done} ({llm_done/len(results)*100:.0f}%)")
        
        with metrics_col4:
            cached = sum(1 for r in results if r.get('llm_cached'))
            st.metric("Aus Cache", cached)
        
        st.markdown("---")
        
        # Branchen-Verteilung
        st.subheader("🏭 Branchen-Verteilung")
        
        branches = {}
        for r in results:
            b = r.get('branche', 'Unbekannt')
            branches[b] = branches.get(b, 0) + 1
        
        if branches:
            import pandas as pd
            branch_df = pd.DataFrame([
                {'Branche': k, 'Anzahl': v} 
                for k, v in sorted(branches.items(), key=lambda x: x[1], reverse=True)
            ])
            st.bar_chart(branch_df.set_index('Branche'))
        
        # Score-Verteilung
        if any('score_total' in r for r in results):
            st.markdown("---")
            st.subheader("⭐ Score-Verteilung")
            
            scores = {}
            for r in results:
                if 'score_total' in r:
                    g = r.get('score_grade', 'N/A')
                    scores[g] = scores.get(g, 0) + 1
            
            if scores:
                score_df = pd.DataFrame([
                    {'Grade': k, 'Anzahl': v} 
                    for k, v in sorted(scores.items())
                ])
                st.bar_chart(score_df.set_index('Grade'))
        
        # Website-Verfügbarkeit
        st.markdown("---")
        st.subheader("🌐 Website-Verfügbarkeit")
        
        has_website = sum(1 for r in results if r.get('website'))
        no_website = len(results) - has_website
        
        website_df = pd.DataFrame([
            {'Kategorie': 'Mit Website', 'Anzahl': has_website},
            {'Kategorie': 'Ohne Website', 'Anzahl': no_website}
        ])
        st.bar_chart(website_df.set_index('Kategorie'))

elif page == "⚙️ Einstellungen":
    st.title("⚙️ Einstellungen")
    
    st.subheader("🔧 Crawler-Einstellungen")
    
    settings_col1, settings_col2 = st.columns(2)
    
    with settings_col1:
        st.markdown("**LLM-Konfiguration**")
        ollama_url = st.text_input("Ollama URL", value="http://192.168.178.123:11434")
        ollama_model = st.selectbox("Standard-Modell", ["qwen2.5:7b", "llama3.2:3b", "mistral:7b"])
        timeout = st.slider("Timeout (Sekunden)", 30, 600, 300)
    
    with settings_col2:
        st.markdown("**Cache-Einstellungen**")
        cache_ttl = st.slider("Cache-TTL (Tage)", 1, 90, 30)
        clear_cache = st.button("🗑️ Cache leeren")
        
        if clear_cache:
            try:
                from analysis_cache import AnalysisCache
                cache = AnalysisCache()
                # Cache leeren Logik hier
                st.success("✅ Cache geleert (Simulation)")
            except Exception as e:
                st.error(f"❌ Fehler: {e}")
    
    st.markdown("---")
    
    st.subheader("📋 System-Info")
    
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        st.markdown("**Projekt**")
        st.write("Version: 1.0.0")
        st.write("Datenquelle: WKO (wirtschaftskammer.at)")
        st.write("LLM: Ollama (lokal)")
    
    with info_col2:
        st.markdown("**Status**")
        st.write("🟢 Crawler: Bereit")
        st.write(f"🟢 LLM: {ollama_url}")
        st.write(f"🟢 Cache: Aktiv ({cache_ttl} Tage)")

# Footer
st.markdown("---")
st.caption("Lead Crawler | WKO-Daten | LLM: Ollama | Made with Streamlit")
