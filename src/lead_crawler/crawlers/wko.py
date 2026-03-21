"""
WKO Crawler Module
Spider für firmen.wko.at (Wirtschaftskammer Firmen A-Z)
"""

import json
import os
import tempfile
import time
from typing import Any

from lead_crawler.config import CrawlerConfig
from lead_crawler.crawlers.base import BaseCrawler, CrawlerFactory, CrawlerResult, CrawlerStatus
from lead_crawler.models import Company, CompanySource
from lead_crawler.services.plz_service import get_plz_service

# Bundesland-Mapping für URL-Normalisierung
BUNDESLAENDER = {
    "burgenland": "burgenland",
    "kärnten": "kärnten",
    "kaernten": "kärnten",
    "niederösterreich": "niederösterreich",
    "niederosterreich": "niederösterreich",
    "noe": "niederösterreich",
    "oberösterreich": "oberösterreich",
    "oberosterreich": "oberösterreich",
    "ooe": "oberösterreich",
    "salzburg": "salzburg",
    "steiermark": "steiermark",
    "stmk": "steiermark",
    "tirol": "tirol",
    "tir": "tirol",
    "vorarlberg": "vorarlberg",
    "vbg": "vorarlberg",
    "wien": "wien",
}

# PLZ-Präfix zu Bundesland
PLZ_BUNDESLAND = {
    "1": "wien",
    "2": "niederösterreich",
    "3": "niederösterreich",
    "4": "oberösterreich",
    "5": "salzburg",
    "6": "steiermark",
    "7": "tirol",
    "8": "vorarlberg",
    "9": "burgenland",
}


