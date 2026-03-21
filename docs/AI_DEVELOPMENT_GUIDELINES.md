# AI Development Guidelines

## Best Practices aus der Lead-Crawler Entwicklung

---

## 1. Projekt-Struktur

### 1.1 Package-Layout

```
project/
├── src/
│   ├── package_name/      # Core Package
│   │   ├── __init__.py
│   │   ├── config.py      # Zentrale Konfiguration
│   │   ├── models/        # Domain Models
│   │   ├── services/      # Business Logic
│   │   ├── crawlers/      # External Interfaces
│   │   └── pipelines/     # Workflows
│   ├── api/               # FastAPI Backend
│   └── web/               # Streamlit Frontend
├── tests/
│   ├── unit/              # Unit Tests
│   ├── integration/       # Integration Tests
│   └── fixtures/          # Test Data
├── legacy/                # Alte Dateien (Referenz)
├── docs/                  # Dokumentation
├── pyproject.toml         # Modern Packaging
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
└── TESTING.md
```

### 1.2 Domain-Driven Design

```
models/          # Reine Datenstrukturen (dataclasses)
├── company.py   # Company, Address, ContactInfo
├── analysis.py  # BranchAnalysis, LLMAnalysisResult
└── scoring.py   # LeadScore, ScoreBreakdown

services/        # Business Logic
├── cache.py     # SQLiteCache mit TTL
├── llm_client.py # LLM Integration
└── plz_service.py # PLZ-Suche

pipelines/       # End-to-End Workflows
├── lead_analysis.py  # Crawl → Analyze → Score
└── export.py    # CSV/JSON/Excel Export
```

---

## 2. Testing

### 2.1 Test-Pyramide

```
        /\
       /  \       Integration Tests (13)
      /____\     - Externe Services
     /      \    - Echte Requests
    /________\  
   /          \  Unit Tests (146)
  /____________\ - Isoliert
                  - Schnell
```

### 2.2 Test-Kategorien

| Marker | Beschreibung | Ausführung |
|--------|--------------|------------|
| `@pytest.mark.unit` | Isolierte Tests | Standard |
| `@pytest.mark.integration` | Externe Services | `-m integration` |
| `@pytest.mark.slow` | Langsame Tests | `-m "not slow"` |

### 2.3 Test-Fixtures

```python
# tests/fixtures/sample_data.py
from typing import Any

SAMPLE_COMPANY: dict[str, Any] = {
    "name": "Test Firma GmbH",
    "address": {"street": "Teststraße 1", "plz": "2351"},
}

def get_sample_company(name: str = "Test") -> dict[str, Any]:
    """Gibt Sample-Company zurück mit angepasstem Namen."""
    company = SAMPLE_COMPANY.copy()
    company["name"] = name
    return company
```

### 2.4 Mock Services

```python
class MockLLMClient:
    """Mock für Tests ohne echte LLM-Verbindung."""
    
    def analyze_branch(self, name: str, content: str) -> dict[str, Any]:
        return {
            "branch": "IT-Dienstleistungen",
            "confidence": 0.95,
            "services": ["Web Development", "Mobile Apps"],
        }
```

---

## 3. CI/CD

### 3.1 GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main, dev]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12', '3.13']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -r requirements.txt
      - run: pytest tests/unit/ -v --cov
      
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install ruff black
      - run: ruff check src/ tests/
      - run: black --check src/ tests/
```

### 3.2 Linting-Konfiguration

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["F401", "F811", "E402", "I001", "N806"]
"src/web/Home.py" = ["N999"]  # Streamlit requires Home.py

[tool.black]
line-length = 100
target-version = ["py311", "py312"]
```

### 3.3 Branch Protection Rules

```
Settings → Branches → Add rule
├── Branch: main
├── Require status checks:
│   ├── test (3.11)
│   ├── test (3.12)
│   ├── test (3.13)
│   └── lint
└── Require branches to be up to date
```

---

## 4. Refactoring-Prozess

### 4.1 Phasierter Ansatz

| Phase | Beschreibung | Dauer |
|-------|--------------|-------|
| 1. Models | Domain Models erstellen | 1-2 Tage |
| 2. Config | Zentrale Konfiguration | 0.5 Tage |
| 3. Services | Business Logic extrahieren | 1-2 Tage |
| 4. Crawlers | Crawler-Architektur | 1-2 Tage |
| 5. Pipelines | Workflows definieren | 1-2 Tage |
| 6. API | REST API aufsetzen | 1-2 Tage |
| 7. Web | Frontend refactoren | 1-2 Tage |
| 8. Tests | Test-Suite erstellen | 1-2 Tage |

### 4.2 Legacy-Handling

```
src/
├── scraper.py          # ALT → legacy/
├── enhanced_scraper.py # ALT → legacy/
└── lead_crawler/       # NEU
    ├── models/
    └── services/
```

**Wichtig:**
- Alte Dateien nicht löschen, sondern nach `legacy/` verschieben
- README in `legacy/` mit Migration Map
- Nach erfolgreicher Tests: Legacy entfernen

### 4.3 Test-First

