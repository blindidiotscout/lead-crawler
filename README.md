# Lead Crawler – Marktanalyse für Agentic Workflow Engineer

**Automatisierte Lead-Generierung für KMU im DACH-Raum**

---

## 🎯 Ziel

Webcrawler zur automatischen Marktanalyse:
- Findet Unternehmen im definierten geografischen Radius (PLZ-basiert)
- Filtert nach Branche, Mitarbeiterzahl, und anderen Kriterien
- Reichert Daten an (Website-Analyse, Bilanzdaten, Services)
- Berechnet Fit-Score für Automation-Services
- Exportiert als CSV + stellt API für n8n bereit

---

## 📋 Anforderungen (v1.0)

| ID | Anforderung | Status |
|----|-------------|--------|
| **REQ-001** | Unternehmensgröße einstellbar (1-10, 10-50, 50-200, 200-500, 500+ MA) | ✅ Planned |
| **REQ-002** | Branchen-Filter (Checkbox-Liste, multi-select) | ✅ Planned |
| **REQ-003** | Geografischer Radius (eigene PLZ + km → alle PLZ im Radius) | ✅ Planned |
| **REQ-004** | Datenquellen: EKO Plus, firmenabc.at, wko.at, Firmenbuch | ✅ Planned |
| **REQ-005** | Output: CSV-Export + REST API (JSON, n8n-kompatibel) | ✅ Planned |
| **REQ-006** | Scoring: Hybrid (Bilanz-Daten + Website-Analyse mit Ollama NLP) | ✅ Planned |
| **REQ-007** | Execution: On-Demand (API-triggerbar für n8n) | ✅ Planned |
| **REQ-008** | Auth: API-Key-basiert | ✅ Planned |
| **REQ-009** | Rate-Limit: Konfigurierbar | ✅ Planned |
| **REQ-010** | Nur kostenlose, öffentliche Daten | ✅ Planned |
| **REQ-011** | Website-Analyse: Pflicht (Ollama NLP) | ✅ Planned |
| **REQ-012** | Backend: FastAPI | ✅ Planned |
| **REQ-013** | Database: Supabase (lokal) | ✅ Planned |
| **REQ-014** | Rechtlich: robots.txt einhalten, ToS prüfen | ✅ Planned |

---

## 🏗️ Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                    Lead Crawler System                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ PLZ-Service  │    │ Source-      │    │ Scoring      │  │
│  │ (Radius-     │    │ Scraper      │    │ Engine       │  │
│  │  Lookup)     │    │ (EKO, wko,   │    │ (Fit-Score   │  │
│  │              │    │   firmenabc) │    │   0-100)     │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                   │           │
│         └───────────────────┼───────────────────┘           │
│                             │                               │
│                    ┌────────▼────────┐                      │
│                    │  Data Enrichment │                      │
│                    │  (Website, Ollama│                      │
│                    │   NLP, Bilanz)   │                      │
│                    └────────┬────────┘                      │
│                             │                               │
│         ┌───────────────────┼───────────────────┐           │
│         │                   │                   │           │
│  ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐     │
│  │  Supabase   │    │  FastAPI    │    │  CSV        │     │
│  │  (PostgreSQL│    │  REST API   │    │  Export     │     │
│  │   Storage)  │    │  (n8n)      │    │             │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech-Stack

| Komponente | Technologie | Begründung |
|------------|-------------|------------|
| **Crawler** | Scrapy (Python) | Robust, production-ready, robots.txt built-in |
| **Backend** | FastAPI (Python) | Modern, async, Auto-OpenAPI, type-safe |
| **Database** | Supabase (PostgreSQL) | Lokal vorhanden, skalierbar, API-ready |
| **NLP** | Ollama (lokale LLMs) | DSGVO-konform, kostenlos, Qwen3.5 |
| **Embeddings** | Qwen3-Embedding:4b | 2560 dim, lokal auf ollama-vm |
| **Vector Store** | Qdrant | Lokal, für semantische Suche |
| **PLZ-Lookup** | Open-Meteo API / Postleitzahlen-DB | Kostenlos, öffentlich |
| **Frontend** | Streamlit (optional) | Quick Dashboard für Filter/Export |