@CrawlerFactory.register
class WKOCrawler(BaseCrawler):
    """
    Crawler für firmen.wko.at (WKO Firmen A-Z)

    Verwendet direkte URLs im Format:
    https://firmen.wko.at/{ort}/{bundesland}

    Beispiel:
    - https://firmen.wko.at/guntramsdorf/niederösterreich
    - https://firmen.wko.at/wien/wien

    Usage:
        from lead_crawler.crawlers import WKOCrawler

        crawler = WKOCrawler()
        result = crawler.crawl(plz="2351")
        # oder
        result = crawler.crawl(ort="Guntramsdorf", bundesland="niederösterreich")
    """

    name = "wko"
    source = CompanySource.WKO
    BASE_URL = "https://firmen.wko.at"

    def __init__(self, config: CrawlerConfig | None = None):
        """
        Initialisiert WKO Crawler

        Args:
            config: CrawlerConfig (default: aus get_settings())
        """
        super().__init__(config)
        self.plz_service = get_plz_service()

    def crawl(
        self,
        plz: str | None = None,
        ort: str | None = None,
        bundesland: str | None = None,
        urls: list[str] | None = None,
        max_pages: int = 5,
        **kwargs,
    ) -> CrawlerResult:
        """
        Führt WKO Crawl aus

        Args:
            plz: PLZ für Suche (wird zu Ort aufgelöst)
            ort: Ortsname für direkte Suche
            bundesland: Bundesland (z.B. "niederösterreich")
            urls: Direkte URLs (überschreibt PLZ/Ort)
            max_pages: Maximale Seiten pro Suche (default: 5)
            **kwargs: Zusätzliche Parameter

        Returns:
            CrawlerResult mit gefundenen Unternehmen
        """
        self._start_crawl()
        result = CrawlerResult()

        try:
            # URLs aufbauen
            if urls:
                crawl_urls = urls
            else:
                crawl_urls = self._build_urls(plz, ort, bundesland)

            if not crawl_urls:
                self.logger.warning("No URLs to crawl")
                self.status = CrawlerStatus.COMPLETED
                return self._finish_crawl(result)

            self.logger.info(f"Crawling {len(crawl_urls)} URL(s)")

            # Scrapy ausführen
            companies = self._run_scrapy(crawl_urls, max_pages)

            result.companies = companies
            self.status = CrawlerStatus.COMPLETED

        except Exception as e:
            self.logger.error(f"Crawl failed: {e}")
            self.status = CrawlerStatus.FAILED
            result.errors.append({"error": str(e)})

        return self._finish_crawl(result)

    def _build_urls(self, plz: str | None, ort: str | None, bundesland: str | None) -> list[str]:
        """
        Baut WKO-URLs basierend auf Parametern

        Priorität:
        1. PLZ (wird zu Ort aufgelöst via PLZ-Datenbank)
        2. Ort + Bundesland
        3. Ort (alle Bundesländer)

        Returns:
            Liste von WKO URLs
        """
        urls = []

        # PLZ-Suche: Zu Ort auflösen
        if plz and not ort:
            plz_info = self.plz_service.get_plz_info(plz)
            if plz_info:
                urls = plz_info.get_wko_urls()
                self.logger.info(f"PLZ {plz} → {len(urls)} URL(s)")
            else:
                self.logger.warning(f"PLZ {plz} nicht gefunden")
                # Fallback
                urls = [f"{self.BASE_URL}/"]
            return urls

        # Bundesland normalisieren
        bl = None
        if bundesland:
            bl = BUNDESLAENDER.get(bundesland.lower(), bundesland.lower())

        # Ortssuche
        if ort:
            ort_clean = ort.lower().replace(" ", "-").replace("ß", "ss")
            if bl:
                urls = [f"{self.BASE_URL}/{ort_clean}/{bl}"]
            else:
                urls = [f"{self.BASE_URL}/{ort_clean}"]

        if not urls:
            self.logger.warning("No search parameters provided")
            return [f"{self.BASE_URL}/"]

        return urls

    def _run_scrapy(self, urls: list[str], max_pages: int) -> list[Company]:
        """
        Führt Scrapy Spider aus

        Args:
            urls: URLs zum Crawlen
            max_pages: Maximale Seiten pro URL

        Returns:
            Liste von Company-Objekten
        """
        # Scrapy importieren (lazy, da optional)
        try:
            from scrapy.crawler import CrawlerProcess
        except ImportError:
            self.logger.error("Scrapy not installed. Run: pip install scrapy")
            return []

        # Temporäre Ausgabedatei
        output_file = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
        output_path = output_file.name
        output_file.close()

        # Scrapy Settings
        settings = {
            "FEEDS": {output_path: {"format": "jsonlines"}},
            "LOG_LEVEL": "WARNING",
            "USER_AGENT": self.config.user_agent,
            "ROBOTSTXT_OBEY": self.config.respect_robots_txt,
            "DOWNLOAD_DELAY": self.config.rate_limit,
            "CONCURRENT_REQUESTS_PER_DOMAIN": self.config.concurrent_requests,
        }

        companies = []

        try:
            # Spider aus eigenem Modul importieren
            from lead_crawler.crawlers.spider import WkoSpider

            # Crawler Process
            process = CrawlerProcess(settings)
            process.crawl(WkoSpider, urls=urls)
            process.start()

            # Ergebnisse laden
            with open(output_path) as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        company = self._parse_item(data)
                        if company:
                            companies.append(company)
                            self._track_success()

        except Exception as e:
            self.logger.error(f"Scrapy error details: {type(e).__name__}: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            self._track_error(f"Scrapy failed: {e}")

        finally:
            # Temp-Datei aufräumen
            if os.path.exists(output_path):
                os.unlink(output_path)

        return companies

    def _parse_item(self, data: dict[str, Any]) -> Company | None:
        """
        Parst ein einzelnes Item (von Scrapy) zu Company

        Args:
            data: Dict von Scrapy Spider

        Returns:
            Company oder None bei Parsing-Fehler
        """
        if not data:
            return None

        name = data.get("name")
        if not name:
            self._track_skip("No name")
            return None

        # Address
        address = {
            "street": data.get("street"),
            "plz": data.get("plz"),
            "ort": data.get("ort"),
            "bundesland": data.get("bundesland"),
        }

        # Contact
        contact = {
            "telefon": data.get("telefon"),
            "email": data.get("email"),
            "website": data.get("website"),
        }

        # Company erstellen
        company = self.create_company(
            name=name,
            address=address,
            contact=contact,
            branche=data.get("branche"),
            url=data.get("url"),
        )

        # Source URL
        company.metadata.source_url = data.get("url")

        return company

    def crawl_radius(
        self,
        center_plz: str,
        radius_km: float = 20.0,
        max_plz: int | None = None,
        dedup: bool = True,
    ) -> CrawlerResult:
        """
        Crawlt alle Unternehmen im Radius um eine PLZ

        Args:
            center_plz: Zentrale PLZ (z.B. "2351")
            radius_km: Radius in Kilometern (default: 20)
            max_plz: Maximale Anzahl PLZs (optional, für Rate-Limiting)
            dedup: Duplikate entfernen (default: True)

        Returns:
            CrawlerResult mit allen gefundenen Unternehmen
        """
        self._start_crawl()
        result = CrawlerResult()

        try:
            # PLZs im Radius finden
            search_result = self.plz_service.find_in_radius(center_plz, radius_km)

            if not search_result.results:
                self.logger.info(f"No PLZs found in {radius_km}km radius around {center_plz}")
                self.status = CrawlerStatus.COMPLETED
                return self._finish_crawl(result)

            plzs = search_result.plzs

            # Optional limitieren
            if max_plz:
                plzs = plzs[:max_plz]

            self.logger.info(
                f"Crawling {len(plzs)} PLZs in {radius_km}km radius around {center_plz}"
            )

            # Unique PLZs (manche PLZ haben mehrere Orte)
            seen_plzs = set()
            all_companies = []

            for plz in plzs:
                if plz in seen_plzs:
                    continue
                seen_plzs.add(plz)

                self.logger.info(f"Crawling PLZ {plz}")

                # Crawl für diese PLZ
                crawl_result = self.crawl(plz=plz)
                all_companies.extend(crawl_result.companies)

                # Stats mergen
                self._stats["pages_crawled"] += crawl_result.stats.get("pages_crawled", 0)
                result.errors.extend(crawl_result.errors)

                # Rate-Limiting
                time.sleep(self.config.rate_limit)

            # Deduplizierung
            if dedup:
                all_companies = self._deduplicate(all_companies)

            result.companies = all_companies
            self.status = CrawlerStatus.COMPLETED

        except Exception as e:
            self.logger.error(f"Radius crawl failed: {e}")
            self.status = CrawlerStatus.FAILED
            result.errors.append({"error": str(e)})

        return self._finish_crawl(result)

    def _deduplicate(self, companies: list[Company]) -> list[Company]:
        """
        Entfernt Duplikate aus der Unternehmensliste

        Duplikat = gleicher Name + gleiche PLZ + gleiche Straße
        """
        seen = set()
        unique = []

        for company in companies:
            # Key: Name + PLZ + Straße (normalisiert)
            name = (company.name or "").lower().strip()
            plz = company.address.plz or ""
            street = (company.address.street or "").lower().strip()

            key = (name, plz, street)

            if key not in seen:
                seen.add(key)
                unique.append(company)

        self.logger.info(f"Deduplicated: {len(companies)} → {len(unique)} companies")
        return unique

    def search_plz(self, plz: str) -> list[str]:
        """
        Gibt WKO-URLs für eine PLZ zurück

        Args:
            plz: 4-stellige PLZ

        Returns:
            Liste von WKO URLs
        """
        return self._build_urls(plz=plz, ort=None, bundesland=None)


# Convenience-Funktion
def crawl_wko(
    plz: str | None = None, ort: str | None = None, bundesland: str | None = None, **kwargs
) -> CrawlerResult:
    """
    Convenience-Funktion für WKO Crawl

    Usage:
        from lead_crawler.crawlers.wko import crawl_wko

        # PLZ-Suche
        result = crawl_wko(plz="2351")

        # Ortssuche
        result = crawl_wko(ort="Guntramsdorf", bundesland="niederösterreich")
    """
    crawler = WKOCrawler()
    return crawler.crawl(plz=plz, ort=ort, bundesland=bundesland, **kwargs)


# Export
__all__ = ["WKOCrawler", "crawl_wko", "CrawlerFactory"]
