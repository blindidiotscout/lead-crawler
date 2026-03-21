"""
UI Components for Streamlit Pages
Wiederverwendbare UI-Elemente
"""

import streamlit as st
from typing import Dict, List, Any, Optional


def render_lead_card(company: Dict[str, Any], show_details: bool = False) -> None:
    """
    Rendert eine Lead-Card für ein Unternehmen.
    
    Args:
        company: Unternehmensdaten als Dict
        show_details: Ob Details angezeigt werden sollen
    """
    st.markdown(f"""
    <div style='background-color: #f8f9fa; border-radius: 10px; 
                padding: 1.5rem; margin: 1rem 0; 
                border-left: 4px solid #4CAF50;'>
        <h3>{company.get('name', 'N/A')}</h3>
        <p>📍 {company.get('strasse', '')}, {company.get('plz', '')} {company.get('ort', '')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    if show_details:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📞 Kontakt**")
            st.write(f"Tel: {company.get('telefon', 'N/A')}")
            st.write(f"Email: {company.get('email', 'N/A')}")
            if company.get('website'):
                st.markdown(f"**🌐 [Website]({company['website']})**")
        
        with col2:
            st.markdown("**🏢 Branche**")
            st.write(company.get('branche', 'N/A'))
            
            if company.get('llm_analysis'):
                llm = company['llm_analysis']
                st.markdown("**🤖 LLM-Analyse**")
                st.write(f"Branche: {llm.get('branch', 'N/A')}")
                st.write(f"Services: {', '.join(llm.get('services', []))[:50]}...")
                st.write(f"Confidence: {llm.get('confidence', 0):.0%}")


def render_score_badge(score: float) -> str:
    """
    Gibt ein farbiges Score-Badge zurück.
    
    Args:
        score: Score-Wert (0-100)
        
    Returns:
        HTML für das Badge
    """
    if score >= 80:
        color = "#4CAF50"  # Grün
        grade = "A"
    elif score >= 60:
        color = "#FF9800"  # Orange
        grade = "B"
    elif score >= 40:
        color = "#FFC107"  # Gelb
        grade = "C"
    else:
        color = "#f44336"  # Rot
        grade = "D"
    
    return f"""
    <span style='background-color: {color}; color: white; 
                 padding: 0.25rem 0.5rem; border-radius: 4px; 
                 font-weight: bold;'>
        {grade} ({score:.0f}%)
    </span>
    """


def render_metrics_grid(metrics: Dict[str, Any], columns: int = 4) -> None:
    """
    Rendert ein Grid von Metriken.
    
    Args:
        metrics: Dict mit Label -> Value
        columns: Anzahl der Spalten
    """
    cols = st.columns(columns)
    
    for idx, (label, value) in enumerate(metrics.items()):
        with cols[idx % columns]:
            st.metric(label, value)


def render_filter_sidebar(
    branches: List[str],
    show_score_filter: bool = True,
    show_website_filter: bool = True
) -> Dict[str, Any]:
    """
    Rendert Filter in der Sidebar.
    
    Args:
        branches: Liste der verfügbaren Branchen
        show_score_filter: Ob Score-Filter angezeigt werden soll
        show_website_filter: Ob Website-Filter angezeigt werden soll
        
    Returns:
        Dict mit Filter-Werten
    """
    filters = {}
    
    with st.sidebar:
        st.markdown("### 🔍 Filter")
        
        if branches:
            filters['branches'] = st.multiselect(
                "Branche",
                branches,
                default=[]
            )
        
        if show_score_filter:
            filters['min_score'] = st.slider(
                "Min. Score",
                min_value=0,
                max_value=100,
                value=0
            )
        
        if show_website_filter:
            filters['has_website'] = st.checkbox(
                "Nur mit Website",
                value=False
            )
    
    return filters


def render_export_buttons(data: List[Dict], filename_prefix: str = "export") -> None:
    """
    Rendert Export-Buttons für CSV und JSON.
    
    Args:
        data: Zu exportierende Daten
        filename_prefix: Prefix für den Dateinamen
    """
    from datetime import datetime
    import json
    import csv
    import io
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 CSV"):
            output = io.StringIO()
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
                
                st.download_button(
                    label="⬇️ CSV herunterladen",
                    data=output.getvalue(),
                    file_name=f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
    
    with col2:
        if st.button("📥 JSON"):
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            st.download_button(
                label="⬇️ JSON herunterladen",
                data=json_str,
                file_name=f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )


def render_status_badge(status: str) -> str:
    """
    Gibt ein farbiges Status-Badge zurück.
    
    Args:
        status: Status-String (running, completed, failed, pending)
        
    Returns:
        HTML für das Badge
    """
    colors = {
        "running": "#2196F3",
        "completed": "#4CAF50",
        "failed": "#f44336",
        "pending": "#9E9E9E"
    }
    
    color = colors.get(status.lower(), "#9E9E9E")
    
    return f"""
    <span style='background-color: {color}; color: white; 
                 padding: 0.25rem 0.5rem; border-radius: 4px; 
                 font-weight: bold;'>
        {status.upper()}
    </span>
    """


def render_progress_bar(current: int, total: int, label: str = "Fortschritt") -> None:
    """
    Rendert eine Fortschrittsanzeige.
    
    Args:
        current: Aktueller Wert
        total: Maximaler Wert
        label: Beschriftung
    """
    progress = current / total if total > 0 else 0
    st.progress(progress, text=f"{label}: {current}/{total} ({progress*100:.0f}%)")


def render_company_table(
    companies: List[Dict],
    show_score: bool = True,
    show_llm: bool = True,
    max_rows: int = 100
) -> None:
    """
    Rendert eine Tabelle von Unternehmen.
    
    Args:
        companies: Liste von Unternehmen
        show_score: Ob Score-Spalte angezeigt werden soll
        show_llm: Ob LLM-Spalte angezeigt werden soll
        max_rows: Maximale Anzahl anzuzeigender Zeilen
    """
    import pandas as pd
    
    # Limitieren
    companies = companies[:max_rows]
    
    # Tabelle aufbauen
    rows = []
    for c in companies:
        row = {
            'Name': c.get('name', 'N/A'),
            'Ort': f"{c.get('plz', '')} {c.get('ort', '')}",
            'Branche': c.get('branche', 'N/A')
        }
        
        if show_score and 'score_total' in c:
            row['Score'] = f"{c['score_total']}/100"
        
        if show_llm:
            row['LLM'] = '✅' if c.get('llm_analysis') else '❌'
        
        rows.append(row)
    
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)


def show_success_toast(message: str) -> None:
    """Zeigt eine Success-Toast-Nachricht."""
    st.toast(f"✅ {message}", icon="✅")


def show_error_toast(message: str) -> None:
    """Zeigt eine Error-Toast-Nachricht."""
    st.toast(f"❌ {message}", icon="❌")


def show_info_toast(message: str) -> None:
    """Zeigt eine Info-Toast-Nachricht."""
    st.toast(f"ℹ️ {message}", icon="ℹ️")


__all__ = [
    'render_lead_card',
    'render_score_badge',
    'render_metrics_grid',
    'render_filter_sidebar',
    'render_export_buttons',
    'render_status_badge',
    'render_progress_bar',
    'render_company_table',
    'show_success_toast',
    'show_error_toast',
    'show_info_toast',
]