"""
Analyze Routes
Batch-Analyse und Job-Management
"""

import uuid
import asyncio
from typing import Dict, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse

from lead_crawler.pipelines import LeadAnalysisPipeline, BatchResult
from api.schemas import (
    AnalyzeBatchRequest,
    AnalyzeJobResponse,
    AnalyzeResponse,
    JobStatusEnum,
)
from api.dependencies import (
    get_analysis_pipeline,
    APIUser,
    verify_api_key,
)


router = APIRouter(prefix="/analyze", tags=["analyze"])


# Simulierte Job-Datenbank (in Produktion: Redis oder echte DB)
_jobs_db: Dict[str, dict] = {}


@router.post("/batch", response_model=AnalyzeJobResponse, summary="Batch-Analyse starten")
async def start_batch_analyze(
    request: AnalyzeBatchRequest,
    background_tasks: BackgroundTasks,
    user: APIUser = Depends(verify_api_key),
    pipeline: LeadAnalysisPipeline = Depends(get_analysis_pipeline)
) -> AnalyzeJobResponse:
    """
    Startet eine Batch-Analyse für mehrere Unternehmen.

    Der Job läuft im Hintergrund und kann über /analyze/{job_id} abgefragt werden.
    """
    # Job erstellen
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "job_type": "batch_analyze",
        "status": JobStatusEnum.PENDING,
        "progress": 0,
        "total": len(request.company_ids),
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "finished_at": None,
        "result": None,
        "error": None,
        "request": request.model_dump(),
    }
    _jobs_db[job_id] = job

    # Background Task starten
    background_tasks.add_task(
        _run_batch_analyze,
        job_id=job_id,
        company_ids=request.company_ids,
        skip_cache=request.skip_cache,
        include_scoring=request.include_scoring
    )

    return AnalyzeJobResponse(
        job_id=job_id,
        status=JobStatusEnum.PENDING,
        progress=0,
        total=len(request.company_ids)
    )


@router.get("/{job_id}", response_model=AnalyzeJobResponse, summary="Job-Status abrufen")
async def get_job_status(
    job_id: str,
    user: APIUser = Depends(verify_api_key)
) -> AnalyzeJobResponse:
    """
    Gibt den Status eines Analyse-Jobs zurück.
    """
    if job_id not in _jobs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} nicht gefunden"
        )

    job = _jobs_db[job_id]

    return AnalyzeJobResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        total=job["total"],
        result=job.get("result")
    )


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Job abbrechen")
async def cancel_job(
    job_id: str,
    user: APIUser = Depends(verify_api_key)
):
    """
    Bricht einen laufenden Job ab.
    """
    if job_id not in _jobs_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} nicht gefunden"
        )

    job = _jobs_db[job_id]

    if job["status"] == JobStatusEnum.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job bereits abgeschlossen"
        )

    job["status"] = JobStatusEnum.FAILED
    job["error"] = "Cancelled by user"
    job["finished_at"] = datetime.now().isoformat()

    return None


async def _run_batch_analyze(
    job_id: str,
    company_ids: list,
    skip_cache: bool,
    include_scoring: bool
):
    """Background Task für Batch-Analyse"""
    from lead_crawler.pipelines import get_llm_client, get_cache

    # Job-Status aktualisieren
    job = _jobs_db[job_id]
    job["status"] = JobStatusEnum.RUNNING
    job["started_at"] = datetime.now().isoformat()

    try:
        # Pipeline instanziieren
        pipeline = LeadAnalysisPipeline()

        # TODO: Unternehmen aus Datenbank laden
        # Für jetzt: Leere Liste
        companies = []

        # Progress Callback
        def progress_callback(current: int, total: int):
            job["progress"] = current

        # Batch-Analyse durchführen
        result = pipeline.analyze_batch(
            companies,
            skip_cache=skip_cache,
            progress_callback=progress_callback
        )

        # Job abschließen
        job["status"] = JobStatusEnum.COMPLETED
        job["finished_at"] = datetime.now().isoformat()
        job["result"] = result.to_dict()

    except Exception as e:
        job["status"] = JobStatusEnum.FAILED
        job["error"] = str(e)
        job["finished_at"] = datetime.now().isoformat()


__all__ = ["router"]