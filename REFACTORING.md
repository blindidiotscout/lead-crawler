# Lead Crawler Refactoring TODO

**Branch:** `refactoring` (based on `dev`)
**Started:** 2026-03-21

---

## 🎯 Übersicht

Refactoring des Lead-Crawlers für bessere Wartbarkeit, Testbarkeit und Erweiterbarkeit.

---

## ✅ Phase 1: Models Extrahieren

**Priorität:** Hoch | **Status:** ✅ Done

### Tasks

- [x] `src/lead_crawler/models/__init__.py` erstellen
- [x] `src/lead_crawler/models/company.py` - Company Domain Model
  - [x] `Company` dataclass mit allen Feldern
  - [x] `Address` dataclass
  - [x] `ContactInfo` dataclass
  - [x] `CompanyMetadata` dataclass
  - [x] `from_dict()` und `to_dict()` Methoden
  - [x] `CompanySource` Enum
- [x] `src/lead_crawler/models/analysis.py` - LLM Analysis Models
  - [x] `BranchAnalysis` dataclass
  - [x] `LLMAnalysisResult` dataclass
  - [x] `CacheEntry` dataclass
  - [x] `TargetMarket` und `CompanySize` Enums
  - [x] Validierungsmethoden
- [x] `src/lead_crawler/models/scoring.py` - Scoring Models
  - [x] `LeadScore` dataclass
  - [x] `ScoreBreakdown` dataclass
  - [x] `ScoreGrade` und `Priority` Enums
  - [x] Factory-Methode `create()`
- [x] `src/lead_crawler/models/plz.py` - PLZ Models
  - [x] `PLZInfo` dataclass
  - [x] `PLZCoordinate` dataclass
  - [x] `PLZSearchResult` dataclass
  - [x] `Bundesland` Enum
  - [x] Helper Functions `plz_to_bundesland()`, `is_valid_plz()`
- [x] `tests/unit/test_models.py` - 31 Tests, alle grün
- [ ] Alte Code-Stellen auf neue Models umstellen (Phase 4)

---

## ✅ Phase 2: Config Zentralisieren

**Priorität:** Hoch | **Status:** ✅ Done

### Tasks

- [x] `config/settings.py` erstellen (dataclass-based) → `src/lead_crawler/config.py`
- [x] Umgebungsvariablen-Loading mit `python-dotenv`
- [x] Alle hardcoded URLs/Pfade in Settings umwandeln
  - [x] `OLLAMA_URL` → `settings.ollama.url`
  - [x] `OLLAMA_MODEL` → `settings.ollama.model`
  - [x] Cache-Pfade → `settings.cache.db_path`
  - [x] PLZ-DB Pfad → `settings.plz.db_path`
- [x] `.env.example` erstellen
- [x] Settings in allen Services injecten (via `get_settings()`)
- [x] 19 Unit Tests für Config
- [ ] Alte Module auf Settings umstellen (Phase 4)

---

## ✅ Phase 3: Services Separieren

**Priorität:** Mittel | **Status:** ✅ Done

### Tasks

- [x] `src/lead_crawler/services/__init__.py` erstellen
- [x] `src/lead_crawler/services/cache.py`
  - [x] `CacheService` Protocol definieren
  - [x] `SQLiteCache` Implementierung
  - [x] Methoden: `get()`, `set()`, `delete()`, `exists()`, `clear()`, `get_stats()`
  - [x] TTL-Support, URL-Normalisierung
- [x] `src/lead_crawler/services/llm_client.py`
  - [x] `LLMClient` ABC (abstrakte Basisklasse)
  - [x] `OllamaClient` Implementierung mit Retry-Logic
  - [x] `MockLLMClient` für Tests
  - [x] `analyze_branch()` Methode für Branchen-Analyse
- [x] `src/lead_crawler/services/website_extractor.py`
  - [x] `WebsiteExtractor` Klasse
  - [x] Extrahiert Titel, Meta, Haupttext, About, Services, Kontakt
  - [x] Rate-Limiting, Robots.txt-Check
  - [x] `WebsiteContent` Dataclass
- [x] `src/lead_crawler/services/plz_service.py`
  - [x] `PLZService` Klasse
  - [x] `PLZDatabase` für SQLite-Speicherung
  - [x] `HaversineCalculator` für Distanzberechnung
  - [x] `find_in_radius()`, `validate_plz()`, etc.
- [x] Singleton Pattern via `get_*()` Funktionen
- [x] 36 Unit Tests für alle Services

---

## ✅ Phase 4: Crawlers Refaktorieren

**Priorität:** Mittel | **Status:** ✅ Done

### Tasks

- [x] `src/lead_crawler/crawlers/__init__.py` erstellen
- [x] `src/lead_crawler/crawlers/base.py`
  - [x] `BaseCrawler` abstrakte Klasse
  - [x] `CrawlerResult` Dataclass
  - [x] `CrawlerStatus` Enum
  - [x] Gemeinsame Parsing-Helpers (`_normalize_phone`, `_normalize_email`, etc.)
  - [x] `create_company()` Factory-Methode
  - [x] Einheitliche Error-Handling
- [x] `src/lead_crawler/crawlers/wko.py`
  - [x] `WKOCrawler` von Base erben
  - [x] Nur WKO-spezifische Logik
  - [x] `crawl()` und `crawl_radius()` Methoden
  - [x] Output als `Company` Model
  - [x] `_parse_item()` Implementation
- [x] `src/lead_crawler/runners/__init__.py` erstellen
- [x] `src/lead_crawler/runners/spider_runner.py`
  - [x] `SpiderRunner` Klasse
  - [x] `RunConfig` und `RunResult` Dataclasses
  - [x] `run()` und `run_with_config()` Methoden
  - [x] Output in JSON/JSONL/CSV
  - [x] Convenience-Funktionen `run_wko()`, `run_wko_radius()`
