"""
Website Extractor Service
Extrahiert Text von Unternehmens-Homepages für LLM-Analyse
"""

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

from lead_crawler.config import CrawlerConfig, get_settings


@dataclass
class WebsiteContent:
    """Extrahierte Website-Inhalte"""

    url: str
    title: str
    meta_description: str
    main_text: str
    about_text: str | None = None
    services_text: str | None = None
    contact_text: str | None = None
    word_count: int = 0
    crawl_time: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Konvertiert zu Dictionary"""
        return {
            "url": self.url,
            "title": self.title,
            "meta_description": self.meta_description,
            "main_text": self.main_text,
            "about_text": self.about_text,
            "services_text": self.services_text,
            "contact_text": self.contact_text,
            "word_count": self.word_count,
            "crawl_time": self.crawl_time,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WebsiteContent":
        """Erstellt WebsiteContent aus Dictionary"""
        return cls(
            url=data.get("url", ""),
            title=data.get("title", ""),
            meta_description=data.get("meta_description", ""),
            main_text=data.get("main_text", ""),
            about_text=data.get("about_text"),
            services_text=data.get("services_text"),
            contact_text=data.get("contact_text"),
            word_count=data.get("word_count", 0),
            crawl_time=data.get("crawl_time", 0.0),
            error=data.get("error"),
        )

    @property
    def is_valid(self) -> bool:
        """True wenn Content erfolgreich extrahiert wurde"""
        return self.error is None and self.word_count > 0

    @property
    def combined_text(self) -> str:
        """Kombinierter Text aller extrahierten Felder"""
        parts = [self.main_text]
        if self.about_text:
            parts.append(f"\n\nAbout: {self.about_text}")
        if self.services_text:
            parts.append(f"\n\nServices: {self.services_text}")
        if self.contact_text:
            parts.append(f"\n\nContact: {self.contact_text}")
        return "\n".join(parts)


class WebsiteExtractor:
    """
    Extrahiert Text von Unternehmens-Websites

    Features:
    - Respektiert robots.txt
    - Rate limiting
    - Extrahiert: Titel, Meta, Haupttext, About, Services, Kontakt
    - Konfigurierbar via CrawlerConfig
    """

    # Selektoren für Hauptinhalt (in Priorität)
    MAIN_SELECTORS = [
        "main",
        "article",
        '[role="main"]',
        ".content",
        ".main-content",
        "#content",
        "#main",
        ".container",
        "body",
    ]

    # Keywords für Unterseiten-Suche
    ABOUT_KEYWORDS = [
        "ueber-uns",
        "about",
        "uber-uns",
        "unternehmen",
        "firma",
        "team",
        "wir-ueber-uns",
    ]
    SERVICES_KEYWORDS = [
        "leistungen",
        "services",
        "angebot",
        "produkte",
        "leistung",
        "service",
        "angebote",
    ]
    CONTACT_KEYWORDS = ["kontakt", "contact", "impressum", "anfahrt"]

    def __init__(self, config: CrawlerConfig | None = None):
        """
        Initialisiert Website Extractor

        Args:
            config: CrawlerConfig (default: aus get_settings())
        """
        if config is None:
            config = get_settings().crawler

        self.timeout = config.website_timeout
        self.max_words = config.website_max_words
        self.delay = config.website_delay
        self.respect_robots = config.respect_robots_txt
        self.max_retries = config.max_retries

        self.headers = {
            "User-Agent": config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
        }

        self._last_request_time = 0.0
        self._robots_cache: dict[str, bool] = {}
        self._session = None

    def _get_session(self):
        """Lazy-init für requests Session"""
        if self._session is None:
            import requests

            self._session = requests.Session()
        return self._session

    def _rate_limit(self) -> None:
        """Wartet falls nötig für Rate Limiting"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request_time = time.time()

    def _check_robots_txt(self, url: str) -> bool:
        """Prüft robots.txt (erlaubt = True)"""
        if not self.respect_robots:
            return True

        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        if base_url in self._robots_cache:
            return self._robots_cache[base_url]

        try:
            import requests

            robots_url = f"{base_url}/robots.txt"
            response = requests.get(robots_url, timeout=5, headers=self.headers)

            content = response.text.lower()
            lines = content.split("\n")

            user_agent_match = False
            for line in lines:
                line = line.strip()
                if line.startswith("user-agent:"):
                    ua = line.split(":", 1)[1].strip()
                    if ua == "*" or "crawler" in ua.lower():
                        user_agent_match = True
                elif user_agent_match and line.startswith("disallow:"):
                    path = line.split(":", 1)[1].strip()
                    if path == "/":
                        self._robots_cache[base_url] = False
                        return False

            self._robots_cache[base_url] = True
            return True

        except Exception:
            self._robots_cache[base_url] = True
            return True

    def _fetch(self, url: str) -> str | None:
        """Holt HTML von URL"""
        import requests

        self._rate_limit()

        for attempt in range(self.max_retries):
            try:
                response = self._get_session().get(
                    url, timeout=self.timeout, headers=self.headers, allow_redirects=True
                )
                response.raise_for_status()
                response.encoding = response.apparent_encoding
                return response.text

            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(self.delay * (attempt + 1))
            except requests.exceptions.RequestException:
                return None

        return None

    def _clean_text(self, text: str) -> str:
        """Bereinigt Text für LLM"""
        if not text:
            return ""

        # HTML-Tags entfernen
        text = re.sub(r"<[^>]+>", " ", text)

        # Mehrfache Leerzeichen/Newlines entfernen
        text = re.sub(r"\s+", " ", text)

        # Trim
        text = text.strip()

        # Auf max_words begrenzen
        words = text.split()
        if len(words) > self.max_words:
            text = " ".join(words[: self.max_words]) + "..."

        return text

    def _extract_main_content(self, soup) -> str:
        """Extrahiert Hauptinhalt aus BeautifulSoup"""
        # Entferne nicht benötigte Tags
        for tag in soup.find_all(
            ["nav", "footer", "aside", "header", "script", "style", "noscript"]
        ):
            tag.decompose()

        for selector in self.MAIN_SELECTORS:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(separator=" ", strip=True)
                if len(text.split()) > 20:
                    return self._clean_text(text)

        return ""

    def _find_page(self, soup, base_url: str, keywords: list[str]) -> str | None:
        """Findet Unterseite anhand von Keywords"""
        for link in soup.find_all("a", href=True):
            href = link["href"].lower()
            text = link.get_text(strip=True).lower()

            for keyword in keywords:
                if keyword in href or keyword in text:
                    return urljoin(base_url, link["href"])

        return None

    def _extract_page_content(self, url: str) -> str | None:
        """Extrahiert Text von einer Unterseite"""
        html = self._fetch(url)
        if not html:
            return None

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup.find_all(["script", "style", "noscript"]):
            tag.decompose()

        return self._extract_main_content(soup)

    def extract(self, url: str) -> WebsiteContent:
        """
        Extrahiert Inhalte von einer Website

        Args:
            url: Website-URL

        Returns:
            WebsiteContent mit extrahierten Daten
        """
        from bs4 import BeautifulSoup

        start_time = time.time()

        # URL normalisieren
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        # robots.txt prüfen
        if not self._check_robots_txt(url):
            return WebsiteContent(
                url=url,
                title="",
                meta_description="",
                main_text="",
                word_count=0,
                crawl_time=time.time() - start_time,
                error="Robots.txt verbietet Crawling",
            )

        # Hauptseite laden
        html = self._fetch(url)
        if not html:
            return WebsiteContent(
                url=url,
                title="",
                meta_description="",
                main_text="",
                word_count=0,
                crawl_time=time.time() - start_time,
                error="Konnte Website nicht laden",
            )

        # Parse HTML
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup.find_all(["script", "style", "noscript"]):
            tag.decompose()

        # Titel extrahieren
        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = self._clean_text(title_tag.get_text())

        # Meta Description
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag:
            meta_desc = self._clean_text(meta_tag.get("content", ""))

        # Hauptinhalt
        main_text = self._extract_main_content(soup)

        # Unterseiten finden und crawlen
        about_text = (
            self._extract_page_content(self._find_page(soup, url, self.ABOUT_KEYWORDS))
            if self._find_page(soup, url, self.ABOUT_KEYWORDS)
            else None
        )

        services_text = (
            self._extract_page_content(self._find_page(soup, url, self.SERVICES_KEYWORDS))
            if self._find_page(soup, url, self.SERVICES_KEYWORDS)
            else None
        )

        contact_text = (
            self._extract_page_content(self._find_page(soup, url, self.CONTACT_KEYWORDS))
            if self._find_page(soup, url, self.CONTACT_KEYWORDS)
            else None
        )

        # Gesamtwortzahl
        all_texts = [main_text, about_text or "", services_text or "", contact_text or ""]
        word_count = sum(len(t.split()) for t in all_texts)

        crawl_time = time.time() - start_time

        return WebsiteContent(
            url=url,
            title=title,
            meta_description=meta_desc,
            main_text=main_text,
            about_text=about_text,
            services_text=services_text,
            contact_text=contact_text,
            word_count=word_count,
            crawl_time=crawl_time,
        )

    def extract_batch(
        self, urls: list[str], progress_callback: Callable[[int, int], None] | None = None
    ) -> list[WebsiteContent]:
        """
        Extrahiert Inhalte von mehreren Websites

        Args:
            urls: Liste von URLs
            progress_callback: Optional callback(current, total)

        Returns:
            Liste von WebsiteContent
        """
        results = []
        total = len(urls)

        for i, url in enumerate(urls):
            if progress_callback:
                progress_callback(i + 1, total)

            result = self.extract(url)
            results.append(result)

        return results

    # Alias für Kompatibilität
    def crawl(self, url: str) -> WebsiteContent:
        """Alias für extract()"""
        return self.extract(url)


# Singleton-Instanz (Lazy)
_extractor_instance: WebsiteExtractor | None = None


def get_website_extractor() -> WebsiteExtractor:
    """
    Gibt die globale Extractor-Instanz zurück (Singleton Pattern)

    Returns:
        WebsiteExtractor Instanz
    """
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = WebsiteExtractor()
    return _extractor_instance


def reset_extractor() -> None:
    """Setzt die globale Extractor-Instanz zurück (für Tests)"""
    global _extractor_instance
    _extractor_instance = None


# Convenience-Funktion
def quick_extract(url: str) -> dict[str, Any]:
    """
    Schnelle Hilfsfunktion für einzelne URLs

    Args:
        url: Website-URL

    Returns:
        Dict mit extrahierten Daten
    """
    extractor = get_website_extractor()
    result = extractor.extract(url)
    return result.to_dict()
