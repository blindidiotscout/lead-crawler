"""
PLZ-Radius-Service für Lead Crawler
Berechnet alle PLZ im gegebenen Radius um eine Ziel-PLZ
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Optional
import sqlite3
from pathlib import Path


@dataclass
class PLZCoordinate:
    plz: str
    ort: str
    lat: float
    lon: float
    bundesland: str = "NÖ"


class PLZDatabase:
    """Verwaltet österreichische PLZ-Daten mit Koordinaten"""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "plz_austria.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialisiert SQLite-Database mit PLZ-Tabelle"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plz_coordinates (
                plz TEXT PRIMARY KEY,
                ort TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                bundesland TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_plz_ort ON plz_coordinates(ort)
        """)
        
        conn.commit()
        conn.close()
    
    def add_plz(self, plz: str, ort: str, lat: float, lon: float, bundesland: str = "NÖ"):
        """Fügt eine PLZ zur Datenbank hinzu"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO plz_coordinates (plz, ort, lat, lon, bundesland)
            VALUES (?, ?, ?, ?, ?)
        """, (plz, ort, lat, lon, bundesland))
        
        conn.commit()
        conn.close()
    
    def get_plz(self, plz: str) -> Optional[PLZCoordinate]:
        """Ruft PLZ-Koordinaten ab"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT plz, ort, lat, lon, bundesland FROM plz_coordinates WHERE plz = ?
        """, (plz,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return PLZCoordinate(plz=row[0], ort=row[1], lat=row[2], lon=row[3], bundesland=row[4])
        return None
    
    def get_all_plz_in_bundesland(self, bundesland: str) -> List[PLZCoordinate]:
        """Ruft alle PLZ eines Bundeslands ab"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT plz, ort, lat, lon, bundesland FROM plz_coordinates WHERE bundesland = ?
        """, (bundesland,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [PLZCoordinate(plz=row[0], ort=row[1], lat=row[2], lon=row[3], bundesland=row[4]) for row in rows]


class HaversineCalculator:
    """Berechnet Distanzen zwischen Koordinaten (Haversine-Formel)"""
    
    ERDE_RADIUS_KM = 6371.0
    
    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Berechnet Distanz zwischen zwei Koordinaten in Kilometern
        
        Args:
            lat1, lon1: Koordinaten Punkt 1
            lat2, lon2: Koordinaten Punkt 2
            
        Returns:
            Distanz in Kilometern
        """
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return HaversineCalculator.ERDE_RADIUS_KM * c


class PLZRadiusService:
    """Haupt-Service für PLZ-Radius-Suche"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db = PLZDatabase(db_path)
        self.calculator = HaversineCalculator()
    
    def find_plz_in_radius(self, center_plz: str, radius_km: float) -> List[Dict]:
        """
        Findet alle PLZ im gegebenen Radius um eine Ziel-PLZ
        
        Args:
            center_plz: Ziel-PLZ (z.B. "2351" für Guntramsdorf)
            radius_km: Radius in Kilometern
            
        Returns:
            Liste von PLZ-Dicts mit Distanz-Info
        """
        center = self.db.get_plz(center_plz)
        if not center:
            raise ValueError(f"PLZ {center_plz} nicht gefunden")
        
        # Hole alle PLZ aus NÖ und Wien (kann erweitert werden)
        all_plz = self.db.get_all_plz_in_bundesland("NÖ")
        all_plz.extend(self.db.get_all_plz_in_bundesland("Wien"))
        
        results = []
        for plz in all_plz:
            distance = self.calculator.calculate_distance(
                center.lat, center.lon, plz.lat, plz.lon
            )
            
            if distance <= radius_km:
                results.append({
                    "plz": plz.plz,
                    "ort": plz.ort,
                    "bundesland": plz.bundesland,
                    "distance_km": round(distance, 2),
                    "lat": plz.lat,
                    "lon": plz.lon
                })
        
        # Sortiere nach Distanz
        results.sort(key=lambda x: x["distance_km"])
        
        return results
    
    def get_plz_prefixes_in_radius(self, center_plz: str, radius_km: float) -> List[str]:
        """
        Gibt alle PLZ-Präfixe (z.B. "23xx") im Radius zurück
        
        Nützlich für fokussierte Suche nach PLZ-Bereichen
        """
        plz_in_radius = self.find_plz_in_radius(center_plz, radius_km)
        
        # Extrahiere Präfixe (erste 2 Ziffern)
        prefixes = set()
        for item in plz_in_radius:
            prefix = item["plz"][:2]
            prefixes.add(prefix)
        
        return sorted(list(prefixes))


# Beispiel-Daten für NÖ PLZ (kann erweitert werden)
def seed_sample_data(db: PLZDatabase):
    """Fügt Beispiel-PLZ-Daten hinzu (für Testing)"""
    
    # Guntramsdorf Basis
    db.add_plz("2351", "Guntramsdorf", 48.1067, 16.3256, "NÖ")
    
    # Wr. Neudorf (EKO Plus Standort)
    db.add_plz("2353", "Wiener Neudorf", 48.1167, 16.3167, "NÖ")
    
    # Mödling
    db.add_plz("2340", "Mödling", 48.0856, 16.2892, "NÖ")
    
    # Vösendorf
    db.add_plz("2334", "Vösendorf", 48.1167, 16.3167, "NÖ")
    
    # Baden
    db.add_plz("2500", "Baden", 48.0067, 16.2317, "NÖ")
    
    # Schwechat
    db.add_plz("2320", "Schwechat", 48.1333, 16.3667, "NÖ")
    
    # Bruck an der Leitha
    db.add_plz("2460", "Bruck an der Leitha", 48.0167, 16.8167, "NÖ")
    
    # Wien (1xxx)
    db.add_plz("1010", "Wien Innere Stadt", 48.2082, 16.3719, "Wien")
    db.add_plz("1100", "Wien Favoriten", 48.1533, 16.3772, "Wien")
    db.add_plz("1220", "Wien Donaustadt", 48.2167, 16.4167, "Wien")


if __name__ == "__main__":
    # Test-Ausführung
    db = PLZDatabase()
    seed_sample_data(db)
    
    service = PLZRadiusService()
    
    print("=== PLZ-Radius-Service Test ===\n")
    
    # Test: 50km Radius um Guntramsdorf
    results = service.find_plz_in_radius("2351", 50)
    print(f"PLZ im 50km Radius um 2351 (Guntramsdorf): {len(results)} gefunden\n")
    
    for item in results[:10]:  # Zeige erste 10
        print(f"{item['plz']} {item['ort']:20} {item['distance_km']:>6.2f} km")
    
    print(f"\n{'... und ' + str(len(results) - 10) + ' weitere' if len(results) > 10 else ''}")
    
    print(f"\nPLZ-Präfixe im Radius: {service.get_plz_prefixes_in_radius('2351', 50)}")
