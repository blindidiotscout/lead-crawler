"""
WKO Crawler Module
Spider für firmen.wko.at (Wirtschaftskammer Firmen A-Z)
"""

import json
import os
import subprocess
import sys
import tempfile
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

    Verwendet Subprocess für Scrapy (vermeidet Reactor-Probleme in Streamlit)

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

            # Scrapy in Subprocess ausführen
            companies = self._run_scrapy_subprocess(crawl_urls, max_pages)

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

    def _run_scrapy_subprocess(self, urls: list[str], max_pages: int) -> list[Company]:
        """
        Führt Scrapy Spider in Subprocess aus (für Streamlit-Kompatibilität)

        Args:
            urls: URLs zum Crawlen
            max_pages: Maximale Seiten pro URL

        Returns:
            Liste von Company-Objekten
        """
        # Temporäre Ausgabedatei
        output_file = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
        output_path = output_file.name
        output_file.close()

        companies = []

        try:
            # Spider-Code für Subprocess
            spider_code = f"""
import json
import sys
from pathlib import Path

# Pfad zum Package hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from scrapy.crawler import CrawlerProcess
from lead_crawler.crawlers.spider import WkoSpider

settings = {{
    "FEEDS": {{r"{output_path}": {{"format": "jsonlines"}}}},
    "LOG_LEVEL": "ERROR",
    "USER_AGENT": r"{self.config.user_agent}",
    "ROBOTSTXT_OBEY": {self.config.respect_robots_txt},
    "DOWNLOAD_DELAY": {self.config.rate_limit},
    "CONCURRENT_REQUESTS_PER_DOMAIN": {self.config.concurrent_requests},
}}

urls = {urls}

process = CrawlerProcess(settings)
process.crawl(WkoSpider, urls=urls)
process.start()
"""

            # Subprocess ausführen
            result = subprocess.run(
                [sys.executable, "-c", spider_code],
                capture_output=True,
                text=True,
                timeout=120,  # 2 Minuten Timeout
            )

            if result.returncode != 0:
                self.logger.error(f"Scrapy subprocess failed: {result.stderr[:500]}")

            # Ergebnisse laden
            if os.path.exists(output_path):
                with open(output_path) as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            company = self._parse_item(data)
                            if company:
                                companies.append(company)
                                self._track_success()

        except subprocess.TimeoutExpired:
            self.logger.error("Scrapy subprocess timed out")
            self._track_error("Scrapy subprocess timed out")
        except Exception as e:
            self.logger.error(f"Scrapy error: {type(e).__name__}: {e}")
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

        # Source URL
        url = data.get("url", "")
        if not url:
            url = data.get("source_url", "")

        return Company(
            name=name,
            url=url,
            address=address,
            contact=contact,
            source=CompanySource.WKO,
            metadata={"raw": data},
        )


# Convenience-Funktion
def crawl_wko(
    plz: str | None = None,
    ort: str | None = None,
    bundesland: str | None = None,
    urls: list[str] | None = None,
    config: CrawlerConfig | None = None,
) -> CrawlerResult:
    """
    Convenience-Funktion für WKO Crawl

    Usage:
        from lead_crawler.crawlers import crawl_wko

        # PLZ-Suche
        result = crawl_wko(plz="2351")

        # Ortssuche
        result = crawl_wko(ort="Guntramsdorf", bundesland="niederösterreich")

        # Direkte URLs
        result = crawl_wko(urls=["https://firmen.wko.at/guntramsdorf/niederösterreich"])
    """
    crawler = WKOCrawler(config)
    return crawler.crawl(plz=plz, ort=ort, bundesland=bundesland, urls=urls)


__all__ = [
    "WKOCrawler",
    "crawl_wko",
]
