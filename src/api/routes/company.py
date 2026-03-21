"""
Company Routes
Unternehmens-Details und -Analysen
"""

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import (
    APIUser,
    get_analysis_pipeline,
    verify_api_key,
)
from api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    CompanyResponse,
    N8nAnalyzeRequest,
)
from lead_crawler.models import Company
from lead_crawler.pipelines import LeadAnalysisPipeline

router = APIRouter(prefix="/company", tags=["company"])


# Simulierte Company-Datenbank (in Produktion: echte Datenbank)
_companies_db: dict = {}


@router.get("/{company_id}", response_model=CompanyResponse, summary="Unternehmens-Details")
async def get_company(company_id: str, user: APIUser = Depends(verify_api_key)) -> CompanyResponse:
    """
    Gibt Details zu einem Unternehmen zurück.
    """
    # In Produktion: Datenbank-Abfrage
    if company_id not in _companies_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unternehmen {company_id} nicht gefunden"
        )

    company = _companies_db[company_id]
    return _company_to_response(company)


@router.post("/analyze", response_model=AnalyzeResponse, summary="Unternehmen analysieren")
async def analyze_company(
    request: AnalyzeRequest,
    user: APIUser = Depends(verify_api_key),
    pipeline: LeadAnalysisPipeline = Depends(get_analysis_pipeline),
) -> AnalyzeResponse:
    """
    Analysiert ein einzelnes Unternehmen mit LLM.

    Extrahiert Branchen-Informationen von der Website und berechnet Lead-Score.
    """
    # Company erstellen
    company = Company(name=request.company_name, contact={"website": request.website_url})

    # Analyse durchführen
    result = pipeline.analyze(
        company, skip_cache=request.skip_cache, skip_scoring=not request.include_scoring
    )

    # Response erstellen
    response = AnalyzeResponse(
        company_name=request.company_name,
        website_url=request.website_url,
        from_cache=result.from_cache,
        analyze_time=result.analyze_time,
    )

    if result.analysis and result.analysis.analysis:
        response.analysis = {
            "branch": result.analysis.analysis.branch,
            "confidence": result.analysis.analysis.confidence,
            "services": result.analysis.analysis.services,
            "target_market": result.analysis.analysis.target_market,
            "keywords": result.analysis.analysis.keywords,
            "reasoning": result.analysis.analysis.reasoning,
        }

    if result.score and request.include_scoring:
        response.score = {
            "total_score": result.score.total_score,
            "percentage": result.score.percentage,
            "grade": result.score.grade,
            "priority": result.score.priority,
            "breakdown": result.score.breakdown.to_dict(),
        }

    return response


@router.post("/analyze/n8n", response_model=AnalyzeResponse, summary="n8n Analyze")
async def n8n_analyze(
    request: N8nAnalyzeRequest,
    user: APIUser = Depends(verify_api_key),
    pipeline: LeadAnalysisPipeline = Depends(get_analysis_pipeline),
) -> AnalyzeResponse:
    """
    Vereinfachte Analyse für n8n Workflows.

    Analysiert ein einzelnes Unternehmen und gibt Branchen-Informationen zurück.
    """
    analyze_request = AnalyzeRequest(
        company_name=request.company_name,
        website_url=request.website,
        skip_cache=False,
        include_scoring=True,
    )

    return await analyze_company(analyze_request, user, pipeline)


def _company_to_response(company: Company) -> CompanyResponse:
    """Konvertiert Company zu Response"""
    from api.schemas import AddressSchema, CompanySourceEnum, ContactSchema

    return CompanyResponse(
        id=company.id,
        name=company.name,
        address=AddressSchema(
            street=company.address.street,
            plz=company.address.plz,
            ort=company.address.ort,
            bundesland=company.address.bundesland,
            country=company.address.country,
        ),
        contact=ContactSchema(
            telefon=company.contact.telefon,
            email=company.contact.email,
            website=company.contact.website,
            fax=company.contact.fax,
        ),
        branche=company.branche,
        source=CompanySourceEnum(company.metadata.source.value),
        source_url=company.metadata.source_url,
        crawled_at=company.metadata.crawled_at,
    )


def _store_company(company: Company) -> str:
    """Speichert Company in simulierter Datenbank"""
    import uuid

    if not company.id:
        company.id = str(uuid.uuid4())
    _companies_db[company.id] = company
    return company.id


__all__ = ["router"]
