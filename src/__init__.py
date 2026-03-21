"""
Lead Crawler - Legacy Compatibility Layer

This module provides backward-compatible imports from the old locations.
For new code, import directly from `lead_crawler` package.

Example:
    # Old (deprecated):
    from src.scraper import run_spider
    from src.scoring import LeadScorer
    
    # New (recommended):
    from lead_crawler.crawlers import WKOCrawler
    from lead_crawler.models import LeadScore
"""

# Re-export from new package for backward compatibility
# Note: Legacy files moved to legacy/ folder
# Use: from lead_crawler import ...

__all__ = [
    # Import from new package instead
    "WKOCrawler",
    "LeadAnalysisPipeline",
    "ExportPipeline",
    "Company",
    "LeadScore",
]

# Recommended imports:
from lead_crawler.crawlers import WKOCrawler
from lead_crawler.pipelines import LeadAnalysisPipeline, ExportPipeline
from lead_crawler.models import Company, LeadScore

# Deprecation warning
import warnings
warnings.warn(
    "Importing from 'src' is deprecated. Use 'from lead_crawler import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)