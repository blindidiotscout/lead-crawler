"""
ecoplus Spider
Crawlt Unternehmen in ecoplus Wirtschaftsparks (Niederösterreich)

Datenquelle:
- https://ecoplus.at/wirtschaftsparks
- Standortkompass: https://standortkompass.at

ecoplus = Wirtschaftsgesellschaft des Landes NÖ
Verwaltet 16 Wirtschaftsparks mit ansässigen Unternehmen
"""

import scrapy
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from datetime import datetime
import re


@dataclass
class EcoplusCompany:
    """Unternehmens-Daten von ecoplus"""
    name: str
    wirtschaftspark: str  # z.B. "IZ NÖ-Süd"
    objekt: Optional[str] = None  # z.B. "M6/M7"
    strasse: Optional[str] = None
    plz: Optional[str] = None
    ort: Optional[str] = None
    website: Optional[str] = None
    branche: Optional[str] = None
    mitarbeiter: Optional[str] = None
    source: str = "ecoplus.at"
    crawled_at: str = None
    
    def __post_init__(self):
        if self.crawled_at is None:
            self.crawled_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


# ecoplus Wirtschaftsparks
WIRTSCHAFTSPARKS = {
    "iz-noe-sued": {
        "name": "IZ NÖ-Süd",
        "url": "https://www.ecoplus.at/wirtschaftsparks/ecoplus-wirtschaftspark-iz-noe-sued",
        "gemeinden": ["Wiener Neudorf", "Guntramsdorf", "Laxenburg", "Biedermannsdorf"],
        "plz": ["2351", "2352", "2353", "2355"]
    },
    "wolkersdorf": {
        "name": "Wirtschaftspark Wolkersdorf",
        "url": "https://www.ecoplus.at/betriebsansiedlung/wirtschaftspark-wolkersdorf",
        "gemeinden": ["Wolkersdorf"],
        "plz": ["2100"]
    },
    "bruck-leitha": {
        "name": "Wirtschaftspark Bruck an der Leitha",
        "url": "https://www.ecoplus.at/betriebsansiedlung/wirtschaftspark-bruck-der-leitha",
        "gemeinden": ["Bruck an der Leitha"],
        "plz": ["2460"]
    },
    "schrems": {
        "name": "Wirtschaftspark Schrems",
        "url": "https://www.ecoplus.at/betriebsansiedlung/wirtschaftspark-schrems",
        "gemeinden": ["Schrems"],
        "plz": ["3943"]
    },
    "kottingbrunn": {
        "name": "CCK Wirtschaftspark Kottingbrunn",
        "url": "https://www.ecoplus.at/betriebsansiedlung/wirtschaftspark-kottingbrunn",
        "gemeinden": ["Kottingbrunn"],
        "plz": ["2542"]
    },
    # Weitere Parks können hier ergänzt werden
}