```python
# 1. Test schreiben
def test_company_creation():
    company = Company(name="Test GmbH")
    assert company.name == "Test GmbH"

# 2. Implementieren
@dataclass
class Company:
    name: str

# 3. Test laufen lassen
# pytest tests/unit/test_models.py -v
```

---

## 5. Code-Qualität

### 5.1 Type Hints

```python
# ✅ Gut
def calculate_score(company: Company) -> LeadScore:
    ...

# ❌ Schlecht
def calculate_score(company):
    ...
```

### 5.2 Docstrings

```python
def find_nearby_plz(plz: str, radius_km: float) -> list[PLZInfo]:
    """Findet PLZ im Umkreis einer PLZ.
    
    Args:
        plz: Ausgangs-PLZ (z.B. "2351")
        radius_km: Radius in Kilometern
        
    Returns:
        Liste von PLZInfo-Objekten im Umkreis
        
    Raises:
        ValueError: Wenn PLZ ungültig
        
    Example:
        >>> nearby = find_nearby_plz("2351", 10.0)
        >>> len(nearby)
        15
    """
```

### 5.3 Naming Conventions

```python
# Klassen: PascalCase
class LeadScore:
    ...

# Funktionen/Variablen: snake_case
def calculate_score():
    total_score = 85

# Konstanten: UPPER_SNAKE_CASE
MAX_RADIUS_KM = 100
DEFAULT_TTL_DAYS = 30

# Private: _prefix
def _normalize_url(url: str) -> str:
    ...
```

---

## 6. Dokumentation

### 6.1 README.md

```markdown
# Project Name

## Features
- Feature 1
- Feature 2

## Installation
pip install -r requirements.txt

## Quick Start
python -m package_name

## Testing
pytest tests/ -v

## License
MIT
```

### 6.2 CHANGELOG.md

```markdown
## [2.0.0] - 2026-03-21

### Added
- Domain Models Package
- Configuration System
- Services Layer

### Changed
- **BREAKING**: Import paths changed

### Removed
- Legacy scraper.py
```

### 6.3 CONTRIBUTING.md

- Development Setup
- Code Style Guidelines
- Testing Requirements
- PR Process

---

## 7. Git Workflow

### 7.1 Branch-Naming

```
feature/xxx    # Neue Features
fix/xxx         # Bug Fixes
refactor/xxx    # Code Refactoring
docs/xxx        # Dokumentation
test/xxx        # Tests
```

### 7.2 Commit Messages

```
feat: Add new crawler for Ecoplus
fix: Handle missing website gracefully
refactor: Extract scoring logic to separate module
docs: Update README with new API endpoints
test: Add tests for PLZService
chore: Update dependencies
```

### 7.3 Pull Request Template

```markdown
## Summary
Brief description of changes.

## Changes
- ✅ Change 1
- ✅ Change 2

## Test Plan
```bash
pytest tests/ -v
```

## Breaking Changes
Document any breaking changes.
```

---

## 8. Performance

### 8.1 Caching

```python
class SQLiteCache:
    """LRU Cache mit TTL für LLM-Resultate."""
    
    def get(self, key: str) -> dict | None:
        """Hole aus Cache, wenn nicht expired."""
        
    def set(self, key: str, value: dict, ttl_days: int = 30):
        """Speichere mit TTL."""
```

### 8.2 Lazy Imports

```python
# ❌ Top-level Import (slow startup)
from scrapy.crawler import CrawlerProcess

# ✅ Lazy Import (nur wenn benötigt)
def run_spider():
    from scrapy.crawler import CrawlerProcess
    ...
```

---

## 9. Security

### 9.1 Environment Variables

```python
# .env
OLLAMA_URL=http://localhost:11434
API_KEY=secret-key-here

# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ollama_url: str
    api_key: str
    
    class Config:
        env_file = ".env"
```

### 9.2 Input Validation

```python
from pydantic import BaseModel, validator

class SearchRequest(BaseModel):
    plz: str
    radius_km: float
    
    @validator('plz')
    def validate_plz(cls, v):
        if not v.isdigit() or len(v) != 4:
            raise ValueError('PLZ muss 4-stellig sein')
        return v
```

---

## 10. Deployment

### 10.1 Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 10.2 PyPI Publishing

```bash
# Build
python -m build

# Check
twine check dist/*

# Publish
twine upload dist/*
```

---

## Checkliste für neue Projekte

- [ ] `pyproject.toml` erstellen
- [ ] `src/package_name/` Struktur
- [ ] Domain Models in `models/`
- [ ] Services in `services/`
- [ ] Tests in `tests/unit/` und `tests/integration/`
- [ ] `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`
- [ ] `.github/workflows/test.yml`
- [ ] `.github/dependabot.yml`
- [ ] `.gitignore` für Python
- [ ] Type Hints für alle Public APIs
- [ ] Docstrings für alle Klassen/Funktionen
- [ ] Ruff + Black konfigurieren
- [ ] Branch Protection Rules setzen

---

*Diese Guidelines wurden aus der Entwicklung des lead-crawler Projekts abgeleitet.*
*Stand: 2026-03-21*