"""
Company Domain Models
Definiert die Kern-Datenstrukturen für Unternehmen
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class CompanySource(Enum):
    """Datenquellen für Unternehmen"""

    WKO = "firmen.wko.at"
    ECOPLUS = "ecoplus.at"
    MANUAL = "manual"
    API = "api"


@dataclass
class Address:
    """Adress-Datenmodell"""

    street: str | None = None
    plz: str | None = None  # Postleitzahl
    ort: str | None = None  # Ort/Stadt
    bundesland: str | None = None  # Bundesland
    country: str = "Österreich"

    def to_dict(self) -> dict[str, Any]:
        """Konvertiert zu Dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Address":
        """Erstellt Address aus Dictionary"""
        return cls(
            street=data.get("street") or data.get("strasse"),
            plz=data.get("plz"),
            ort=data.get("ort"),
            bundesland=data.get("bundesland"),
            country=data.get("country", "Österreich"),
        )

    def __str__(self) -> str:
        """Formatierte Adresse"""
        parts = []
        if self.street:
            parts.append(self.street)
        if self.plz and self.ort:
            parts.append(f"{self.plz} {self.ort}")
        elif self.ort:
            parts.append(self.ort)
        if self.bundesland and self.bundesland != self.ort:
            parts.append(self.bundesland)
        return ", ".join(parts)


@dataclass
class ContactInfo:
    """Kontaktinformationen"""

    telefon: str | None = None
    email: str | None = None
    website: str | None = None
    fax: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Konvertiert zu Dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContactInfo":
        """Erstellt ContactInfo aus Dictionary"""
        return cls(
            telefon=data.get("telefon") or data.get("phone"),
            email=data.get("email"),
            website=data.get("website") or data.get("url"),
            fax=data.get("fax"),
        )

    @property
    def has_contact(self) -> bool:
        """Prüft ob mindestens ein Kontakt vorhanden ist"""
        return bool(self.telefon or self.email or self.website)

    @property
    def contact_score(self) -> float:
        """
        Bewertet Kontakt-Qualität (0-25)
        - Email: 10 Punkte
        - Telefon: 8 Punkte
        - Website: 7 Punkte
        """
        score = 0.0
        if self.email:
            score += 10.0
        if self.telefon:
            score += 8.0
        if self.website:
            score += 7.0
        return min(score, 25.0)


@dataclass
class CompanyMetadata:
    """Metadaten für ein Unternehmen"""

    source: CompanySource = CompanySource.WKO
    source_url: str | None = None
    crawled_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str | None = None
    crawl_version: str = "1.0"
    raw_data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Konvertiert zu Dictionary"""
        data = asdict(self)
        data["source"] = self.source.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompanyMetadata":
        """Erstellt Metadata aus Dictionary"""
        source_value = data.get("source", "firmen.wko.at")
        source = CompanySource(source_value) if isinstance(source_value, str) else source_value

        return cls(
            source=source,
            source_url=data.get("source_url") or data.get("url"),
            crawled_at=data.get("crawled_at", datetime.now().isoformat()),
            last_updated=data.get("last_updated"),
            crawl_version=data.get("crawl_version", "1.0"),
            raw_data=data.get("raw_data"),
        )


@dataclass
class Company:
    """
    Haupt-Datenmodell für ein Unternehmen

    Vereinheitlicht alle Unternehmensdaten aus verschiedenen Quellen
    und stellt einheitliche Schnittstellen bereit.
    """

    # Pflichtfelder
    name: str

    # Identifikation
    id: str | None = None  # Eindeutige ID (UUID oder Source-ID)

    # Adressdaten
    address: Address = field(default_factory=Address)

    # Kontaktdaten
    contact: ContactInfo = field(default_factory=ContactInfo)

    # Branchendaten
    branche: str | None = None  # WKO-Branchenbezeichnung
    llm_analysis: "LLMAnalysisResult | None" = None  # LLM-Analyse (wird später definiert)

    # Metadaten
    metadata: CompanyMetadata = field(default_factory=CompanyMetadata)

    # Scoring (wird später hinzugefügt)
    score: "LeadScore | None" = None  # type: ignore

    def to_dict(self) -> dict[str, Any]:
        """Konvertiert Company zu Dictionary (für JSON/CSV Export)"""
        data = {
            "name": self.name,
            "id": self.id,
            "street": self.address.street,
            "plz": self.address.plz,
            "ort": self.address.ort,
            "bundesland": self.address.bundesland,
            "telefon": self.contact.telefon,
            "email": self.contact.email,
            "website": self.contact.website,
            "branche": self.branche,
            "source": self.metadata.source.value,
            "source_url": self.metadata.source_url,
            "crawled_at": self.metadata.crawled_at,
        }

        # LLM Analysis hinzufügen falls vorhanden
        if self.llm_analysis:
            data["llm_analysis"] = self.llm_analysis.to_dict()
            data["llm_cached"] = self.llm_analysis.cached

        # Score hinzufügen falls vorhanden
        if self.score:
            data["score_total"] = self.score.total_score
            data["score_grade"] = self.score.grade
            data["score_priority"] = self.score.priority

        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Company":
        """Erstellt Company aus Dictionary (z.B. von WKO Spider)"""
        # Address extrahieren
        address = Address.from_dict(data)

        # Contact extrahieren
        contact = ContactInfo.from_dict(data)

        # Metadata extrahieren
        metadata = CompanyMetadata.from_dict(data)

        # Company erstellen
        company = cls(
            name=data.get("name", "Unknown"),
            id=data.get("id"),
            address=address,
            contact=contact,
            branche=data.get("branche"),
            metadata=metadata,
        )

        # LLM Analysis falls vorhanden
        if data.get("llm_analysis"):
            # Wird später importiert um Circular Import zu vermeiden
            from lead_crawler.models.analysis import LLMAnalysisResult

            if isinstance(data["llm_analysis"], dict):
                company.llm_analysis = LLMAnalysisResult.from_dict(data["llm_analysis"])
            else:
                company.llm_analysis = data["llm_analysis"]

        return company

    @classmethod
    def from_wko_result(cls, data: dict[str, Any]) -> "Company":
        """
        Erstellt Company aus WKO Spider Ergebnis

        Args:
            data: Dict von WkoSpider.parse()

        Returns:
            Company-Instanz
        """
        return cls.from_dict(data)

    def __str__(self) -> str:
        """Kurze String-Repräsentation"""
        location = f"{self.address.plz} {self.address.ort}".strip()
        if location:
            return f"{self.name} ({location})"
        return self.name

    def __repr__(self) -> str:
        """Debug-Repräsentation"""
        return f"Company(name='{self.name}', id={self.id})"


# Forward Reference für Type Hints
def __post_import():
    """Nach Import: Verknüpft Forward References"""
    from lead_crawler.models.analysis import LLMAnalysisResult
    from lead_crawler.models.scoring import LeadScore

    Company.__annotations__["llm_analysis"] = LLMAnalysisResult | None
    Company.__annotations__["score"] = LeadScore | None
