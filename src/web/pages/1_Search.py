"""
Search Page - Unternehmenssuche
PLZ/Radius Suche mit LLM-Analyse
"""

import csv
import io
import json
from datetime import datetime

import streamlit as st

from lead_crawler.config import get_settings
from lead_crawler.crawlers import WKOCrawler
from lead_crawler.pipelines import LeadAnalysisPipeline
from lead_crawler.services.plz_service import get_plz_service

# Page config
st.set_page_config(page_title="Suche - Lead Crawler", page_icon="🔎", layout="wide")

# Session State
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "last_search" not in st.session_state:
    st.session_state.last_search = None

# Settings
settings = get_settings()

st.title("🔎 Unternehmenssuche")

# Suchparameter
st.subheader("Suchparameter")

search_col1, search_col2, search_col3 = st.columns(3)

with search_col1:
    plz_input = st.text_input("📮 PLZ", placeholder="z.B. 2351", max_chars=4)

with search_col2:
    radius_km = st.slider("📍 Radius (km)", min_value=0, max_value=50, value=10)

with search_col3:
    bundesland = st.selectbox(
        "🏛️ Bundesland",
        [
            "Alle",
            "Wien",
            "Niederösterreich",
            "Oberösterreich",
            "Steiermark",
            "Tirol",
            "Kärnten",
            "Salzburg",
            "Burgenland",
            "Vorarlberg",
        ],
    )

# Optionen
st.markdown("---")
options_col1, options_col2 = st.columns(2)

with options_col1:
    use_llm = st.toggle(
        "🤖 LLM-Analyse aktivieren", value=True, help="Analysiert Websites mit lokalem LLM (Ollama)"
    )
    if use_llm:
        llm_model = st.selectbox("LLM-Modell", ["qwen2.5:7b", "qwen3.5:397b-cloud", "llama3.2:3b"])

with options_col2:
    analyze_websites = st.toggle(
        "🌐 Websites crawlen", value=True, help="Extrahiert Text von Unternehmenswebsites"
    )
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
                plz_service = get_plz_service()
                coords = plz_service.get_plz(plz_input)

                if not coords:
                    st.error(f"❌ PLZ {plz_input} nicht gefunden")
                else:
                    st.info(f"📍 {coords.ort}, {coords.bundesland}")

                    # Crawler ausführen
                    crawler = WKOCrawler()

                    # Immer crawler ausführen
                    crawler_result = crawler.crawl_radius(center_plz=plz_input, radius_km=radius_km)

                    if use_llm:
                        # Mit LLM-Analyse
                        pipeline = LeadAnalysisPipeline(settings=settings)
                        batch_result = pipeline.analyze_from_crawler(
                            crawler_result, skip_cache=False
                        )
                        # Konvertiere zu Dict-Liste
                        companies = [r.company.to_dict() for r in batch_result.results]
                    else:
                        # Ohne LLM
                        companies = [c.to_dict() for c in crawler_result.companies]

                    # Duplikate entfernen
                    seen = set()
                    unique_results = []
                    for r in companies:
                        key = r.get("name", "") + r.get("plz", "") + r.get("ort", "")
                        if key not in seen:
                            seen.add(key)
                            unique_results.append(r)

                    # Limitieren
                    unique_results = unique_results[:max_companies]

                    st.session_state.search_results = unique_results
                    st.session_state.last_search = {
                        "plz": plz_input,
                        "radius": radius_km,
                        "bundesland": bundesland,
                        "timestamp": datetime.now().isoformat(),
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
        branches = list(
            set(
                [
                    r.get("branche", "Unbekannt")
                    for r in st.session_state.search_results
                    if r.get("branche")
                ]
            )
        )
        selected_branch = []
        if branches:
            selected_branch = st.multiselect("🏭 Branche filtern", branches)

    with filter_col2:
        # Website-Filter
        has_website_filter = st.checkbox("Nur mit Website", value=False)

    # Ergebnisse filtern
    filtered_results = st.session_state.search_results
    if selected_branch:
        filtered_results = [r for r in filtered_results if r.get("branche") in selected_branch]
    if has_website_filter:
        filtered_results = [r for r in filtered_results if r.get("website")]

    # Als Tabelle anzeigen
    if filtered_results:
        display_data = []
        for r in filtered_results:
            row = {
                "Name": r.get("name", "N/A"),
                "Ort": f"{r.get('plz', '')} {r.get('ort', '')}",
                "Branche": (
                    r.get("branche", "N/A")[:30] + "..."
                    if len(r.get("branche", "")) > 30
                    else r.get("branche", "N/A")
                ),
                "Website": "✅" if r.get("website") else "❌",
                "LLM": "✅" if r.get("llm_analysis") else "❌",
            }

            # Scoring hinzufügen wenn vorhanden
            if "score_total" in r:
                row["Score"] = f"{r['score_total']}/100"

            display_data.append(row)

        st.dataframe(display_data, use_container_width=True, hide_index=True)

        # Einzelne Unternehmen anzeigen
        st.markdown("---")
        st.subheader("🔍 Details")

        company_names = [r.get("name", "Unbekannt") for r in filtered_results]
        selected_company = st.selectbox("Unternehmen auswählen", company_names)

        if selected_company:
            company = next((r for r in filtered_results if r.get("name") == selected_company), None)
            if company:
                with st.container():
                    st.markdown(
                        f"""
                    <div class='lead-card'>
                        <h3>{company.get('name', 'N/A')}</h3>
                        <p>📍 {company.get('strasse', '')}, {company.get('plz', '')} {company.get('ort', '')}</p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                    detail_col1, detail_col2 = st.columns(2)

                    with detail_col1:
                        st.markdown("**📞 Kontakt**")
                        st.write(f"Tel: {company.get('telefon', 'N/A')}")
                        st.write(f"Email: {company.get('email', 'N/A')}")

                        if company.get("website"):
                            st.markdown(f"**🌐 [Website]({company['website']})**")

                    with detail_col2:
                        st.markdown("**🏢 Branche**")
                        st.write(company.get("branche", "N/A"))

                        if company.get("llm_analysis"):
                            llm = company["llm_analysis"]
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
                        fieldnames = [
                            "name",
                            "strasse",
                            "plz",
                            "ort",
                            "bundesland",
                            "telefon",
                            "email",
                            "website",
                            "branche",
                        ]
                        if filtered_results[0].get("llm_analysis"):
                            fieldnames.extend(["llm_branch", "llm_services", "llm_confidence"])

                        writer = csv.DictWriter(output, fieldnames=fieldnames)
                        writer.writeheader()

                        for r in filtered_results:
                            row = {
                                k: r.get(k, "")
                                for k in [
                                    "name",
                                    "strasse",
                                    "plz",
                                    "ort",
                                    "bundesland",
                                    "telefon",
                                    "email",
                                    "website",
                                    "branche",
                                ]
                            }
                            if r.get("llm_analysis"):
                                llm = r["llm_analysis"]
                                row["llm_branch"] = llm.get("branch", "")
                                row["llm_services"] = ", ".join(llm.get("services", []))
                                row["llm_confidence"] = llm.get("confidence", 0)
                            writer.writerow(row)

                        st.download_button(
                            label="⬇️ CSV herunterladen",
                            data=output.getvalue(),
                            file_name=f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
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
                        mime="application/json",
                    )
                except Exception as e:
                    st.error(f"Export fehlgeschlagen: {e}")
