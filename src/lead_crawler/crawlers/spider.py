"""
WKO Spider Module
Scrapy Spider für firmen.wko.at (Wirtschaftskammer Firmen A-Z)
"""

import re
from typing import Any

import scrapy


class WkoSpider(scrapy.Spider):
    """Spider für firmen.wko.at (WKO Firmen A-Z).

    Verwendet direkte URLs im Format:
    https://firmen.wko.at/{ort}/{bundesland}

    Beispiel:
    - https://firmen.wko.at/guntramsdorf/niederösterreich
    - https://firmen.wko.at/wien/wien
    """

    name = "wko"
    allowed_domains = ["wko.at", "firmen.wko.at"]
    BASE_URL = "https://firmen.wko.at"

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

    def __init__(self, urls: list[str] | None = None, *args, **kwargs):
        """Initialisiert Spider.

        Args:
            urls: Direkte URLs zum Crawlen
        """
        super().__init__(*args, **kwargs)
        self.start_urls = urls if urls else [f"{self.BASE_URL}/"]

    def parse(self, response):
        """Parse WKO Suchergebnisse."""
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

    def _parse_result_article(self, article, response) -> dict[str, Any] | None:
        """Parst einen einzelnen Suchergebnis-Artikel."""
        # Name
        name = article.css('h3::text').get()
        if not name:
            name = article.css('a.title-link h3::text').get()

        if not name:
            return None

        name = name.strip()

        # URL
        url = article.css('a.title-link::attr(href)').get()
        if url and not url.startswith('http'):
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
            'name': name,
            'url': url,
            'street': street,
            'plz': plz,
            'ort': ort,
            'bundesland': bundesland,
            'telefon': telefon,
            'email': email,
            'website': website,
            'source': 'firmen.wko.at',
        }

    def _extract_plz_ort(self, place_text: str) -> tuple[str | None, str | None]:
        """Extrahiert PLZ und Ort aus Place-Text."""
        if not place_text:
            return None, None

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

    def _extract_bundesland(self, url: str) -> str | None:
        """Extrahiert Bundesland aus URL."""
        # Format: https://firmen.wko.at/{ort}/{bundesland}
        parts = url.split('/')
        if len(parts) >= 5:
            bl = parts[4].split('?')[0]
            return self.BUNDESLAENDER.get(bl, bl)
        return None
