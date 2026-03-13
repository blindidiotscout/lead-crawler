"""
Lead Crawler Scraper Module
Scrapy-basierte Spider für österreichische Unternehmensdaten

Datenquellen:
- firmenabc.at
- wko.at (Wirtschaftskammer Firmen A-Z)
- Firmenbuch (justiz.gv.at)
"""

import scrapy
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


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
    impressum_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    crawled_at: str = None
    
    def __post_init__(self):
        if self.crawled_at is None:
            self.crawled_at = datetime.now().isoformat()


class FirmenabcSpider(scrapy.Spider):
    """Spider für firmenabc.at"""
    
    name = "firmenabc"
    allowed_domains = ["firmenabc.at", "www.firmenabc.at"]
    
    def __init__(self, plz: Optional[str] = None, ort: Optional[str] = None, 
                 branche: Optional[str] = None, *args, **kwargs):
        """
        Initialisiert Spider mit Suchparametern
        
        Args:
            plz: PLZ für regionale Suche (z.B. "2351")
            ort: Ort für Suche (z.B. "Guntramsdorf")
            branche: Branche für Filter (z.B. "Industrie")
        """
        super().__init__(*args, **kwargs)
        self.plz = plz
        self.ort = ort
        self.branche = branche
        
        # Build search URL
        if plz:
            self.start_urls = [f"https://www.firmenabc.at/suche?query={plz}"]
        elif ort:
            self.start_urls = [f"https://www.firmenabc.at/suche?query={ort}"]
        elif branche:
            self.start_urls = [f"https://www.firmenabc.at/suche?query={branche}"]
        else:
            self.start_urls = ["https://www.firmenabc.at/"]
    
    def parse(self, response):
        """Parse search results or company pages"""
        
        # Extract search result links
        for company_link in response.css("a.company-link::attr(href)").getall():
            yield response.follow(company_link, self.parse_company)
        
        # Pagination
        next_page = response.css("a.next-page::attr(href)").get()
        if next_page:
            yield response.follow(next_page, self.parse)
    
    def parse_company(self, response):
        """Parse individual company page"""
        
        company = CompanyData(
            name=response.css("h1.company-name::text").get(default=""),
            url=response.url,
            address=response.css("div.address::text").get(default=""),
            plz=self._extract_plz(response.css("div.address::text").get(default="")),
            ort=self._extract_ort(response.css("div.address::text").get(default="")),
            branche=response.css("div.industry::text").get(default=""),
            telefon=response.css("a.phone::text").get(default=""),
            email=response.css("a.email::text").get(default=""),
            description=response.css("div.description::text").get(default=""),
            source="firmenabc.at"
        )
        
        yield company
    
    def _extract_plz(self, address_text: str) -> Optional[str]:
        """Extrahiert PLZ aus Adress-Text"""
        import re
        match = re.search(r"\b(\d{4})\b", address_text)
        return match.group(1) if match else None
    
    def _extract_ort(self, address_text: str) -> Optional[str]:
        """Extrahiert Ort aus Adress-Text"""
        import re
        match = re.search(r"\d{4}\s+([A-Za-zÄÖÜäöüß\s\-]+)", address_text)
        return match.group(1).strip() if match else None


class WkoSpider(scrapy.Spider):
    """Spider für wko.at Firmen A-Z"""
    
    name = "wko"
    allowed_domains = ["wko.at", "firmen.wko.at"]
    
    def __init__(self, plz: Optional[str] = None, ort: Optional[str] = None,
                 branche: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plz = plz
        self.ort = ort
        self.branche = branche
        
        # WKO search URL structure
        if plz:
            self.start_urls = [f"https://firmen.wko.at/search?plz={plz}"]
        elif ort:
            self.start_urls = [f"https://firmen.wko.at/search?ort={ort}"]
        else:
            self.start_urls = ["https://firmen.wko.at/"]
    
    def parse(self, response):
        """Parse WKO search results"""
        
        for company_link in response.css("a.firmen-link::attr(href)").getall():
            yield response.follow(company_link, self.parse_company)
        
        # Pagination
        next_page = response.css("a.pagination-next::attr(href)").get()
        if next_page:
            yield response.follow(next_page, self.parse)
    
    def parse_company(self, response):
        """Parse WKO company detail page"""
        
        company = CompanyData(
            name=response.css("h1.firma-name::text").get(default=""),
            url=response.url,
            address=response.css("div.adresse::text").get(default=""),
            plz=self._extract_plz(response.css("div.adresse::text").get(default="")),
            ort=self._extract_ort(response.css("div.adresse::text").get(default="")),
            branche=response.css("div.branche::text").get(default=""),
            telefon=response.css("a.telefon::text").get(default=""),
            source="wko.at"
        )
        
        yield company
    
    def _extract_plz(self, address_text: str) -> Optional[str]:
        import re
        match = re.search(r"\b(\d{4})\b", address_text)
        return match.group(1) if match else None
    
    def _extract_ort(self, address_text: str) -> Optional[str]:
        import re
        match = re.search(r"\d{4}\s+([A-Za-zÄÖÜäöüß\s\-]+)", address_text)
        return match.group(1).strip() if match else None


# Helper function to run spider
def run_spider(spider_name: str, **kwargs):
    """
    Helper zum Ausführen eines Spiders
    
    Usage:
        from src.scraper import run_spider
        run_spider("firmenabc", plz="2351", ort="Guntramsdorf")
    """
    import subprocess
    cmd = ["scrapy", "crawl", spider_name]
    
    for key, value in kwargs.items():
        if value:
            cmd.extend(["-a", f"{key}={value}"])
    
    subprocess.run(cmd, cwd="..")  # Run from project root


if __name__ == "__main__":
    # Test: Run firmenabc spider for Guntramsdorf
    print("=== Test: FirmenABC Spider für 2351 Guntramsdorf ===\n")
    run_spider("firmenabc", plz="2351", ort="Guntramsdorf")
