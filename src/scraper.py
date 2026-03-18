"""
Lead Crawler Scraper Module
Scrapy-basierte Spider für österreichische Unternehmensdaten

Datenquellen:
- firmen.wko.at (Wirtschaftskammer Firmen A-Z)

URL-Formate:
- Ortssuche: https://firmen.wko.at/{ort}/{bundesland}
- Beispiel: https://firmen.wko.at/guntramsdorf/niederösterreich
"""

import scrapy
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import re
import sqlite3
from pathlib import Path


class PLZLookup:
    """PLZ zu Ort/Bundesland Lookup aus SQLite-Datenbank"""
    
    def __init__(self, db_path: str = None):
        """
        Initialisiert PLZ-Lookup
        
        Args:
            db_path: Pfad zur plz_austria.db (default: data/plz_austria.db)
        """
        if db_path is None:
            # Default-Pfad relativ zum Modul
            module_dir = Path(__file__).parent.parent
            db_path = module_dir / "data" / "plz_austria.db"
        
        self.db_path = str(db_path)
        self._conn = None
    
    @property
    def conn(self):
        """Lazy connection initialization"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
        return self._conn
    
    def get_ort_by_plz(self, plz: str) -> List[Tuple[str, str, str]]:
        """
        Sucht Ort(e) für eine PLZ
        
        Args:
            plz: 4-stellige PLZ (z.B. "2351")
        
        Returns:
            Liste von (ort, bundesland, bezirk) Tupeln
            Beispiel: [("Guntramsdorf", "Niederösterreich", "Mödling")]
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT ort, bundesland, bezirk
            FROM plz_coordinates
            WHERE plz = ?
            ORDER BY ort
        """, (plz,))
        
        results = cursor.fetchall()
        return [(row[0], row[1], row[2]) for row in results]
    
    def get_plz_info(self, plz: str) -> Optional[Dict]:
        """
        Gibt alle Infos zu einer PLZ zurück
        
        Args:
            plz: 4-stellige PLZ
        
        Returns:
            Dict mit plz, ort, bundesland, lat, lon (erster Treffer)
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT plz, ort, bundesland, lat, lon, bezirk
            FROM plz_coordinates
            WHERE plz = ?
            ORDER BY ort
            LIMIT 1
        """, (plz,))
        
        row = cursor.fetchone()
        if row:
            return {
                'plz': row[0],
                'ort': row[1],
                'bundesland': row[2],
                'lat': row[3],
                'lon': row[4],
                'bezirk': row[5]
            }
        return None
    
    def get_all_orte_by_plz(self, plz: str) -> List[Dict]:
        """
        Gibt alle Orte zu einer PLZ zurück
        
        Args:
            plz: 4-stellige PLZ
        
        Returns:
            Liste von Dicts mit ort, bundesland, bezirk, lat, lon
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT ort, bundesland, bezirk, lat, lon
            FROM plz_coordinates
            WHERE plz = ?
            ORDER BY ort
        """, (plz,))
        
        return [
            {'ort': row[0], 'bundesland': row[1], 'bezirk': row[2], 'lat': row[3], 'lon': row[4]}
            for row in cursor.fetchall()
        ]
    
    def get_wko_url(self, plz: str) -> List[str]:
        """
        Generiert WKO-URLs für alle Orte einer PLZ
        
        Args:
            plz: 4-stellige PLZ
        
        Returns:
            Liste von WKO URLs (eine pro Ort)
        """
        orte = self.get_all_orte_by_plz(plz)
        if not orte:
            return []
        
        urls = []
        for ort_info in orte:
            ort = ort_info['ort'].lower().replace(' ', '-')
            bundesland = ort_info['bundesland'].lower()
            urls.append(f"https://firmen.wko.at/{ort}/{bundesland}")
        
        return urls
    
    def close(self):
        """Schließt DB-Verbindung"""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Globale Instanz (lazy)
_plz_lookup = None


def get_plz_lookup() -> PLZLookup:
    """Gibt globale PLZ-Lookup Instanz zurück"""
    global _plz_lookup
    if _plz_lookup is None:
        _plz_lookup = PLZLookup()
    return _plz_lookup


# Bundesland-Mapping
BUNDESLAENDER = {
    "burgenland": "burgenland",
    "kärnten": "kärnten",
    "kaernten": "kärnten",
    "niederösterreich": "niederösterreich",
    "niederosterreich": "niederösterreich",
    "oberösterreich": "oberösterreich",
    "oberosterreich": "oberösterreich",
    "salzburg": "salzburg",
    "steiermark": "steiermark",
    "tirol": "tirol",
    "vorarlberg": "vorarlberg",
    "wien": "wien",
}

# PLZ zu Bundesland (erste Ziffer)
PLZ_BUNDESLAND = {
    "1": "wien",      # 1010-1230 Wien
    "2": "niederösterreich",  # 2000-2999 NÖ (teils)
    "3": "niederösterreich",  # 3000-3999 NÖ (teils)
    "4": "oberösterreich",  # 4000-4999 OÖ
    "5": "salzburg",  # 5000-5999 Salzburg
    "6": "steiermark",  # 6000-6999 Steiermark
    "7": "tirol",  # 7000-7999 Tirol
    "8": "vorarlberg",  # 8000-8999 Vorarlberg
    "9": "burgenland",  # 9000-9999 Burgenland
}


@dataclass
class CompanyData:
    """Standardisiertes Unternehmens-Datenmodell"""
    name: str
    url: Optional[str] = None
    address: Optional[str] = None
    street: Optional[str] = None
    plz: Optional[str] = None
    ort: Optional[str] = None
    bundesland: Optional[str] = None
    branche: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    source: Optional[str] = None
    crawled_at: str = None
    
    def __post_init__(self):
        if self.crawled_at is None:
            self.crawled_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Konvertiert zu Dictionary"""
        return {k: v for k, v in asdict(self).items() if v is not None}


