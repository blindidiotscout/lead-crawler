"""
CSV Export Module
Exportiert Unternehmensdaten als CSV

Features:
- Flexible Spaltenauswahl
- LLM-Analyse-Daten
- Scoring-Integration
- Deduplizierung
- Multiple Quellen mergen
"""

import csv
from typing import List, Dict, Optional, Set
from pathlib import Path
from datetime import datetime


# Standard-Spalten für CSV-Export
DEFAULT_COLUMNS = [
    'name',
    'strasse',
    'plz',
    'ort',
    'bundesland',
    'website',
    'telefon',
    'email',
    'branche',
    'quelle',
]

# Erweiterte Spalten mit LLM-Analyse
LLM_COLUMNS = [
    'llm_branch',
    'llm_sub_branches',
    'llm_services',
    'llm_target_market',
    'llm_size_hint',
    'llm_keywords',
    'llm_confidence',
    'llm_cached',
]

# Scoring-Spalten
SCORING_COLUMNS = [
    'score_total',
    'score_grade',
    'score_priority',
]


def flatten_company(company: Dict) -> Dict:
    """
    Flacht ein Unternehmen-Dict auf für CSV-Export
    
    Extrahiert verschachtelte LLM-Analyse in flache Spalten
    
    Args:
        company: Unternehmens-Dict (von Spider oder Pipeline)
    
    Returns:
        Flaches Dict mit allen Spalten
    """
    flat = {}
    
    # Basis-Felder
    flat['name'] = company.get('name', '')
    flat['strasse'] = company.get('street', company.get('strasse', ''))
    flat['plz'] = company.get('plz', '')
    flat['ort'] = company.get('ort', '')
    flat['bundesland'] = company.get('bundesland', '')
    flat['website'] = company.get('website', '')
    flat['telefon'] = company.get('telefon', company.get('phone', ''))
    flat['email'] = company.get('email', '')
    flat['branche'] = company.get('branche', '')
    flat['quelle'] = company.get('source', company.get('quelle', ''))
    
    # LLM-Analyse (falls vorhanden)
    llm = company.get('llm_analysis', {})
    if llm and isinstance(llm, dict):
        flat['llm_branch'] = llm.get('branch', '')
        
        sub_branches = llm.get('sub_branches', [])
        if isinstance(sub_branches, list):
            flat['llm_sub_branches'] = '; '.join(sub_branches)
        else:
            flat['llm_sub_branches'] = ''
        
        services = llm.get('services', [])
        if isinstance(services, list):
            flat['llm_services'] = '; '.join(services[:5])  # Max 5
        else:
            flat['llm_services'] = ''
        
        flat['llm_target_market'] = llm.get('target_market', '')
        flat['llm_size_hint'] = llm.get('company_size_hint', '')
        
        keywords = llm.get('keywords', [])
        if isinstance(keywords, list):
            flat['llm_keywords'] = '; '.join(keywords[:10])  # Max 10
        else:
            flat['llm_keywords'] = ''
        
        flat['llm_confidence'] = llm.get('confidence', 0)
        flat['llm_cached'] = 'ja' if company.get('llm_cached') else 'nein'
    else:
        # Keine LLM-Analyse
        for col in LLM_COLUMNS:
            flat[col] = ''
    
    # Scoring (falls vorhanden)
    score = company.get('score', {})
    if score and isinstance(score, dict):
        flat['score_total'] = score.get('total_score', 0)
        flat['score_grade'] = score.get('grade', '')
        flat['score_priority'] = score.get('priority', '')
    else:
        for col in SCORING_COLUMNS:
            flat[col] = ''
    
    # Zeitstempel
    flat['exportiert_am'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    return flat


def export_to_csv(companies: List[Dict],
                  output_path: str,
                  columns: Optional[List[str]] = None,
                  include_llm: bool = True,
                  include_scoring: bool = True,
                  dedup: bool = True) -> int:
    """
    Exportiert Unternehmen als CSV
    
    Args:
        companies: Liste von Unternehmen
        output_path: Pfad zur CSV-Datei
        columns: Spalten (None = Standard)
        include_llm: LLM-Analyse-Spalten inkludieren
        include_scoring: Scoring-Spalten inkludieren
        dedup: Duplikate entfernen
    
    Returns:
        Anzahl exportierter Unternehmen
    
    Example:
        from src.csv_export import export_to_csv
        
        companies = run_enhanced_spider(plz="2351")
        count = export_to_csv(companies, "output.csv")
    """
    # Spalten festlegen
    if columns is None:
        columns = DEFAULT_COLUMNS.copy()
        if include_llm:
            columns.extend(LLM_COLUMNS)
        if include_scoring:
            columns.extend(SCORING_COLUMNS)
        columns.append('exportiert_am')
    
    # Deduplizierung
    if dedup:
        seen: Set[tuple] = set()
        unique = []
        for c in companies:
            key = (c.get('name', '').lower().strip(),
                   c.get('plz', ''),
                   c.get('street', c.get('strasse', '')).lower().strip())
            if key not in seen:
                seen.add(key)
                unique.append(c)
        companies = unique
    
    # Flatten
    rows = [flatten_company(c) for c in companies]
    
    # CSV schreiben
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    
    return len(rows)


def merge_and_export(sources: Dict[str, List[Dict]],
                     output_path: str,
                     columns: Optional[List[str]] = None,
                     include_llm: bool = True,
                     include_scoring: bool = True) -> Dict[str, int]:
    """
    Merged mehrere Quellen und exportiert als CSV
    
    Args:
        sources: Dict mit Quellname → Liste von Unternehmen
        output_path: Pfad zur CSV-Datei
        columns: Spalten
        include_llm: LLM-Analyse inkludieren
        include_scoring: Scoring inkludieren
    
    Returns:
        Dict mit Statistiken: {'total': N, 'wko': N, 'ecoplus': N, ...}
    
    Example:
        from src.csv_export import merge_and_export
        from src.scraper import run_spider_radius
        from src.ecoplus_spider import run_ecoplus_spider
        
        wko = run_spider_radius("2351", radius_km=20)
        ecoplus = run_ecoplus_spider()
        
        stats = merge_and_export(
            {'wko': wko, 'ecoplus': ecoplus},
            "merged_output.csv"
        )
    """
    all_companies = []
    stats = {'total': 0}
    
    for source_name, companies in sources.items():
        # Quelle markieren
        for c in companies:
            c['quelle'] = source_name
        all_companies.extend(companies)
        stats[source_name] = len(companies)
    
    # Export
    count = export_to_csv(
        all_companies,
        output_path,
        columns=columns,
        include_llm=include_llm,
        include_scoring=include_scoring,
        dedup=True
    )
    
    stats['total'] = count
    stats['duplicates_removed'] = len(all_companies) - count
    
    return stats


def export_summary(companies: List[Dict],
                   output_path: str) -> Dict[str, any]:
    """
    Erstellt eine Zusammenfassung der Unternehmen
    
    Args:
        companies: Liste von Unternehmen
        output_path: Pfad zur Zusammenfassungs-Datei (JSON)
    
    Returns:
        Zusammenfassungs-Dict
    
    Example:
        from src.csv_export import export_summary
        
        companies = run_enhanced_spider(plz="2351")
        summary = export_summary(companies, "summary.json")
        
        print(f"Gefunden: {summary['total']} Unternehmen")
        print(f"Top Branchen: {summary['top_branches']}")
    """
    import json
    
    summary = {
        'total': len(companies),
        'exported_at': datetime.now().isoformat(),
        'sources': {},
        'branches': {},
        'llm_analyzed': 0,
        'llm_cached': 0,
        'with_website': 0,
        'with_email': 0,
        'with_phone': 0,
    }
    
    for c in companies:
        # Quellen
        source = c.get('source', c.get('quelle', 'unknown'))
        summary['sources'][source] = summary['sources'].get(source, 0) + 1
        
        # Branchen
        branche = c.get('branche', '')
        if branche:
            summary['branches'][branche] = summary['branches'].get(branche, 0) + 1
        
        # LLM
        if c.get('llm_analysis'):
            summary['llm_analyzed'] += 1
            if c.get('llm_cached'):
                summary['llm_cached'] += 1
            
            # LLM-Branche
            llm_branch = c['llm_analysis'].get('branch', '')
            if llm_branch:
                summary['branches'][f'[LLM] {llm_branch}'] = \
                    summary['branches'].get(f'[LLM] {llm_branch}', 0) + 1
        
        # Kontakte
        if c.get('website'):
            summary['with_website'] += 1
        if c.get('email'):
            summary['with_email'] += 1
        if c.get('telefon') or c.get('phone'):
            summary['with_phone'] += 1
    
    # Top Branchen
    if summary['branches']:
        sorted_branches = sorted(summary['branches'].items(), 
                                  key=lambda x: x[1], reverse=True)
        summary['top_branches'] = dict(sorted_branches[:10])
    else:
        summary['top_branches'] = {}
    
    # Schreiben
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    return summary


# Convenience-Funktion für Kommandozeile
def main():
    """CLI Entry Point"""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description='CSV Export für Lead Crawler')
    parser.add_argument('--input', '-i', required=True,
                        help='Input JSON-Datei (von Spider)')
    parser.add_argument('--output', '-o', default='output.csv',
                        help='Output CSV-Datei')
    parser.add_argument('--summary', '-s', default=None,
                        help='Summary JSON-Datei (optional)')
    parser.add_argument('--no-llm', action='store_true',
                        help='LLM-Spalten nicht inkludieren')
    parser.add_argument('--no-scoring', action='store_true',
                        help='Scoring-Spalten nicht inkludieren')
    parser.add_argument('--no-dedup', action='store_true',
                        help='Duplikate nicht entfernen')
    
    args = parser.parse_args()
    
    # Input laden
    import json
    with open(args.input, 'r', encoding='utf-8') as f:
        companies = [json.loads(line) for line in f if line.strip()]
    
    print(f"Geladen: {len(companies)} Unternehmen")
    
    # Export
    count = export_to_csv(
        companies,
        args.output,
        include_llm=not args.no_llm,
        include_scoring=not args.no_scoring,
        dedup=not args.no_dedup
    )
    
    print(f"Exportiert: {count} Unternehmen → {args.output}")
    
    # Summary
    if args.summary:
        summary = export_summary(companies, args.summary)
        print(f"Summary: {args.summary}")
        print(f"  Top Branchen: {list(summary['top_branches'].keys())[:5]}")


if __name__ == "__main__":
    main()