class EcoplusSpider(scrapy.Spider):
    """Spider für ecoplus.at Wirtschaftsparks"""
    
    name = "ecoplus"
    allowed_domains = ["ecoplus.at", "standortkompass.at"]
    
    def __init__(self, 
                 park: Optional[str] = None,
                 parks: Optional[List[str]] = None,
                 *args, **kwargs):
        """
        Initialisiert Spider
        
        Args:
            park: Einzelner Wirtschaftspark (z.B. "iz-noe-sued")
            parks: Liste von Parks (z.B. ["iz-noe-sued", "wolkersdorf"])
        """
        super().__init__(*args, **kwargs)
        
        # Parks auswählen
        if parks:
            self.target_parks = {k: v for k, v in WIRTSCHAFTSPARKS.items() if k in parks}
        elif park:
            self.target_parks = {park: WIRTSCHAFTSPARKS.get(park, {})}
        else:
            # Alle Parks
            self.target_parks = WIRTSCHAFTSPARKS
        
        # Start-URLs
        self.start_urls = [p.get('url') for p in self.target_parks.values() if p.get('url')]
    
    def parse(self, response):
        """Parst ecoplus Wirtschaftspark Seite"""
        
        park_key = self._extract_park_key(response.url)
        park_info = self.target_parks.get(park_key, {})
        
        self.logger.info(f"Parsing: {park_info.get('name', park_key)}")
        
        # Suche nach Unternehmenslisten
        # ecoplus hat verschiedene Formate je Park
        
        # 1. News-Artikel über Neuansiedlungen
        for article in response.css('article'):
            company = self._parse_news_article(article, park_info)
            if company:
                yield company
        
        # 2. Statische Listen (manche Parks haben PDFs/JPGs)
        # Diese müssen separat verarbeitet werden
        
        # 3. Links zu Unternehmensseiten
        for link in response.css('a[href*="unternehmen"]'):
            yield response.follow(link, self.parse_company, 
                                  meta={'park_info': park_info})
        
        # 4. Links zu Standortkompass
        for link in response.css('a[href*="standortkompass"]'):
            yield response.follow(link, self.parse_standortkompass,
                                  meta={'park_info': park_info})
    
    def _extract_park_key(self, url: str) -> str:
        """Extrahiert Park-Key aus URL"""
        for key, info in WIRTSCHAFTSPARKS.items():
            if info.get('url') == url or key in url.lower():
                return key
        return url.split('/')[-1]
    
    def _parse_news_article(self, article, park_info: Dict) -> Optional[Dict]:
        """Parst News-Artikel über Neuansiedlungen"""
        
        # Titel enthält oft Firmennamen
        title = article.css('h2::text, h3::text, .title::text').get()
        if not title:
            return None
        
        # Firmenname aus Titel extrahieren
        name = self._extract_company_name(title)
        if not name:
            return None
        
        # Ort/Adresse
        text = article.css('p::text').getall()
        text = ' '.join(text)
        
        plz = self._extract_plz(text)
        ort = self._extract_ort(text, plz)
        
        return {
            'name': name,
            'wirtschaftspark': park_info.get('name', 'Unknown'),
            'plz': plz,
            'ort': ort,
            'source': 'ecoplus.at/news'
        }
    
    def _extract_company_name(self, title: str) -> Optional[str]:
        """Extrahiert Firmennamen aus Titel"""
        # Pattern: "Firmenname GmbH: ..." oder "Neue Ansiedlung: Firmenname"
        patterns = [
            r'^([A-Z][A-Za-zäöüß\s]+(?:GmbH|AG|KG|OG|GmbH & Co KG))',
            r'Ansiedlung[:\s]+([A-Z][A-Za-zäöüß\s]+)',
            r'Neu[:\s]+([A-Z][A-Za-zäöüß\s]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_plz(self, text: str) -> Optional[str]:
        """Extrahiert PLZ aus Text"""
        match = re.search(r'\b(\d{4})\b', text)
        return match.group(1) if match else None
    
    def _extract_ort(self, text: str, plz: Optional[str]) -> Optional[str]:
        """Extrahiert Ort aus Text"""
        # Ort steht oft nach PLZ
        if plz:
            match = re.search(rf'{plz}\s+([A-Z][a-zäöüß]+)', text)
            if match:
                return match.group(1)
        return None
    
    def parse_company(self, response):
        """Parst Unternehmensseite"""
        
        park_info = response.meta.get('park_info', {})
        
        # Firmenname
        name = response.css('h1::text, .company-name::text').get()
        
        # Adresse
        street = response.css('.street::text, .address::text').get()
        plz_ort = response.css('.place::text, .location::text').get()
        
        plz = self._extract_plz(plz_ort or '')
        
        # Website
        website = response.css('a[href^="http"]::attr(href)').get()
        
        # Branche (falls verfügbar)
        branche = response.css('.branch::text, .category::text').get()
        
        yield {
            'name': name.strip() if name else None,
            'wirtschaftspark': park_info.get('name', 'Unknown'),
            'strasse': street,
            'plz': plz,
            'website': website,
            'branche': branche,
            'source': 'ecoplus.at'
        }
    
    def parse_standortkompass(self, response):
        """Parst Standortkompass (JavaScript-App)"""
        
        # Standortkompass ist eine React/Vue App
        # Daten werden wahrscheinlich via API geladen
        
        # Versuche JSON aus embedded data zu extrahieren
        for script in response.css('script::text').getall():
            if '__INITIAL_STATE__' in script or 'window.__data' in script:
                # JSON-Daten extrahieren
                # TODO: Implementieren wenn wir die Struktur kennen
                pass
        
        # Fallback: Company-Links
        for link in response.css('a[href*="unternehmen"], a[href*="company"]'):
            yield response.follow(link, self.parse_company)


def run_ecoplus_spider(park: Optional[str] = None,
                        parks: Optional[List[str]] = None) -> List[Dict]:
    """
    Führt ecoplus Spider aus
    
    Args:
        park: Einzelner Park (z.B. "iz-noe-sued")
        parks: Liste von Parks
    
    Returns:
        Liste von Unternehmen
    
    Example:
        # Alle Parks
        results = run_ecoplus_spider()
        
        # Nur IZ NÖ-Süd
        results = run_ecoplus_spider(park="iz-noe-sued")
        
        # Mehrere Parks
        results = run_ecoplus_spider(parks=["iz-noe-sued", "wolkersdorf"])
    """
    from scrapy.crawler import CrawlerProcess
    import json
    import tempfile
    import os
    
    # Temp-File
    output_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
    output_path = output_file.name
    output_file.close()
    
    # Scrapy Settings
    settings = {
        'FEEDS': {output_path: {'format': 'jsonlines'}},
        'LOG_LEVEL': 'INFO',
        'USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'ROBOTSTXT_OBEY': True,
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }
    
    # Spider args
    spider_kwargs = {}
    if park:
        spider_kwargs['park'] = park
    if parks:
        spider_kwargs['parks'] = parks
    
    # Run
    process = CrawlerProcess(settings)
    process.crawl(EcoplusSpider, **spider_kwargs)
    process.start()
    
    # Load results
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


def get_ecoplus_parks() -> Dict[str, Dict]:
    """
    Gibt alle verfügbaren ecoplus Wirtschaftsparks zurück
    
    Returns:
        Dict mit Park-Keys und Infos
    """
    return WIRTSCHAFTSPARKS.copy()


def get_parks_by_plz(plz: str) -> List[str]:
    """
    Findet Wirtschaftsparks für eine PLZ
    
    Args:
        plz: 4-stellige PLZ
    
    Returns:
        Liste von Park-Keys
    """
    parks = []
    for key, info in WIRTSCHAFTSPARKS.items():
        if plz in info.get('plz', []):
            parks.append(key)
    return parks


if __name__ == "__main__":
    print("=== ecoplus Spider Test ===\n")
    
    # Verfügbare Parks
    print("Verfügbare Wirtschaftsparks:")
    for key, info in WIRTSCHAFTSPARKS.items():
        print(f"  - {key}: {info['name']}")
        print(f"    Gemeinden: {', '.join(info['gemeinden'])}")
        print(f"    PLZ: {', '.join(info['plz'])}")
    
    print("\nTest: PLZ 2351 → Parks:", get_parks_by_plz("2351"))
    
    # Spider laufen lassen (IZ NÖ-Süd)
    print("\nCrawle IZ NÖ-Süd...")
    results = run_ecoplus_spider(park="iz-noe-sued")
    
    print(f"\nGefunden: {len(results)} Unternehmen")
    for c in results[:5]:
        print(f"  - {c.get('name')}: {c.get('wirtschaftspark')}")