class WkoSpider(scrapy.Spider):
    """Spider für firmen.wko.at (WKO Firmen A-Z)
    
    Verwendet direkte URLs im Format:
    https://firmen.wko.at/{ort}/{bundesland}
    
    Beispiel:
    - https://firmen.wko.at/guntramsdorf/niederösterreich
    - https://firmen.wko.at/wien/wien
    """
    
    name = "wko"
    allowed_domains = ["wko.at", "firmen.wko.at"]
    BASE_URL = "https://firmen.wko.at"
    
    def __init__(self, plz: Optional[str] = None, ort: Optional[str] = None,
                 bundesland: Optional[str] = None, page: int = 1,
                 _urls: Optional[List[str]] = None, *args, **kwargs):
        """
        Initialisiert Spider mit Suchparametern
        
        Args:
            plz: PLZ für Suche (wird zu Ort aufgelöst)
            ort: Ortsname für direkte Suche (z.B. "Guntramsdorf")
            bundesland: Bundesland (z.B. "niederösterreich")
            page: Startseite für Paginierung
            _urls: Direkte URLs (intern verwendet)
        """
        super().__init__(*args, **kwargs)
        self.plz = plz
        self.ort = ort
        self.bundesland = bundesland
        self.page = page
        
        # URL aufbauen
        if _urls:
            # URLs wurden direkt übergeben
            self.start_urls = _urls
        else:
            self.start_urls = self._build_urls()
    
    def _build_urls(self) -> List[str]:
        """Baut Such-URLs basierend auf Parametern
        
        Priorität:
        1. PLZ (wird zu Ort aufgelöst via PLZ-Datenbank)
        2. Ort + Bundesland
        3. Ort (alle Bundesländer)
        
        Returns:
            Liste von URLs (kann mehrere sein für PLZ mit mehreren Orten)
        """
        
        # PLZ-Suche: Zu Ort auflösen
        if self.plz and not self.ort:
            lookup = get_plz_lookup()
            urls = lookup.get_wko_url(self.plz)
            
            if urls:
                self.logger.info(f"PLZ {self.plz} → {len(urls)} URL(s)")
                for url in urls:
                    self.logger.info(f"  {url}")
                return urls
            else:
                self.logger.warning(f"PLZ {self.plz} nicht in Datenbank gefunden")
                return [f"{self.BASE_URL}/"]
        
        # Bundesland normalisieren
        bl = None
        if self.bundesland:
            bl = BUNDESLAENDER.get(self.bundesland.lower(), self.bundesland.lower())
        
        # Ortssuche
        if self.ort:
            ort_clean = self.ort.lower().replace(' ', '-')
            if bl:
                return [f"{self.BASE_URL}/{ort_clean}/{bl}"]
            else:
                return [f"{self.BASE_URL}/{ort_clean}"]
        
        # Default: Hauptseite
        return [f"{self.BASE_URL}/"]
    
    def parse(self, response):
        """Parse WKO Suchergebnisse"""
        
        # Prüfe auf "Keine Treffer"
        no_results = response.css('h3:contains("keinen Treffer")').get()
        if no_results:
            self.logger.warning(f"Keine Ergebnisse gefunden für {response.url}")
            return
        
        # Extrahiere Firmeneinträge
        articles = response.css('article.search-result-article')
        self.logger.info(f"Gefunden: {len(articles)} Firmeneinträge auf {response.url}")
        
        for article in articles:
            company = self._parse_result_article(article, response)
            if company:
                yield company
        
        # Paginierung
        # WKO verwendet ASP.NET, Paginierung ist komplex
        # Für jetzt: nur erste Seite
        # TODO: Paginierung implementieren
    
    def _parse_result_article(self, article, response) -> Optional[Dict]:
        """Parst einen einzelnen Suchergebnis-Artikel"""
        
        # Name
        name = article.css('h3::text').get()
        if not name:
            name = article.css('a.title-link h3::text').get()
        
        # URL
        url = article.css('a.title-link::attr(href)').get()
        if url and not url.startswith('http'):
            # URL bereinigen (Query-Parameter entfernen)
            url = url.split('?')[0]
            url = response.urljoin(url)
        
        # Adresse
        street = article.css('div.street::text').get(default='').strip()
        place = article.css('div.place::text').get(default='').strip()
        
        # PLZ und Ort extrahieren
        plz, ort = self._extract_plz_ort(place)
        
        # Bundesland aus URL extrahieren
        bundesland = self._extract_bundesland(response.url)
        
        # Telefon
        telefon = article.css('a[href^="tel:"]::attr(href)').get()
        if telefon:
            telefon = telefon.replace('tel:', '').replace('%20', ' ').strip()
        
        # Email
        email = article.css('a[href^="mailto:"]::attr(href)').get()
        if email:
            email = email.replace('mailto:', '').strip()
        
        # Website (nicht WKO-Links)
        website = None
        for link in article.css('a[href^="http"]::attr(href)').getall():
            if 'wko.at' not in link and 'maps.google' not in link:
                website = link
                break
        
        return {
            'name': name.strip() if name else None,
            'url': url,
            'street': street,
            'plz': plz,
            'ort': ort,
            'bundesland': bundesland,
            'telefon': telefon,
            'email': email,
            'website': website,
            'source': 'firmen.wko.at'
        }
    
    def _extract_plz_ort(self, place_text: str) -> tuple:
        """Extrahiert PLZ und Ort aus Place-Text"""
        if not place_text:
            return None, None
        
        # Format: "1010           Wien" oder "2353 Guntramsdorf"
        place_text = place_text.strip()
        
        # PLZ (4-stellig)
        plz_match = re.search(r'\b(\d{4})\b', place_text)
        plz = plz_match.group(1) if plz_match else None
        
        # Ort (alles nach PLZ)
        if plz:
            ort_match = re.search(r'\d{4}\s+(.+)', place_text)
            ort = ort_match.group(1).strip() if ort_match else None
        else:
            ort = place_text
        
        return plz, ort
    
    def _extract_bundesland(self, url: str) -> Optional[str]:
        """Extrahiert Bundesland aus URL"""
        # Format: https://firmen.wko.at/{ort}/{bundesland}
        parts = url.split('/')
        if len(parts) >= 5:
            bl = parts[4].split('?')[0]
            return BUNDESLAENDER.get(bl, bl)
        return None


