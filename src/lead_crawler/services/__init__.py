"""
Lead Crawler Services Package
Business Logic Services für Caching, LLM, Website Extraction, etc.
"""

from lead_crawler.services.cache import (
    CacheService,
    SQLiteCache,
    CacheEntry,
)

from lead_crawler.services.llm_client import (
    LLMClient,
    OllamaClient,
    MockLLMClient,
)

from lead_crawler.services.website_extractor import (
    WebsiteExtractor,
    WebsiteContent,
)

from lead_crawler.services.plz_service import (
    PLZService,
    PLZDatabase,
)

__all__ = [
    # Cache
    "CacheService",
    "SQLiteCache",
    "CacheEntry",
    # LLM
    "LLMClient",
    "OllamaClient",
    "MockLLMClient",
    # Website
    "WebsiteExtractor",
    "WebsiteContent",
    # PLZ
    "PLZService",
    "PLZDatabase",
]