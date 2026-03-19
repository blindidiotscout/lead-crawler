# Lead Crawler

**Automatisierte Lead-Generierung für KMU in Österreich**

---

## 🎯 Was macht das Tool?

Findet und analysiert Unternehmen:
- 📍 Geografische Suche (PLZ + Radius)
- 🏢 WKO Firmen-Daten (kostenlos, öffentlich)
- 🤖 LLM-basierte Branchen-Erkennung (lokal via Ollama)
- 📊 Lead-Scoring (0-100 Punkte)
- 💾 Cache für Analysen (SQLite)

---

## ✅ Implementiert

| Komponente | Status | Beschreibung |
|------------|--------|--------------|
| **WKO Spider** | ✅ | `scraper.py` - Crawlt firmen.wko.at |
| **PLZ-Radius** | ✅ | `plz_radius.py` - Findet PLZ im Umkreis |
| **Website Crawler** | ✅ | `website_crawler.py` - Extrahiert Text von Websites |
| **LLM Analyzer** | ✅ | `llm_analyzer.py` - Branchen-Erkennung via Ollama |
| **Analysis Cache** | ✅ | `analysis_cache.py` - SQLite-Cache für LLM-Results |
| **LLM Pipeline** | ✅ | `llm_pipeline.py` - End-to-End: Crawl → Analyze → Cache |
| **Enhanced Spider** | ✅ | `enhanced_scraper.py` - WKO + LLM kombiniert |
| **Scoring Engine** | ✅ | `scoring.py` + `enhanced_scoring.py` |
| **ecoplus Spider** | 🔬 | `ecoplus_spider.py` - Experimentell (NÖ Industrieparks) |

---

## 🏗️ Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                    Lead Crawler                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ PLZ-Service  │───▶│ WKO Spider   │───▶│ LLM Pipeline │  │
│  │ (Radius)     │    │ (scraper.py) │    │              │  │
│  └──────────────┘    └──────────────┘    └──────┬───────┘  │
│                                                   │          │
│                                          ┌───────▼───────┐  │
│                                          │ Website       │  │
│                                          │ Crawler       │  │
│                                          └───────┬───────┘  │
│                                                  │          │
│                                          ┌───────▼───────┐  │
│                                          │ LLM Analyzer  │  │
│                                          │ (Ollama)      │  │
│                                          └───────┬───────┘  │
│                                                  │          │
│                          ┌───────────────────────┼────────┐ │
│                          │                       │        │ │
│                   ┌──────▼──────┐         ┌──────▼──────┐ │ │
│                   │ Scoring     │         │ Cache       │ │ │
│                   │ Engine      │         │ (SQLite)    │ │ │
│                   └─────────────┘         └─────────────┘ │ │
│                                                          │ │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech-Stack

| Komponente | Technologie |
|------------|-------------|
| **Crawler** | Scrapy (Python) |
| **PLZ-Daten** | SQLite (offline) |
| **LLM** | Ollama (lokal, qwen2.5:7b) |
| **Cache** | SQLite |
| **HTTP** | requests + beautifulsoup4 |

---

## 📁 Projektstruktur

```
lead-crawler/
├── README.md
├── requirements.txt
├── config/
│   └── settings.example.py
├── data/
│   ├── plz_austria.db          # PLZ-Datenbank (SQLite)
│   ├── analysis_cache.db       # LLM-Analysen (SQLite)
│   └── *.json                  # Rohdaten
└── src/
    ├── scraper.py              # WKO Spider (Basis)
    ├── enhanced_scraper.py     # WKO + LLM
    ├── plz_radius.py           # PLZ-Radius-Service
    ├── website_crawler.py      # Website-Text extrahieren
    ├── llm_analyzer.py         # Branchen-Erkennung (Ollama)
    ├── llm_pipeline.py         # End-to-End Pipeline
    ├── analysis_cache.py       # Cache für LLM-Results
    ├── scoring.py              # Lead-Scoring Engine
    └── enhanced_scoring.py     # Scoring mit LLM-Daten
```

