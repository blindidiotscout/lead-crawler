"""
Export Page - Daten exportieren
Export in verschiedene Formate
"""

import csv
import io
from datetime import datetime

import streamlit as st

from lead_crawler.pipelines import ExportConfig, ExportPipeline

# Page config
st.set_page_config(
    page_title="Export - Lead Crawler",
    page_icon="📥",
    layout="wide"
)

# Session State
if 'search_results' not in st.session_state:
    st.session_state.search_results = []

st.title("📥 Daten exportieren")

if not st.session_state.search_results:
    st.info("ℹ️ Starte zuerst eine Suche auf der 🔎 Suche-Seite um Daten zu exportieren")
    st.stop()

results = st.session_state.search_results

st.subheader("Export-Optionen")

# Export-Format
export_col1, export_col2 = st.columns(2)

with export_col1:
    export_format = st.selectbox(
        "Dateiformat",
        ["CSV", "JSON", "JSONL", "Excel (xlsx)"]
    )

with export_col2:
    include_llm = st.checkbox("LLM-Analyse inkludieren", value=True)
    include_score = st.checkbox("Scoring inkludieren", value=True)

# Felder-Auswahl
st.markdown("---")
st.subheader("Felder auswählen")

all_fields = ['name', 'strasse', 'plz', 'ort', 'bundesland', 'telefon', 'email', 'website', 'branche']
if include_llm:
    all_fields.extend(['llm_branch', 'llm_services', 'llm_confidence'])
if include_score:
    all_fields.extend(['score_total', 'score_grade', 'priority'])

selected_fields = st.multiselect(
    "Zu exportierende Felder",
    all_fields,
    default=all_fields
)

# Filter-Optionen
st.markdown("---")
st.subheader("Filter")

filter_col1, filter_col2 = st.columns(2)

with filter_col1:
    min_score = st.slider("Mindest-Score", 0, 100, 0)

with filter_col2:
    priority_filter = st.multiselect(
        "Priorität",
        ["HIGH", "MEDIUM", "LOW"],
        ["HIGH", "MEDIUM", "LOW"]
    )

# Vorschau
st.markdown("---")
st.subheader("📋 Vorschau")

# Filter anwenden
filtered_results = results
if min_score > 0:
    filtered_results = [r for r in filtered_results if r.get('score_total', 0) >= min_score]
# Priority filter would need actual priority field in data

st.write(f"**{len(filtered_results)}** von {len(results)} Unternehmen werden exportiert")

# Vorschau-Tabelle
if filtered_results:
    preview_data = []
    for r in filtered_results[:10]:  # Nur erste 10 für Vorschau
        row = {k: r.get(k, 'N/A') for k in selected_fields[:5]}  # Nur erste 5 Felder
        preview_data.append(row)

    st.dataframe(preview_data, use_container_width=True, hide_index=True)

    if len(filtered_results) > 10:
        st.info(f"... und {len(filtered_results) - 10} weitere")

# Export-Button
st.markdown("---")

if st.button("🚀 Export starten", type="primary"):
    with st.spinner("Export läuft..."):
        try:
            # Export-Pipeline verwenden
            config = ExportConfig(
                output_format=export_format.lower().replace(' (xlsx)', ''),
                fields=selected_fields if selected_fields else None,
                min_score=min_score
            )

            # In Export Pipeline umwandeln
            from lead_crawler.models import Company
            companies = []
            for r in filtered_results:
                # Dict zu Company konvertieren (vereinfacht)
                company = Company(name=r.get('name', 'N/A'))
                if r.get('plz'):
                    company.address.plz = r.get('plz')
                if r.get('ort'):
                    company.address.ort = r.get('ort')
                companies.append(company)

            # Export durchführen
            pipeline = ExportPipeline()
            result = pipeline.export(companies, config)

            # Download
            if result.output_path:
                st.success(f"✅ {result.exported_companies} Unternehmen exportiert!")

                # Datei lesen
                with open(result.output_path, 'rb') as f:
                    file_data = f.read()

                filename = f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                if export_format == "CSV":
                    filename += ".csv"
                    mime = "text/csv"
                elif export_format == "JSON":
                    filename += ".json"
                    mime = "application/json"
                elif export_format == "JSONL":
                    filename += ".jsonl"
                    mime = "application/jsonl"
                else:
                    filename += ".xlsx"
                    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

                st.download_button(
                    label=f"⬇️ {export_format} herunterladen",
                    data=file_data,
                    file_name=filename,
                    mime=mime
                )
            else:
                st.error("Export fehlgeschlagen: Keine Ausgabedatei")

        except Exception as e:
            st.error(f"Export fehlgeschlagen: {str(e)}")

# Alternative: Direkter CSV-Export (ohne Pipeline)
st.markdown("---")
st.subheader(" Schnell-Export (CSV)")

if st.button("📥 Direkt als CSV exportieren"):
    try:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=selected_fields)
        writer.writeheader()

        for r in filtered_results:
            row = {k: str(r.get(k, '')) for k in selected_fields}
            writer.writerow(row)

        st.download_button(
            label="⬇️ CSV herunterladen",
            data=output.getvalue(),
            file_name=f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    except Exception as e:
        st.error(f"Export fehlgeschlagen: {str(e)}")
