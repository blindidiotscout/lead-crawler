"""
PLZ Domain Models
Definiert Postleitzahlen- und Geodaten-Modelle
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Tuple
from enum import Enum


class Bundesland(Enum):
    """Österreichische Bundesländer"""
    WIEN = "Wien"
    NIEDEROESTERREICH = "Niederösterreich"
    OBEROESTERREICH = "Oberösterreich"
    STEIERMARK = "Steiermark"
    TIROL = "Tirol"
    KAERNTEN = "Kärnten"
    SALZBURG = "Salzburg"
    BURGENLAND = "Burgenland"
    VORARLBERG = "Vorarlberg"

    @classmethod
    def from_string(cls, name: str) -> "Bundesland":
        """
        Normalisiert Bundesland-String

        Args:
            name: Bundesland-Name (verschiedene Schreibweisen)

        Returns:
            Bundesland Enum
        """
        normalized = name.lower().strip()

        mappings = {
            "wien": cls.WIEN,
            "niederösterreich": cls.NIEDEROESTERREICH,
            "niederosterreich": cls.NIEDEROESTERREICH,
            "noe": cls.NIEDEROESTERREICH,
            "oberösterreich": cls.OBEROESTERREICH,
            "oberosterreich": cls.OBEROESTERREICH,
            "ooe": cls.OBEROESTERREICH,
            "steiermark": cls.STEIERMARK,
            "stmk": cls.STEIERMARK,
            "tirol": cls.TIROL,
            "tir": cls.TIROL,
            "kärnten": cls.KAERNTEN,
            "kaernten": cls.KAERNTEN,
            "k": cls.KAERNTEN,
            "salzburg": cls.SALZBURG,
            "sbg": cls.SALZBURG,
            "burgenland": cls.BURGENLAND,
            "bgld": cls.BURGENLAND,
            "vorarlberg": cls.VORARLBERG,
            "vbg": cls.VORARLBERG,
        }

        return mappings.get(normalized, cls.NIEDEROESTERREICH)  # Default fallback


# PLZ zu Bundesland Mapping (erste Ziffer)
PLZ_BUNDESLAND_PREFIX = {
    "1": Bundesland.WIEN,
    "2": Bundesland.NIEDEROESTERREICH,
    "3": Bundesland.NIEDEROESTERREICH,
    "4": Bundesland.OBEROESTERREICH,
    "5": Bundesland.SALZBURG,
    "6": Bundesland.STEIERMARK,
    "7": Bundesland.TIROL,
    "8": Bundesland.VORARLBERG,
    "9": Bundesland.BURGENLAND,
}


@dataclass
class PLZCoordinate:
    """
    Koordinaten für eine PLZ

    Enthält Geokoordinaten und Ortsinformationen
    """
    plz: str  # 4-stellige PLZ
    ort: str  # Ortsname
    bundesland: str  # Bundesland
    bezirk: Optional[str] = None  # Politischer Bezirk
    lat: float = 0.0  # Breitengrad
    lon: float = 0.0  # Längengrad

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PLZCoordinate":
        """Erstellt PLZCoordinate aus Dictionary"""
        return cls(
            plz=data.get("plz", ""),
            ort=data.get("ort", ""),
            bundesland=data.get("bundesland", ""),
            bezirk=data.get("bezirk"),
            lat=data.get("lat", 0.0),
            lon=data.get("lon", 0.0)
        )

    @property
    def bundesland_enum(self) -> Bundesland:
        """Gibt Bundesland als Enum zurück"""
        return Bundesland.from_string(self.bundesland)

    def distance_to(self, other: "PLZCoordinate") -> float:
        """
        Berechnet Luftlinien-Distanz zu einer anderen Koordinate (in km)

        Verwendet Haversine-Formel

        Args:
            other: Andere PLZCoordinate

        Returns:
            Distanz in Kilometern
        """
        import math

        # Haversine-Formel
        R = 6371  # Erdradius in km

        lat1 = math.radians(self.lat)
        lat2 = math.radians(other.lat)
        dlat = math.radians(other.lat - self.lat)
        dlon = math.radians(other.lon - self.lon)

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def __str__(self) -> str:
        """String-Repräsentation"""
        return f"{self.plz} {self.ort} ({self.bundesland})"


@dataclass
class PLZInfo:
    """
    Vollständige PLZ-Informationen

    Enthält alle Daten zu einer PLZ inkl. Geodaten
    """
    plz: str
    coordinates: List[PLZCoordinate] = field(default_factory=list)

    # Cache für häufige Abfragen
    _primary_ort: Optional[str] = None
    _primary_coordinate: Optional[PLZCoordinate] = None

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary"""
        return {
            "plz": self.plz,
            "orte": [c.to_dict() for c in self.coordinates]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PLZInfo":
        """Erstellt PLZInfo aus Dictionary"""
        coordinates = [
            PLZCoordinate.from_dict(c)
            for c in data.get("coordinates", [])
        ]
        return cls(
            plz=data.get("plz", ""),
            coordinates=coordinates
        )

    @property
    def orte(self) -> List[str]:
        """Alle Orte für diese PLZ"""
        return list(set(c.ort for c in self.coordinates))

    @property
    def primary_ort(self) -> str:
        """Hauptort für diese PLZ (erster Eintrag)"""
        if self._primary_ort is None:
            self._primary_ort = self.coordinates[0].ort if self.coordinates else ""
        return self._primary_ort

    @property
    def primary_coordinate(self) -> Optional[PLZCoordinate]:
        """Hauptkoordinate für diese PLZ"""
        if self._primary_coordinate is None and self.coordinates:
            self._primary_coordinate = self.coordinates[0]
        return self._primary_coordinate

    @property
    def bundesland(self) -> str:
        """Bundesland der PLZ"""
        return self.coordinates[0].bundesland if self.coordinates else ""

    def get_wko_urls(self) -> List[str]:
        """
        Generiert WKO-URLs für alle Orte dieser PLZ

        Returns:
            Liste von WKO URLs
        """
        urls = []
        for coord in self.coordinates:
            ort = coord.ort.lower().replace(' ', '-')
            bundesland = coord.bundesland.lower()
            urls.append(f"https://firmen.wko.at/{ort}/{bundesland}")
        return urls

    def __str__(self) -> str:
        """String-Repräsentation"""
        orte_str = ", ".join(self.orte[:3])
        if len(self.orte) > 3:
            orte_str += f" (+{len(self.orte) - 3})"
        return f"{self.plz}: {orte_str} ({self.bundesland})"


@dataclass
class PLZSearchResult:
    """
    Ergebnis einer PLZ-Radius-Suche

    Enthält alle gefundenen PLZ mit Distanzen
    """
    center_plz: str
    radius_km: float
    results: List[Tuple[PLZCoordinate, float]] = field(default_factory=list)  # (coordinate, distance)

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary"""
        return {
            "center_plz": self.center_plz,
            "radius_km": self.radius_km,
            "results": [
                {"plz": coord.plz, "ort": coord.ort, "distance_km": dist}
                for coord, dist in self.results
            ]
        }

    @property
    def count(self) -> int:
        """Anzahl gefundener PLZ"""
        return len(self.results)

    @property
    def plzs(self) -> List[str]:
        """Alle gefundenen PLZ (einzigartig)"""
        return list(set(coord.plz for coord, _ in self.results))

    @property
    def max_distance(self) -> float:
        """Maximale Distanz in den Ergebnissen"""
        return max((dist for _, dist in self.results), default=0.0)

    @property
    def min_distance(self) -> float:
        """Minimale Distanz in den Ergebnissen"""
        return min((dist for _, dist in self.results), default=0.0)

    def filter_by_distance(self, max_km: float) -> "PLZSearchResult":
        """
        Filtert Ergebnisse nach maximaler Distanz

        Args:
            max_km: Maximale Distanz in km

        Returns:
            Neues PLZSearchResult mit gefilterten Ergebnissen
        """
        filtered = [(coord, dist) for coord, dist in self.results if dist <= max_km]
        return PLZSearchResult(
            center_plz=self.center_plz,
            radius_km=self.radius_km,
            results=filtered
        )

    def sort_by_distance(self) -> "PLZSearchResult":
        """
        Sortiert Ergebnisse nach Distanz (aufsteigend)

        Returns:
            Neues PLZSearchResult mit sortierten Ergebnissen
        """
        sorted_results = sorted(self.results, key=lambda x: x[1])
        return PLZSearchResult(
            center_plz=self.center_plz,
            radius_km=self.radius_km,
            results=sorted_results
        )

    def __str__(self) -> str:
        """String-Repräsentation"""
        return f"PLZ {self.center_plz}: {self.count} PLZ im {self.radius_km}km Radius"


# Convenience Functions

def plz_to_bundesland(plz: str) -> Bundesland:
    """
    Ermittelt Bundesland aus PLZ (basierend auf erster Ziffer)

    Args:
        plz: 4-stellige PLZ

    Returns:
        Bundesland Enum
    """
    if not plz or len(plz) < 1:
        return Bundesland.NIEDEROESTERREICH  # Default

    first_digit = plz[0]
    return PLZ_BUNDESLAND_PREFIX.get(first_digit, Bundesland.NIEDEROESTERREICH)


def is_valid_plz(plz: str) -> bool:
    """
    Prüft ob PLZ gültig (4-stellige Zahl)

    Args:
        plz: PLZ-String

    Returns:
        True wenn gültig
    """
    if not plz:
        return False
    if len(plz) != 4:
        return False
    if not plz.isdigit():
        return False
    # Erste Ziffer muss 1-9 sein
    if plz[0] not in "123456789":
        return False
    return True