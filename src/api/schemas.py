"""
API Schemas
Pydantic Models für Request und Response
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, HttpUrl


# Enums

class CompanySourceEnum(str, Enum):
    """Datenquelle für Unternehmen"""
    WKO = "firmen.wko.at"
    ECOPLUS = "ecoplus.at"
    MANUAL = "manual"
    API = "api"


class PriorityEnum(str, Enum):
    """Lead-Priorität"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class GradeEnum(str, Enum):
    """Lead-Note"""
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class ExportFormatEnum(str, Enum):
    """Export-Format"""
    CSV = "csv"
    JSON = "json"
    JSONL = "jsonl"
    EXCEL = "excel"


class JobStatusEnum(str, Enum):
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
    detail: Optional[str] = None
    code: Optional[str] = None


# Address Schema

class AddressSchema(BaseModel):
    """Adresse"""
    street: Optional[str] = None
    plz: Optional[str] = None
    ort: Optional[str] = None
    bundesland: Optional[str] = None
    country: str = "Österreich"

    model_config = {"from_attributes": True}


# Contact Schema

class ContactSchema(BaseModel):
    """Kontaktinformationen"""
    telefon: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    fax: Optional[str] = None

    model_config = {"from_attributes": True}


# Company Schemas

class CompanyBase(BaseModel):
    """Basis-Unternehmensdaten"""
    name: str
    address: Optional[AddressSchema] = None
    contact: Optional[ContactSchema] = None
    branche: Optional[str] = None


class CompanyCreateRequest(CompanyBase):
    """Request für neues Unternehmen"""
    pass


class CompanyResponse(BaseResponse):
    """Unternehmens-Details"""
    id: Optional[str] = None
    name: str
    address: AddressSchema
    contact: ContactSchema
    branche: Optional[str] = None
    source: CompanySourceEnum
    source_url: Optional[str] = None
    crawled_at: Optional[str] = None

    # LLM-Analyse (optional)
    branch: Optional[str] = None
    confidence: Optional[float] = None
    services: List[str] = []
    target_market: Optional[str] = None

    # Score (optional)
    score_total: Optional[float] = None
    score_grade: Optional[str] = None
    priority: Optional[str] = None

    model_config = {"from_attributes": True}


class CompanyListResponse(BaseResponse):
    """Liste von Unternehmen"""
    companies: List[CompanyResponse]
    total: int
    page: int = 1
    page_size: int = 50


# Search Schemas

class SearchRequest(BaseModel):
    """Such-Request"""
    plz: Optional[str] = Field(None, description="4-stellige PLZ")
    ort: Optional[str] = Field(None, description="Ortsname")
    bundesland: Optional[str] = Field(None, description="Bundesland")
    radius_km: Optional[float] = Field(None, ge=1, le=100, description="Radius in km")

    # Filter
    branche: Optional[str] = None
    min_score: Optional[float] = Field(None, ge=0, le=100)
    min_priority: Optional[PriorityEnum] = None

    # Pagination
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=500)

    # Options
    include_analysis: bool = False
    include_score: bool = False


class SearchResponse(BaseResponse):
    """Such-Response"""
    query: Dict[str, Any]
    results: List[CompanyResponse]
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
    company_ids: List[str] = Field(..., max_length=100)
    skip_cache: bool = False
    include_scoring: bool = True


class AnalyzeResponse(BaseResponse):
    """Analyse-Response"""
    company_name: str
    website_url: str
    analysis: Optional[Dict[str, Any]] = None
    score: Optional[Dict[str, Any]] = None
    from_cache: bool = False
    analyze_time: float = 0.0


class AnalyzeJobResponse(BaseResponse):
    """Async Analyse-Job Response"""
    job_id: str
    status: JobStatusEnum
    progress: int = 0
    total: int = 0
    result: Optional[Dict[str, Any]] = None


# Export Schemas

class ExportRequest(BaseModel):
    """Export-Request"""
    company_ids: Optional[List[str]] = None
    search_query: Optional[Dict[str, Any]] = None
    format: ExportFormatEnum = ExportFormatEnum.CSV
    fields: Optional[List[str]] = None
    min_score: Optional[float] = None
    min_priority: Optional[PriorityEnum] = None


class ExportResponse(BaseResponse):
    """Export-Response"""
    export_id: str
    status: JobStatusEnum
    download_url: Optional[str] = None
    total_companies: int = 0
    file_size_bytes: int = 0


# PLZ Schemas

class PLZInfoResponse(BaseResponse):
    """PLZ-Informationen"""
    plz: str
    orte: List[str]
    bundesland: str
    coordinates: List[Dict[str, float]]


class PLZRadiusSearchRequest(BaseModel):
    """PLZ-Radius-Suche Request"""
    plz: str = Field(..., min_length=4, max_length=4, description="4-stellige PLZ")
    radius_km: float = Field(20.0, ge=1, le=100, description="Radius in km")


class PLZRadiusSearchResponse(BaseResponse):
    """PLZ-Radius-Suche Response"""
    center_plz: str
    radius_km: float
    results: List[Dict[str, Any]]
    count: int


# Health & Status

class HealthResponse(BaseResponse):
    """Health-Check Response"""
    status: str = "ok"
    version: str = "2.0.0"
    services: Dict[str, bool] = {}
    uptime_seconds: float = 0.0


class StatusResponse(BaseResponse):
    """Status-Response"""
    status: str = "running"
    active_jobs: int = 0
    cache_size: int = 0
    last_crawl: Optional[str] = None


# Job Management

class JobStatusResponse(BaseResponse):
    """Job-Status Response"""
    job_id: str
    job_type: str
    status: JobStatusEnum
    progress: int = 0
    total: int = 0
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


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
    webhook_url: Optional[str] = None


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