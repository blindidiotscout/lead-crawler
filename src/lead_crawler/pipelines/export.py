"""
Export Pipeline
Export von Unternehmen in verschiedene Formate (CSV, JSON, Excel)
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
import csv
import json
import logging

from lead_crawler.config import get_settings, Settings
from lead_crawler.models import Company, LeadScore


@dataclass
class ExportConfig:
    """Konfiguration für Export"""
    # Output
    output_path: Optional[Path] = None
    output_format: str = "csv"  # csv, json, jsonl, excel

    # Filterung
    min_score: float = 0.0  # Minimale Score (0-100)
    max_score: float = 100.0  # Maximale Score
    min_priority: str = "LOW"  # LOW, MEDIUM, HIGH
    include_errors: bool = True  # Unternehmen mit Fehlern einschließen

    # Felder
    fields: Optional[List[str]] = None  # Zu exportierende Felder (None = alle)
    include_analysis: bool = True  # LLM-Analyse einschließen
    include_score: bool = True  # Score einschließen

    # Formatting
    date_format: str = "%Y-%m-%d %H:%M:%S"
    decimal_separator: str = "."  # Für CSV
    encoding: str = "utf-8"

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary"""
        return {
            'output_path': str(self.output_path) if self.output_path else None,
            'output_format': self.output_format,
            'min_score': self.min_score,
            'max_score': self.max_score,
            'min_priority': self.min_priority,
            'include_errors': self.include_errors,
            'fields': self.fields,
            'include_analysis': self.include_analysis,
            'include_score': self.include_score,
            'date_format': self.date_format,
            'decimal_separator': self.decimal_separator,
            'encoding': self.encoding
        }


