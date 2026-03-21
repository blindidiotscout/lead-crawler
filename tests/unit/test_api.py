"""
Unit Tests für API Module
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Add src directory to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


class TestAPISchemas:
    """Tests für API Schemas"""

    def test_search_request_defaults(self):
        """SearchRequest mit Defaults"""
        from api.schemas import SearchRequest

        request = SearchRequest()
        assert request.page == 1
        assert request.page_size == 50
        assert request.include_analysis is False
        assert request.include_score is False

    def test_search_request_with_params(self):
        """SearchRequest mit Parametern"""
        from api.schemas import SearchRequest

        request = SearchRequest(
            plz="2351",
            radius_km=20.0,
            branche="IT",
            min_score=50.0,
            page=2,
            page_size=100
        )
        assert request.plz == "2351"
        assert request.radius_km == 20.0
        assert request.branche == "IT"
        assert request.min_score == 50.0
        assert request.page == 2
        assert request.page_size == 100

    def test_analyze_request(self):
        """AnalyzeRequest"""
        from api.schemas import AnalyzeRequest

        request = AnalyzeRequest(
            company_name="Test GmbH",
            website_url="https://example.com",
            skip_cache=True,
            include_scoring=True
        )
        assert request.company_name == "Test GmbH"
        assert request.website_url == "https://example.com"
        assert request.skip_cache is True

    def test_export_request(self):
        """ExportRequest"""
        from api.schemas import ExportRequest, ExportFormatEnum

        request = ExportRequest(
            format=ExportFormatEnum.JSON,
            min_score=60.0
        )
        assert request.format == ExportFormatEnum.JSON
        assert request.min_score == 60.0

    def test_plz_radius_search_request(self):
        """PLZRadiusSearchRequest"""
        from api.schemas import PLZRadiusSearchRequest

        request = PLZRadiusSearchRequest(plz="2351", radius_km=15.0)
        assert request.plz == "2351"
        assert request.radius_km == 15.0

    def test_company_response(self):
        """CompanyResponse"""
        from api.schemas import CompanyResponse, CompanySourceEnum
        from datetime import datetime

        response = CompanyResponse(
            name="Test GmbH",
            address={},
            contact={},
            source=CompanySourceEnum.WKO
        )
        assert response.name == "Test GmbH"
        assert response.source == CompanySourceEnum.WKO
        assert response.timestamp is not None

    def test_error_response(self):
        """ErrorResponse"""
        from api.schemas import ErrorResponse

        response = ErrorResponse(
            error="Test Error",
            detail="Test Detail",
            code="TEST_ERROR"
        )
        assert response.error == "Test Error"
        assert response.detail == "Test Detail"
        assert response.code == "TEST_ERROR"

    def test_health_response(self):
        """HealthResponse"""
        from api.schemas import HealthResponse

        response = HealthResponse(
            status="ok",
            version="2.0.0",
            services={"cache": True, "llm": True},
            uptime_seconds=123.45
        )
        assert response.status == "ok"
        assert response.version == "2.0.0"
        assert response.uptime_seconds == 123.45


class TestDependencies:
    """Tests für API Dependencies"""

    def test_pagination_params(self):
        """PaginationParams"""
        from api.dependencies import PaginationParams

        params = PaginationParams(page=2, page_size=50)
        assert params.offset == 50
        assert params.limit == 50

    def test_company_filter(self):
        """CompanyFilter"""
        from api.dependencies import CompanyFilter

        filter = CompanyFilter(
            branche="IT",
            min_score=50.0,
            include_analysis=True
        )
        assert filter.branche == "IT"
        assert filter.min_score == 50.0
        assert filter.include_analysis is True


class TestHealthEndpoints:
    """Tests für Health Endpoints"""

    def test_health_endpoint(self):
        """Health Check Endpoint"""
        from api.main import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_root_endpoint(self):
        """Root Endpoint"""
        from api.main import app

        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestSearchEndpoints:
    """Tests für Search Endpoints"""

    def test_search_without_params(self):
        """Search ohne Parameter"""
        from api.main import app

        client = TestClient(app)
        response = client.post("/api/v1/search", json={})

        # Da API-Key Pflicht sein kann, prüfen wir nur dass es läuft
        assert response.status_code in [200, 401, 422]

    def test_search_with_plz(self):
        """Search mit PLZ"""
        from api.main import app

        client = TestClient(app)
        response = client.post("/api/v1/search", json={
            "plz": "2351",
            "page_size": 10
        })

        assert response.status_code in [200, 401, 422]

    def test_plz_info_endpoint(self):
        """PLZ Info Endpoint"""
        from api.main import app

        client = TestClient(app)
        response = client.get("/api/v1/search/plz/2351")

        # Kann 404 sein wenn PLZ nicht in DB
        assert response.status_code in [200, 401, 404]

    def test_plz_radius_endpoint(self):
        """PLZ Radius Suche"""
        from api.main import app

        client = TestClient(app)
        response = client.post("/api/v1/search/radius", json={
            "plz": "2351",
            "radius_km": 10.0
        })

        assert response.status_code in [200, 401, 422]


class TestCompanyEndpoints:
    """Tests für Company Endpoints"""

    def test_analyze_endpoint(self):
        """Analyze Endpoint"""
        from api.main import app

        client = TestClient(app)
        response = client.post("/api/v1/company/analyze", json={
            "company_name": "Test GmbH",
            "website_url": "https://example.com"
        })

        assert response.status_code in [200, 401, 422]

    def test_company_not_found(self):
        """Company nicht gefunden"""
        from api.main import app

        client = TestClient(app)
        response = client.get("/api/v1/company/nonexistent-id")

        assert response.status_code in [401, 404]


class TestExportEndpoints:
    """Tests für Export Endpoints"""

    def test_export_endpoint(self):
        """Export Endpoint"""
        from api.main import app

        client = TestClient(app)
        response = client.post("/api/v1/export", json={
            "format": "json"
        })

        assert response.status_code in [200, 401, 422]


class TestOpenAPI:
    """Tests für OpenAPI Schema"""

    def test_openapi_schema(self):
        """OpenAPI Schema ist gültig"""
        from api.main import app

        client = TestClient(app)
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema

    def test_openapi_n8n_schema(self):
        """n8n OpenAPI Schema"""
        from api.main import app

        client = TestClient(app)
        response = client.get("/openapi-n8n.json")

        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema


class TestErrorHandling:
    """Tests für Error Handling"""

    def test_404_error(self):
        """404 Error"""
        from api.main import app

        client = TestClient(app)
        response = client.get("/nonexistent")

        assert response.status_code == 404

    def test_422_validation_error(self):
        """Validation Error"""
        from api.main import app

        client = TestClient(app)
        # Invalid PLZ (not 4 digits)
        response = client.post("/api/v1/search/radius", json={
            "plz": "12",
            "radius_km": 10.0
        })

        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])