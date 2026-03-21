# Lead Crawler v2.0

**Automatisierte Lead-Generierung für KMU in Österreich**

Eine moderne, modulare Anwendung zum Crawlen, Analysieren und Bewerten von Unternehmensdaten.

---

## 🎯 Features

| Feature | Beschreibung |
|---------|--------------|
| 🔍 **PLZ/Radius Suche** | Finde Unternehmen im Umkreis einer PLZ |
| 🏢 **WKO Daten** | Crawlt firmen.wko.at (kostenlos, öffentlich) |
| 🤖 **LLM-Analyse** | Branchen-Erkennung via Ollama (lokal) |
| 📊 **Lead Scoring** | Automatische Bewertung (0-100 Punkte) |
| 💾 **Caching** | SQLite-Cache für Analysen |
| 🌐 **REST API** | FastAPI Backend für n8n Integration |
| 🖥️ **Web UI** | Streamlit Multi-Page Frontend |

---

## 🏗️ Architektur

```
src/
├── lead_crawler/           # Core Package
│   ├── models/             # Domain Models
│   │   ├── company.py      # Company, Address, ContactInfo
│   │   ├── analysis.py     # BranchAnalysis, LLMAnalysisResult
│   │   ├── scoring.py      # LeadScore, ScoreBreakdown
│   │   └── plz.py          # PLZCoordinate, PLZInfo
│   ├── services/           # Business Logic
│   │   ├── cache.py        # SQLiteCache mit TTL
│   │   ├── llm_client.py   # OllamaClient, MockLLMClient
│   │   ├── website_extractor.py
│   │   └── plz_service.py  # PLZ-Radius-Suche
│   ├── crawlers/           # Web Crawlers
│   │   ├── base.py         # BaseCrawler, CrawlerResult
│   │   └── wko.py          # WKOCrawler
│   ├── runners/            # Scrapy Runner
│   └── pipelines/          # End-to-End Workflows
│       ├── lead_analysis.py
│       └── export.py
│
├── api/                    # FastAPI Backend
│   ├── main.py             # App Entry Point
│   ├── schemas.py          # Pydantic Models
│   ├── dependencies.py     # DI Container
│   └── routes/
│       ├── search.py       # /search, /search/n8n
│       ├── company.py      # /company, /company/analyze
│       ├── analyze.py      # /analyze/batch
│       └── export.py       # /export, /export/n8n
│
└── web/                    # Streamlit Frontend
    ├── Home.py             # Startseite
    └── pages/
        ├── 1_Search.py     # Unternehmenssuche
        ├── 2_Analysis.py   # Statistiken
        ├── 3_Export.py     # Datenexport
        └── 4_Settings.py   # Einstellungen
```

---

## 📦 Installation

```bash
# 1. Clone
git clone https://github.com/blindidiotscout/lead-crawler.git
cd lead-crawler

# 2. Virtual Environment
python3 -m venv venv
source venv/bin/activate

# 3. Install
pip install -r requirements.txt

# 4. Environment (optional)
cp .env.example .env
# Edit .env with your settings
```

---

## 🚀 Quick Start

### 1. Kommandozeile (CLI)

```python
from lead_crawler.crawlers import WKOCrawler
from lead_crawler.pipelines import LeadAnalysisPipeline

# Einfacher Crawl
crawler = WKOCrawler()
result = crawler.crawl(plz="2351", radius_km=20)
print(f"Found {result.total} companies")

# Mit LLM-Analyse
pipeline = LeadAnalysisPipeline()
result = pipeline.analyze_from_crawler(crawler, plz="2351")
for company in result.companies:
    print(f"{company.name}: {company.score.grade}")
```

### 2. Web UI (Streamlit)

```bash
streamlit run web/Home.py
```

### 3. REST API (FastAPI)

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

API Endpoints:
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc
- `POST /api/v1/search` - Unternehmenssuche
- `POST /api/v1/company/analyze` - LLM-Analyse
- `POST /api/v1/export` - Datenexport

---

## 🧪 Tests

```bash
# Alle Unit Tests
pytest tests/unit/ -v

# Mit Coverage
pytest tests/unit/ --cov=lead_crawler --cov-report=html

# Integration Tests (benötigt Ollama)
pytest tests/integration/ -v -m integration

# Alle Tests
pytest tests/ -v
```

**Test-Statistiken:**
- Unit Tests: 146
- Integration Tests: 13
- **Total: 159 Tests ✅**

---

## 📊 Verwendung

### Crawler

```python
from lead_crawler.crawlers import WKOCrawler

crawler = WKOCrawler()

# PLZ-Suche
result = crawler.crawl(plz="2351")

# Radius-Suche
result = crawler.crawl_radius(center_plz="2351", radius_km=20)

# Ort-Suche
result = crawler.crawl(ort="Guntramsdorf", bundesland="niederösterreich")
```

### Pipeline

