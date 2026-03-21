"""
Integration Tests für Pipelines
Testet End-to-End Workflows
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock
import tempfile

# Add src directory to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from lead_crawler.config import get_settings
from lead_crawler.models import Company
from lead_crawler.pipelines import LeadAnalysisPipeline, ExportPipeline, PipelineResult, BatchResult, ExportConfig
from tests.fixtures.sample_data import SAMPLE_COMPANIES


class TestLeadAnalysisPipelineUnit:
    """Unit Tests für LeadAnalysisPipeline"""

    @pytest.fixture
    def settings(self):
        """Gibt Test-Settings zurück"""
        return get_settings()

    @pytest.fixture
    def pipeline(self, settings):
        """Gibt eine Pipeline-Instanz zurück"""
        return LeadAnalysisPipeline(settings=settings)

    def test_pipeline_creation(self, pipeline):
        """Pipeline kann erstellt werden"""
        assert pipeline is not None
        assert pipeline.settings is not None

    def test_pipeline_result_creation(self):
        """PipelineResult wird korrekt erstellt"""
        result = PipelineResult(
            company=Company(name="Test"),
            analysis=None,
            score=None,
            from_cache=False,
            analyze_time=1.5
        )

        assert result.company.name == "Test"
        assert result.from_cache is False
        assert result.analyze_time == 1.5

    def test_pipeline_result_to_dict(self):
        """PipelineResult to_dict()"""
        company = Company(name="Test GmbH")
        result = PipelineResult(
            company=company,
            analysis=None,
            score=None,
            from_cache=True,
            analyze_time=0.5
        )

        result_dict = result.to_dict()
        assert "company" in result_dict
        assert result_dict["from_cache"] is True

    def test_batch_result_creation(self):
        """BatchResult wird korrekt erstellt"""
        result = BatchResult(
            results=[],
            total=0,
            successful=0,
            failed=0,
            total_time=0.0
        )

        assert result.total == 0
        assert result.successful == 0

    def test_batch_result_with_results(self):
        """BatchResult mit Ergebnissen"""
        results = [
            PipelineResult(company=Company(name="Test1"), analysis=None, score=None, from_cache=False, analyze_time=1.0),
            PipelineResult(company=Company(name="Test2"), analysis=None, score=None, from_cache=True, analyze_time=0.5)
        ]

        batch = BatchResult(
            results=results,
            total=2,
            successful=2,
            failed=0,
            total_time=1.5
        )

        assert batch.total == 2
        assert batch.successful == 2
        assert len(batch.results) == 2

    def test_batch_result_to_dict(self):
        """BatchResult to_dict()"""
        results = [PipelineResult(company=Company(name="Test"), analysis=None, score=None, from_cache=False, analyze_time=1.0)]
        batch = BatchResult(results=results, total=1, successful=1, failed=0, total_time=1.0)

        batch_dict = batch.to_dict()
        assert "results" in batch_dict
        assert batch_dict["total"] == 1


class TestLeadAnalysisPipelineIntegration:
    """Integration Tests für LeadAnalysisPipeline"""

    @pytest.fixture
    def settings(self):
        """Gibt Test-Settings zurück"""
        return get_settings()

    @pytest.fixture
    def mock_cache(self):
        """Gibt einen Mock-Cache zurück"""
        cache = Mock()
        cache.get.return_value = None
        cache.set.return_value = True
        cache.exists.return_value = False
        return cache

    @pytest.fixture
    def mock_llm(self):
        """Gibt einen Mock-LLM-Client zurück"""
        llm = Mock()
        llm.analyze_branch.return_value = Mock(
            branch="IT-Dienstleistungen",
            confidence=0.9,
            services=["Web", "Mobile"]
        )
        llm.is_available.return_value = True
        return llm

    @pytest.fixture
    def mock_extractor(self):
        """Gibt einen Mock-Website-Extractor zurück"""
        extractor = Mock()
        extractor.extract.return_value = Mock(
            url="https://test.at",
            title="Test Firma",
            main_text="Test content",
            about_text="About us",
            services_text="Our services"
        )
        return extractor

    def test_pipeline_analyze_mocked(self, settings, mock_cache, mock_llm, mock_extractor):
        """Pipeline analyze() mit gemockten Services"""
        pipeline = LeadAnalysisPipeline(settings=settings)
        pipeline.cache = mock_cache
        pipeline.llm_client = mock_llm
        pipeline.website_extractor = mock_extractor

        company = Company(name="Test GmbH")
        result = pipeline.analyze(company, skip_cache=True, skip_scoring=True)

        assert result is not None
        assert result.company.name == "Test GmbH"

    def test_pipeline_with_cache_hit(self, settings, mock_llm, mock_extractor):
        """Pipeline mit Cache-Hit"""
        # Mock-Cache mit vorhandenem Eintrag
        mock_cache = Mock()
        mock_cache.exists.return_value = True

        pipeline = LeadAnalysisPipeline(settings=settings)
        pipeline.cache = mock_cache
        pipeline.llm_client = mock_llm
        pipeline.website_extractor = mock_extractor

        company = Company(name="Test GmbH")
        result = pipeline.analyze(company, skip_cache=False, skip_scoring=True)

        assert result is not None


class TestExportPipelineUnit:
    """Unit Tests für ExportPipeline"""

    @pytest.fixture
    def settings(self):
        """Gibt Test-Settings zurück"""
        return get_settings()

    @pytest.fixture
    def pipeline(self, settings):
        """Gibt eine ExportPipeline-Instanz zurück"""
        return ExportPipeline(settings=settings)

    def test_export_pipeline_creation(self, pipeline):
        """ExportPipeline kann erstellt werden"""
        assert pipeline is not None
        assert pipeline.settings is not None

    def test_export_config_creation(self):
        """ExportConfig wird korrekt erstellt"""
        config = ExportConfig(
            output_format="csv",
            min_score=50
        )

        assert config.output_format == "csv"
        assert config.min_score == 50

    def test_export_config_defaults(self):
        """ExportConfig Default-Werte"""
        config = ExportConfig()

        # Default ist csv
        assert config.output_format == "csv"


class TestPipelineStage:
    """Tests für Pipeline Stage Enum"""

    def test_pipeline_stage_extract(self):
        """Stage: EXTRACT"""
        from lead_crawler.pipelines import PipelineStage

        stage = PipelineStage.EXTRACT
        assert stage.name == "EXTRACT"

    def test_pipeline_stage_analyze(self):
        """Stage: ANALYZE"""
        from lead_crawler.pipelines import PipelineStage

        stage = PipelineStage.ANALYZE
        assert stage.name == "ANALYZE"

    def test_pipeline_stage_cache(self):
        """Stage: CACHE"""
        from lead_crawler.pipelines import PipelineStage

        stage = PipelineStage.CACHE
        assert stage.name == "CACHE"

    def test_pipeline_stage_score(self):
        """Stage: SCORE"""
        from lead_crawler.pipelines import PipelineStage

        stage = PipelineStage.SCORE
        assert stage.name == "SCORE"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])