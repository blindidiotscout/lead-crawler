# Entwickler Guidelines

## Best Practices aus der Lead-Crawler Entwicklung

**Eine Referenz für zukünftige Projekte**

---

## 📋 Übersicht

Dieses Dokument fasst die Best Practices zusammen, die während der Entwicklung des Lead-Crawler Projekts entstanden sind. Es dient als Referenz für zukünftige Projekte.

---

## 1. Projekt-Struktur

### Empfohlene Verzeichnisstruktur

```
project/
├── src/
│   ├── package_name/      # Core Package
│   │   ├── models/        # Domain Models
│   │   ├── services/      # Business Logic
│   │   └── pipelines/     # Workflows
│   ├── api/               # REST API
│   └── web/               # Frontend
├── tests/
│   ├── unit/              # Unit Tests
│   ├── integration/       # Integration Tests
│   └── fixtures/          # Test Data
├── legacy/                # Alte Dateien
├── docs/                  # Dokumentation
├── pyproject.toml         # Modern Packaging
└── requirements.txt
```

### Wichtige Regeln

| Regel | Begründung |
|-------|------------|
| `src/` Package | Ermöglicht relative Imports |
| `models/` separat | Domain-Driven Design |
| `legacy/` aufbewahren | Referenz für Migration |
| `tests/fixtures/` | Wiederverwendbare Test-Daten |

---

## 2. Testing

### Test-Pyramide

```
        /\
       /  \      Integration (13 Tests)
      /____\    - Externe Services
     /      \   
    /________\  Unit (146 Tests)
   /          \ - Isoliert, schnell
```

### Test-Marker

```python
@pytest.mark.unit          # Standard
@pytest.mark.integration   # Mit Services
@pytest.mark.slow          # Langsame Tests
```

### Ausführung

```bash
# Unit Tests
pytest tests/unit/ -v

# Integration Tests
pytest tests/integration/ -v -m integration

# Mit Coverage
pytest tests/unit/ --cov --cov-report=html
```

### Mock Services

```python
class MockLLMClient:
    """Mock für Tests ohne echte LLM-Verbindung."""
    
    def analyze_branch(self, name: str, content: str) -> dict:
        return {"branch": "IT", "confidence": 0.95}
```

---

## 3. CI/CD

### GitHub Actions Workflow

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12', '3.13']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r requirements.txt
      - run: pytest tests/unit/ -v
      
  lint:
    runs-on: ubuntu-latest
    steps:
      - run: ruff check src/ tests/
      - run: black --check src/ tests/
```

### Linting Setup

```toml
# pyproject.toml
[tool.ruff]
line-length = 100

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["F401", "E402"]  # Tests dürfen mehr

[tool.black]
line-length = 100
```

### Branch Protection

```
✅ Require status checks
✅ Require tests to pass
✅ Require linting to pass
✅ Require branches up to date
```

---

## 4. Refactoring

### Phasierter Ansatz

| Phase | Inhalt | Tests |
|-------|--------|-------|
| 1. Models | Domain Models | ✅ |
| 2. Config | Settings | ✅ |
| 3. Services | Business Logic | ✅ |
| 4. Crawlers | External Interfaces | ✅ |
| 5. Pipelines | Workflows | ✅ |
| 6. API | REST Endpoints | ✅ |
| 7. Web | Frontend | ✅ |
| 8. Integration | E2E Tests | ✅ |

### Test-First

1. **Test schreiben** - Was soll das Modul tun?
2. **Implementieren** - Minimaler Code
3. **Test laufen** - Grün? ✅
4. **Refactorn** - Code verbessern

### Legacy-Handling

```
ALT:                    NEU:
src/                    src/
├── scraper.py    →     ├── lead_crawler/
└── scoring.py    →     │   ├── models/
                        │   └── services/
                        
legacy/
└── README.md    ← Migration Map
```

---

## 5. Code-Qualität

### Type Hints

```python
# ✅ Gut
def calculate_score(company: Company) -> LeadScore:
    ...

# ❌ Schlecht
def calculate_score(company):
    ...
```

### Docstrings

```python
def find_nearby_plz(plz: str, radius_km: float) -> list[PLZInfo]:
    """Findet PLZ im Umkreis.
    
    Args:
        plz: Ausgangs-PLZ
        radius_km: Radius in km
        
    Returns:
        Liste von PLZ im Umkreis
    """
```

### Naming

```python
# Klassen: PascalCase
class LeadScore:
    pass

# Funktionen: snake_case
def calculate_score():
    pass