```python
from lead_crawler.pipelines import LeadAnalysisPipeline
from lead_crawler.models import Company

pipeline = LeadAnalysisPipeline()

# Einzelnes Unternehmen
company = Company(name="Test GmbH")
company.contact.website = "https://test.at"
result = pipeline.analyze(company)

print(result.analysis.branch)      # "IT-Dienstleistungen"
print(result.score.total_score)    # 85
print(result.from_cache)           # False
```

### Export

```python
from lead_crawler.pipelines import ExportPipeline, ExportConfig
from lead_crawler.crawlers import WKOCrawler

# Unternehmen suchen
crawler = WKOCrawler()
companies = crawler.crawl(plz="2351").companies

# Exportieren
config = ExportConfig(
    output_format="csv",
    min_score=50
)
pipeline = ExportPipeline()
result = pipeline.export(companies, config)

print(f"Exported {result.exported_companies} companies to {result.output_path}")
```

### REST API

```bash
# Search
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"plz": "2351", "radius_km": 20}'

# Analyze
curl -X POST http://localhost:8000/api/v1/company/analyze \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Test GmbH", "website_url": "https://test.at"}'

# Export
curl -X POST http://localhost:8000/api/v1/export \
  -H "Content-Type: application/json" \
  -d '{"format": "json"}'
```

---

## ⚙️ Konfiguration

### Environment Variables (.env)

```env
# Ollama
OLLAMA_URL=http://192.168.178.123:11434
OLLAMA_MODEL=qwen2.5:7b

# Cache
CACHE_DB_PATH=data/analysis_cache.db
CACHE_TTL_DAYS=30

# PLZ
PLZ_DB_PATH=data/plz_austria.db

# API
API_HOST=0.0.0.0
API_PORT=8000
API_KEYS=your-api-key-here
```

### Settings (Python)

```python
from lead_crawler.config import get_settings

settings = get_settings()
print(settings.ollama.url)     # http://192.168.178.123:11434
print(settings.ollama.model)   # qwen2.5:7b
print(settings.cache.ttl_days) # 30
```

---

## 📁 Projektstruktur

```
lead-crawler/
├── src/
│   ├── lead_crawler/      # Core Package
│   └── api/               # FastAPI Backend
├── web/                   # Streamlit Frontend
├── tests/
│   ├── unit/              # Unit Tests
│   ├── integration/       # Integration Tests
│   └── fixtures/          # Test Data
├── legacy/                # Alte Dateien (Referenz)
├── data/                  # Datenbanken
│   ├── plz_austria.db
│   └── analysis_cache.db
├── requirements.txt
├── pytest.ini
└── REFACTORING.md        # Refactoring-Dokumentation
```

---

## 📊 Output-Beispiel

```json
{
  "name": "Test GmbH",
  "address": {
    "street": "Teststraße 1",
    "plz": "2351",
    "ort": "Guntramsdorf"
  },
  "contact": {
    "telefon": "+43 2236 12345",
    "email": "info@test.at",
    "website": "https://test.at"
  },
  "analysis": {
    "branch": "IT-Dienstleistungen",
    "confidence": 0.92,
    "services": ["Web Development", "Mobile Apps"],
    "target_market": "KMU"
  },
  "score": {
    "total_score": 85,
    "grade": "A",
    "priority": "HIGH"
  }
}
```

---

## 🧪 Test-Strategie

Siehe `tests/TESTING.md` für detaillierte Dokumentation.

| Kategorie | Tests | Status |
|-----------|-------|--------|
| Models | 31 | ✅ |
| Config | 19 | ✅ |
| Services | 36 | ✅ |
| Crawlers | 23 | ✅ |
| Pipelines | 22 | ✅ |
| Web | 15 | ✅ |
| API | 28 | ✅ |
| Integration | 13 | ✅ |

---

## 🔧 Entwicklung

```bash
# Tests laufen
pytest tests/unit/ -v

# Tests mit Coverage
pytest tests/unit/ --cov=lead_crawler --cov-report=html

# Formatierung
black src/ tests/

# Linting
ruff check src/ tests/
```

---

## ⚖️ Rechtliches

- **robots.txt:** Wird eingehalten (Scrapy built-in)
- **Rate-Limiting:** 1-2 Requests/Sekunde
- **DSGVO:** Nur Firmendaten (keine Personen)
- **Quelle:** WKO = öffentlich zugänglich

---

## 📄 Lizenz

MIT License

---

## 📝 Changelog

### v2.0.0 (2026-03-21)

**Major Refactoring:**
- ✅ Domain Models (`models/`)
- ✅ Configuration System (`config.py`)
- ✅ Services Layer (`services/`)
- ✅ Crawler Architecture (`crawlers/`)
- ✅ Pipeline Pattern (`pipelines/`)
- ✅ FastAPI Backend (`api/`)
- ✅ Streamlit Multi-Page Frontend (`web/`)
- ✅ Comprehensive Test Suite (159 tests)
- ✅ Integration Tests

**Breaking Changes:**
- Alte Imports nicht mehr kompatibel
- Neue Package-Struktur
- API-Endpoints geändert

---

*Stand: 2026-03-21*