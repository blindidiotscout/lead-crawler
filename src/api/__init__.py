"""
Lead Crawler API Package
FastAPI Backend für n8n Integration und externe Clients
"""

from api.main import app
from api.schemas import (
    # Request Models
    SearchRequest,
    AnalyzeRequest,
    ExportRequest,
    CompanyCreateRequest,
    # Response Models
    CompanyResponse,
    SearchResponse,
    AnalyzeResponse,
    ExportResponse,
    ErrorResponse,
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