"""
Search Routes
PLZ/Radius Suche und Unternehmens-Suche
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status

from lead_crawler.config import Settings
from lead_crawler.models import Company
from lead_crawler.services.plz_service import PLZService
from lead_crawler.crawlers import WKOCrawler, CrawlerResult
from api.schemas import (
    SearchRequest,
    SearchResponse,
    CompanyResponse,
    PLZRadiusSearchRequest,
    PLZRadiusSearchResponse,
    PLZInfoResponse,
    N8nSearchRequest,
)
from api.dependencies import (
    get_plz_service_dep,
    get_pagination,
    get_company_filter,
    PaginationParams,
    CompanyFilter,
    APIUser,
    verify_api_key,
)


router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse, summary="Unternehmens-Suche")
async def search_companies(
    request: SearchRequest,
    user: APIUser = Depends(verify_api_key)
) -> SearchResponse:
    """
    Durchsucht Unternehmen nach PLZ, Ort oder Bundesland.

    Unterstützt Radius-Suche um eine PLZ und Filterung nach Score/Priorität.
    """
    # Crawler instanziieren
    crawler = WKOCrawler()

    # Suche durchführen
    if request.plz and request.radius_km:
        # Radius-Suche
        result = crawler.crawl_radius(
            center_plz=request.plz,
            radius_km=request.radius_km
        )
    else:
        # Normale Suche
        result = crawler.crawl(
            plz=request.plz,
            ort=request.ort,
            bundesland=request.bundesland
        )

    # Filter anwenden
    companies = result.companies

    if request.branche:
        companies = [c for c in companies if c.branche and request.branche.lower() in c.branche.lower()]

    if request.min_score is not None:
        companies = [c for c in companies if c.score and c.score.percentage >= request.min_score]

    if request.min_priority:
        priority_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        min_prio = priority_order.get(request.min_priority, 0)
        companies = [c for c in companies if c.score and priority_order.get(c.score.priority, 0) >= min_prio]

    # Pagination
    total = len(companies)
    start = (request.page - 1) * request.page_size
    end = start + request.page_size
    companies_page = companies[start:end]

    # Response erstellen
    company_responses = [
        _company_to_response(c, request.include_analysis, request.include_score)
        for c in companies_page
    ]

    return SearchResponse(
        query={
            "plz": request.plz,
            "ort": request.ort,
            "bundesland": request.bundesland,
            "radius_km": request.radius_km,
            "branche": request.branche,
            "min_score": request.min_score,
            "min_priority": request.min_priority,
        },
        results=company_responses,
        total=total,
        page=request.page,
        page_size=request.page_size,
        total_pages=(total + request.page_size - 1) // request.page_size
    )


@router.get("/plz/{plz}", response_model=PLZInfoResponse, summary="PLZ-Informationen")
async def get_plz_info(
    plz: str,
    user: APIUser = Depends(verify_api_key),
    plz_service: PLZService = Depends(get_plz_service_dep)
) -> PLZInfoResponse:
    """
    Gibt Informationen zu einer PLZ zurück (Orte, Koordinaten).
    """
    if not plz.isdigit() or len(plz) != 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PLZ muss 4-stellig sein"
        )

    info = plz_service.get_plz_info(plz)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PLZ {plz} nicht gefunden"
        )

    return PLZInfoResponse(
        plz=info.plz,
        orte=info.orte,
        bundesland=info.bundesland,
        coordinates=[{"lat": c.lat, "lon": c.lon} for c in info.coordinates]
    )


@router.post("/radius", response_model=PLZRadiusSearchResponse, summary="PLZ-Radius-Suche")
async def search_plz_radius(
    request: PLZRadiusSearchRequest,
    user: APIUser = Depends(verify_api_key),
    plz_service: PLZService = Depends(get_plz_service_dep)
) -> PLZRadiusSearchResponse:
    """
    Findet alle PLZ im angegebenen Radius um eine Ziel-PLZ.
    """
    if not request.plz.isdigit() or len(request.plz) != 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PLZ muss 4-stellig sein"
        )

    try:
        result = plz_service.find_in_radius(request.plz, request.radius_km)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    results = [
        {
            "plz": coord.plz,
            "ort": coord.ort,
            "bundesland": coord.bundesland,
            "distance_km": dist
        }
        for coord, dist in result.results
    ]

    return PLZRadiusSearchResponse(
        center_plz=request.plz,
        radius_km=request.radius_km,
        results=results,
        count=len(results)
    )


@router.post("/n8n", response_model=SearchResponse, summary="n8n Search")
async def n8n_search(
    request: N8nSearchRequest,
    user: APIUser = Depends(verify_api_key)
) -> SearchResponse:
    """
    Vereinfachte Suche für n8n Workflows.

    Gibt Unternehmen im angegebenen Radius um eine PLZ zurück.
    """
    crawler = WKOCrawler()

    result = crawler.crawl_radius(
        center_plz=request.plz,
        radius_km=request.radius,
        max_plz=request.limit
    )

    # Limitieren
    companies = result.companies[:request.limit]

    company_responses = [_company_to_response(c, False, False) for c in companies]

    return SearchResponse(
        query={"plz": request.plz, "radius_km": request.radius},
        results=company_responses,
        total=len(companies),
        page=1,
        page_size=request.limit,
        total_pages=1
    )


def _company_to_response(
    company: Company,
    include_analysis: bool = False,
    include_score: bool = False
) -> CompanyResponse:
    """Konvertiert Company zu Response"""
    from api.schemas import AddressSchema, ContactSchema, CompanySourceEnum

    response = CompanyResponse(
        id=company.id,
        name=company.name,
        address=AddressSchema(
            street=company.address.street,
            plz=company.address.plz,
            ort=company.address.ort,
            bundesland=company.address.bundesland,
            country=company.address.country
        ),
        contact=ContactSchema(
            telefon=company.contact.telefon,
            email=company.contact.email,
            website=company.contact.website,
            fax=company.contact.fax
        ),
        branche=company.branche,
        source=CompanySourceEnum(company.metadata.source.value),
        source_url=company.metadata.source_url,
        crawled_at=company.metadata.crawled_at
    )

    # LLM-Analyse hinzufügen
    if include_analysis and company.llm_analysis and company.llm_analysis.analysis:
        response.branch = company.llm_analysis.analysis.branch
        response.confidence = company.llm_analysis.analysis.confidence
        response.services = company.llm_analysis.analysis.services
        response.target_market = company.llm_analysis.analysis.target_market

    # Score hinzufügen
    if include_score and company.score:
        response.score_total = company.score.total_score
        response.score_grade = company.score.grade
        response.priority = company.score.priority

    return response


__all__ = ["router"]