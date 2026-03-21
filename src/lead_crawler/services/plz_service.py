"""
PLZ Service
Service für PLZ-Verwaltung und Radius-Berechnung
"""

import math
import sqlite3
from pathlib import Path
from typing import Any

from lead_crawler.config import PLZConfig, get_settings
from lead_crawler.models.plz import (
    PLZCoordinate,
    PLZInfo,
    PLZSearchResult,
    plz_to_bundesland,
)


class PLZDatabase:
    """
    Verwaltet österreichische PLZ-Daten mit Koordinaten

    Wrapper um SQLite-Datenbank für PLZ-Geodaten.
    """

    def __init__(self, db_path: Path | None = None):
        """
        Initialisiert PLZ-Datenbank

        Args:
            db_path: Pfad zur SQLite-Datenbank (default: aus Config)
        """
        if db_path is None:
            db_path = get_settings().plz.db_path

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialisiert SQLite-Database mit PLZ-Tabelle"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS plz_coordinates (
                    plz TEXT PRIMARY KEY,
                    ort TEXT NOT NULL,
                    lat REAL NOT NULL,
                    lon REAL NOT NULL,
                    bundesland TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_plz_ort ON plz_coordinates(ort)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_plz_bundesland ON plz_coordinates(bundesland)
            """)
            conn.commit()

    def add_plz(
        self, plz: str, ort: str, lat: float, lon: float, bundesland: str | None = None
    ) -> None:
        """
        Fügt eine PLZ zur Datenbank hinzu

        Args:
            plz: 4-stellige PLZ
            ort: Ortsname
            lat: Breitengrad
            lon: Längengrad
            bundesland: Optional Bundesland
        """
        if bundesland is None:
            bundesland = plz_to_bundesland(plz).value

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO plz_coordinates (plz, ort, lat, lon, bundesland)
                VALUES (?, ?, ?, ?, ?)
            """,
                (plz, ort, lat, lon, bundesland),
            )
            conn.commit()

    def add_many(self, entries: list[dict[str, Any]]) -> int:
        """
        Fügt mehrere PLZ-Einträge hinzu

        Args:
            entries: Liste von Dicts mit plz, ort, lat, lon, bundesland

        Returns:
            Anzahl eingefügter Einträge
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            for entry in entries:
                bundesland = entry.get("bundesland") or plz_to_bundesland(entry["plz"]).value
                conn.execute(
                    """
                    INSERT OR REPLACE INTO plz_coordinates (plz, ort, lat, lon, bundesland)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (entry["plz"], entry["ort"], entry["lat"], entry["lon"], bundesland),
                )
            conn.commit()
        return len(entries)

    def get_plz(self, plz: str) -> PLZCoordinate | None:
        """
        Ruft PLZ-Koordinaten ab

        Args:
            plz: 4-stellige PLZ

        Returns:
            PLZCoordinate oder None
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT plz, ort, lat, lon, bundesland FROM plz_coordinates WHERE plz = ?
            """,
                (plz,),
            )
            row = cursor.fetchone()

            if row:
                return PLZCoordinate(
                    plz=row["plz"],
                    ort=row["ort"],
                    lat=row["lat"],
                    lon=row["lon"],
                    bundesland=row["bundesland"],
                )
            return None

    def get_plz_by_ort(self, ort: str, limit: int = 10) -> list[PLZCoordinate]:
        """
        Sucht PLZ nach Ortsnamen

        Args:
            ort: Ortsname (Teilstring)
            limit: Maximale Ergebnisse

        Returns:
            Liste von PLZCoordinate
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT plz, ort, lat, lon, bundesland FROM plz_coordinates
                WHERE ort LIKE ?
                LIMIT ?
            """,
                (f"%{ort}%", limit),
            )

            return [
                PLZCoordinate(
                    plz=row["plz"],
                    ort=row["ort"],
                    lat=row["lat"],
                    lon=row["lon"],
                    bundesland=row["bundesland"],
                )
                for row in cursor.fetchall()
            ]

    def get_all_plz(self) -> list[PLZCoordinate]:
        """
        Ruft alle PLZ aus der Datenbank ab

        Returns:
            Liste aller PLZCoordinate
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT plz, ort, lat, lon, bundesland FROM plz_coordinates
            """)

            return [
                PLZCoordinate(
                    plz=row["plz"],
                    ort=row["ort"],
                    lat=row["lat"],
                    lon=row["lon"],
                    bundesland=row["bundesland"],
                )
                for row in cursor.fetchall()
            ]

    def get_plz_by_bundesland(self, bundesland: str) -> list[PLZCoordinate]:
        """
        Ruft alle PLZ eines Bundeslands ab

        Args:
            bundesland: Bundesland-Name

        Returns:
            Liste von PLZCoordinate
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT plz, ort, lat, lon, bundesland FROM plz_coordinates
                WHERE bundesland = ?
            """,
                (bundesland,),
            )

            return [
                PLZCoordinate(
                    plz=row["plz"],
                    ort=row["ort"],
                    lat=row["lat"],
                    lon=row["lon"],
                    bundesland=row["bundesland"],
                )
                for row in cursor.fetchall()
            ]

    def count(self) -> int:
        """Gibt Anzahl der PLZ-Einträge zurück"""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM plz_coordinates")
            return cursor.fetchone()[0]


