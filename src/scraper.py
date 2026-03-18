"""
Lead Crawler Scraper Module
Scrapy-basierte Spider für österreichische Unternehmensdaten

Datenquellen:
- firmen.wko.at (Wirtschaftskammer Firmen A-Z)
- firmenabc.at (falls benötigt)
"""

import scrapy
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime
import re


@dataclass
class CompanyData:
    """Standardisiertes Unternehmens-Datenmodell"""
    name: str
    url: Optional[str] = None
    address: Optional[str] = None
    plz: Optional[str] = None
    ort: Optional[str] = None
    bundesland: Optional[str] = None
    branche: Optional[str] = None
    mitarbeiter: Optional[int] = None
    umsatz: Optional[str] = None
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
    """Spider für firmen.wko.at (WKO Firmen A-Z)"""
    
    name = "wko"
    allowed_domains = ["wko.at", "firmen.wko.at"]
    
    def __init__(self, plz: Optional[str] = None, ort: Optional[str] = None,
                 branche: Optional[str] = None, page: int = 1, *args, **kwargs):
        """
        Initialisiert Spider mit Suchparametern
        
        Args:
            plz: PLZ für regionale Suche (z.B. "2351")
            ort: Ort für Suche (z.B. "Guntramsdorf")
            branche: Branche für Filter (z.B. "Elektroinstallation")
            page: Startseite für Paginierung
        """
        super().__init__(*args, **kwargs)
        self.plz = plz
        self.ort = ort
        self.branche = branche
        self.page = page
        
        # WKO search URL structure
        if plz:
            self.start_urls = [f"https://firmen.wko.at/search?plz={plz}&page={page}"]
        elif ort:
            self.start_urls = [f"https://firmen.wko.at/search?ort={ort}&page={page}"]
        elif branche:
            # Branchensuche: z.B. https://firmen.wko.at/elektroinstallation/niederösterreich
            self.start_urls = [f"https://firmen.wko.at/{branche}"]
        else:
            self.start_urls = ["https://firmen.wko.at/"]
    
    def parse(self, response):
        """Parse WKO search results"""
        
        # Extrahiere Firmeneinträge aus Suchergebnissen
        # HTML-Struktur: <article class='search-result-article'>
        articles = response.css("article.search-result-article")
        
        self.logger.info(f"Gefunden: {len(articles)} Firmeneinträge auf Seite {self.page}")
        
        for article in articles:
            company = self._parse_result_article(article, response)
            if company:
                yield company
        
        # Paginierung: Suche nach "next" Link
        # WKO verwendet ASP.NET PostBacks, daher müssen wir anders vorgehen
        next_page_link = response.css("a[rel='next']::attr(href)").get()
        if not next_page_link:
            # Alternativ: Link-Text "»" oder Seitenzahl
            next_page_link = response.css("a.pagination-next::attr(href)").get()
        
        if next_page_link:
            self.logger.info(f"Gehe zur nächsten Seite: {next_page_link}")
            yield response.follow(next_page_link, self.parse)
        else:
            # Prüfe auf Paginierungs-Links mit Seitenzahlen
            current_page = response.css("li.active a::text").get()
            if current_page:
                try:
                    current = int(current_page.strip())
                    next_url = response.url.replace(f"page={current}", f"page={current + 1}")
                    if f"page={current}" in response.url:
                        self.logger.info(f"Gehe zu Seite {current + 1}")
                        yield response.follow(next_url, self.parse)
                except ValueError:
                    pass
    
    def _parse_result_article(self, article, response) -> Optional[CompanyData]:
        """Parst einen einzelnen Suchergebnis-Artikel"""
        
        # Name und URL
        name = article.css("h3::text").get()
        if not name:
            name = article.css("a.title-link h3::text").get()
        
        url = article.css("a.title-link::attr(href)").get()
        if url and not url.startswith("http"):
            url = response.urljoin(url)
        
        # Adresse
        street = article.css("div.street::text").get(default="").strip()
        place = article.css("div.place::text").get(default="").strip()
        
        # PLZ und Ort aus place extrahieren (Format: "1010           Wien")
        plz, ort = self._extract_plz_ort(place)
        
        # Adresse kombinieren
        address = f"{street}, {place}".strip(", ")
        
        # Telefon und Website
        telefon = article.css("a[href^='tel:']::attr(href)").get()
        if telefon:
            telefon = telefon.replace("tel:", "").replace("%20", " ").strip()
        
        email = article.css("a[href^='mailto:']::attr(href)").get()
        if email:
            email = email.replace("mailto:", "").strip()
        
        website = article.css("a[href^='http']:not([href*='wko.at'])::attr(href)").get()
        
        return CompanyData(
            name=name.strip() if name else None,
            url=url,
            address=address if address else None,
            plz=plz,
            ort=ort,
            telefon=telefon,
            email=email,
            website=website,
            source="firmen.wko.at"
        )
    
    def parse_company_detail(self, response):
        """Parse WKO company detail page (für erweiterte Daten)"""
        
        # Diese Methode könnte für Detailseiten verwendet werden
        # Aktuell extrahieren wir alles aus der Suchergebnisliste
        
        company = CompanyData(
            name=response.css("h1.company-name::text").get(),
            url=response.url,
            source="firmen.wko.at"
        )
        
        yield company
    
    def _extract_plz_ort(self, place_text: str) -> tuple:
        """Extrahiert PLZ und Ort aus Place-Text"""
        if not place_text:
            return None, None
        
        # Format: "1010           Wien" oder "2351  Guntramsdorf"
        place_text = place_text.strip()
        
        # PLZ extrahieren (4-stellig)
        plz_match = re.search(r"\b(\d{4})\b", place_text)
        plz = plz_match.group(1) if plz_match else None
        
        # Ort extrahieren (alles nach der PLZ)
        if plz:
            ort_match = re.search(r"\d{4}\s+(.+)", place_text)
            ort = ort_match.group(1).strip() if ort_match else None
        else:
            ort = place_text
        
        return plz, ort


