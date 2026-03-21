"""
Spider Runner Module
Einheitliche Factory und Runner für alle Spider/Crawler
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable
from pathlib import Path
import json
import logging

from lead_crawler.config import get_settings, Settings
from lead_crawler.crawlers.base import CrawlerResult, CrawlerStatus, CrawlerFactory
from lead_crawler.models import Company


@dataclass
class RunConfig:
    """Konfiguration für einen Crawler-Run"""
    # Crawler-Parameter
    crawler_name: str
    plz: Optional[str] = None
    ort: Optional[str] = None
    bundesland: Optional[str] = None
    radius_km: Optional[float] = None

    # Output-Optionen
    output_format: str = "json"  # json, jsonl, csv
    output_path: Optional[Path] = None
    dedup: bool = True

    # Limiting
    max_results: Optional[int] = None
    max_plz: Optional[int] = None

    # Callbacks
    on_company: Optional[Callable[[Company], None]] = None
    on_error: Optional[Callable[[Dict], None]] = None
    on_progress: Optional[Callable[[int, int], None]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary"""
        return {
            'crawler_name': self.crawler_name,
            'plz': self.plz,
            'ort': self.ort,
            'bundesland': self.bundesland,
            'radius_km': self.radius_km,
            'output_format': self.output_format,
            'output_path': str(self.output_path) if self.output_path else None,
            'dedup': self.dedup,
            'max_results': self.max_results,
            'max_plz': self.max_plz
        }


