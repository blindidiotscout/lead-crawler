"""
Base Crawler Module
Abstrakte Basisklasse für alle Crawler/Spider
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from lead_crawler.config import CrawlerConfig, get_settings
from lead_crawler.models import Company, CompanySource


class CrawlerStatus(Enum):
    """Status eines Crawlers"""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CrawlerResult:
    """Ergebnis eines Crawler-Runs"""

    companies: list[Company] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    status: CrawlerStatus = CrawlerStatus.COMPLETED
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: str | None = None
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Konvertiert zu Dictionary"""
        return {
            "companies": [c.to_dict() for c in self.companies],
            "errors": self.errors,
            "stats": self.stats,
            "status": self.status.value,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": self.duration_seconds,
            "total_companies": len(self.companies),
            "total_errors": len(self.errors),
        }

    @property
    def total(self) -> int:
        """Anzahl gefundener Unternehmen"""
        return len(self.companies)

    @property
    def success_rate(self) -> float:
        """Erfolgsrate (0-1)"""
        total_items = len(self.companies) + len(self.errors)
        if total_items == 0:
            return 0.0
        return len(self.companies) / total_items


class BaseCrawler(ABC):
    """
    Abstrakte Basisklasse für alle Crawler

    Stellt gemeinsame Funktionalität bereit:
    - Einheitliche Logging-Schnittstelle
    - Statistiken-Tracking
    - Error-Handling
    - Result-Building
    """

    # Name des Crawlers (überschreiben in Subklassen)
    name: str = "base_crawler"
    source: CompanySource = CompanySource.MANUAL

    def __init__(self, config: CrawlerConfig | None = None):
        """
        Initialisiert Crawler

        Args:
            config: CrawlerConfig (default: aus get_settings())
        """
        if config is None:
            config = get_settings().crawler

        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.status = CrawlerStatus.IDLE
        self._stats: dict[str, int] = {
            "pages_crawled": 0,
            "companies_found": 0,
            "errors": 0,
            "skipped": 0,
        }

    @abstractmethod
    def crawl(self, **kwargs) -> CrawlerResult:
        """
        Führt den Crawl aus

        Args:
            **kwargs: Crawler-spezifische Parameter

        Returns:
            CrawlerResult mit gefundenen Unternehmen
        """
        pass

    @abstractmethod
    def _parse_item(self, item: Any) -> Company | None:
        """
        Parst ein einzelnes Item (HTML, JSON, etc.) zu Company

        Args:
            item: Raw Item (crawler-spezifisch)

        Returns:
            Company oder None bei Parsing-Fehler
        """
        pass

    def _start_crawl(self) -> None:
        """Wird zu Beginn des Crawls aufgerufen"""
        self.status = CrawlerStatus.RUNNING
        self._stats = {k: 0 for k in self._stats}
        self.logger.info(f"[{self.name}] Starting crawl...")

    def _finish_crawl(self, result: CrawlerResult) -> CrawlerResult:
        """Wird am Ende des Crawls aufgerufen"""
        result.finished_at = datetime.now().isoformat()
        result.status = self.status
        result.stats = self._stats.copy()

        # Duration berechnen
        if result.started_at and result.finished_at:
            start = datetime.fromisoformat(result.started_at)
            end = datetime.fromisoformat(result.finished_at)
            result.duration_seconds = (end - start).total_seconds()

        self.logger.info(
            f"[{self.name}] Crawl finished: {result.total} companies, "
            f"{len(result.errors)} errors, {result.duration_seconds:.1f}s"
        )

        return result

    def _track_success(self) -> None:
        """Trackt erfolgreichen Parse"""
        self._stats["companies_found"] += 1

    def _track_error(self, error: str, context: dict | None = None) -> None:
        """Trackt Fehler"""
        self._stats["errors"] += 1
        error_entry = {"error": error}
        if context:
            error_entry.update(context)
        self.logger.error(f"[{self.name}] {error}")

    def _track_skip(self, reason: str = "") -> None:
        """Trackt übersprungenes Item"""
        self._stats["skipped"] += 1
        if reason:
            self.logger.debug(f"[{self.name}] Skipped: {reason}")

    def _normalize_phone(self, phone: str | None) -> str | None:
        """Normalisiert Telefonnummer"""
        if not phone:
            return None
        # Leerzeichen und Sonderzeichen entfernen
        phone = phone.strip()
        # Bereinigen: nur + und Zahlen
        import re

        phone = re.sub(r"[^\d+]", "", phone)
        return phone if phone else None

    def _normalize_email(self, email: str | None) -> str | None:
        """Normalisiert E-Mail-Adresse"""
        if not email:
            return None
        email = email.strip().lower()
        # E-Mail validieren
        import re

        if re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            return email
        return None

    def _normalize_url(self, url: str | None) -> str | None:
        """Normalisiert URL"""
        if not url:
            return None
        url = url.strip()
        # Protocol hinzufügen falls fehlt
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url

    def _normalize_plz(self, plz: str | None) -> str | None:
        """Normalisiert österreichische PLZ"""
        if not plz:
            return None
        # Nur Ziffern extrahieren
        import re

        digits = re.sub(r"\D", "", plz)
        # Österreichische PLZ ist 4-stellig
        if len(digits) == 4:
            return digits
        return None

    def _clean_string(self, text: str | None) -> str | None:
        """Bereinigt String (Whitespace, etc.)"""
        if not text:
            return None
        text = text.strip()
        # Mehrfache Leerzeichen entfernen
        import re

        text = re.sub(r"\s+", " ", text)
        return text if text else None

    def create_company(
        self,
        name: str,
        address: dict | None = None,
        contact: dict | None = None,
        branche: str | None = None,
        url: str | None = None,
        **kwargs,
    ) -> Company:
        """
        Erstellt Company-Objekt mit normalisierten Daten

        Args:
            name: Unternehmensname
            address: Dict mit street, plz, ort, bundesland
            contact: Dict mit telefon, email, website
            branche: Branchenbezeichnung
            url: Quell-URL
            **kwargs: Zusätzliche Felder

        Returns:
            Company-Objekt
        """
        from lead_crawler.models import Address, CompanyMetadata, ContactInfo

        # Address normalisieren
        addr = Address()
        if address:
            addr = Address(
                street=self._clean_string(address.get("street")),
                plz=self._normalize_plz(address.get("plz")),
                ort=self._clean_string(address.get("ort")),
                bundesland=self._clean_string(address.get("bundesland")),
            )

        # Contact normalisieren
        contact_obj = ContactInfo()
        if contact:
            contact_obj = ContactInfo(
                telefon=self._normalize_phone(contact.get("telefon")),
                email=self._normalize_email(contact.get("email")),
                website=self._normalize_url(contact.get("website")),
            )

        # Metadata
        metadata = CompanyMetadata(source=self.source, source_url=url)

        # Company erstellen
        company = Company(
            name=self._clean_string(name) or "Unknown",
            address=addr,
            contact=contact_obj,
            branche=self._clean_string(branche),
            metadata=metadata,
        )

        # Zusätzliche Felder im metadata.raw_data speichern
        if kwargs:
            company.metadata.raw_data = kwargs

        return company


