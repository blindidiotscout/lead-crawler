# Testing Strategy - Lead Crawler

## Overview

Dieses Dokument beschreibt die Test-Strategie für den Lead Crawler nach dem Refactoring.

## Test-Architektur

```
tests/
├── unit/                    # Unit Tests (keine externen Dienste)
│   ├── test_models.py        # 31 Tests - Domain Models
│   ├── test_config.py        # 19 Tests - Configuration
│   ├── test_services.py      # 36 Tests - Services Layer
│   ├── test_crawlers.py      # 23 Tests - Crawler Architecture
│   ├── test_pipelines.py     # 22 Tests - Pipelines
│   ├── test_web.py           # 15 Tests - Web Components
│   └── test_api.py           # 28 Tests - API Endpoints
│
├── integration/              # Integration Tests (externe Dienste)
│   ├── test_crawlers.py      # WKO Crawler Tests
│   ├── test_llm_client.py    # Ollama LLM Tests
│   └── test_pipelines.py     # End-to-End Pipeline Tests
│
└── fixtures/                 # Test Fixtures
    └── sample_data.py        # Sample Data für Tests
```

## Test-Typen

### 1. Unit Tests

Unit Tests testen isolierte Komponenten ohne externe Abhängigkeiten.

**Merkmale:**
- Schnelle Ausführung (< 1 Sekunde pro Test)
- Keine Netzwerk-Calls
- Keine Datenbank-Zugriffe
- Mocking für externe Services

**Abdeckung:**
- `test_models.py`: Company, Address, ContactInfo, LeadScore, BranchAnalysis, etc.
- `test_config.py`: Settings, OllamaConfig, CacheConfig, etc.
- `test_services.py`: SQLiteCache, MockLLMClient, PLZService, WebsiteExtractor
- `test_crawlers.py`: BaseCrawler, WKOCrawler, CrawlerResult
- `test_pipelines.py`: LeadAnalysisPipeline, ExportPipeline, PipelineResult
- `test_web.py`: UI-Komponenten, Filter-Logik, Export-Formate
- `test_api.py`: FastAPI Endpoints, Schemas, Dependencies

### 2. Integration Tests

Integration Tests testen das Zusammenspiel mehrerer Komponenten.

**Merkmale:**
- Können externe Dienste benötigen (Ollama, WKO)
- Langsamere Ausführung
- Werden mit `@pytest.mark.integration` markiert
- Werden nur mit `-m integration` ausgeführt

**Ausführung:**
```bash
# Alle Tests außer Integration
pytest tests/unit/ -v

# Nur Integration Tests
pytest tests/integration/ -v -m integration

# Alle Tests
pytest tests/ -v
```

### 3. E2E Tests (Optional)

End-to-End Tests testen komplette Workflows.

**Merkmale:**
- Testen vollständige User-Workflows
- Erfordern laufende Services
- Für CI/CD geeignet

## Test-Ausführung

### Lokal

```bash
# Unit Tests
pytest tests/unit/ -v

# Mit Coverage
pytest tests/unit/ --cov=lead_crawler --cov-report=html

# Integration Tests
pytest tests/integration/ -v

# Spezifische Tests
pytest tests/unit/test_models.py -v -k "test_company"
```

### CI/CD (GitHub Actions)

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: pytest tests/unit/ -v --cov=lead_crawler
```

## Test-Statistiken

| Kategorie | Tests | Status |
|----------|-------|--------|
| Models | 31 | ✅ All passing |
| Config | 19 | ✅ All passing |
| Services | 36 | ✅ All passing |
| Crawlers | 23 | ✅ All passing |
| Pipelines | 22 | ✅ All passing |
| Web | 15 | ✅ All passing |
| API | 28 | ✅ All passing |
| Integration | 13 | ✅ All passing |
| **Total** | **174** | **✅ All passing** |

## Test-Coverage-Ziele

| Modul | Aktuell | Ziel |
|-------|---------|------|
| lead_crawler.models | ~90% | 95% |
| lead_crawler.config | ~85% | 90% |
| lead_crawler.services | ~80% | 85% |
| lead_crawler.crawlers | ~75% | 80% |
| lead_crawler.pipelines | ~70% | 80% |
| api.routes | ~60% | 75% |
| web.pages | ~50% | 70% |

## Erweiterte Test-Strategie

### 1. Property-Based Testing

Für komplexe Logik (Scoring, Filtering):

```python
from hypothesis import given, strategies as st

@given(st.floats(min_value=0, max_value=100))
def test_score_percentage(score):
    """Score sollte immer zwischen 0 und 100 liegen"""
    assert 0 <= score <= 100
```

### 2. Mutation Testing

Testet ob Tests echte Bugs finden:

```bash
pip install mutmut
mutmut run --paths-to-mutate=src/lead_crawler/
```

### 3. Contract Testing

API-Contracts validieren:

```python
def test_api_contracts():
    """API-Schema sollte mit OpenAPI-Spec übereinstimmen"""
    from openapi_spec_validator import validate_spec
    # Validate OpenAPI schema
```

### 4. Performance Testing

Für Performance-kritische Pfade:

```python
import pytest
import time

@pytest.mark.slow
def test_crawler_performance():
    """Crawler sollte in < 30s antworten"""
    start = time.time()
    # ... crawler test
    elapsed = time.time() - start
    assert elapsed < 30
```

## Test-Fixtures

### Sample Data

```python
from tests.fixtures.sample_data import (
    SAMPLE_COMPANY,      # Einzelnes Sample-Unternehmen
    SAMPLE_COMPANIES,    # Liste von Unternehmen
    SAMPLE_ANALYSIS,     # Sample LLM-Analyse
    SAMPLE_PLZ_DATA,     # Sample PLZ-Daten
)
```

### Mock Services

```python
from lead_crawler.services.llm_client import MockLLMClient

# Mock LLM Client (kein echter Ollama nötig)
llm = MockLLMClient()
result = llm.analyze_branch("Test Firma", "Test Content")
```

## Best Practices

1. **Test-First**: Neue Features brauchen Tests
2. **Isoliert**: Unit Tests sollten isoliert laufen
3. **Schnell**: Unit Tests < 1 Sekunde
4. **Aussagekräftig**: Test-Namen beschreiben was getestet wird
5. **DRY**: Fixtures für wiederkehrende Daten
6. **Coverage**: Ziel ist 80%+ Coverage

## Continuous Improvement

1. **Regelmäßige Reviews**: Tests bei PR-Reviews prüfen
2. **Coverage-Tracking**: Coverage bei jedem PR tracken
3. **Test-Metriken**: Test-Ausführungszeit überwachen
4. **Refactoring**: Tests bei Refactoring aktualisieren

---

*Last updated: 2026-03-21*