class WkoBranchSpider(scrapy.Spider):
    """Spider für Branchen-Urls auf firmen.wko.at"""
    
    name = "wko_branch"
    allowed_domains = ["wko.at", "firmen.wko.at"]
    
    def __init__(self, branche: str = None, region: str = None, *args, **kwargs):
        """
        Spider für Branchensuche
        
        Args:
            branche: Branchen-Slug (z.B. "elektroinstallation")
            region: Region-Slug (z.B. "niederösterreich", "wien")
        """
        super().__init__(*args, **kwargs)
        self.branche = branche
        self.region = region
        
        if branche and region:
            self.start_urls = [f"https://firmen.wko.at/{branche}/{region}"]
        elif branche:
            self.start_urls = [f"https://firmen.wko.at/{branche}"]
        else:
            self.start_urls = ["https://firmen.wko.at/"]
    
    def parse(self, response):
        """Parse Branchen-Seite"""
        
        # Extrahiere Firmeneinträge
        articles = response.css("article.search-result-article")
        
        for article in articles:
            company = self._parse_result_article(article, response)
            if company:
                yield company
    
    def _parse_result_article(self, article, response) -> Optional[CompanyData]:
        """Parst einen einzelnen Artikel (wiederverwendet von WkoSpider)"""
        
        name = article.css("h3::text").get()
        if not name:
            name = article.css("a.title-link h3::text").get()
        
        url = article.css("a.title-link::attr(href)").get()
        if url and not url.startswith("http"):
            url = response.urljoin(url)
        
        street = article.css("div.street::text").get(default="").strip()
        place = article.css("div.place::text").get(default="").strip()
        
        plz_match = re.search(r"\b(\d{4})\b", place)
        plz = plz_match.group(1) if plz_match else None
        
        ort_match = re.search(r"\d{4}\s+(.+)", place)
        ort = ort_match.group(1).strip() if ort_match else place.strip()
        
        address = f"{street}, {place}".strip(", ")
        
        return CompanyData(
            name=name.strip() if name else None,
            url=url,
            address=address if address else None,
            plz=plz,
            ort=ort,
            source="firmen.wko.at"
        )


# Hilfsfunktionen zum Ausführen der Spider
def run_spider(spider_name: str, **kwargs) -> List[Dict]:
    """
    Führt einen Spider aus und gibt Ergebnisse zurück
    
    Usage:
        from src.scraper import run_spider
        results = run_spider("wko", plz="2351")
    """
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings
    import json
    import tempfile
    import os
    
    # Temporäre Ausgabedatei
    output_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    output_path = output_file.name
    output_file.close()
    
    # Scrapy Einstellungen
    settings = {
        'FEEDS': {
            output_path: {'format': 'json'}
        },
        'LOG_LEVEL': 'INFO',
        'USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'ROBOTSTXT_OBEY': True,
        'DOWNLOAD_DELAY': 1,  # 1 Sekunde Verzögerung zwischen Requests
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
    print("=== Test: WKO Spider für PLZ 2351 ===\n")
    
    # Test ohne Scrapy (nur URL-Auflistung)
    import sys
    print(f"Start-URLs für PLZ 2351:")
    spider = WkoSpider(plz="2351")
    for url in spider.start_urls:
        print(f"  {url}")
    
    print(f"\nSpider-Name: {spider.name}")
    print(f"Allowed Domains: {spider.allowed_domains}")