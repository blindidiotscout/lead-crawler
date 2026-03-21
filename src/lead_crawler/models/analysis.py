"""
Analysis Domain Models
Definiert LLM-Analyse-Ergebnisse und Cache-Strukturen
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TargetMarket(Enum):
    """Zielmarkt-Klassifikation"""

    B2B = "B2B"
    B2C = "B2C"
    B2B_B2C = "B2B/B2C"
    UNKNOWN = "Unknown"


class CompanySize(Enum):
    """Unternehmensgröße (Schätzung)"""

    MICRO = "Micro (<10 MA)"
    SMALL = "Small (10-49 MA)"
    MEDIUM = "Medium (50-249 MA)"
    LARGE = "Large (250+ MA)"
    UNKNOWN = "Unknown"


@dataclass
class BranchAnalysis:
    """
    LLM-Analyse-Ergebnis für ein Unternehmen

    Enthält alle extrahierten Informationen aus Website-Analyse
    """

    # Hauptbranche
    branch: str  # z.B. "Industrie/Fertigung"

    # Unterbranchen / Spezialisierungen
    sub_branches: list[str] = field(
        default_factory=list
    )  # z.B. ["Aromenherstellung", "Getränkeindustrie"]

    # Dienstleistungen / Services
    services: list[str] = field(default_factory=list)  # z.B. ["Produktion", "Beratung"]

    # Zielmarkt
    target_market: str = "Unknown"  # B2B, B2C, B2B/B2C

    # Unternehmensgröße (Schätzung)
    company_size_hint: str = "Unknown"  # Micro, Small, Medium, Large

    # Keywords für Suche
    keywords: list[str] = field(default_factory=list)

    # Confidence-Score (0.0 - 1.0)
    confidence: float = 0.0

    # Begründung (Warum diese Branche?)
    reasoning: str = ""

    # Metadaten
    analyzed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    model: str = ""  # Verwendetes LLM-Modell

    def to_dict(self) -> dict[str, Any]:
        """Konvertiert zu Dictionary"""
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BranchAnalysis":
        """Erstellt BranchAnalysis aus Dictionary"""
        return cls(
            branch=data.get("branch", "Unknown"),
            sub_branches=data.get("sub_branches", []),
            services=data.get("services", []),
            target_market=data.get("target_market", "Unknown"),
            company_size_hint=data.get("company_size_hint", "Unknown"),
            keywords=data.get("keywords", []),
            confidence=data.get("confidence", 0.0),
            reasoning=data.get("reasoning", ""),
            analyzed_at=data.get("analyzed_at", datetime.now().isoformat()),
            model=data.get("model", ""),
        )

    @property
    def confidence_percentage(self) -> float:
        """Confidence als Prozentwert (0-100)"""
        return self.confidence * 100

    @property
    def is_high_confidence(self) -> bool:
        """True wenn Confidence >= 0.8"""
        return self.confidence >= 0.8

    @property
    def is_medium_confidence(self) -> bool:
        """True wenn Confidence zwischen 0.5 und 0.8"""
        return 0.5 <= self.confidence < 0.8

    @property
    def is_low_confidence(self) -> bool:
        """True wenn Confidence < 0.5"""
        return self.confidence < 0.5

    def __str__(self) -> str:
        """Kurze String-Repräsentation"""
        services_str = ", ".join(self.services[:3])
        if len(self.services) > 3:
            services_str += "..."
        return f"{self.branch} ({self.confidence:.0%}) - Services: {services_str}"


@dataclass
class LLMAnalysisResult:
    """
    Vollständiges LLM-Analyse-Ergebnis

    Kapselt BranchAnalysis und zusätzliche Metadaten wie
    Cache-Status, Timing, etc.
    """

    # Analysedaten
    analysis: BranchAnalysis | None = None

    # Website-Informationen
    website_url: str = ""
    website_word_count: int = 0
    website_title: str = ""

    # Cache-Status
    cached: bool = False
    cached_at: str | None = None

    # Timing
    crawl_time: float = 0.0  # Sekunden
    analyze_time: float = 0.0  # Sekunden
    total_time: float = 0.0  # Sekunden

    # Fehlerbehandlung
    error: str | None = None

    # Unternehmensname (für Reference)
    company_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Konvertiert zu Dictionary"""
        data = {
            "company_name": self.company_name,
            "website_url": self.website_url,
            "website_word_count": self.website_word_count,
            "website_title": self.website_title,
            "cached": self.cached,
            "cached_at": self.cached_at,
            "crawl_time": self.crawl_time,
            "analyze_time": self.analyze_time,
            "total_time": self.total_time,
            "error": self.error,
        }

        if self.analysis:
            data.update(self.analysis.to_dict())

        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LLMAnalysisResult":
        """Erstellt LLMAnalysisResult aus Dictionary"""
        # BranchAnalysis extrahieren falls vorhanden
        analysis = None
        if data.get("branch"):
            # Dict hat BranchAnalysis-Felder direkt
            analysis = BranchAnalysis.from_dict(data)
        elif data.get("analysis"):
            # analysis als Sub-Objekt
            if isinstance(data["analysis"], dict):
                analysis = BranchAnalysis.from_dict(data["analysis"])
            else:
                analysis = data["analysis"]

        return cls(
            analysis=analysis,
            website_url=data.get("website_url", ""),
            website_word_count=data.get("website_word_count", 0),
            website_title=data.get("website_title", ""),
            cached=data.get("cached", False),
            cached_at=data.get("cached_at"),
            crawl_time=data.get("crawl_time", 0.0),
            analyze_time=data.get("analyze_time", 0.0),
            total_time=data.get("total_time", 0.0),
            error=data.get("error"),
            company_name=data.get("company_name", ""),
        )

    @classmethod
    def from_pipeline_result(cls, result: dict[str, Any]) -> "LLMAnalysisResult":
        """
        Erstellt LLMAnalysisResult aus Pipeline-Ergebnis

        Args:
            result: Dict von LLMPipeline.analyze_company()

        Returns:
            LLMAnalysisResult-Instanz
        """
        analysis_dict = result.get("analysis") or {}

        return cls(
            company_name=result.get("company_name", ""),
            website_url=result.get("url", ""),
            website_word_count=(
                result.get("website_content", {}).get("word_count", 0)
                if result.get("website_content")
                else 0
            ),
            website_title=(
                result.get("website_content", {}).get("title", "")
                if result.get("website_content")
                else ""
            ),
            analysis=BranchAnalysis.from_dict(analysis_dict) if analysis_dict else None,
            cached=result.get("cached", False),
            crawl_time=result.get("crawl_time", 0.0),
            analyze_time=result.get("analyze_time", 0.0),
            total_time=result.get("total_time", 0.0),
            error=result.get("error"),
        )

    @property
    def is_successful(self) -> bool:
        """True wenn Analyse erfolgreich war"""
        return self.analysis is not None and self.error is None

    @property
    def is_cached(self) -> bool:
        """True wenn Ergebnis aus Cache kam"""
        return self.cached

    def __str__(self) -> str:
        """String-Repräsentation"""
        status = "✓" if self.is_successful else "✗"
        cache = "📦" if self.cached else "🔄"
        time_str = f"{self.total_time:.1f}s" if self.total_time > 0 else ""

        if self.analysis:
            return f"{status} {cache} {self.analysis.branch} ({time_str})"
        return f"{status} {cache} Keine Analyse {time_str}"


@dataclass
class CacheEntry:
    """
    Cache-Eintrag für LLM-Analysen

    Wird in der SQLite-Datenbank gespeichert
    """

    url: str  # Primary Key
    company_name: str
    analysis: BranchAnalysis
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: str | None = None  # TTL-basiert

    def to_dict(self) -> dict[str, Any]:
        """Konvertiert zu Dictionary"""
        return {
            "url": self.url,
            "company_name": self.company_name,
            "analysis": self.analysis.to_dict(),
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CacheEntry":
        """Erstellt CacheEntry aus Dictionary"""
        analysis = BranchAnalysis.from_dict(data.get("analysis", {}))
        return cls(
            url=data["url"],
            company_name=data.get("company_name", ""),
            analysis=analysis,
            created_at=data.get("created_at", datetime.now().isoformat()),
            expires_at=data.get("expires_at"),
        )

    def is_expired(self, ttl_days: int = 30) -> bool:
        """Prüft ob Eintrag abgelaufen ist"""
        if not self.expires_at:
            return False
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.now() > expires
