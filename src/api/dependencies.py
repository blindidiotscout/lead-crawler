"""
API Dependencies
Dependency Injection für FastAPI Endpoints
"""

from typing import Optional, Generator
from functools import lru_cache

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from lead_crawler.config import get_settings, Settings
from lead_crawler.services.cache import SQLiteCache, get_cache
from lead_crawler.services.llm_client import LLMClient, OllamaClient, MockLLMClient, get_llm_client
from lead_crawler.services.website_extractor import WebsiteExtractor, get_website_extractor
from lead_crawler.services.plz_service import PLZService, get_plz_service
from lead_crawler.crawlers import CrawlerFactory
from lead_crawler.pipelines import LeadAnalysisPipeline, ExportPipeline


# API Key Security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIUser(BaseModel):
    """API User Info"""
    api_key: str
    is_admin: bool = False


@lru_cache()
def get_settings_cached() -> Settings:
    """Gibt gecachte Settings zurück"""
    return get_settings()


def get_cache_service() -> SQLiteCache:
    """Gibt Cache-Service zurück"""
    return get_cache()


def get_llm_service() -> LLMClient:
    """Gibt LLM-Client zurück"""
    return get_llm_client()


def get_website_extractor_service() -> WebsiteExtractor:
    """Gibt Website-Extractor zurück"""
    return get_website_extractor()


def get_plz_service_dep() -> PLZService:
    """Gibt PLZ-Service zurück"""
    return get_plz_service()


def get_analysis_pipeline(
    settings: Settings = Depends(get_settings_cached),
    cache: SQLiteCache = Depends(get_cache_service),
    llm: LLMClient = Depends(get_llm_service),
    extractor: WebsiteExtractor = Depends(get_website_extractor_service),
    plz: PLZService = Depends(get_plz_service_dep)
) -> LeadAnalysisPipeline:
    """Gibt Analysis-Pipeline zurück (mit injected Services)"""
    pipeline = LeadAnalysisPipeline(settings=settings)
    pipeline.cache = cache
    pipeline.llm_client = llm
    pipeline.website_extractor = extractor
    pipeline.plz_service = plz
    return pipeline


def get_export_pipeline(
    settings: Settings = Depends(get_settings_cached)
) -> ExportPipeline:
    """Gibt Export-Pipeline zurück"""
    return ExportPipeline(settings=settings)


async def verify_api_key(
    api_key: Optional[str] = Security(api_key_header),
    settings: Settings = Depends(get_settings_cached)
) -> APIUser:
    """
    Verifiziert API-Key

    Wenn keine API-Keys konfiguriert sind, ist jeder Request erlaubt.
    Wenn API-Keys konfiguriert sind, muss ein gültiger Key vorhanden sein.
    """
    # Wenn keine API-Keys konfiguriert: Auth deaktiviert
    if not settings.api.api_keys:
        return APIUser(api_key="anonymous", is_admin=True)

    # API-Key prüfen
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key required. Provide X-API-Key header."
        )

    if api_key not in settings.api.api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )

    # Admin-Key prüfen (erster Key in der Liste ist Admin)
    is_admin = api_key == settings.api.api_keys[0] if settings.api.api_keys else False

    return APIUser(api_key=api_key, is_admin=is_admin)


async def get_optional_api_key(
    api_key: Optional[str] = Security(api_key_header),
    settings: Settings = Depends(get_settings_cached)
) -> Optional[APIUser]:
    """
    Optionale API-Key Verifizierung

    Gibt None zurück wenn kein Key vorhanden und Auth deaktiviert.
    Wirft Exception wenn Key vorhanden aber ungültig.
    """
    if not settings.api.api_keys:
        return None

    if api_key is None:
        return None

    return await verify_api_key(api_key, settings)


# Pagination Dependencies

class PaginationParams(BaseModel):
    """Pagination Parameter"""
    page: int = 1
    page_size: int = 50

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def get_pagination(
    page: int = 1,
    page_size: int = 50
) -> PaginationParams:
    """Extrahiert Pagination-Parameter"""
    return PaginationParams(page=max(1, page), page_size=min(500, max(1, page_size)))


# Filter Dependencies

class CompanyFilter(BaseModel):
    """Filter für Unternehmens-Suche"""
    branche: Optional[str] = None
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    min_priority: Optional[str] = None
    include_analysis: bool = False
    include_score: bool = False


def get_company_filter(
    branche: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    min_priority: Optional[str] = None,
    include_analysis: bool = False,
    include_score: bool = False
) -> CompanyFilter:
    """Extrahiert Filter-Parameter"""
    return CompanyFilter(
        branche=branche,
        min_score=min_score,
        max_score=max_score,
        min_priority=min_priority,
        include_analysis=include_analysis,
        include_score=include_score
    )


__all__ = [
    # Security
    "verify_api_key",
    "get_optional_api_key",
    "APIUser",
    # Services
    "get_settings_cached",
    "get_cache_service",
    "get_llm_service",
    "get_website_extractor_service",
    "get_plz_service_dep",
    "get_analysis_pipeline",
    "get_export_pipeline",
    # Pagination
    "PaginationParams",
    "get_pagination",
    # Filter
    "CompanyFilter",
    "get_company_filter",
]