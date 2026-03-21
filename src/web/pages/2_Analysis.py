"""
Analysis Page - Statistiken und Analyse
Visualisierung der Suchergebnisse
"""

from datetime import datetime

import streamlit as st

# Page config
st.set_page_config(page_title="Analyse - Lead Crawler", page_icon="📊", layout="wide")

# Session State
if "search_results" not in st.session_state:
    st.session_state.search_results = []

st.title("📊 Analyse & Statistiken")

if not st.session_state.search_results:
    st.info("ℹ️ Starte zuerst eine Suche auf der 🔎 Suche-Seite um Statistiken zu sehen")
    st.stop()

results = st.session_state.search_results

# Metriken
st.subheader("📈 Übersicht")

metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)

with metrics_col1:
    st.metric("Gefunden", len(results))

with metrics_col2:
    websites = sum(1 for r in results if r.get("website"))
    st.metric("Mit Website", f"{websites} ({websites/len(results)*100:.0f}%)")

with metrics_col3:
    llm_done = sum(1 for r in results if r.get("llm_analysis"))
    st.metric("LLM-Analysiert", f"{llm_done} ({llm_done/len(results)*100:.0f}%)")

with metrics_col4:
    cached = sum(1 for r in results if r.get("llm_cached"))
    st.metric("Aus Cache", cached)

st.markdown("---")

# Branchen-Verteilung
st.subheader("🏭 Branchen-Verteilung")

branches = {}
for r in results:
    b = r.get("branche", "Unbekannt")
    branches[b] = branches.get(b, 0) + 1

if branches:
    import pandas as pd

    branch_df = pd.DataFrame(
        [
            {"Branche": k, "Anzahl": v}
            for k, v in sorted(branches.items(), key=lambda x: x[1], reverse=True)
        ]
    )
    st.bar_chart(branch_df.set_index("Branche"))

    # Top Branchen
    st.markdown("**Top 5 Branchen:**")
    top_branches = sorted(branches.items(), key=lambda x: x[1], reverse=True)[:5]
    for branch, count in top_branches:
        st.write(f"- {branch}: {count} Unternehmen")

# Score-Verteilung
if any("score_total" in r for r in results):
    st.markdown("---")
    st.subheader("⭐ Score-Verteilung")

    scores = {}
    for r in results:
        if "score_total" in r:
            g = r.get("score_grade", "N/A")
            scores[g] = scores.get(g, 0) + 1

    if scores:
        score_df = pd.DataFrame([{"Grade": k, "Anzahl": v} for k, v in sorted(scores.items())])
        st.bar_chart(score_df.set_index("Grade"))

        # Score-Kategorien
        st.markdown("**Score-Kategorien:**")
        st.write("- 🟢 **A (80-100)**: High-Value Leads")
        st.write("- 🟡 **B (60-79)**: Medium-Value Leads")
        st.write("- 🟠 **C (40-59)**: Low-Value Leads")
        st.write("- 🔴 **D/F (<40)**: Ungeeignet")

# Website-Verfügbarkeit
st.markdown("---")
st.subheader("🌐 Website-Verfügbarkeit")

has_website = sum(1 for r in results if r.get("website"))
no_website = len(results) - has_website

website_df = pd.DataFrame(
    [
        {"Kategorie": "Mit Website", "Anzahl": has_website},
        {"Kategorie": "Ohne Website", "Anzahl": no_website},
    ]
)
st.bar_chart(website_df.set_index("Kategorie"))

# Kontaktdaten-Statistik
st.markdown("---")
st.subheader("📞 Kontaktdaten-Statistik")

contact_stats = {
    "Telefon": sum(1 for r in results if r.get("telefon")),
    "Email": sum(1 for r in results if r.get("email")),
    "Website": sum(1 for r in results if r.get("website")),
}

contact_df = pd.DataFrame([{"Kategorie": k, "Anzahl": v} for k, v in contact_stats.items()])
st.bar_chart(contact_df.set_index("Kategorie"))

# Letzte Suchen (Historie)
st.markdown("---")
st.subheader("📜 Such-Historie")

if st.session_state.get("last_search"):
    last = st.session_state.last_search
    st.write(f"**Letzte Suche:** {last.get('plz', 'N/A')}")
    st.write(f"**Radius:** {last.get('radius', 'N/A')} km")
    st.write(f"**Zeitpunkt:** {last.get('timestamp', 'N/A')}")

# Export der Analyse
st.markdown("---")
st.subheader("📥 Analyse exportieren")

export_col1, export_col2 = st.columns(2)

with export_col1:
    if st.button("📊 Branchen-Statistik als CSV"):
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Branche", "Anzahl", "Prozent"])
        total = sum(branches.values())
        for branch, count in sorted(branches.items(), key=lambda x: x[1], reverse=True):
            writer.writerow([branch, count, f"{count/total*100:.1f}%"])

        st.download_button(
            label="⬇️ CSV herunterladen",
            data=output.getvalue(),
            file_name=f"branchen_statistik_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )

with export_col2:
    if st.button("📋 Zusammenfassung als Text"):
        summary = f"""# Lead Crawler Analyse
        
## Übersicht
- Gefundene Unternehmen: {len(results)}
- Mit Website: {has_website} ({has_website/len(results)*100:.0f}%)
- LLM-analysiert: {llm_done} ({llm_done/len(results)*100:.0f}%)

## Top 5 Branchen
"""
        for branch, count in top_branches:
            summary += f"- {branch}: {count}\n"

        st.download_button(
            label="⬇️ Text herunterladen",
            data=summary,
            file_name=f"zusammenfassung_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
        )
