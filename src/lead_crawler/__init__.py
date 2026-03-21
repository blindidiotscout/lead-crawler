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

__all__ = [
    # Models
    "Company",
    "Address",
    "ContactInfo",
    "CompanyMetadata",
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
]