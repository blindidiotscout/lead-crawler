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
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from datetime import datetime
import re


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
                 bundesland: Optional[str] = None, page: int = 1, *args, **kwargs):
        """
        Initialisiert Spider mit Suchparametern
        
        Args:
            plz: PLZ für Suche (wird zu Ort aufgelöst)
            ort: Ortsname für direkte Suche (z.B. "Guntramsdorf")
            bundesland: Bundesland (z.B. "niederösterreich")
            page: Startseite für Paginierung
        """
        super().__init__(*args, **kwargs)
        self.plz = plz
        self.ort = ort
        self.bundesland = bundesland
        self.page = page
        
        # URL aufbauen
        self.start_urls = self._build_urls()
    
    def _build_urls(self) -> List[str]:
        """Baut Such-URLs basierend auf Parametern"""
        
        # Bundesland normalisieren
        bl = None
        if self.bundesland:
            bl = BUNDESLAENDER.get(self.bundesland.lower(), self.bundesland.lower())
        
        # Ort: Wenn PLZ gegeben, muss diese zu Ort aufgelöst werden
        # Aktuell: PLZ-Suche nicht direkt unterstützt, nur Ortssuche
        if self.ort:
            ort_clean = self.ort.lower().replace(' ', '-')
            if bl:
                return [f"{self.BASE_URL}/{ort_clean}/{bl}"]
            else:
                # Versuche alle Bundesländer
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
        
        # PLZ-Suche (benötigt Ort-Auflösung)
        results = run_spider(plz="2351")  # Guntramsdorf
        
        # Ortssuche
        results = run_spider(ort="Guntramsdorf", bundesland="niederösterreich")
        
        # Bundesland-Suche
        results = run_spider(ort="Wien", bundesland="wien")
    """
    from scrapy.crawler import CrawlerProcess
    import json
    import tempfile
    import os
    
    # Temporäre Ausgabedatei
    output_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
    output_path = output_file.name
    output_file.close()
    
    # PLZ zu Ort auflösen (vereinfacht)
    if 'plz' in kwargs and 'ort' not in kwargs:
        # TODO: PLZ-Datenbank nutzen
        plz_to_ort = {
            '2351': ('Guntramsdorf', 'niederösterreich'),
            '2353': ('Guntramsdorf', 'niederösterreich'),
            '1010': ('Wien', 'wien'),
            # ... weitere
        }
        plz = kwargs.pop('plz')
        if plz in plz_to_ort:
            ort, bl = plz_to_ort[plz]
            kwargs['ort'] = ort
            if 'bundesland' not in kwargs:
                kwargs['bundesland'] = bl
    
    # Scrapy Einstellungen
    settings = {
        'FEEDS': {output_path: {'format': 'jsonlines'}},
        'LOG_LEVEL': 'INFO',
        'USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'ROBOTSTXT_OBEY': True,
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }
    
    # Spider ausführen
    process = CrawlerProcess(settings)
    process.crawl(spider_name, **kwargs)
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