def run_spider(spider_name: str = "wko", **kwargs) -> List[Dict]:
    """
    Führt einen Spider aus und gibt Ergebnisse zurück
    
    Usage:
        from src.scraper import run_spider
        
        # PLZ-Suche (nutzt PLZ-Datenbank)
        results = run_spider(plz="2351")  # → Guntramsdorf
        
        # Ortssuche
        results = run_spider(ort="Guntramsdorf", bundesland="niederösterreich")
        
        # Alle Orte im Umkreis (nutzt PLZ-Datenbank)
        from src.plz_radius import PLZRadiusService
        service = PLZRadiusService('data/plz_austria.db')
        plz_list = service.find_plz_in_radius("2351", 20)  # 20km Radius
        all_results = []
        for item in plz_list:
            results = run_spider(plz=item['plz'])
            all_results.extend(results)
    """
    from scrapy.crawler import CrawlerProcess
    import json
    import tempfile
    import os
    
    # Temporäre Ausgabedatei
    output_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
    output_path = output_file.name
    output_file.close()
    
    # PLZ zu Ort auflösen via Datenbank
    if 'plz' in kwargs and 'ort' not in kwargs:
        lookup = get_plz_lookup()
        urls = lookup.get_wko_url(kwargs['plz'])
        
        if urls:
            # URLs direkt übergeben
            kwargs['_urls'] = urls
            import logging
            logging.info(f"PLZ {kwargs['plz']} → {len(urls)} URLs")
    
    # Scrapy Einstellungen
    settings = {
        'FEEDS': {output_path: {'format': 'jsonlines'}},
        'LOG_LEVEL': 'INFO',
        'USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'ROBOTSTXT_OBEY': True,
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }
    
    # Spider ausführen - direkt Klasse übergeben
    process = CrawlerProcess(settings)
    process.crawl(WkoSpider, **kwargs)  # Spider-Klasse direkt, nicht Name
    process.start()
    
    # Ergebnisse laden
    results = []
    try:
        with open(output_path, 'r') as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
    except FileNotFoundError:
        pass
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)
    
    return results


if __name__ == "__main__":
    print("=== WKO Spider Test ===\n")
    
    # Test mit Guntramsdorf
    print("Test: Suche nach Guntramsdorf")
    print("URL: https://firmen.wko.at/guntramsdorf/niederösterreich\n")
    
    results = run_spider(ort="Guntramsdorf", bundesland="niederösterreich")
    
    print(f"Gefundene Unternehmen: {len(results)}\n")
    for i, c in enumerate(results[:5], 1):
        print(f"{i}. {c.get('name')}")
        print(f"   {c.get('street')}, {c.get('plz')} {c.get('ort')}")
        print()