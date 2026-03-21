"""
Lead Crawler Models Package
Domain Models für Unternehmen, Analyse, Scoring und PLZ
"""

# Company Models
# Analysis Models
from lead_crawler.models.analysis import (
    BranchAnalysis,
    CacheEntry,
    CompanySize,
    LLMAnalysisResult,
    TargetMarket,
)
from lead_crawler.models.company import (
    Address,
    Company,
    CompanyMetadata,
    CompanySource,
    ContactInfo,
)

# PLZ Models
from lead_crawler.models.plz import (
    PLZ_BUNDESLAND_PREFIX,
    Bundesland,
    PLZCoordinate,
    PLZInfo,
    PLZSearchResult,
    is_valid_plz,
    plz_to_bundesland,
)

# Scoring Models
from lead_crawler.models.scoring import (
    DEFAULT_WEIGHTS,
    LeadScore,
    Priority,
    ScoreBreakdown,
    ScoreGrade,
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