---

## 📁 Projektstruktur

```
lead-crawler/
├── README.md                 # Dieses File
├── requirements.txt          # Python-Dependencies
├── config/
│   ├── settings.py          # Konfiguration (API-Keys, DB-URL)
│   └── branches.json        # Branchen-Liste (für Checkbox-UI)
├── src/
│   ├── main.py              # FastAPI Entry Point
│   ├── crawler/
│   │   ├── spider_eko.py    # EKO Plus Scraper
│   │   ├── spider_wko.py    # WKO Scraper
│   │   ├── spider_firmenabc.py  # Firmenabc Scraper
│   │   └── base_spider.py   # Base-Klasse
│   ├── plz/
│   │   ├── radius_lookup.py # PLZ-Radius-Service
│   │   └── plz_database.py  # PLZ-Datenbank (AT)
│   ├── enrichment/
│   │   ├── website_analyzer.py  # Website-Crawling + Ollama NLP
│   │   ├── balance_sheet.py     # Firmenbuch API
│   │   └── scoring.py           # Fit-Score Engine
│   ├── api/
│   │   ├── routes.py        # FastAPI Routes
│   │   ├── auth.py          # API-Key Auth
│   │   └── models.py        # Pydantic Models
│   ├── db/
│   │   ├── supabase_client.py  # Supabase Connection
│   │   └── schemas.py          # DB-Schema Definition
│   └── export/
│       ├── csv_export.py    # CSV-Generator
│       └── json_export.py   # JSON-Export für API
├── tests/
│   ├── test_crawler.py
│   ├── test_plz_lookup.py
│   └── test_api.py
└── docs/
    ├── architecture.md      # Architektur-Docs
    ├── api.md               # API-Dokumentation
    └── legal.md             # Rechtliche Absicherung
```

---

## 🚀 Quick Start (geplant)

```bash
# 1. Clone
git clone https://github.com/blindidiotscout/lead-crawler.git
cd lead-crawler

# 2. Install
pip install -r requirements.txt

# 3. Config
cp config/settings.example.py config/settings.py
# Edit: Supabase-URL, API-Key, Ollama-Endpoint

# 4. Run Crawler
python src/main.py crawl --plz 2351 --radius 50 --branches IT,Recht

# 5. API Start
python src/main.py serve --port 8000

# 6. Test API
curl http://localhost:8000/api/companies?plz=2351&radius=50
```

---

## 🔑 API-Endpunkte (geplant)

| Methode | Endpunkt | Beschreibung |
|---------|----------|--------------|
| `POST` | `/api/crawl` | Startet neuen Crawl-Job |
| `GET` | `/api/companies` | Listet Unternehmen (filterbar) |
| `GET` | `/api/companies/{id}` | Details einzelnes Unternehmen |
| `GET` | `/api/plz/lookup` | PLZ-Radius-Lookup |
| `GET` | `/api/export/csv` | CSV-Export der Results |
| `GET` | `/api/health` | Health-Check |

**Auth:** API-Key via Header `X-API-Key: your-key`

---

## ⚖️ Rechtliches

- **robots.txt:** Wird strikt eingehalten (Scrapy built-in)
- **Terms of Service:** Jede Quelle wird geprüft vor Integration
- **DSGVO:** Nur Firmendaten (keine personenbezogenen Daten)
- **Rate-Limiting:** 1-2 Requests/Sekunde (nicht aggressiv)
- **User-Agent:** Echter Browser-String

**→ Risikostatus:** Low bei Einhaltung der obigen Punkte.

---

## 📅 Nächste Schritte

1. **PLZ-Datenbank** besorgen (AT-PLZ mit Koordinaten)
2. **Scrapy-Projekt** initialisieren (`scrapy startproject`)
3. **FastAPI-Grundgerüst** bauen (Hello-World API)
4. **Supabase-Schema** definieren (Companies-Table)
5. **EKO Plus Scraper** als ersten Spider implementieren
6. **Test-Run** mit 10-20 Unternehmen

---

## 📄 Lizenz

MIT License – für interne Nutzung (Max, Agentic Workflow Engineer)

---

*Erstellt: 2026-03-12 | Status: Initial Setup*
