"""
Test Fixtures Package
Sample Data und Fixtures für Tests
"""

from tests.fixtures.sample_data import (
    EXPORT_TEST_DATA,
    SAMPLE_ANALYSIS,
    SAMPLE_CACHE_ENTRY,
    SAMPLE_COMPANIES,
    SAMPLE_COMPANY,
    SAMPLE_CRAWLER_RESULT,
    SAMPLE_LLM_RESPONSE,
    SAMPLE_PLZ_DATA,
    SAMPLE_SCORE_RESULT,
    SAMPLE_WEBSITE_CONTENT,
    SAMPLE_WKO_HTML,
    get_sample_companies,
    get_sample_company,
    get_sample_plz_data,
)

__all__ = [
    "SAMPLE_COMPANY",
    "SAMPLE_COMPANIES",
    "SAMPLE_ANALYSIS",
    "SAMPLE_PLZ_DATA",
    "SAMPLE_CACHE_ENTRY",
    "SAMPLE_CRAWLER_RESULT",
    "SAMPLE_WEBSITE_CONTENT",
    "SAMPLE_SCORE_RESULT",
    "SAMPLE_LLM_RESPONSE",
    "SAMPLE_WKO_HTML",
    "EXPORT_TEST_DATA",
    "get_sample_company",
    "get_sample_companies",
    "get_sample_plz_data",
]