# Konstanten: UPPER_SNAKE_CASE
MAX_RADIUS = 100
```

---

## 6. Git Workflow

### Branch-Naming

```
feature/xxx    # Neue Features
fix/xxx        # Bug Fixes
refactor/xxx   # Refactoring
docs/xxx       # Dokumentation
```

### Commit Messages

```
feat: Add feature X
fix: Fix bug in Y
refactor: Improve Z
test: Add tests for X
docs: Update README
chore: Update deps
```

### PR Checklist

- [ ] Tests grün
- [ ] Linting grün
- [ ] Coverage ≥ 80%
- [ ] Docstrings vorhanden
- [ ] CHANGELOG aktualisiert

---

## 7. Dokumentation

### README.md

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
```

### CHANGELOG.md

```markdown
## [2.0.0] - 2026-03-21

### Added
- Domain Models

### Changed
- **BREAKING**: Import paths

### Removed
- Legacy scraper
```

---

## 8. Performance

### Caching

```python
class SQLiteCache:
    """Cache mit TTL."""
    
    def get(self, key: str) -> dict | None:
        """Hole aus Cache."""
        
    def set(self, key: str, value: dict, ttl_days: int = 30):
        """Speichere mit TTL."""
```

### Lazy Imports

```python
# ❌ Top-level (slow startup)
from scrapy.crawler import CrawlerProcess

# ✅ Lazy (nur wenn benötigt)
def run_spider():
    from scrapy.crawler import CrawlerProcess
    ...
```

---

## 9. Security

### Environment Variables

```python
# .env
API_KEY=secret
DATABASE_URL=postgres://...

# config.py
class Settings(BaseSettings):
    api_key: str
    database_url: str
    
    class Config:
        env_file = ".env"
```

### Input Validation

```python
class SearchRequest(BaseModel):
    plz: str
    radius_km: float
    
    @validator('plz')
    def validate_plz(cls, v):
        if not v.isdigit() or len(v) != 4:
            raise ValueError('PLZ ungültig')
        return v
```

---

## 10. Deployment

### Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0"]
```

### PyPI Publishing

```bash
# Build
python -m build

# Check
twine check dist/*

# Publish
twine upload dist/*
```

---

## ✅ Checkliste für neue Projekte

### Projekt-Setup

- [ ] `pyproject.toml` erstellen
- [ ] `src/package_name/` Struktur
- [ ] `.gitignore` für Python
- [ ] `requirements.txt` und `requirements-dev.txt`

### Code-Qualität

- [ ] Type Hints für alle Public APIs
- [ ] Docstrings für alle Klassen/Funktionen
- [ ] Ruff + Black konfigurieren

### Testing

- [ ] `tests/unit/` Verzeichnis
- [ ] `tests/fixtures/sample_data.py`
- [ ] `pytest.ini` konfigurieren

### CI/CD

- [ ] `.github/workflows/test.yml`
- [ ] `.github/dependabot.yml`
- [ ] Branch Protection Rules

### Dokumentation

- [ ] `README.md`
- [ ] `CHANGELOG.md`
- [ ] `CONTRIBUTING.md`
- [ ] `docs/` Verzeichnis

---

## 📊 Projekt-Statistiken (Lead-Crawler)

| Metrik | Wert |
|--------|------|
| Phasen | 8 |
| Commits | 15+ |
| Unit Tests | 169 |
| Integration Tests | 13 |
| Coverage | ~85% |
| Python Versionen | 3.11, 3.12, 3.13 |
| CI Jobs | 5 (test x3, lint, build) |

---

## 🎯 Key Learnings

### Was gut funktionierte

1. **Phasierter Ansatz** - Jede Phase hatte klare Ziele
2. **Test-First** - Tests schrieben die Specs
3. **Legacy-Archiv** - Alte Dateien als Referenz
4. **CI/CD von Anfang an** - Automatische Qualitätssicherung
5. **Domain-Driven Design** - Klare Trennung der Verantwortlichkeiten

### Was wir verbessern können

1. **Integration Tests früher** - E2E Tests früher schreiben
2. **Mock-First** - Mehr Mocking für schnellere Tests
3. **Dokumentation parallel** - Nicht am Ende nachholen
4. **Performance Tests** - Benchmarking integrieren

---

## 📚 Ressourcen

### Python Packaging

- https://packaging.python.org/en/latest/
- https://python-poetry.org/

### Testing

- https://docs.pytest.org/
- https://coverage.readthedocs.io/

### CI/CD

- https://docs.github.com/en/actions
- https://docs.github.com/en/code-security/dependabot

### Best Practices

- https://realpython.com/python-project-structure/
- https://docs.python-guide.org/

---

*Diese Guidelines wurden aus der Entwicklung des lead-crawler Projekts abgeleitet.*
*Stand: 2026-03-21*