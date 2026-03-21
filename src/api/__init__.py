"""
Lead Crawler API Package
FastAPI Backend für n8n Integration und externe Clients
"""

from api.main import app
from api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    CompanyCreateRequest,
    # Response Models
    CompanyResponse,
    ErrorResponse,
    ExportRequest,
    ExportResponse,
    # Request Models
    SearchRequest,
    SearchResponse,
)

__all__ = [
    # App
    "app",
    # Schemas
    "SearchRequest",
    "AnalyzeRequest",
    "ExportRequest",
    "CompanyCreateRequest",
    "CompanyResponse",
    "SearchResponse",
    "AnalyzeResponse",
    "ExportResponse",
    "ErrorResponse",
]