- [x] `CrawlerFactory` für Crawler-Registry
- [x] 23 Unit Tests für Crawlers
- [ ] Alte `scraper.py` und `enhanced_scraper.py` als Legacy behalten (Phase 5: Migration)

---

## ✅ Phase 5: Pipelines Organisieren

**Priorität:** Niedrig | **Status:** ✅ Done

### Tasks

- [x] `src/lead_crawler/pipelines/__init__.py` erstellen
- [x] `src/lead_crawler/pipelines/lead_analysis.py`
  - [x] `LeadAnalysisPipeline` Klasse
  - [x] Orchestriert: Crawl → Extract → Analyze → Cache → Score
  - [x] `PipelineResult` und `BatchResult` Dataclasses
  - [x] Progress Callbacks für UI
  - [x] Error Handling pro Schritt
  - [x] `analyze()`, `analyze_batch()`, `analyze_from_crawler()` Methoden
- [x] `src/lead_crawler/pipelines/export.py`
  - [x] `ExportPipeline` für CSV/JSON/JSONL/Excel
  - [x] `ExportConfig` und `ExportResult` Dataclasses
  - [x] Filterung nach Score/Priority
  - [x] Feld-Auswahl und Format-Optionen
- [x] Convenience-Funktionen `run_analysis()`, `export_companies()`
- [x] 22 Unit Tests für Pipelines

---

## ✅ Phase 6: API Backend

**Priorität:** Niedrig | **Status:** ✅ Done

### Tasks

- [x] `src/api/__init__.py` erstellen
- [x] `src/api/main.py` - FastAPI Entry Point
  - [x] Lifespan Context Manager
  - [x] CORS Middleware
  - [x] Health & Status Endpoints
  - [x] Global Error Handler
- [x] `src/api/schemas.py` - Pydantic Models
  - [x] Request Models (Search, Analyze, Export)
  - [x] Response Models (Company, PLZ, Job)
  - [x] Enums (Source, Priority, Format)
- [x] `src/api/dependencies.py` - DI Container
  - [x] Service Dependencies
  - [x] API Key Authentication
  - [x] Pagination & Filter
- [x] `src/api/routes/search.py`
  - [x] `POST /search` - PLZ/Radius Suche
  - [x] `GET /search/plz/{plz}` - PLZ-Informationen
  - [x] `POST /search/radius` - PLZ-Radius-Suche
  - [x] `POST /search/n8n` - n8n Workflow Integration
- [x] `src/api/routes/company.py`
  - [x] `GET /company/{id}` - Unternehmensdetails
  - [x] `POST /company/analyze` - LLM-Analyse
  - [x] `POST /company/analyze/n8n` - n8n Integration
- [x] `src/api/routes/analyze.py`
  - [x] `POST /analyze/batch` - Batch-Analyse
  - [x] `GET /analyze/{job_id}` - Job-Status
  - [x] `DELETE /analyze/{job_id}` - Job abbrechen
- [x] `src/api/routes/export.py`
  - [x] `POST /export` - Export starten
  - [x] `GET /export/{id}` - Export-Status
  - [x] `GET /export/{id}/download` - Download
  - [x] `POST /export/n8n` - n8n Export mit Webhook
- [x] OpenAPI Docs (`/docs`, `/redoc`)
- [x] n8n-specific OpenAPI Schema (`/openapi-n8n.json`)
- [x] 28 Unit Tests für API

---

## ✅ Phase 7: Web Frontend Refaktorieren

**Priorität:** Niedrig | **Status:** ⚪ Pending

### Tasks

- [ ] Streamlit Multi-Page Setup
- [ ] `web/pages/1_Search.py` extrahieren
- [ ] `web/pages/2_Analysis.py` extrahieren
- [ ] `web/pages/3_Export.py` extrahieren
- [ ] `web/pages/4_Settings.py` extrahieren
- [ ] `web/components/` für wiederverwendbare UI-Elemente
- [ ] API-Backend Anbindung (statt direkte Imports)

---

## ✅ Phase 8: Tests & Docs

**Priorität:** Mittel | **Status:** ⚪ Pending

### Tasks

- [ ] `tests/unit/` Struktur erstellen
- [ ] Unit Tests für alle Models
- [ ] Unit Tests für alle Services
- [ ] `tests/integration/` Struktur erstellen
- [ ] Integration Tests für Crawlers
- [ ] Integration Tests für Pipelines
- [ ] `tests/fixtures/` mit Sample Data
- [ ] `pytest.ini` und `pyproject.toml` konfigurieren
- [ ] CI/CD Pipeline (GitHub Actions)
- [ ] API Documentation (OpenAPI)
- [ ] README.md überarbeiten

---

## 📊 Fortschritt

| Phase | Status | Progress |
|-------|--------|----------|
| 1. Models | ✅ Done | 100% |
| 2. Config | ✅ Done | 100% |
| 3. Services | ✅ Done | 100% |
| 4. Crawlers | ✅ Done | 100% |
| 5. Pipelines | ✅ Done | 100% |
| 6. API | ✅ Done | 100% |
| 7. Web | ⚪ Pending | 0% |
| 8. Tests | ⚪ Pending | 0% |

**Legende:** ⚪ Pending | 🔵 In Progress | ✅ Done | ❌ Blocked

---

## 📝 Notizen

- Jede Phase wird in einem eigenen Commit abgeschlossen
- Vor jedem Commit: Tests laufen lassen
- Nach Phase 1-3 kann die API bereits entwickelt werden (parallel)
- Phase 4 (Crawlers) kann aufwendig sein - ggf. in Sub-Tasks aufteilen

---

*Last updated: 2026-03-21*