@dataclass
class ExportResult:
    """Ergebnis eines Exports"""
    # Stats
    total_companies: int = 0
    exported_companies: int = 0
    filtered_companies: int = 0
    error_companies: int = 0

    # Output
    output_path: Optional[Path] = None
    output_size_bytes: int = 0

    # Timing
    export_time: float = 0.0

    # Errors
    errors: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary"""
        return {
            'total_companies': self.total_companies,
            'exported_companies': self.exported_companies,
            'filtered_companies': self.filtered_companies,
            'error_companies': self.error_companies,
            'output_path': str(self.output_path) if self.output_path else None,
            'output_size_bytes': self.output_size_bytes,
            'export_time': self.export_time,
            'errors': self.errors
        }

    @property
    def is_successful(self) -> bool:
        """True wenn Export erfolgreich"""
        return self.output_path is not None and len(self.errors) == 0


class ExportPipeline:
    """
    Pipeline für Export von Unternehmensdaten

    Unterstützte Formate:
    - CSV (Standard)
    - JSON (Array)
    - JSONL (Line-delimited)
    - Excel (mit pandas)

    Usage:
        pipeline = ExportPipeline()
        result = pipeline.export(companies, config)

        # Oder mit Convenience-Funktion:
        export_companies(companies, format="csv", path="output.csv")
    """

    # Standard-Felder für Export
    DEFAULT_FIELDS = [
        'name',
        'street',
        'plz',
        'ort',
        'bundesland',
        'telefon',
        'email',
        'website',
        'branche',
        'source',
        'branch',
        'confidence',
        'target_market',
        'services',
        'score_total',
        'score_grade',
        'priority'
    ]

    # Priorität für Filterung
    PRIORITY_ORDER = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialisiert Export-Pipeline

        Args:
            settings: Settings (default: aus get_settings())
        """
        self.settings = settings or get_settings()
        self.logger = logging.getLogger(self.__class__.__name__)

    def export(
        self,
        companies: List[Company],
        config: Optional[ExportConfig] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> ExportResult:
        """
        Exportiert Unternehmen in konfiguriertem Format

        Args:
            companies: Liste von Company-Objekten (mit optionaler Pipeline-Analyse)
            config: Export-Konfiguration
            progress_callback: Callback(current, total)

        Returns:
            ExportResult mit Export-Statistiken
        """
        import time
        start_time = time.time()

        config = config or ExportConfig()
        result = ExportResult()
        result.total_companies = len(companies)

        # Filtern
        filtered = self._filter_companies(companies, config, result)
        result.filtered_companies = len(filtered)

        # Output-Pfad bestimmen
        if config.output_path is None:
            output_dir = self.settings.output_dir
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = config.output_format
            config.output_path = output_dir / f"export_{timestamp}.{extension}"

        # Export durchführen
        try:
            if config.output_format == "csv":
                self._export_csv(filtered, config, result, progress_callback)
            elif config.output_format == "json":
                self._export_json(filtered, config, result, progress_callback)
            elif config.output_format == "jsonl":
                self._export_jsonl(filtered, config, result, progress_callback)
            elif config.output_format == "excel":
                self._export_excel(filtered, config, result, progress_callback)
            else:
                raise ValueError(f"Unknown format: {config.output_format}")

            # Dateigröße
            if config.output_path.exists():
                result.output_size_bytes = config.output_path.stat().st_size

            result.output_path = config.output_path

        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            result.errors.append({'error': str(e)})

        result.export_time = time.time() - start_time
        result.exported_companies = len(filtered)

        self.logger.info(
            f"Exported {result.exported_companies} companies to {result.output_path} "
            f"({result.output_size_bytes} bytes, {result.export_time:.2f}s)"
        )

        return result

    def _filter_companies(
        self,
        companies: List[Company],
        config: ExportConfig,
        result: ExportResult
    ) -> List[Company]:
        """Filtert Unternehmen nach Konfiguration"""
        filtered = []

        for company in companies:
            # Score prüfen
            if company.score:
                score_pct = company.score.percentage
                if score_pct < config.min_score or score_pct > config.max_score:
                    continue

                # Priority prüfen
                company_priority = self.PRIORITY_ORDER.get(company.score.priority, 0)
                min_priority = self.PRIORITY_ORDER.get(config.min_priority, 0)
                if company_priority < min_priority:
                    continue

            # Fehler prüfen
            if not config.include_errors:
                if company.metadata.raw_data and company.metadata.raw_data.get('error'):
                    result.error_companies += 1
                    continue

            filtered.append(company)

        return filtered

    def _prepare_row(self, company: Company, config: ExportConfig) -> Dict[str, Any]:
        """Bereitet eine Zeile für Export vor"""
        row = {}

        # Felder bestimmen
        fields = config.fields or self.DEFAULT_FIELDS

        # Basis-Daten
        base_data = {
            'name': company.name,
            'street': company.address.street,
            'plz': company.address.plz,
            'ort': company.address.ort,
            'bundesland': company.address.bundesland,
            'telefon': company.contact.telefon,
            'email': company.contact.email,
            'website': company.contact.website,
            'branche': company.branche,
            'source': company.metadata.source.value,
            'source_url': company.metadata.source_url,
            'crawled_at': company.metadata.crawled_at
        }

        # Analysis-Daten
        if config.include_analysis and company.llm_analysis and company.llm_analysis.analysis:
            analysis = company.llm_analysis.analysis
            analysis_data = {
                'branch': analysis.branch,
                'confidence': analysis.confidence,
                'target_market': analysis.target_market,
                'company_size_hint': analysis.company_size_hint,
                'services': ', '.join(analysis.services[:5]),  # Erste 5 Services
                'keywords': ', '.join(analysis.keywords[:5]),
                'reasoning': analysis.reasoning[:200] if analysis.reasoning else ''
            }
        else:
            analysis_data = {
                'branch': company.branche or '',
                'confidence': 0,
                'target_market': '',
                'company_size_hint': '',
                'services': '',
                'keywords': '',
                'reasoning': ''
            }

        # Score-Daten
        if config.include_score and company.score:
            score_data = {
                'score_total': company.score.total_score,
                'score_percentage': company.score.percentage,
                'score_grade': company.score.grade,
                'priority': company.score.priority,
                'score_contact': company.score.breakdown.contact,
                'score_location': company.score.breakdown.location,
                'score_branch': company.score.breakdown.branch,
                'score_completeness': company.score.breakdown.completeness
            }
        else:
            score_data = {
                'score_total': 0,
                'score_percentage': 0,
                'score_grade': 'F',
                'priority': 'LOW',
                'score_contact': 0,
                'score_location': 0,
                'score_branch': 0,
                'score_completeness': 0
            }

        # Alle Daten zusammenführen
        all_data = {**base_data, **analysis_data, **score_data}

        # Nur gewünschte Felder
        for field in fields:
            if field in all_data:
                row[field] = all_data[field]
            else:
                row[field] = ''

        return row

    def _export_csv(
        self,
        companies: List[Company],
        config: ExportConfig,
        result: ExportResult,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> None:
        """Exportiert als CSV"""
        fields = config.fields or self.DEFAULT_FIELDS

        with open(config.output_path, 'w', newline='', encoding=config.encoding) as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()

            for i, company in enumerate(companies):
                row = self._prepare_row(company, config)
                writer.writerow(row)

                if progress_callback:
                    progress_callback(i + 1, len(companies))

    def _export_json(
        self,
        companies: List[Company],
        config: ExportConfig,
        result: ExportResult,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> None:
        """Exportiert als JSON-Array"""
        rows = []

        for i, company in enumerate(companies):
            row = self._prepare_row(company, config)
            rows.append(row)

            if progress_callback:
                progress_callback(i + 1, len(companies))

        with open(config.output_path, 'w', encoding=config.encoding) as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)

    def _export_jsonl(
        self,
        companies: List[Company],
        config: ExportConfig,
        result: ExportResult,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> None:
        """Exportiert als JSONL (ein JSON pro Zeile)"""
        with open(config.output_path, 'w', encoding=config.encoding) as f:
            for i, company in enumerate(companies):
                row = self._prepare_row(company, config)
                f.write(json.dumps(row, ensure_ascii=False))
                f.write('\n')

                if progress_callback:
                    progress_callback(i + 1, len(companies))

    def _export_excel(
        self,
        companies: List[Company],
        config: ExportConfig,
        result: ExportResult,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> None:
        """Exportiert als Excel (benötigt pandas)"""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas required for Excel export: pip install pandas openpyxl")

        rows = []
        for i, company in enumerate(companies):
            row = self._prepare_row(company, config)
            rows.append(row)

            if progress_callback:
                progress_callback(i + 1, len(companies))

        df = pd.DataFrame(rows)
        df.to_excel(config.output_path, index=False, engine='openpyxl')


# Convenience-Funktionen
def export_companies(
    companies: List[Company],
    format: str = "csv",
    path: Optional[Path] = None,
    **kwargs
) -> ExportResult:
    """
    Convenience-Funktion für Export

    Usage:
        from lead_crawler.pipelines import export_companies

        result = export_companies(companies, format="csv", path="output.csv")
        print(f"Exported {result.exported_companies} companies")

        # Mit Filterung
        result = export_companies(
            companies,
            format="json",
            min_score=50,
            min_priority="MEDIUM"
        )
    """
    config = ExportConfig(
        output_path=path,
        output_format=format,
        **kwargs
    )

    pipeline = ExportPipeline()
    return pipeline.export(companies, config)


def export_to_csv(companies: List[Company], path: Path, **kwargs) -> ExportResult:
    """Exportiert als CSV"""
    return export_companies(companies, format="csv", path=path, **kwargs)


def export_to_json(companies: List[Company], path: Path, **kwargs) -> ExportResult:
    """Exportiert als JSON"""
    return export_companies(companies, format="json", path=path, **kwargs)


__all__ = [
    'ExportPipeline',
    'ExportConfig',
    'ExportResult',
    'export_companies',
    'export_to_csv',
    'export_to_json',
]