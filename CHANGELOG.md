# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-03-21

### Added

#### Core Architecture
- **Domain Models Package** (`lead_crawler/models/`)
  - `Company`, `Address`, `ContactInfo`, `CompanyMetadata`
  - `BranchAnalysis`, `LLMAnalysisResult`, `CacheEntry`
  - `LeadScore`, `ScoreBreakdown`, `ScoreCategory`
  - `PLZCoordinate`, `PLZInfo`, `PLZSearchResult`

- **Configuration System** (`lead_crawler/config.py`)
  - Centralized Settings with environment variables
  - OllamaConfig, CacheConfig, PLZConfig, CrawlerConfig, ScoringConfig, APIConfig
  - `.env` file support

- **Services Layer** (`lead_crawler/services/`)
  - `SQLiteCache` - LRU Cache with TTL support
  - `OllamaClient` - LLM integration for local Ollama
  - `MockLLMClient` - Testing without LLM
  - `WebsiteExtractor` - Text extraction from websites
  - `PLZService` - PLZ radius search for Austria

- **Crawler Architecture** (`lead_crawler/crawlers/`)
  - `BaseCrawler` - Abstract base class for crawlers
  - `WKOCrawler` - WKO (Wirtschaftskammer) crawler
  - `CrawlerResult` - Standardized result format

- **Pipeline Pattern** (`lead_crawler/pipelines/`)
  - `LeadAnalysisPipeline` - End-to-end analysis workflow
  - `ExportPipeline` - CSV/JSON/Excel export
  - `PipelineResult`, `BatchResult` - Result containers
  - `PipelineStage` - Stage enum (Extract → Analyze → Cache → Score)

- **FastAPI Backend** (`api/`)
  - RESTful API with OpenAPI documentation
  - `/search` - PLZ/Radius search
  - `/company/analyze` - Single company analysis
  - `/analyze/batch` - Batch analysis with background jobs
  - `/export` - Multi-format export
  - `/n8n` endpoints for n8n workflow integration
  - API Key authentication

- **Streamlit Frontend** (`web/`)
  - Multi-page Streamlit app
  - `1_Search.py` - Company search
  - `2_Analysis.py` - Statistics
  - `3_Export.py` - Data export
  - `4_Settings.py` - Configuration
  - Reusable UI components

#### Testing
- **Unit Tests** (146 tests)
  - Models, Config, Services, Crawlers, Pipelines, Web, API
- **Integration Tests** (13 tests)
  - Crawlers, LLM Client, Pipelines
- **Test Fixtures** (`tests/fixtures/`)
  - Sample data for testing
- **pytest.ini** configuration with markers

#### CI/CD
- **GitHub Actions** (`.github/workflows/`)
  - `test.yml` - Run tests on push/PR
  - `release.yml` - Publish to PyPI
  - Dependabot for dependency updates
- **pyproject.toml** - Modern Python packaging
- **Coverage reports** via Codecov

### Changed

- **BREAKING**: Complete package restructure
  - Old: `from src.scraper import run_spider`
  - New: `from lead_crawler.crawlers import WKOCrawler`

- **BREAKING**: Import paths changed
  - `src.scraper` → `lead_crawler.crawlers.wko`
  - `src.scoring` → `lead_crawler.models.scoring`
  - `src.llm_pipeline` → `lead_crawler.pipelines.lead_analysis`
  - `src.analysis_cache` → `lead_crawler.services.cache`
  - `src.plz_radius` → `lead_crawler.services.plz_service`

### Removed

- **Legacy files** moved to `legacy/` folder (reference only)
  - `scraper.py`
  - `enhanced_scraper.py`
  - `scoring.py`
  - `enhanced_scoring.py`
  - `llm_pipeline.py`
  - `llm_analyzer.py`
  - `website_crawler.py`
  - `analysis_cache.py`
  - `plz_radius.py`
  - `csv_export.py`

### Fixed

- Proper separation of concerns
- Type hints throughout
- Comprehensive docstrings
- Test coverage for all modules

### Security

- API Key authentication for API endpoints
- Input validation via Pydantic
- Rate limiting ready (middleware)

---

## [1.0.0] - 2026-03-19

### Added
- Initial WKO spider implementation
- PLZ radius search
- LLM analysis with Ollama
- Lead scoring engine
- CSV export
- Analysis cache (SQLite)

---

[2.0.0]: https://github.com/blindidiotscout/lead-crawler/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/blindidiotscout/lead-crawler/releases/tag/v1.0.0