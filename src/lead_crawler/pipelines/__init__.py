"""
Lead Crawler Pipelines Package
End-to-End Workflows für Lead-Analyse und Export
"""

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

__all__ = [
    # Analysis Pipeline
    "LeadAnalysisPipeline",
    "PipelineResult",
    "PipelineStage",
    "BatchResult",
    "run_analysis",
    # Export Pipeline
    "ExportPipeline",
    "ExportConfig",
    "ExportResult",
    "export_companies",
]