class HaversineCalculator:
    """
    Berechnet Distanzen zwischen Koordinaten (Haversine-Formel)

    Die Haversine-Formel berechnet die Luftlinie zwischen zwei Punkten
    auf einer Kugel (Erde) unter Berücksichtigung der Krümmung.
    """

    ERDE_RADIUS_KM = 6371.0

    @classmethod
    def distance(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Berechnet Distanz zwischen zwei Koordinaten in Kilometern

        Args:
            lat1, lon1: Koordinaten Punkt 1 (Dezimalgrad)
            lat2, lon2: Koordinaten Punkt 2 (Dezimalgrad)

        Returns:
            Distanz in Kilometern
        """
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return cls.ERDE_RADIUS_KM * c

    @classmethod
    def distance_between_coords(cls, coord1: PLZCoordinate, coord2: PLZCoordinate) -> float:
        """
        Berechnet Distanz zwischen zwei PLZCoordinate-Objekten

        Args:
            coord1: Erste Koordinate
            coord2: Zweite Koordinate

        Returns:
            Distanz in Kilometern
        """
        return cls.distance(coord1.lat, coord1.lon, coord2.lat, coord2.lon)


class PLZService:
    """
    Haupt-Service für PLZ-Operationen

    Kombiniert Datenbank-Zugriff und Distanz-Berechnung.
    """

    def __init__(self, config: PLZConfig | None = None):
        """
        Initialisiert PLZ-Service

        Args:
            config: PLZConfig (default: aus get_settings())
        """
        if config is None:
            config = get_settings().plz

        self.db = PLZDatabase(config.db_path)
        self.calculator = HaversineCalculator()
        self.default_radius = config.default_radius_km
        self.max_radius = config.max_radius_km

    def find_in_radius(self, center_plz: str, radius_km: float | None = None) -> PLZSearchResult:
        """
        Findet alle PLZ im gegebenen Radius um eine Ziel-PLZ

        Args:
            center_plz: Ziel-PLZ (z.B. "2351" für Guntramsdorf)
            radius_km: Radius in km (default: aus Config)

        Returns:
            PLZSearchResult mit allen gefundenen PLZ und Distanzen
        """
        if radius_km is None:
            radius_km = self.default_radius

        if radius_km > self.max_radius:
            raise ValueError(f"Radius {radius_km}km exceeds maximum {self.max_radius}km")

        center = self.db.get_plz(center_plz)
        if not center:
            raise ValueError(f"PLZ {center_plz} nicht gefunden")

        all_plz = self.db.get_all_plz()
        results = []

        for plz in all_plz:
            distance = self.calculator.distance_between_coords(center, plz)

            if distance <= radius_km:
                results.append((plz, distance))

        # Sortiere nach Distanz
        results.sort(key=lambda x: x[1])

        return PLZSearchResult(center_plz=center_plz, radius_km=radius_km, results=results)

    def find_nearby_plz(self, center_plz: str, radius_km: float | None = None) -> list[str]:
        """
        Gibt alle PLZ im Radius zurück (nur PLZ-Codes)

        Args:
            center_plz: Ziel-PLZ
            radius_km: Radius in km

        Returns:
            Liste von PLZ-Codes (einzigartig)
        """
        result = self.find_in_radius(center_plz, radius_km)
        return result.plzs

    def get_plz_info(self, plz: str) -> PLZInfo | None:
        """
        Gibt alle Informationen zu einer PLZ zurück

        Args:
            plz: 4-stellige PLZ

        Returns:
            PLZInfo mit allen Orten dieser PLZ
        """
        # In der aktuellen DB-Struktur hat jede PLZ nur einen Ort
        coord = self.db.get_plz(plz)
        if not coord:
            return None

        return PLZInfo(plz=plz, coordinates=[coord])

    def get_wko_urls(self, plz: str) -> list[str]:
        """
        Generiert WKO-URLs für eine PLZ

        Args:
            plz: 4-stellige PLZ

        Returns:
            Liste von WKO URLs
        """
        info = self.get_plz_info(plz)
        if not info:
            return []

        return info.get_wko_urls()

    def get_plz_by_ort(self, ort: str, limit: int = 10) -> list[PLZCoordinate]:
        """
        Sucht PLZ nach Ortsnamen

        Args:
            ort: Ortsname (Teilstring)
            limit: Maximale Ergebnisse

        Returns:
            Liste von PLZCoordinate
        """
        return self.db.get_plz_by_ort(ort, limit)

    def validate_plz(self, plz: str) -> bool:
        """
        Prüft ob PLZ in der Datenbank existiert

        Args:
            plz: 4-stellige PLZ

        Returns:
            True wenn PLZ existiert
        """
        return self.db.get_plz(plz) is not None

    def count(self) -> int:
        """Gibt Anzahl der PLZ in der Datenbank zurück"""
        return self.db.count()


# Singleton-Instanz (Lazy)
_plz_service_instance: PLZService | None = None


def get_plz_service() -> PLZService:
    """
    Gibt die globale PLZ-Service Instanz zurück (Singleton Pattern)

    Returns:
        PLZService Instanz
    """
    global _plz_service_instance
    if _plz_service_instance is None:
        _plz_service_instance = PLZService()
    return _plz_service_instance


def reset_plz_service() -> None:
    """Setzt die globale PLZ-Service Instanz zurück (für Tests)"""
    global _plz_service_instance
    _plz_service_instance = None


# Legacy-Kompatibilität
def get_plz_lookup() -> PLZDatabase:
    """Alias für PLZDatabase (Legacy)"""
    return PLZDatabase()


# Seed-Funktion für Test-Daten
def seed_sample_data(db: PLZDatabase | None = None) -> None:
    """
    Fügt Beispiel-PLZ-Daten hinzu (für Testing)

    Args:
        db: Optional PLZDatabase Instanz
    """
    if db is None:
        db = PLZDatabase()

    sample_data = [
        {
            "plz": "1010",
            "ort": "Wien Innere Stadt",
            "lat": 48.2082,
            "lon": 16.3719,
            "bundesland": "Wien",
        },
        {
            "plz": "1100",
            "ort": "Wien Favoriten",
            "lat": 48.1533,
            "lon": 16.3772,
            "bundesland": "Wien",
        },
        {
            "plz": "1220",
            "ort": "Wien Donaustadt",
            "lat": 48.2167,
            "lon": 16.4167,
            "bundesland": "Wien",
        },
        {
            "plz": "2351",
            "ort": "Guntramsdorf",
            "lat": 48.1067,
            "lon": 16.3256,
            "bundesland": "Niederösterreich",
        },
        {
            "plz": "2353",
            "ort": "Wiener Neudorf",
            "lat": 48.1167,
            "lon": 16.3167,
            "bundesland": "Niederösterreich",
        },
        {
            "plz": "2340",
            "ort": "Mödling",
            "lat": 48.0856,
            "lon": 16.2892,
            "bundesland": "Niederösterreich",
        },
        {
            "plz": "2334",
            "ort": "Vösendorf",
            "lat": 48.1167,
            "lon": 16.3167,
            "bundesland": "Niederösterreich",
        },
        {
            "plz": "2500",
            "ort": "Baden",
            "lat": 48.0067,
            "lon": 16.2317,
            "bundesland": "Niederösterreich",
        },
        {
            "plz": "2320",
            "ort": "Schwechat",
            "lat": 48.1333,
            "lon": 16.3667,
            "bundesland": "Niederösterreich",
        },
        {
            "plz": "2460",
            "ort": "Bruck an der Leitha",
            "lat": 48.0167,
            "lon": 16.8167,
            "bundesland": "Niederösterreich",
        },
        {
            "plz": "4020",
            "ort": "Linz",
            "lat": 48.3069,
            "lon": 14.2858,
            "bundesland": "Oberösterreich",
        },
        {
            "plz": "5020",
            "ort": "Salzburg",
            "lat": 47.8095,
            "lon": 13.0550,
            "bundesland": "Salzburg",
        },
        {"plz": "6020", "ort": "Innsbruck", "lat": 47.2692, "lon": 11.4041, "bundesland": "Tirol"},
        {"plz": "8010", "ort": "Graz", "lat": 47.0707, "lon": 15.4395, "bundesland": "Steiermark"},
        {
            "plz": "9020",
            "ort": "Klagenfurt",
            "lat": 46.6247,
            "lon": 14.3088,
            "bundesland": "Kärnten",
        },
    ]

    db.add_many(sample_data)