@dataclass
class RunResult:
    """Ergebnis eines Crawler-Runs mit Output-Informationen"""
    crawler_result: CrawlerResult
    config: RunConfig
    output_file: Optional[Path] = None
    success: bool = True
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary"""
        return {
            'success': self.success,
            'message': self.message,
            'config': self.config.to_dict(),
            'output_file': str(self.output_file) if self.output_file else None,
            'stats': {
                'total_companies': self.crawler_result.total,
                'total_errors': len(self.crawler_result.errors),
                'duration_seconds': self.crawler_result.duration_seconds,
                'status': self.crawler_result.status.value
            }
        }


class SpiderRunner:
    """
    Einheitliche Runner-Klasse für alle Crawler

    Features:
    - Einheitliche Schnittstelle für alle Crawler
    - Output in verschiedenen Formaten (JSON, JSONL, CSV)
    - Callbacks für Progress und Error-Handling
    - Deduplizierung
    - Result-Limiting

    Usage:
        from lead_crawler.runners import SpiderRunner

        runner = SpiderRunner()
        result = runner.run(plz="2351", radius_km=20)

        # Oder mit Config:
        config = RunConfig(
            crawler_name="wko",
            plz="2351",
            radius_km=20,
            output_format="csv"
        )
        result = runner.run_with_config(config)
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialisiert Runner

        Args:
            settings: Settings (default: aus get_settings())
        """
        self.settings = settings or get_settings()
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(
        self,
        crawler_name: str = "wko",
        plz: Optional[str] = None,
        ort: Optional[str] = None,
        bundesland: Optional[str] = None,
        radius_km: Optional[float] = None,
        output_format: str = "json",
        output_path: Optional[Path] = None,
        dedup: bool = True,
        max_results: Optional[int] = None,
        on_company: Optional[Callable[[Company], None]] = None,
        on_error: Optional[Callable[[Dict], None]] = None,
        **kwargs
    ) -> RunResult:
        """
        Führt Crawler mit Parametern aus

        Args:
            crawler_name: Name des Crawlers (default: "wko")
            plz: PLZ für Suche
            ort: Ortsname
            bundesland: Bundesland
            radius_km: Radius für PLZ-Suche
            output_format: Ausgabeformat (json, jsonl, csv)
            output_path: Ausgabedatei (optional)
            dedup: Duplikate entfernen
            max_results: Maximale Ergebnisse
            on_company: Callback für jedes gefundene Unternehmen
            on_error: Callback für jeden Fehler
            **kwargs: Zusätzliche Crawler-Parameter

        Returns:
            RunResult mit Ergebnissen
        """
        config = RunConfig(
            crawler_name=crawler_name,
            plz=plz,
            ort=ort,
            bundesland=bundesland,
            radius_km=radius_km,
            output_format=output_format,
            output_path=output_path,
            dedup=dedup,
            max_results=max_results,
            on_company=on_company,
            on_error=on_error
        )

        return self.run_with_config(config, **kwargs)

    def run_with_config(self, config: RunConfig, **kwargs) -> RunResult:
        """
        Führt Crawler mit RunConfig aus

        Args:
            config: RunConfig mit allen Parametern
            **kwargs: Zusätzliche Crawler-Parameter

        Returns:
            RunResult mit Ergebnissen
        """
        self.logger.info(f"Starting crawler '{config.crawler_name}'")

        try:
            # Crawler erstellen
            crawler = CrawlerFactory.create(config.crawler_name)

            # Crawler ausführen
            if config.radius_km:
                # Radius-Suche
                result = crawler.crawl_radius(
                    center_plz=config.plz,
                    radius_km=config.radius_km,
                    max_plz=config.max_plz,
                    dedup=config.dedup
                )
            else:
                # Normale Suche
                result = crawler.crawl(
                    plz=config.plz,
                    ort=config.ort,
                    bundesland=config.bundesland,
                    **kwargs
                )

            # Callbacks aufrufen
            if config.on_company:
                for company in result.companies:
                    config.on_company(company)

            if config.on_error:
                for error in result.errors:
                    config.on_error(error)

            # Limitieren falls gewünscht
            if config.max_results and len(result.companies) > config.max_results:
                result.companies = result.companies[:config.max_results]

            # Output schreiben
            output_file = None
            if config.output_path:
                output_file = self._write_output(result.companies, config)

            return RunResult(
                crawler_result=result,
                config=config,
                output_file=output_file,
                success=True,
                message=f"Found {len(result.companies)} companies"
            )

        except Exception as e:
            self.logger.error(f"Crawler failed: {e}")

            # Error Result
            error_result = CrawlerResult(
                errors=[{'error': str(e)}],
                status=CrawlerStatus.FAILED
            )

            return RunResult(
                crawler_result=error_result,
                config=config,
                success=False,
                message=str(e)
            )

    def _write_output(self, companies: List[Company], config: RunConfig) -> Path:
        """
        Schreibt Ergebnisse in Ausgabedatei

        Args:
            companies: Liste von Company-Objekten
            config: RunConfig mit Output-Einstellungen

        Returns:
            Pfad zur Ausgabedatei
        """
        output_path = config.output_path
        if output_path is None:
            # Default-Pfad
            output_dir = self.settings.output_dir
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = config.output_format
            output_path = output_dir / f"crawl_{timestamp}.{extension}"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if config.output_format == "json":
            self._write_json(companies, output_path)
        elif config.output_format == "jsonl":
            self._write_jsonl(companies, output_path)
        elif config.output_format == "csv":
            self._write_csv(companies, output_path)
        else:
            # Default: JSON
            self._write_json(companies, output_path)

        self.logger.info(f"Wrote {len(companies)} companies to {output_path}")
        return output_path

    def _write_json(self, companies: List[Company], path: Path) -> None:
        """Schreibt JSON-Datei"""
        data = [c.to_dict() for c in companies]
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _write_jsonl(self, companies: List[Company], path: Path) -> None:
        """Schreibt JSONL-Datei (ein JSON pro Zeile)"""
        with open(path, 'w', encoding='utf-8') as f:
            for company in companies:
                f.write(json.dumps(company.to_dict(), ensure_ascii=False))
                f.write('\n')

    def _write_csv(self, companies: List[Company], path: Path) -> None:
        """Schreibt CSV-Datei"""
        import csv

        if not companies:
            return

        # Felder aus erstem Company-Objekt
        first = companies[0].to_dict()
        fieldnames = list(first.keys())

        with open(path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for company in companies:
                writer.writerow(company.to_dict())


# Convenience-Funktionen
def run_wko(plz: Optional[str] = None, **kwargs) -> RunResult:
    """
    Führt WKO Crawler aus

    Args:
        plz: PLZ für Suche
        **kwargs: Zusätzliche Parameter

    Returns:
        RunResult
    """
    runner = SpiderRunner()
    return runner.run(crawler_name="wko", plz=plz, **kwargs)


def run_wko_radius(center_plz: str, radius_km: float = 20.0, **kwargs) -> RunResult:
    """
    Führt WKO Radius-Suche aus

    Args:
        center_plz: Zentrale PLZ
        radius_km: Radius in km
        **kwargs: Zusätzliche Parameter

    Returns:
        RunResult
    """
    runner = SpiderRunner()
    return runner.run(
        crawler_name="wko",
        plz=center_plz,
        radius_km=radius_km,
        **kwargs
    )


__all__ = [
    'SpiderRunner',
    'RunConfig',
    'RunResult',
    'run_wko',
    'run_wko_radius'
]