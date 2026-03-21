"""
Lead Crawler Pipelines Package
End-to-End Workflows für Lead-Analyse und Export
"""

from lead_crawler.pipelines.lead_analysis import (
    LeadAnalysisPipeline,
    PipelineResult,
    PipelineStage,
    BatchResult,
    run_analysis,
)

from lead_crawler.pipelines.export import (
    ExportPipeline,
    ExportConfig,
    ExportResult,
    export_companies,
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