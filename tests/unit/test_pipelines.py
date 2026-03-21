"""
Unit Tests für Pipeline Module
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add src directory to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from lead_crawler.models import (
    Address,
    BranchAnalysis,
    Company,
    CompanyMetadata,
    CompanySource,
    ContactInfo,
    LeadScore,
    LLMAnalysisResult,
    ScoreBreakdown,
)
from lead_crawler.pipelines.export import (
    ExportConfig,
    ExportPipeline,
    ExportResult,
    export_companies,
)
from lead_crawler.pipelines.lead_analysis import (
    BatchResult,
    LeadAnalysisPipeline,
    PipelineResult,
    PipelineStage,
    run_analysis,
)
from lead_crawler.services.llm_client import MockLLMClient


class TestPipelineResult:
    """Tests für PipelineResult"""

    def test_create_result(self):
        """PipelineResult erstellen"""
        company = Company(name="Test GmbH")
        result = PipelineResult(company=company)

        assert result.company.name == "Test GmbH"
        assert result.analysis is None
        assert result.score is None
        assert result.is_successful is False

    def test_result_with_score(self):
        """PipelineResult mit Score"""
        company = Company(name="Test GmbH")
        score = LeadScore.create(
            name="Test GmbH",
            breakdown=ScoreBreakdown(
                contact=20, location=15, branch=15, completeness=10, freshness=5, size=5
            ),
        )

        result = PipelineResult(
            company=company, score=score, stages_completed=[PipelineStage.SCORE]
        )

        assert result.is_successful is True
        assert result.score.total_score == 70.0

    def test_result_with_error(self):
        """PipelineResult mit Fehler"""
        company = Company(name="Test GmbH")
        result = PipelineResult(
            company=company, errors=[{"stage": "analyze", "error": "LLM failed"}]
        )

        assert result.is_successful is False

    def test_result_to_dict(self):
        """PipelineResult zu Dictionary"""
        company = Company(name="Test GmbH")
        result = PipelineResult(company=company, total_time=1.5)

        data = result.to_dict()
        assert "company" in data
        assert data["total_time"] == 1.5


class TestBatchResult:
    """Tests für BatchResult"""

    def test_create_batch(self):
        """BatchResult erstellen"""
        batch = BatchResult()
        assert batch.total == 0
        assert batch.successful == 0
        assert batch.failed == 0

    def test_add_result(self):
        """Ergebnis hinzufügen"""
        batch = BatchResult()

        # Erfolgreiches Ergebnis
        company = Company(name="Test GmbH")
        score = LeadScore.create(name="Test GmbH", breakdown=ScoreBreakdown(contact=25))
        result1 = PipelineResult(
            company=company, score=score, stages_completed=[PipelineStage.SCORE]
        )
        batch.add_result(result1)

        assert batch.total == 1
        assert batch.successful == 1
        assert batch.failed == 0

        # Fehlerhaftes Ergebnis
        result2 = PipelineResult(
            company=Company(name="Fehler AG"), errors=[{"stage": "analyze", "error": "Failed"}]
        )
        batch.add_result(result2)

        assert batch.total == 2
        assert batch.successful == 1
        assert batch.failed == 1

    def test_batch_with_progress(self):
        """Batch mit Progress-Callback"""
        progress_calls = []

        def callback(current, total):
            progress_calls.append((current, total))

        batch = BatchResult(progress_callback=callback)

        company = Company(name="Test GmbH")
        result = PipelineResult(company=company)
        batch.add_result(result)

        assert len(progress_calls) == 1
        assert progress_calls[0] == (1, 1)


class TestLeadAnalysisPipeline:
    """Tests für LeadAnalysisPipeline"""

    def test_create_pipeline(self):
        """Pipeline erstellen"""
        pipeline = LeadAnalysisPipeline()
        assert pipeline.settings is not None
        assert pipeline.cache is not None
        assert pipeline.llm_client is not None

    def test_analyze_simple_company(self):
        """Einfaches Unternehmen analysieren"""
        pipeline = LeadAnalysisPipeline()

        company = Company(
            name="Test GmbH",
            address=Address(plz="2351", ort="Guntramsdorf"),
            contact=ContactInfo(email="test@example.com"),
        )

        result = pipeline.analyze(company, skip_analysis=True)

        assert result.company.name == "Test GmbH"
        assert PipelineStage.EXTRACT not in result.stages_completed  # Keine Website

    def test_analyze_company_with_website(self):
        """Unternehmen mit Website analysieren (Mock)"""
        pipeline = LeadAnalysisPipeline()
        pipeline.llm_client = MockLLMClient()  # Mock für Tests

        company = Company(name="Test GmbH", contact=ContactInfo(website="https://example.com"))

        # Website-Extractor mocken
        with patch.object(pipeline.website_extractor, "extract") as mock_extract:
            from lead_crawler.services.website_extractor import WebsiteContent

            mock_extract.return_value = WebsiteContent(
                url="https://example.com",
                title="Test GmbH",
                meta_description="Test",
                main_text="We are a software company...",
                word_count=100,
            )

            # Cache mocken
            with patch.object(pipeline.cache, "get", return_value=None):
                with patch.object(pipeline.cache, "set"):
                    result = pipeline.analyze(company, skip_cache=True)

        assert result.company.name == "Test GmbH"
        # Mindestens Scoring sollte durchgeführt worden sein
        assert PipelineStage.SCORE in result.stages_completed

    def test_analyze_from_cache(self):
        """Analyse aus Cache laden"""
        pipeline = LeadAnalysisPipeline()

        company = Company(name="Test GmbH", contact=ContactInfo(website="https://example.com"))

        # Cache-Mock
        cached_data = {
            "branch": "IT",
            "confidence": 0.9,
            "services": ["Software"],
            "target_market": "B2B",
            "_cached_at": "2026-03-21T00:00:00",
        }

        with patch.object(pipeline.cache, "get", return_value=cached_data):
            result = pipeline.analyze(company)

        assert result.from_cache is True
        assert result.analysis is not None
        assert result.analysis.analysis.branch == "IT"

    def test_get_stats(self):
        """Pipeline-Statistiken"""
        pipeline = LeadAnalysisPipeline()

        company = Company(name="Test GmbH")
        result = PipelineResult(company=company, stages_completed=[PipelineStage.SCORE])
        result.is_successful  # Trigger property

        pipeline._stats["companies_processed"] = 5
        pipeline._stats["analyses_completed"] = 3
        pipeline._stats["cache_hits"] = 2

        stats = pipeline.get_stats()
        assert stats["companies_processed"] == 5
        assert stats["analyses_completed"] == 3
        assert stats["cache_hits"] == 2

    def test_reset_stats(self):
        """Statistiken zurücksetzen"""
        pipeline = LeadAnalysisPipeline()
        pipeline._stats["companies_processed"] = 10

        pipeline.reset_stats()
        stats = pipeline.get_stats()

        assert stats["companies_processed"] == 0


class TestExportPipeline:
    """Tests für ExportPipeline"""

    def test_create_pipeline(self):
        """Pipeline erstellen"""
        pipeline = ExportPipeline()
        assert pipeline.settings is not None

    def test_export_csv(self, tmp_path):
        """CSV-Export"""
        companies = [
            Company(
                name="Test GmbH",
                address=Address(plz="2351", ort="Guntramsdorf"),
                contact=ContactInfo(email="test@example.com"),
            ),
            Company(
                name="Test AG",
                address=Address(plz="1010", ort="Wien"),
                contact=ContactInfo(telefon="+43 1 234"),
            ),
        ]

        config = ExportConfig(output_path=tmp_path / "test.csv", output_format="csv")

        pipeline = ExportPipeline()
        result = pipeline.export(companies, config)

        assert result.is_successful
        assert result.total_companies == 2
        assert result.exported_companies == 2
        assert result.output_path.exists()

    def test_export_json(self, tmp_path):
        """JSON-Export"""
        companies = [
            Company(name="Test GmbH"),
        ]

        config = ExportConfig(output_path=tmp_path / "test.json", output_format="json")

        pipeline = ExportPipeline()
        result = pipeline.export(companies, config)

        assert result.is_successful
        assert result.output_path.exists()

        # JSON laden und prüfen
        with open(result.output_path) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["name"] == "Test GmbH"

    def test_export_jsonl(self, tmp_path):
        """JSONL-Export"""
        companies = [
            Company(name="Test GmbH"),
            Company(name="Test AG"),
        ]

        config = ExportConfig(output_path=tmp_path / "test.jsonl", output_format="jsonl")

        pipeline = ExportPipeline()
        result = pipeline.export(companies, config)

        assert result.is_successful

        # JSONL laden
        with open(result.output_path) as f:
            lines = f.readlines()
        assert len(lines) == 2

    def test_export_with_filter(self, tmp_path):
        """Export mit Score-Filter"""
        # Company mit hohem Score
        company_high = Company(
            name="High Score GmbH",
            score=LeadScore.create(
                name="High Score GmbH",
                breakdown=ScoreBreakdown(
                    contact=25, location=20, branch=20, completeness=15, freshness=10, size=10
                ),
            ),
        )

        # Company mit niedrigem Score
        company_low = Company(
            name="Low Score AG",
            score=LeadScore.create(
                name="Low Score AG",
                breakdown=ScoreBreakdown(
                    contact=5, location=5, branch=5, completeness=5, freshness=5, size=5
                ),
            ),
        )

        companies = [company_high, company_low]

        config = ExportConfig(
            output_path=tmp_path / "test.csv", output_format="csv", min_score=50  # Nur Scores >= 50
        )

        pipeline = ExportPipeline()
        result = pipeline.export(companies, config)

        assert result.exported_companies == 1  # Nur die mit hohem Score

    def test_export_with_priority_filter(self, tmp_path):
        """Export mit Priority-Filter"""
        # HIGH priority
        company_high = Company(
            name="High Priority GmbH",
            score=LeadScore.create(
                name="High Priority GmbH",
                breakdown=ScoreBreakdown(
                    contact=20, location=18, branch=18, completeness=12, freshness=8, size=8
                ),
            ),
        )
        company_high.score.priority = "HIGH"

        # LOW priority
        company_low = Company(
            name="Low Priority AG",
            score=LeadScore.create(
                name="Low Priority AG",
                breakdown=ScoreBreakdown(
                    contact=5, location=5, branch=5, completeness=5, freshness=5, size=5
                ),
            ),
        )
        company_low.score.priority = "LOW"

        companies = [company_high, company_low]

        config = ExportConfig(
            output_path=tmp_path / "test.csv", output_format="csv", min_priority="HIGH"
        )

        pipeline = ExportPipeline()
        result = pipeline.export(companies, config)

        assert result.exported_companies == 1


class TestConvenienceFunctions:
    """Tests für Convenience-Funktionen"""

    def test_run_analysis(self):
        """run_analysis Funktion"""
        companies = [
            Company(name="Test GmbH"),
        ]

        # Mit Mock-Pipeline
        with patch("lead_crawler.pipelines.lead_analysis.LeadAnalysisPipeline") as MockPipeline:
            mock_instance = MagicMock()
            mock_instance.analyze_batch.return_value = BatchResult()
            MockPipeline.return_value = mock_instance

            result = run_analysis(companies)

            assert isinstance(result, BatchResult)

    def test_export_companies(self, tmp_path):
        """export_companies Funktion"""
        companies = [
            Company(name="Test GmbH"),
        ]

        result = export_companies(companies, format="json", path=tmp_path / "test.json")

        assert result.is_successful


class TestScoreBreakdownExport:
    """Tests für ScoreBreakdown im Export"""

    def test_export_with_score_breakdown(self, tmp_path):
        """Export mit Score-Breakdown"""
        company = Company(
            name="Test GmbH",
            score=LeadScore.create(
                name="Test GmbH",
                breakdown=ScoreBreakdown(
                    contact=20, location=15, branch=18, completeness=12, freshness=8, size=7
                ),
            ),
        )

        config = ExportConfig(
            output_path=tmp_path / "test.csv",
            output_format="csv",
            fields=[
                "name",
                "score_total",
                "score_grade",
                "priority",
                "score_contact",
                "score_location",
            ],
        )

        pipeline = ExportPipeline()
        result = pipeline.export([company], config)

        assert result.is_successful

        # CSV lesen und prüfen
        with open(result.output_path) as f:
            content = f.read()
            assert "Test GmbH" in content
            assert "score_total" in content.lower() or "Total" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
