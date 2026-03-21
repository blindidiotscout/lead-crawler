"""
Lead Analysis Pipeline
End-to-End Pipeline für Branchen-Analyse mit Caching und Scoring
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any, Callable
import time
import logging

from lead_crawler.config import get_settings, Settings
from lead_crawler.models import (
    Company,
    BranchAnalysis,
    LLMAnalysisResult,
    LeadScore,
    ScoreBreakdown,
)
from lead_crawler.services.cache import get_cache, reset_cache
from lead_crawler.services.llm_client import get_llm_client, MockLLMClient
from lead_crawler.services.website_extractor import get_website_extractor, WebsiteContent
from lead_crawler.services.plz_service import get_plz_service
from lead_crawler.crawlers.base import CrawlerResult


class PipelineStage(Enum):
    """Pipeline-Stufen"""
    CRAWL = "crawl"
    EXTRACT = "extract"
    ANALYZE = "analyze"
    CACHE = "cache"
    SCORE = "score"
    EXPORT = "export"


@dataclass
class PipelineResult:
    """Ergebnis der Lead-Analysis-Pipeline"""
    # Company
    company: Company

    # Analysis
    analysis: Optional[LLMAnalysisResult] = None

    # Score
    score: Optional[LeadScore] = None

    # Pipeline Stats
    stages_completed: List[PipelineStage] = field(default_factory=list)
    errors: List[Dict[str, str]] = field(default_factory=list)

    # Timing
    total_time: float = 0.0
    crawl_time: float = 0.0
    analyze_time: float = 0.0

    # Cache
    from_cache: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary"""
        return {
            'company': self.company.to_dict(),
            'analysis': self.analysis.to_dict() if self.analysis else None,
            'score': self.score.to_dict() if self.score else None,
            'stages_completed': [s.value for s in self.stages_completed],
            'errors': self.errors,
            'total_time': self.total_time,
            'crawl_time': self.crawl_time,
            'analyze_time': self.analyze_time,
            'from_cache': self.from_cache,
        }

    @property
    def is_successful(self) -> bool:
        """True wenn alle Stufen erfolgreich"""
        return len(self.errors) == 0 and PipelineStage.SCORE in self.stages_completed


