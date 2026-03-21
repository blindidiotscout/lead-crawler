"""
API Routes Package
FastAPI Router für verschiedene Endpoints
"""

from api.routes.analyze import router as analyze_router
from api.routes.company import router as company_router
from api.routes.export import router as export_router
from api.routes.search import router as search_router

__all__ = [
    "search_router",
    "company_router",
    "analyze_router",
    "export_router",
]
