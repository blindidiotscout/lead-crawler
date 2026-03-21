"""
Website Crawler
Extrahiert Text von Unternehmens-Homepages für LLM-Analyse
"""

import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re
import time
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class WebsiteContent:
    """Extrahierte Website-Inhalte"""
    url: str
    title: str
    meta_description: str
    main_text: str
    about_text: Optional[str]
    services_text: Optional[str]
    contact_text: Optional[str]
    word_count: int
    crawl_time: float
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'url': self.url,
            'title': self.title,
            'meta_description': self.meta_description,
            'main_text': self.main_text,
            'about_text': self.about_text,
            'services_text': self.services_text,
            'contact_text': self.contact_text,
            'word_count': self.word_count,
            'crawl_time': self.crawl_time,
            'error': self.error
        }


class WebsiteCrawler:
    """
    Höflicher Website-Crawler
    - Respektiert robots.txt
    - Rate limiting (1 Sekunde zwischen Requests)
    - Extrahiert: Titel, Meta, Hauptinhalt, About, Services
    """
    
    def __init__(self, 
                 timeout: int = 15,
                 max_words: int = 800,
                 respect_robots: bool = True,
                 delay: float = 1.0):
        """
        Args:
            timeout: Request timeout in Sekunden
            max_words: Maximale Wörter pro Textfeld
            respect_robots: robots.txt prüfen
            delay: Sekunden zwischen Requests
        """
        self.timeout = timeout
        self.max_words = max_words
        self.respect_robots = respect_robots
        self.delay = delay
        self.last_request_time = 0
        
        # Headers für realistischen Browser-Request
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
        }
        
        # robots.txt Cache
        self._robots_cache: Dict[str, bool] = {}
    
    def _rate_limit(self):
        """Einfaches Rate Limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request_time = time.time()
    
    def _check_robots_txt(self, url: str) -> bool:
        """Prüft robots.txt (erlaubt = True)"""
        if not self.respect_robots:
            return True
        
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        if base_url in self._robots_cache:
            return self._robots_cache[base_url]
        
        try:
            robots_url = f"{base_url}/robots.txt"
            response = requests.get(robots_url, timeout=5, headers=self.headers)
            
            # Einfache Prüfung: User-agent: * und Disallow: /
            content = response.text.lower()
            lines = content.split('\n')
            
            user_agent_match = False
            for line in lines:
                line = line.strip()
                if line.startswith('user-agent:'):
                    ua = line.split(':', 1)[1].strip()
                    if ua == '*' or 'crawler' in ua.lower():
                        user_agent_match = True
                elif user_agent_match and line.startswith('disallow:'):
                    path = line.split(':', 1)[1].strip()
                    if path == '/':
                        self._robots_cache[base_url] = False
                        return False
            
            self._robots_cache[base_url] = True
            return True
            
        except Exception:
            # Bei Fehler: erlauben
            self._robots_cache[base_url] = True
            return True
    
    def _fetch(self, url: str) -> Optional[str]:
        """Holt HTML von URL"""
        self._rate_limit()
        
        try:
            response = requests.get(
                url, 
                timeout=self.timeout, 
                headers=self.headers,
                allow_redirects=True
            )
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response.text
            
        except requests.exceptions.Timeout:
            return None
        except requests.exceptions.RequestException:
            return None
    
    def _clean_text(self, text: str) -> str:
        """Bereinigt Text für LLM"""
        if not text:
            return ""
        
        # HTML-Tags entfernen (falls noch vorhanden)
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Mehrfache Leerzeichen/Neuzeilen entfernen
        text = re.sub(r'\s+', ' ', text)
        
        # Trim
        text = text.strip()
        
        # Auf max_words begrenzen
        words = text.split()
        if len(words) > self.max_words:
            text = ' '.join(words[:self.max_words]) + '...'
        
        return text
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extrahiert Hauptinhalt aus verschiedenen Selektoren"""
        selectors = [
            'main',
            'article',
            '[role="main"]',
            '.content',
            '.main-content',
            '#content',
            '#main',
            '.container',
            'body'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                # Navigation, Footer, Sidebar entfernen
                for tag in element.find_all(['nav', 'footer', 'aside', 'header']):
                    tag.decompose()
                
                text = element.get_text(separator=' ', strip=True)
                if len(text.split()) > 20:  # Mindestens 20 Wörter
                    return self._clean_text(text)
        
        return ""
    
    def _find_page(self, soup: BeautifulSoup, base_url: str, keywords: List[str]) -> Optional[str]:
        """Findet Seite anhand von Keywords (z.B. 'ueber-uns', 'about')"""
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            text = link.get_text(strip=True).lower()
            
            for keyword in keywords:
                if keyword in href or keyword in text:
                    full_url = urljoin(base_url, link['href'])
                    return full_url
        
        return None
    
    def _extract_page_content(self, url: str) -> Optional[str]:
        """Extrahiert Text von einer Unterseite"""
        html = self._fetch(url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "noscript"]):
            script.decompose()
        
        return self._extract_main_content(soup)
    
    def crawl(self, url: str) -> WebsiteContent:
        """
        Crawlt eine Website und extrahiert Inhalte
        
        Args:
            url: Website-URL
            
        Returns:
            WebsiteContent mit extrahierten Daten
        """
        start_time = time.time()
        
        # URL normalisieren
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # robots.txt prüfen
        if not self._check_robots_txt(url):
            return WebsiteContent(
                url=url,
                title="",
                meta_description="",
                main_text="",
                about_text=None,
                services_text=None,
                contact_text=None,
                word_count=0,
                crawl_time=time.time() - start_time,
                error="Robots.txt verbietet Crawling"
            )
        
        # Hauptseite laden
        html = self._fetch(url)
        if not html:
            return WebsiteContent(
                url=url,
                title="",
                meta_description="",
                main_text="",
                about_text=None,
                services_text=None,
                contact_text=None,
                word_count=0,
                crawl_time=time.time() - start_time,
                error="Konnte Website nicht laden"
            )
        
        # Parse HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "noscript"]):
            script.decompose()
        
        # Titel extrahieren
        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = self._clean_text(title_tag.get_text())
        
        # Meta Description
        meta_desc = ""
        meta_tag = soup.find('meta', attrs={'name': 'description'})
        if meta_tag:
            meta_desc = self._clean_text(meta_tag.get('content', ''))
        
        # Hauptinhalt
        main_text = self._extract_main_content(soup)
        
        # Unterseiten finden und crawlen
        about_text = None
        services_text = None
        contact_text = None
        
        # About-Seite
        about_url = self._find_page(soup, url, ['ueber-uns', 'about', 'uber-uns', 'unternehmen', 'firma'])
        if about_url:
            about_text = self._extract_page_content(about_url)
        
        # Services/Leistungen
        services_url = self._find_page(soup, url, ['leistungen', 'services', 'angebot', 'produkte', 'leistung'])
        if services_url:
            services_text = self._extract_page_content(services_url)
        
        # Kontakt
        contact_url = self._find_page(soup, url, ['kontakt', 'contact'])
        if contact_url:
            contact_text = self._extract_page_content(contact_url)
        
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
            crawl_time=crawl_time
        )
    
    def crawl_batch(self, urls: List[str], 
                    progress_callback=None) -> List[WebsiteContent]:
        """
        Crawlt mehrere Websites
        
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
            
            result = self.crawl(url)
            results.append(result)
        
        return results


def quick_crawl(url: str) -> Dict:
    """Schnelle Hilfsfunktion für einzelne URLs"""
    crawler = WebsiteCrawler()
    result = crawler.crawl(url)
    return result.to_dict()


if __name__ == "__main__":
    print("=== Website Crawler Test ===\n")
    
    # Test-URLs
    test_urls = [
        "https://www.akras.at",
    ]
    
    crawler = WebsiteCrawler(max_words=500)
    
    for url in test_urls:
        print(f"Crawling: {url}")
        result = crawler.crawl(url)
        
        if result.error:
            print(f"  ❌ Fehler: {result.error}")
        else:
            print(f"  ✅ Titel: {result.title[:60]}...")
            print(f"  📝 Wörter: {result.word_count}")
            print(f"  ⏱️  Zeit: {result.crawl_time:.1f}s")
            print(f"  📄 Haupttext: {result.main_text[:150]}...")
            if result.about_text:
                print(f"  ℹ️  About: {result.about_text[:100]}...")
        print()
