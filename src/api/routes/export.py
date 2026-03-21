"""
Export Routes
Export von Unternehmensdaten
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from api.dependencies import (
    APIUser,
    get_export_pipeline,
    verify_api_key,
)
from api.schemas import (
    ExportRequest,
    ExportResponse,
    JobStatusEnum,
    N8nExportRequest,
)
from lead_crawler.models import Company
from lead_crawler.pipelines import ExportConfig, ExportPipeline

router = APIRouter(prefix="/export", tags=["export"])


# Simulierte Export-Datenbank (in Produktion: Redis oder echte DB)
_exports_db: dict[str, dict] = {}


@router.post("", response_model=ExportResponse, summary="Export starten")
async def start_export(
    request: ExportRequest,
    user: APIUser = Depends(verify_api_key),
    export_pipeline: ExportPipeline = Depends(get_export_pipeline),
) -> ExportResponse:
    """
    Startet einen Export von Unternehmensdaten.

    Unterstützt CSV, JSON, JSONL und Excel Formate.
    """
    # Export-ID generieren
    export_id = str(uuid.uuid4())

    # TODO: Unternehmen aus Datenbank laden basierend auf company_ids oder search_query
    # Für jetzt: Leere Liste
    companies: list[Company] = []

    # Export durchführen
    try:
        config = ExportConfig(
            output_format=request.format.value,
            min_score=request.min_score or 0,
            min_priority=request.min_priority.value if request.min_priority else "LOW",
        )

        result = export_pipeline.export(companies, config)

        # Response
        return ExportResponse(
            export_id=export_id,
            status=JobStatusEnum.COMPLETED,
            download_url=f"/export/{export_id}/download",
            total_companies=result.exported_companies,
            file_size_bytes=result.output_size_bytes,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export fehlgeschlagen: {str(e)}",
        )


@router.get("/{export_id}", response_model=ExportResponse, summary="Export-Status")
async def get_export_status(
    export_id: str, user: APIUser = Depends(verify_api_key)
) -> ExportResponse:
    """
    Gibt den Status eines Exports zurück.
    """
    if export_id not in _exports_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Export {export_id} nicht gefunden"
        )

    export = _exports_db[export_id]

    return ExportResponse(
        export_id=export_id,
        status=export["status"],
        download_url=export.get("download_url"),
        total_companies=export["total_companies"],
        file_size_bytes=export["file_size_bytes"],
    )


@router.get("/{export_id}/download", summary="Export herunterladen")
async def download_export(export_id: str, user: APIUser = Depends(verify_api_key)):
    """
    Lädt die Export-Datei herunter.
    """
    if export_id not in _exports_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Export {export_id} nicht gefunden"
        )

    export = _exports_db[export_id]

    if export["status"] != JobStatusEnum.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Export noch nicht abgeschlossen"
        )

    file_path = Path(export["file_path"])
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Export-Datei nicht gefunden"
        )

    return FileResponse(
        path=file_path, filename=file_path.name, media_type=_get_media_type(file_path.suffix)
    )


@router.post("/n8n", response_model=ExportResponse, summary="n8n Export")
async def n8n_export(
    request: N8nExportRequest,
    user: APIUser = Depends(verify_api_key),
    export_pipeline: ExportPipeline = Depends(get_export_pipeline),
) -> ExportResponse:
    """
    Vereinfachter Export für n8n Workflows.

    Exportiert Unternehmen im angegebenen Format und sendet optional an Webhook.
    """
    from lead_crawler.crawlers import WKOCrawler

    # Unternehmen suchen
    crawler = WKOCrawler()
    result = crawler.crawl(plz=request.plz, radius_km=request.radius)
    companies = result.companies[: request.limit]

    # Export durchführen
    config = ExportConfig(output_format=request.format)

    export_result = export_pipeline.export(companies, config)

    # Webhook senden falls angegeben
    if request.webhook_url:
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    request.webhook_url,
                    json={
                        "export_id": str(uuid.uuid4()),
                        "total_companies": export_result.exported_companies,
                        "file_path": str(export_result.output_path),
                    },
                )
        except Exception:
            pass  # Webhook-Fehler ignorieren

    return ExportResponse(
        export_id=str(uuid.uuid4()),
        status=JobStatusEnum.COMPLETED,
        download_url=str(export_result.output_path),
        total_companies=export_result.exported_companies,
        file_size_bytes=export_result.output_size_bytes,
    )


def _get_media_type(suffix: str) -> str:
    """Gibt Media-Type für Dateiendung zurück"""
    media_types = {
        ".csv": "text/csv",
        ".json": "application/json",
        ".jsonl": "application/jsonl",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
    }
    return media_types.get(suffix.lower(), "application/octet-stream")


__all__ = ["router"]
