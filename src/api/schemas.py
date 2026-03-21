"""
API Schemas
Pydantic Models für Request und Response
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

# Enums


class CompanySourceEnum(StrEnum):
    """Datenquelle für Unternehmen"""

    WKO = "firmen.wko.at"
    ECOPLUS = "ecoplus.at"
    MANUAL = "manual"
    API = "api"


class PriorityEnum(StrEnum):
    """Lead-Priorität"""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class GradeEnum(StrEnum):
    """Lead-Note"""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class ExportFormatEnum(StrEnum):
    """Export-Format"""

    CSV = "csv"
    JSON = "json"
    JSONL = "jsonl"
    EXCEL = "excel"


class JobStatusEnum(StrEnum):
    """Job-Status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Base Models


class BaseResponse(BaseModel):
    """Basis-Response mit Timestamp"""

    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseResponse):
    """Fehler-Response"""

    error: str
    detail: str | None = None
    code: str | None = None


# Address Schema


class AddressSchema(BaseModel):
    """Adresse"""

    street: str | None = None
    plz: str | None = None
    ort: str | None = None
    bundesland: str | None = None
    country: str = "Österreich"

    model_config = {"from_attributes": True}


# Contact Schema


class ContactSchema(BaseModel):
    """Kontaktinformationen"""

    telefon: str | None = None
    email: str | None = None
    website: str | None = None
    fax: str | None = None

    model_config = {"from_attributes": True}


# Company Schemas


class CompanyBase(BaseModel):
    """Basis-Unternehmensdaten"""

    name: str
    address: AddressSchema | None = None
    contact: ContactSchema | None = None
    branche: str | None = None


class CompanyCreateRequest(CompanyBase):
    """Request für neues Unternehmen"""

    pass


class CompanyResponse(BaseResponse):
    """Unternehmens-Details"""

    id: str | None = None
    name: str
    address: AddressSchema
    contact: ContactSchema
    branche: str | None = None
    source: CompanySourceEnum
    source_url: str | None = None
    crawled_at: str | None = None

    # LLM-Analyse (optional)
    branch: str | None = None
    confidence: float | None = None
    services: list[str] = []
    target_market: str | None = None

    # Score (optional)
    score_total: float | None = None
    score_grade: str | None = None
    priority: str | None = None

    model_config = {"from_attributes": True}


class CompanyListResponse(BaseResponse):
    """Liste von Unternehmen"""

    companies: list[CompanyResponse]
    total: int
    page: int = 1
    page_size: int = 50


# Search Schemas


class SearchRequest(BaseModel):
    """Such-Request"""

    plz: str | None = Field(None, description="4-stellige PLZ")
    ort: str | None = Field(None, description="Ortsname")
    bundesland: str | None = Field(None, description="Bundesland")
    radius_km: float | None = Field(None, ge=1, le=100, description="Radius in km")

    # Filter
    branche: str | None = None
    min_score: float | None = Field(None, ge=0, le=100)
    min_priority: PriorityEnum | None = None

    # Pagination
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=500)

    # Options
    include_analysis: bool = False
    include_score: bool = False


class SearchResponse(BaseResponse):
    """Such-Response"""

    query: dict[str, Any]
    results: list[CompanyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# Analyze Schemas


class AnalyzeRequest(BaseModel):
    """Analyse-Request"""

    company_name: str
    website_url: str
    skip_cache: bool = False
    include_scoring: bool = True


class AnalyzeBatchRequest(BaseModel):
    """Batch-Analyse-Request"""

    company_ids: list[str] = Field(..., max_length=100)
    skip_cache: bool = False
    include_scoring: bool = True


class AnalyzeResponse(BaseResponse):
    """Analyse-Response"""

    company_name: str
    website_url: str
    analysis: dict[str, Any] | None = None
    score: dict[str, Any] | None = None
    from_cache: bool = False
    analyze_time: float = 0.0


class AnalyzeJobResponse(BaseResponse):
    """Async Analyse-Job Response"""

    job_id: str
    status: JobStatusEnum
    progress: int = 0
    total: int = 0
    result: dict[str, Any] | None = None


# Export Schemas


class ExportRequest(BaseModel):
    """Export-Request"""

    company_ids: list[str] | None = None
    search_query: dict[str, Any] | None = None
    format: ExportFormatEnum = ExportFormatEnum.CSV
    fields: list[str] | None = None
    min_score: float | None = None
    min_priority: PriorityEnum | None = None


class ExportResponse(BaseResponse):
    """Export-Response"""

    export_id: str
    status: JobStatusEnum
    download_url: str | None = None
    total_companies: int = 0
    file_size_bytes: int = 0


# PLZ Schemas


class PLZInfoResponse(BaseResponse):
    """PLZ-Informationen"""

    plz: str
    orte: list[str]
    bundesland: str
    coordinates: list[dict[str, float]]


class PLZRadiusSearchRequest(BaseModel):
    """PLZ-Radius-Suche Request"""

    plz: str = Field(..., min_length=4, max_length=4, description="4-stellige PLZ")
    radius_km: float = Field(20.0, ge=1, le=100, description="Radius in km")


class PLZRadiusSearchResponse(BaseResponse):
    """PLZ-Radius-Suche Response"""

    center_plz: str
    radius_km: float
    results: list[dict[str, Any]]
    count: int


# Health & Status


class HealthResponse(BaseResponse):
    """Health-Check Response"""

    status: str = "ok"
    version: str = "2.0.0"
    services: dict[str, bool] = {}
    uptime_seconds: float = 0.0


class StatusResponse(BaseResponse):
    """Status-Response"""

    status: str = "running"
    active_jobs: int = 0
    cache_size: int = 0
    last_crawl: str | None = None


# Job Management


class JobStatusResponse(BaseResponse):
    """Job-Status Response"""

    job_id: str
    job_type: str
    status: JobStatusEnum
    progress: int = 0
    total: int = 0
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


# Request Models für n8n Integration


class N8nSearchRequest(BaseModel):
    """Vereinfachter Request für n8n Workflows"""

    plz: str = Field(..., description="PLZ für die Suche")
    radius: int = Field(20, ge=1, le=100, description="Radius in km")
    limit: int = Field(100, ge=1, le=500, description="Maximale Ergebnisse")


class N8nAnalyzeRequest(BaseModel):
    """Vereinfachter Analyse-Request für n8n"""

    company_name: str
    website: str


class N8nExportRequest(BaseModel):
    """Vereinfachter Export-Request für n8n"""

    plz: str
    radius: int = 20
    format: str = "json"
    webhook_url: str | None = None


__all__ = [
    # Enums
    "CompanySourceEnum",
    "PriorityEnum",
    "GradeEnum",
    "ExportFormatEnum",
    "JobStatusEnum",
    # Base
    "BaseResponse",
    "ErrorResponse",
    # Address & Contact
    "AddressSchema",
    "ContactSchema",
    # Company
    "CompanyBase",
    "CompanyCreateRequest",
    "CompanyResponse",
    "CompanyListResponse",
    # Search
    "SearchRequest",
    "SearchResponse",
    # Analyze
    "AnalyzeRequest",
    "AnalyzeBatchRequest",
    "AnalyzeResponse",
    "AnalyzeJobResponse",
    # Export
    "ExportRequest",
    "ExportResponse",
    # PLZ
    "PLZInfoResponse",
    "PLZRadiusSearchRequest",
    "PLZRadiusSearchResponse",
    # Health & Status
    "HealthResponse",
    "StatusResponse",
    "JobStatusResponse",
    # n8n
    "N8nSearchRequest",
    "N8nAnalyzeRequest",
    "N8nExportRequest",
]
