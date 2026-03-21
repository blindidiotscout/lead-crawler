"""
Scoring Domain Models
Definiert Lead-Scoring-Ergebnisse und Bewertungsmetriken
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from enum import Enum


class ScoreGrade(Enum):
    """Noten für Lead-Qualität"""
    A = "A"  # Excellent (80-100%)
    B = "B"  # Good (60-79%)
    C = "C"  # Fair (40-59%)
    D = "D"  # Poor (20-39%)
    F = "F"  # Bad (0-19%)


class Priority(Enum):
    """Priorität für Lead-Followup"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class ScoreBreakdown:
    """
    Aufschlüsselung des Scores in einzelne Kategorien

    Jede Kategorie hat einen Score zwischen 0 und ihrem Max-Wert.
    """
    # Kontakt-Score (0-25)
    # Bewertet: Email, Telefon, Website vorhanden
    contact: float = 0.0

    # Location-Score (0-20)
    # Bewertet: Distanz zum Zielgebiet
    location: float = 0.0

    # Branchen-Score (0-20)
    # Bewertet: Relevanz der Branche
    branch: float = 0.0

    # Vollständigkeits-Score (0-15)
    # Bewertet: Wie viele Felder sind ausgefüllt
    completeness: float = 0.0

    # Freshness-Score (0-10)
    # Bewertet: Aktualität der Daten (Website-Impressum)
    freshness: float = 0.0

    # Größen-Score (0-10)
    # Bewertet: Unternehmensgröße (Schätzung)
    size: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        """Konvertiert zu Dictionary"""
        return {
            "contact": self.contact,
            "location": self.location,
            "branch": self.branch,
            "completeness": self.completeness,
            "freshness": self.freshness,
            "size": self.size
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "ScoreBreakdown":
        """Erstellt ScoreBreakdown aus Dictionary"""
        return cls(
            contact=data.get("contact", 0.0),
            location=data.get("location", 0.0),
            branch=data.get("branch", 0.0),
            completeness=data.get("completeness", 0.0),
            freshness=data.get("freshness", 0.0),
            size=data.get("size", 0.0)
        )

    @property
    def total(self) -> float:
        """Gesamtscore (Summe aller Kategorien)"""
        return sum([
            self.contact,
            self.location,
            self.branch,
            self.completeness,
            self.freshness,
            self.size
        ])

    @property
    def max_score(self) -> float:
        """Maximal möglicher Score (100)"""
        return 100.0

    @property
    def percentage(self) -> float:
        """Score als Prozent (0-100)"""
        return (self.total / self.max_score * 100) if self.max_score > 0 else 0.0

    def get_weakest_category(self) -> str:
        """Gibt die schwächste Kategorie zurück"""
        scores = self.to_dict()
        return min(scores, key=scores.get)  # type: ignore

    def get_strongest_category(self) -> str:
        """Gibt die stärkste Kategorie zurück"""
        scores = self.to_dict()
        return max(scores, key=scores.get)  # type: ignore


# Standard-Gewichtung für Scoring
DEFAULT_WEIGHTS = {
    "contact": 25,      # Kontakt-Infos (Email, Telefon, Website)
    "location": 20,     # Standort (Distanz)
    "branch": 20,       # Branchen-Relevanz
    "completeness": 15, # Datenvollständigkeit
    "freshness": 10,    # Aktualität
    "size": 10,         # Unternehmensgröße
}


@dataclass
class LeadScore:
    """
    Lead-Scoring-Ergebnis für ein Unternehmen

    Enthält den Gesamtscore, die Aufschlüsselung und Empfehlungen
    """
    # Unternehmensname (für Reference)
    name: str

    # Scores
    total_score: float  # Summe aller Kategorien
    max_score: float = 100.0  # Maximal möglicher Score

    # Aufschlüsselung
    breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)

    # Abgeleitete Werte
    percentage: float = 0.0  # Score als Prozent
    grade: str = "F"  # A, B, C, D, F
    priority: str = "LOW"  # HIGH, MEDIUM, LOW

    # Begründungen
    reasons: List[str] = field(default_factory=list)

    # Zusätzliche Metadaten
    target_branches: List[str] = field(default_factory=list)
    distance_km: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary"""
        return {
            "name": self.name,
            "total_score": self.total_score,
            "max_score": self.max_score,
            "percentage": self.percentage,
            "breakdown": self.breakdown.to_dict(),
            "grade": self.grade,
            "priority": self.priority,
            "reasons": self.reasons,
            "target_branches": self.target_branches,
            "distance_km": self.distance_km
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LeadScore":
        """Erstellt LeadScore aus Dictionary"""
        breakdown = ScoreBreakdown.from_dict(data.get("breakdown", {}))

        return cls(
            name=data.get("name", "Unknown"),
            total_score=data.get("total_score", 0.0),
            max_score=data.get("max_score", 100.0),
            percentage=data.get("percentage", 0.0),
            breakdown=breakdown,
            grade=data.get("grade", "F"),
            priority=data.get("priority", "LOW"),
            reasons=data.get("reasons", []),
            target_branches=data.get("target_branches", []),
            distance_km=data.get("distance_km")
        )

    @staticmethod
    def calculate_grade(percentage: float) -> str:
        """
        Berechnet Note aus Prozentwert

        Args:
            percentage: Score als Prozent (0-100)

        Returns:
            Grade als String (A, B, C, D, F)
        """
        if percentage >= 80:
            return "A"
        elif percentage >= 60:
            return "B"
        elif percentage >= 40:
            return "C"
        elif percentage >= 20:
            return "D"
        else:
            return "F"

    @staticmethod
    def calculate_priority(percentage: float, breakdown: ScoreBreakdown) -> str:
        """
        Berechnet Priorität basierend auf Score und Kategorien

        Hohe Priorität wenn:
        - Score >= 70%
        - UND contact_score >= 15 (mindestens Email + Telefon)

        Mittlere Priorität wenn:
        - Score >= 50%
        - UND contact_score >= 10 (mindestens Email)

        Sonst: Niedrige Priorität
        """
        if percentage >= 70 and breakdown.contact >= 15:
            return "HIGH"
        elif percentage >= 50 and breakdown.contact >= 10:
            return "MEDIUM"
        else:
            return "LOW"

    @classmethod
    def create(cls, name: str, breakdown: ScoreBreakdown) -> "LeadScore":
        """
        Factory-Methode: Erstellt LeadScore mit berechneten Werten

        Args:
            name: Unternehmensname
            breakdown: Score-Aufschlüsselung

        Returns:
            LeadScore mit berechnetem Grade und Priority
        """
        total = breakdown.total
        max_score = breakdown.max_score
        percentage = breakdown.percentage

        grade = cls.calculate_grade(percentage)
        priority = cls.calculate_priority(percentage, breakdown)

        return cls(
            name=name,
            total_score=total,
            max_score=max_score,
            breakdown=breakdown,
            percentage=percentage,
            grade=grade,
            priority=priority
        )

    @property
    def is_high_quality(self) -> bool:
        """True wenn Grade A oder B"""
        return self.grade in ("A", "B")

    @property
    def is_medium_quality(self) -> bool:
        """True wenn Grade C"""
        return self.grade == "C"

    @property
    def is_low_quality(self) -> bool:
        """True wenn Grade D oder F"""
        return self.grade in ("D", "F")

    @property
    def is_followup_candidate(self) -> bool:
        """True wenn Priority HIGH oder MEDIUM"""
        return self.priority in ("HIGH", "MEDIUM")

    def __str__(self) -> str:
        """String-Repräsentation"""
        return f"{self.name}: {self.percentage:.0f}% ({self.grade}) - {self.priority}"

    def __repr__(self) -> str:
        """Debug-Repräsentation"""
        return f"LeadScore(name='{self.name}', score={self.total_score:.1f}, grade='{self.grade}')"