class CrawlerFactory:
    """
    Factory für Crawler-Instanzen

    Ermöglicht einfache Erstellung von Crawlern nach Namen.
    """

    _crawlers: dict[str, type] = {}

    @classmethod
    def register(cls, crawler_class: type) -> type:
        """
        Registriert einen Crawler

        Usage:
            @CrawlerFactory.register
            class MyCrawler(BaseCrawler):
                name = "my_crawler"
                ...
        """
        cls._crawlers[crawler_class.name] = crawler_class
        return crawler_class

    @classmethod
    def create(cls, name: str, **kwargs) -> BaseCrawler:
        """
        Erstellt Crawler-Instanz nach Namen

        Args:
            name: Crawler-Name (z.B. "wko", "ecoplus")
            **kwargs: Crawler-spezifische Parameter

        Returns:
            Crawler-Instanz

        Raises:
            ValueError: Wenn Crawler nicht gefunden
        """
        if name not in cls._crawlers:
            available = list(cls._crawlers.keys())
            raise ValueError(f"Crawler '{name}' not found. Available: {available}")

        return cls._crawlers[name](**kwargs)

    @classmethod
    def list_crawlers(cls) -> list[str]:
        """Gibt Liste aller registrierten Crawler zurück"""
        return list(cls._crawlers.keys())
