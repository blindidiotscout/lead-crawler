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

**Priorität:** Mittel | **Status:** ⚪ Pending

### Tasks

- [ ] `src/lead_crawler/services/__init__.py` erstellen
- [ ] `src/lead_crawler/services/cache.py`
  - [ ] `CacheService` Interface definieren
  - [ ] SQLite-Implementierung
  - [ ] Methoden: `get()`, `set()`, `invalidate()`, `get_stats()`
- [ ] `src/lead_crawler/services/llm_client.py`
  - [ ] `LLMClient` Interface
  - [ ] `OllamaClient` Implementierung
  - [ ] `MockLLMClient` für Tests
- [ ] `src/lead_crawler/services/website_extractor.py`
  - [ ] `WebsiteExtractor` Klasse
  - [ ] Extrahiert Titel, Meta, Haupttext, About, Services
  - [ ] Rate-Limiting als Parameter
- [ ] `src/lead_crawler/services/plz_service.py`
  - [ ] `PLZService` Klasse extrahieren
  - [ ] Radius-Berechnung
  - [ ] Orte-Suche
- [ ] Dependency Injection Pattern implementieren
- [ ] Unit Tests für alle Services

---

## ✅ Phase 4: Crawlers Refaktorieren

**Priorität:** Mittel | **Status:** ⚪ Pending

### Tasks

- [ ] `src/lead_crawler/crawlers/__init__.py` erstellen
- [ ] `src/lead_crawler/crawlers/base.py`
  - [ ] `BaseSpider` abstrakte Klasse
  - [ ] Gemeinsame Parsing-Helpers
  - [ ] Einheitliche Error-Handling
- [ ] `src/lead_crawler/crawlers/wko.py`
  - [ ] `WKOSpider` von Base erben
  - [ ] Nur WKO-spezifische Logik
- [ ] `src/lead_crawler/crawlers/ecoplus.py`
  - [ ] `EcoPlusSpider` separieren
- [ ] `src/lead_crawler/runners/__init__.py` erstellen
- [ ] `src/lead_crawler/runners/spider_runner.py`
  - [ ] Einheitliche `run_spider()` Factory
  - [ ] Settings-Integration
  - [ ] Output-Format-Konfiguration
- [ ] Alte `scraper.py` und `enhanced_scraper.py` migrieren
- [ ] Integration Tests

---

## ✅ Phase 5: Pipelines Organisieren

**Priorität:** Niedrig | **Status:** ⚪ Pending

### Tasks

- [ ] `src/lead_crawler/pipelines/__init__.py` erstellen
- [ ] `src/lead_crawler/pipelines/lead_analysis.py`
  - [ ] `LeadAnalysisPipeline` Klasse
  - [ ] Orchestriert: Crawl → Extract → Analyze → Cache
  - [ ] Progress Callbacks
- [ ] `src/lead_crawler/pipelines/export.py`
  - [ ] `ExportPipeline` für CSV/JSON
  - [ ] Templates für verschiedene Export-Formate
- [ ] Pipeline-Runner CLI in `cli/`

---

## ✅ Phase 6: API Backend

**Priorität:** Niedrig | **Status:** ⚪ Pending

### Tasks

- [ ] `src/api/__init__.py` erstellen
- [ ] `src/api/main.py` - FastAPI Entry Point
- [ ] `src/api/routes/__init__.py`
- [ ] `src/api/routes/search.py`
  - [ ] `POST /search` - PLZ/Radius Suche
  - [ ] `GET /search/{id}` - Suchergebnis abrufen
- [ ] `src/api/routes/company.py`
  - [ ] `GET /company/{id}` - Unternehmensdetails
  - [ ] `GET /company/{id}/analysis` - LLM-Analyse
- [ ] `src/api/routes/analyze.py`
  - [ ] `POST /analyze` - Einzelne Website analysieren
- [ ] `src/api/dependencies.py` - DI Container
- [ ] API-Key Authentication
- [ ] OpenAPI Docs
- [ ] Docker Compose für API + Ollama

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
| 3. Services | ⚪ Pending | 0% |
| 4. Crawlers | ⚪ Pending | 0% |
| 5. Pipelines | ⚪ Pending | 0% |
| 6. API | ⚪ Pending | 0% |
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