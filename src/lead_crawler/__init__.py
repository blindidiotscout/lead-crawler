"""
Lead Crawler Package
Automatisierte Lead-Generierung für KMU in Österreich
"""

__version__ = "2.0.0"

from lead_crawler.models import (
    Company,
    Address,
    ContactInfo,
    CompanyMetadata,
    CompanySource,
    BranchAnalysis,
    LLMAnalysisResult,
    LeadScore,
    ScoreBreakdown,
    PLZInfo,
    PLZCoordinate,
)

from lead_crawler.config import (
    Settings,
    OllamaConfig,
    CacheConfig,
    PLZConfig,
    CrawlerConfig,
    ScoringConfig,
    APIConfig,
    get_settings,
    reset_settings,
)

from lead_crawler.services import (
    SQLiteCache,
    LLMClient,
    OllamaClient,
    MockLLMClient,
    WebsiteExtractor,
    WebsiteContent,
    PLZService,
    PLZDatabase,
    get_cache,
    get_llm_client,
    get_website_extractor,
    get_plz_service,
)

from lead_crawler.crawlers import (
    BaseCrawler,
    CrawlerResult,
    CrawlerStatus,
    CrawlerFactory,
    WKOCrawler,
    crawl_wko,
)

from lead_crawler.runners import (
    SpiderRunner,
    RunConfig,
    RunResult,
    run_wko,
    run_wko_radius,
)

from lead_crawler.pipelines import (
    LeadAnalysisPipeline,
    PipelineResult,
    PipelineStage,
    run_analysis,
    ExportPipeline,
    ExportConfig,
    export_companies,
)

__all__ = [
    # Models
    "Company",
    "Address",
    "ContactInfo",
    "CompanyMetadata",
    "CompanySource",
    "BranchAnalysis",
    "LLMAnalysisResult",
    "LeadScore",
    "ScoreBreakdown",
    "PLZInfo",
    "PLZCoordinate",
    # Config
    "Settings",
    "OllamaConfig",
    "CacheConfig",
    "PLZConfig",
    "CrawlerConfig",
    "ScoringConfig",
    "APIConfig",
    "get_settings",
    "reset_settings",
    # Services
    "SQLiteCache",
    "LLMClient",
    "OllamaClient",
    "MockLLMClient",
    "WebsiteExtractor",
    "WebsiteContent",
    "PLZService",
    "PLZDatabase",
    "get_cache",
    "get_llm_client",
    "get_website_extractor",
    "get_plz_service",
    # Crawlers
    "BaseCrawler",
    "CrawlerResult",
    "CrawlerStatus",
    "CrawlerFactory",
    "WKOCrawler",
    "crawl_wko",
    # Runners
    "SpiderRunner",
    "RunConfig",
    "RunResult",
    "run_wko",
    "run_wko_radius",
    # Pipelines
    "LeadAnalysisPipeline",
    "PipelineResult",
    "PipelineStage",
    "run_analysis",
    "ExportPipeline",
    "ExportConfig",
    "export_companies",
]