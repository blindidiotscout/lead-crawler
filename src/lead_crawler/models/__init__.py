"""
Lead Crawler Models Package
Domain Models für Unternehmen, Analyse, Scoring und PLZ
"""

# Company Models
from lead_crawler.models.company import (
    Company,
    Address,
    ContactInfo,
    CompanyMetadata,
    CompanySource,
)

# Analysis Models
from lead_crawler.models.analysis import (
    BranchAnalysis,
    LLMAnalysisResult,
    CacheEntry,
    TargetMarket,
    CompanySize,
)

# Scoring Models
from lead_crawler.models.scoring import (
    LeadScore,
    ScoreBreakdown,
    ScoreGrade,
    Priority,
    DEFAULT_WEIGHTS,
)

# PLZ Models
from lead_crawler.models.plz import (
    PLZCoordinate,
    PLZInfo,
    PLZSearchResult,
    Bundesland,
    plz_to_bundesland,
    is_valid_plz,
    PLZ_BUNDESLAND_PREFIX,
)

__all__ = [
    # Company
    "Company",
    "Address",
    "ContactInfo",
    "CompanyMetadata",
    "CompanySource",
    # Analysis
    "BranchAnalysis",
    "LLMAnalysisResult",
    "CacheEntry",
    "TargetMarket",
    "CompanySize",
    # Scoring
    "LeadScore",
    "ScoreBreakdown",
    "ScoreGrade",
    "Priority",
    "DEFAULT_WEIGHTS",
    # PLZ
    "PLZCoordinate",
    "PLZInfo",
    "PLZSearchResult",
    "Bundesland",
    "plz_to_bundesland",
    "is_valid_plz",
    "PLZ_BUNDESLAND_PREFIX",
]