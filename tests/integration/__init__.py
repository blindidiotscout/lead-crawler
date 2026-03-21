"""
Integration Tests Package
Tests die externe Dienste benötigen (Crawler, LLM, etc.)
"""

from tests.fixtures.sample_data import (
    SAMPLE_ANALYSIS,
    SAMPLE_COMPANIES,
    SAMPLE_COMPANY,
    SAMPLE_PLZ_DATA,
)

__all__ = [
    "SAMPLE_COMPANY",
    "SAMPLE_COMPANIES",
    "SAMPLE_ANALYSIS",
    "SAMPLE_PLZ_DATA",
]