@dataclass
class BatchResult:
    """Ergebnis einer Batch-Analyse"""
    results: List[PipelineResult] = field(default_factory=list)
    total: int = 0
    successful: int = 0
    failed: int = 0
    cached: int = 0

    # Timing
    total_time: float = 0.0
    avg_time_per_company: float = 0.0

    # Progress
    progress_callback: Optional[Callable[[int, int], None]] = field(default=None, repr=False)

    def add_result(self, result: PipelineResult) -> None:
        """Fügt Ergebnis hinzu"""
        self.results.append(result)
        self.total += 1

        if result.is_successful:
            self.successful += 1
        else:
            self.failed += 1

        if result.from_cache:
            self.cached += 1

        if self.progress_callback:
            self.progress_callback(len(self.results), self.total)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary"""
        return {
            'total': self.total,
            'successful': self.successful,
            'failed': self.failed,
            'cached': self.cached,
            'total_time': self.total_time,
            'avg_time_per_company': self.avg_time_per_company,
            'results': [r.to_dict() for r in self.results]
        }


class LeadAnalysisPipeline:
    """
    End-to-End Pipeline für Lead-Analyse

    Workflow:
    1. Crawl: Hole Unternehmensdaten (via Crawler oder direkt)
    2. Extract: Extrahiere Website-Content
    3. Analyze: Analysiere Branche mit LLM
    4. Cache: Speichere Analyse im Cache
    5. Score: Berechne Lead-Score

    Usage:
        pipeline = LeadAnalysisPipeline()

        # Einzelnes Unternehmen
        result = pipeline.analyze(company)

        # Batch
        results = pipeline.analyze_batch(companies)
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialisiert Pipeline

        Args:
            settings: Settings (default: aus get_settings())
        """
        self.settings = settings or get_settings()
        self.logger = logging.getLogger(self.__class__.__name__)

        # Services
        self.cache = get_cache()
        self.llm_client = get_llm_client()
        self.website_extractor = get_website_extractor()
        self.plz_service = get_plz_service()

        # Stats
        self._stats = {
            'companies_processed': 0,
            'analyses_completed': 0,
            'cache_hits': 0,
            'errors': 0
        }

    def analyze(
        self,
        company: Company,
        skip_cache: bool = False,
        skip_analysis: bool = False,
        skip_scoring: bool = False,
        **kwargs
    ) -> PipelineResult:
        """
        Analysiert ein einzelnes Unternehmen

        Args:
            company: Company-Objekt
            skip_cache: Cache überspringen
            skip_analysis: LLM-Analyse überspringen
            skip_scoring: Scoring überspringen
            **kwargs: Zusätzliche Optionen

        Returns:
            PipelineResult mit Analyse und Score
        """
        start_time = time.time()
        result = PipelineResult(company=company)

        try:
            # Stage 1: Website extrahieren
            if company.contact.website and not skip_analysis:
                result = self._extract_stage(result)

            # Stage 2: LLM-Analyse
            if result.analysis is None and company.contact.website and not skip_analysis:
                result = self._analyze_stage(result, skip_cache)

            # Stage 3: Scoring
            if not skip_scoring:
                result = self._score_stage(result)

        except Exception as e:
            self.logger.error(f"Pipeline error for {company.name}: {e}")
            result.errors.append({
                'stage': 'pipeline',
                'error': str(e)
            })

        # Timing
        result.total_time = time.time() - start_time
        self._stats['companies_processed'] += 1

        if result.is_successful:
            self._stats['analyses_completed'] += 1

        if result.from_cache:
            self._stats['cache_hits'] += 1

        if result.errors:
            self._stats['errors'] += len(result.errors)

        return result

    def _extract_stage(self, result: PipelineResult) -> PipelineResult:
        """Stage 1: Website Content extrahieren"""
        website_url = result.company.contact.website

        if not website_url:
            result.errors.append({'stage': 'extract', 'error': 'No website URL'})
            return result

        try:
            crawl_start = time.time()

            website_content = self.website_extractor.extract(website_url)
            result.crawl_time = time.time() - crawl_start

            if website_content.error:
                result.errors.append({
                    'stage': 'extract',
                    'error': website_content.error
                })
                return result

            # Website-Content in LLMAnalysisResult speichern
            result.analysis = LLMAnalysisResult(
                company_name=result.company.name,
                website_url=website_url,
                website_word_count=website_content.word_count,
                website_title=website_content.title,
                crawl_time=result.crawl_time
            )

            result.stages_completed.append(PipelineStage.EXTRACT)
            self.logger.debug(f"Extracted {website_content.word_count} words from {website_url}")

        except Exception as e:
            result.errors.append({
                'stage': 'extract',
                'error': str(e)
            })

        return result

    def _analyze_stage(self, result: PipelineResult, skip_cache: bool = False) -> PipelineResult:
        """Stage 2: LLM-Analyse mit Cache"""
        website_url = result.company.contact.website

        # Cache prüfen
        if not skip_cache:
            cached = self.cache.get(website_url)
            if cached:
                result.from_cache = True

                # Cached Analysis in BranchAnalysis umwandeln
                branch_analysis = BranchAnalysis(
                    branch=cached.get('branch', 'Unknown'),
                    sub_branches=cached.get('sub_branches', []),
                    services=cached.get('services', []),
                    target_market=cached.get('target_market', 'Unknown'),
                    company_size_hint=cached.get('company_size_hint', 'Unknown'),
                    keywords=cached.get('keywords', []),
                    confidence=cached.get('confidence', 0.0),
                    reasoning=cached.get('reasoning', '')
                )

                result.analysis = LLMAnalysisResult(
                    company_name=result.company.name,
                    website_url=website_url,
                    analysis=branch_analysis,
                    cached=True,
                    cached_at=cached.get('_cached_at')
                )

                result.stages_completed.append(PipelineStage.CACHE)
                result.stages_completed.append(PipelineStage.ANALYZE)
                self.logger.debug(f"Cache hit for {website_url}")
                return result

        # LLM-Analyse durchführen
        try:
            analyze_start = time.time()

            # Website-Content für Analyse vorbereiten
            website_content = {
                'title': result.analysis.website_title if result.analysis else '',
                'main_text': '',  # Würde von WebsiteExtractor kommen
                'word_count': result.analysis.website_word_count if result.analysis else 0
            }

            branch_analysis = self.llm_client.analyze_branch(
                company_name=result.company.name,
                website_content=website_content
            )

            result.analyze_time = time.time() - analyze_start

            if branch_analysis:
                result.analysis = LLMAnalysisResult(
                    company_name=result.company.name,
                    website_url=website_url,
                    analysis=branch_analysis,
                    cached=False,
                    crawl_time=result.crawl_time,
                    analyze_time=result.analyze_time
                )

                # Im Cache speichern
                self.cache.set(website_url, branch_analysis.to_dict())
                result.stages_completed.append(PipelineStage.CACHE)

                result.stages_completed.append(PipelineStage.ANALYZE)
                self.logger.debug(f"Analyzed {result.company.name}: {branch_analysis.branch}")

            else:
                result.errors.append({
                    'stage': 'analyze',
                    'error': 'LLM analysis returned None'
                })

        except Exception as e:
            result.errors.append({
                'stage': 'analyze',
                'error': str(e)
            })

        return result

    def _score_stage(self, result: PipelineResult) -> PipelineResult:
        """Stage 3: Lead-Scoring"""
        try:
            company = result.company
            weights = self.settings.scoring.weights

            # Score-Breakdown berechnen
            breakdown = ScoreBreakdown()

            # Contact Score
            contact_score = company.contact.contact_score  # 0-25
            breakdown.contact = contact_score

            # Location Score (Distanz zu Ziel-PLZ falls bekannt)
            # Für jetzt: Default score basierend auf Bundesland
            location_score = 15.0  # Default
            if company.address.plz and company.address.ort:
                location_score = 18.0  # Gut wenn Adresse bekannt
            breakdown.location = location_score

            # Branch Score (aus Analyse)
            branch_score = 10.0  # Default
            if result.analysis and result.analysis.analysis:
                confidence = result.analysis.analysis.confidence
                branch_score = confidence * 20.0  # 0-20 basierend auf Confidence
            breakdown.branch = branch_score

            # Completeness Score
            completeness = 0.0
            if company.name:
                completeness += 5.0
            if company.address.street:
                completeness += 3.0
            if company.address.plz:
                completeness += 3.0
            if company.address.ort:
                completeness += 2.0
            if company.contact.telefon:
                completeness += 2.0
            breakdown.completeness = min(completeness, 15.0)

            # Freshness Score (aus Analysis)
            freshness = 5.0  # Default
            if result.analysis and not result.analysis.cached:
                freshness = 8.0  # Frisch analysiert
            breakdown.freshness = freshness

            # Size Score (aus Analyse)
            size_score = 5.0  # Default
            if result.analysis and result.analysis.analysis:
                size_hint = result.analysis.analysis.company_size_hint
                if 'Medium' in size_hint or 'Large' in size_hint:
                    size_score = 8.0
                elif 'Small' in size_hint:
                    size_score = 6.0
            breakdown.size = size_score

            # LeadScore erstellen
            result.score = LeadScore.create(name=company.name, breakdown=breakdown)
            result.stages_completed.append(PipelineStage.SCORE)

            self.logger.debug(
                f"Scored {company.name}: {result.score.total_score:.1f} ({result.score.grade})"
            )

        except Exception as e:
            result.errors.append({
                'stage': 'score',
                'error': str(e)
            })

        return result

    def analyze_batch(
        self,
        companies: List[Company],
        skip_cache: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        **kwargs
    ) -> BatchResult:
        """
        Analysiert mehrere Unternehmen (Batch)

        Args:
            companies: Liste von Company-Objekten
            skip_cache: Cache überspringen
            progress_callback: Callback(current, total)
            **kwargs: Zusätzliche Optionen

        Returns:
            BatchResult mit allen Ergebnissen
        """
        start_time = time.time()
        batch_result = BatchResult(progress_callback=progress_callback)
        batch_result.total = len(companies)

        for i, company in enumerate(companies):
            result = self.analyze(company, skip_cache=skip_cache, **kwargs)
            batch_result.add_result(result)

            # Rate-Limiting zwischen Requests
            if i < len(companies) - 1 and not result.from_cache:
                time.sleep(self.settings.crawler.rate_limit)

        # Timing
        batch_result.total_time = time.time() - start_time
        batch_result.avg_time_per_company = (
            batch_result.total_time / len(companies) if companies else 0.0
        )

        return batch_result

    def analyze_from_crawler(
        self,
        crawler_result: CrawlerResult,
        **kwargs
    ) -> BatchResult:
        """
        Analysiert Ergebnisse aus einem Crawler-Run

        Args:
            crawler_result: CrawlerResult mit Company-Liste
            **kwargs: Zusätzliche Optionen für analyze_batch

        Returns:
            BatchResult mit allen Ergebnissen
        """
        return self.analyze_batch(crawler_result.companies, **kwargs)

    def get_stats(self) -> Dict[str, int]:
        """Gibt Pipeline-Statistiken zurück"""
        return self._stats.copy()

    def reset_stats(self) -> None:
        """Setzt Statistiken zurück"""
        self._stats = {
            'companies_processed': 0,
            'analyses_completed': 0,
            'cache_hits': 0,
            'errors': 0
        }


# Convenience-Funktionen
def run_analysis(
    companies: List[Company],
    settings: Optional[Settings] = None,
    **kwargs
) -> BatchResult:
    """
    Convenience-Funktion für Batch-Analyse

    Usage:
        from lead_crawler.pipelines import run_analysis

        companies = [Company(name="Test GmbH", ...), ...]
        results = run_analysis(companies)

        for r in results.results:
            print(f"{r.company.name}: {r.score.total_score}")
    """
    pipeline = LeadAnalysisPipeline(settings=settings)
    return pipeline.analyze_batch(companies, **kwargs)


__all__ = [
    'LeadAnalysisPipeline',
    'PipelineResult',
    'PipelineStage',
    'BatchResult',
    'run_analysis',
]