#!/usr/bin/env python3
"""
Test: Enhanced Spider + CSV Export mit echten Daten
"""
import sys
sys.path.insert(0, '/home/clawbert/.openclaw/workspace/projects/lead-crawler')

from src.enhanced_scraper import run_enhanced_spider
from src.csv_export import export_to_csv, export_summary
from datetime import datetime

print("=" * 60)
print("TEST: Enhanced Spider + CSV Export")
print("=" * 60)

# Spider laufen lassen
print(f"\n🕷️  Crawle PLZ 2351 (Guntramsdorf) mit LLM...")
print(f"   Start: {datetime.now().strftime('%H:%M:%S')}")

results = run_enhanced_spider(
    plz="2351",
    use_llm=True,
    llm_model="qwen2.5:7b",
    analyze_websites=True,
    max_websites_per_batch=10  # Mehr Firmen
)

print(f"   Ende: {datetime.now().strftime('%H:%M:%S')}")
print(f"\n📊 Gefunden: {len(results)} Unternehmen")

# CSV Export
print(f"\n📁 Exportiere nach CSV...")
output_file = "/home/clawbert/.openclaw/workspace/projects/lead-crawler/output/leads.csv"
summary_file = "/home/clawbert/.openclaw/workspace/projects/lead-crawler/output/summary.json"

count = export_to_csv(results, output_file, include_llm=True, include_scoring=True)
print(f"   Exportiert: {count} Zeilen")

# Summary
summary = export_summary(results, summary_file)
print(f"\n📈 Zusammenfassung:")
print(f"   Gesamt: {summary['total']}")
print(f"   Quellen: {summary['sources']}")
print(f"   Mit Website: {summary['with_website']}")
print(f"   LLM analysiert: {summary['llm_analyzed']}")
print(f"   Aus Cache: {summary['llm_cached']}")

if summary['top_branches']:
    print(f"\n   Top Branchen:")
    for branche, count in list(summary['top_branches'].items())[:5]:
        print(f"     - {branche}: {count}")

# Zeige CSV-Ausschnitt
print(f"\n📄 CSV-Vorschau (erste 5 Zeilen):")
with open(output_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines[:6]):
        # Kürze für Lesbarkeit
        if i == 0:
            print(f"   HEADER: {line.strip()[:80]}...")
        else:
            parts = line.strip().split(',')
            name = parts[0] if len(parts) > 0 else ''
            branche = parts[10] if len(parts) > 10 else ''
            llm_branch = parts[11] if len(parts) > 11 else ''
            print(f"   {i}. {name[:30]:<30} | {branche[:15]:<15} | LLM: {llm_branch[:15]}")

print(f"\n✅ Fertig!")
print(f"   CSV: {output_file}")
print(f"   Summary: {summary_file}")