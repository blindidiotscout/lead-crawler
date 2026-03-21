# Legacy Code

Dieser Ordner enthält die **ursprünglichen Module** vor dem Refactoring.

## ⚠️ Wichtig

**Diese Dateien werden nicht mehr aktiv verwendet!**

Die neue Package-Struktur befindet sich in `src/lead_crawler/`:

## Migration Map

| Legacy Datei | Neue Location |
|-------------|---------------|
| `scraper.py` | `lead_crawler/crawlers/wko.py` |
| `enhanced_scraper.py` | `lead_crawler/pipelines/lead_analysis.py` |
| `scoring.py` | `lead_crawler/models/scoring.py` |
| `enhanced_scoring.py` | `lead_crawler/models/scoring.py` |
| `llm_pipeline.py` | `lead_crawler/pipelines/lead_analysis.py` |
| `llm_analyzer.py` | `lead_crawler/services/llm_client.py` |
| `website_crawler.py` | `lead_crawler/services/website_extractor.py` |
| `analysis_cache.py` | `lead_crawler/services/cache.py` |
| `plz_radius.py` | `lead_crawler/services/plz_service.py` |
| `csv_export.py` | `lead_crawler/pipelines/export.py` |
| `ecoplus_spider.py` | `lead_crawler/crawlers/ecoplus.py` (optional) |

## Warum aufbewahren?

- Referenz für Migration
- Fallback falls etwas fehlt
- Historie der Code-Entwicklung

## Entfernen

Wenn die neue Package-Struktur vollständig getestet ist, kann dieser Ordner gelöscht werden:

```bash
rm -rf legacy/
```

---

*Created: 2026-03-21*
*Migrated during Phase 1-8 Refactoring*