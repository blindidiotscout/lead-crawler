"""
Lead Crawler API
FastAPI Backend für n8n Integration und externe Clients
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import analyze_router, company_router, export_router, search_router
from api.schemas import HealthResponse, StatusResponse
from lead_crawler.config import get_settings


# Startup/Shutdown Context Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup und Shutdown Handler"""
    # Startup
    start_time = time.time()
    app.state.start_time = start_time
    print("[API] Lead Crawler API starting...")
    print(f"[API] Version: {app.version}")

    yield

    # Shutdown
    print("[API] Lead Crawler API shutting down...")


# App erstellen
app = FastAPI(
    title="Lead Crawler API",
    description="""
API für automatisierte Lead-Generierung für KMU in Österreich.

## Features

- **Unternehmens-Suche**: Suche nach PLZ, Ort oder Radius
- **Branchen-Analyse**: LLM-basierte Branchen-Erkennung
- **Lead-Scoring**: Automatische Bewertung von Leads
- **Export**: CSV, JSON, JSONL, Excel Formate

## Authentication

Bei konfigurierten API-Keys muss der `X-API-Key` Header gesendet werden.

## n8n Integration

Vereinfachte Endpoints für n8n Workflows:
- `/search/n8n` - Einfache PLZ-Suche
- `/company/analyze/n8n` - Einfache Analyse
- `/export/n8n` - Einfacher Export
""",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# CORS Middleware
settings = get_settings()
if settings.api.cors_origins and settings.api.cors_origins != ["*"]:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Router einbinden
app.include_router(search_router, prefix="/api/v1")
app.include_router(company_router, prefix="/api/v1")
app.include_router(analyze_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")


# Health Check
@app.get("/", response_model=HealthResponse, tags=["health"])
async def root() -> HealthResponse:
    """
    Root Endpoint mit API-Informationen.
    """
    services = {"cache": True, "llm": True, "crawler": True}  # Wird beim ersten Request geprüft

    return HealthResponse(
        status="ok",
        version="2.0.0",
        services=services,
        uptime_seconds=(
            time.time() - app.state.start_time if hasattr(app.state, "start_time") else 0
        ),
    )


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    """
    Health Check Endpoint.
    """
    services = {"cache": True, "llm": True, "crawler": True}

    return HealthResponse(
        status="ok",
        version="2.0.0",
        services=services,
        uptime_seconds=(
            time.time() - app.state.start_time if hasattr(app.state, "start_time") else 0
        ),
    )


@app.get("/status", response_model=StatusResponse, tags=["health"])
async def status_check() -> StatusResponse:
    """
    Detaillierter Status Endpoint.
    """
    return StatusResponse(
        status="running",
        active_jobs=0,  # TODO: Echte Job-Anzahl
        cache_size=0,  # TODO: Echte Cache-Größe
        last_crawl=None,
    )


# Error Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Globaler Error Handler"""
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc), "code": "INTERNAL_ERROR"},
    )


# Custom OpenAPI Schema für n8n
@app.get("/openapi-n8n.json")
async def get_openapi_n8n():
    """
    OpenAPI Schema mit nur n8n-relevanten Endpoints.
    """
    from fastapi.openapi.utils import get_openapi

    schema = get_openapi(
        title="Lead Crawler API (n8n)",
        version="2.0.0",
        routes=app.routes,
        tags=[
            {"name": "search", "description": "Suche nach Unternehmen"},
            {"name": "company", "description": "Unternehmens-Details"},
            {"name": "export", "description": "Export von Daten"},
        ],
    )

    # Nur n8n-relevante Endpoints behalten
    n8n_paths = {
        path: schema["paths"][path]
        for path in schema["paths"]
        if "/n8n" in path or path in ["/", "/health"]
    }
    schema["paths"] = n8n_paths

    return schema


# Run mit: uvicorn api.main:app --reload
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app", host=settings.api.host, port=settings.api.port, reload=settings.api.debug
    )


__all__ = ["app"]
