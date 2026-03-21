"""
Lead Crawler Services Package
Business Logic Services für Caching, LLM, Website Extraction, etc.
"""

from lead_crawler.services.cache import (
    SQLiteCache,
    get_cache,
    reset_cache,
)

from lead_crawler.services.llm_client import (
    LLMClient,
    OllamaClient,
    MockLLMClient,
    LLMResponse,
    get_llm_client,
    reset_llm_client,
)

from lead_crawler.services.website_extractor import (
    WebsiteExtractor,
    WebsiteContent,
    get_website_extractor,
    reset_extractor,
    quick_extract,
)

from lead_crawler.services.plz_service import (
    PLZService,
    PLZDatabase,
    HaversineCalculator,
    get_plz_service,
    reset_plz_service,
    seed_sample_data,
)

__all__ = [
    # Cache
    "SQLiteCache",
    "get_cache",
    "reset_cache",
    # LLM
    "LLMClient",
    "OllamaClient",
    "MockLLMClient",
    "LLMResponse",
    "get_llm_client",
    "reset_llm_client",
    # Website
    "WebsiteExtractor",
    "WebsiteContent",
    "get_website_extractor",
    "reset_extractor",
    "quick_extract",
    # PLZ
    "PLZService",
    "PLZDatabase",
    "HaversineCalculator",
    "get_plz_service",
    "reset_plz_service",
    "seed_sample_data",
]