---

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/blindidiotscout/lead-crawler.git
cd lead-crawler

# 2. Virtual Environment
python3 -m venv venv
source venv/bin/activate

# 3. Install
pip install -r requirements.txt

# 4. Ollama starten (auf 192.168.178.123:11434)
# Modell: qwen2.5:7b

# 5. Test
python -c "from src.enhanced_scraper import run_enhanced_spider; print('OK')"
```

---

## 📖 Usage

### Einfacher WKO-Crawl

```python
from src.scraper import run_spider

# PLZ-Suche
results = run_spider(plz="2351")

# Ortssuche
results = run_spider(ort="Guntramsdorf", bundesland="niederösterreich")

# Radius-Suche
results = run_spider_radius("2351", radius_km=20)
```

### Mit LLM-Analyse

```python
from src.enhanced_scraper import run_enhanced_spider

# PLZ mit LLM-Branchenanalyse
results = run_enhanced_spider(
    plz="2351",
    use_llm=True,
    llm_model="qwen2.5:7b",
    analyze_websites=True
)

# Jedes Ergebnis hat jetzt:
# - llm_analysis.branch
# - llm_analysis.services
# - llm_analysis.confidence
# - llm_cached (True = aus Cache)
```

### LLM Pipeline direkt

```python
from src.llm_pipeline import LLMPipeline

pipeline = LLMPipeline(ollama_model="qwen2.5:7b")

# Einzelnes Unternehmen
result = pipeline.analyze_company(
    company_name="AKRAS Flavours",
    website_url="https://www.akras.at"
)

print(result.analysis.branch)  # "Industrie/Fertigung"
print(result.analysis.confidence)  # 0.85
```

### Scoring

```python
from src.scoring import LeadScorer

scorer = LeadScorer()
score = scorer.score({
    'name': 'Test GmbH',
    'branche': 'IT',
    'plz': '2351',
    'website': 'https://example.com'
})

print(score.total_score)  # 0-100
print(score.grade)  # A, B, C, D, F
print(score.priority)  # HIGH, MEDIUM, LOW
```

---

## ⚙️ Konfiguration

### Ollama

```python
# In llm_analyzer.py / llm_pipeline.py
OLLAMA_URL = "http://192.168.178.123:11434"
MODEL = "qwen2.5:7b"
TIMEOUT = 300  # Sekunden
```

### Cache

```python
# Cache-Dauer
CACHE_TTL_DAYS = 30

# Cache-Location
CACHE_DB = "data/analysis_cache.db"
```

---

## 📊 Beispiel-Output

```python
{
  'name': 'AKRAS Flavours GmbH',
  'street': 'IZ-NÖ-SÜD Straße 1',
  'plz': '2351',
  'ort': 'Biedermannsdorf',
  'website': 'https://www.akras.at/',
  'llm_analysis': {
    'branch': 'Industrie/Fertigung',
    'sub_branches': ['Aromenherstellung', 'Getränkeindustrie'],
    'services': ['Produktion von Aromen', 'Kundenservice'],
    'target_market': 'B2B',
    'company_size_hint': 'Groß (50+ MA)',
    'confidence': 0.85
  },
  'llm_cached': False
}
```

---

## ⚖️ Rechtliches

- **robots.txt:** Wird eingehalten (Scrapy built-in)
- **Rate-Limiting:** 1-2 Requests/Sekunde
- **DSGVO:** Nur Firmendaten (keine Personen)
- **Quelle:** WKO = öffentlich zugänglich

---

## 🔧 TODO / Roadmap

| Feature | Status |
|---------|--------|
| FastAPI Backend | 🔲 Geplant |
| CSV/JSON Export | 🔲 Geplant |
| Weitere Datenquellen (EKO Plus) | 🔲 Geplant |
| Web-UI (Streamlit) | 🔲 Geplant |
| API-Key Auth | 🔲 Geplant |

---

## 📄 Lizenz

MIT License

---

*Stand: 2026-03-19*