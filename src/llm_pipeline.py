"""
LLM Pipeline
Integriert Website Crawler, LLM Analyzer und Analysis Cache
Einfache Schnittstelle für Branchen-Analyse
"""

from typing import Dict, Optional, List
from dataclasses import dataclass
import time

from src.website_crawler import WebsiteCrawler, WebsiteContent
from src.llm_analyzer import LLMAnalyzer, CompanyAnalysis
from src.analysis_cache import AnalysisCache


@dataclass
class PipelineResult:
    """Ergebnis der kompletten Pipeline"""
    company_name: str
    url: str
    website_content: Optional[WebsiteContent]
    analysis: Optional[CompanyAnalysis]
    cached: bool
    crawl_time: float
    analyze_time: float
    total_time: float
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'company_name': self.company_name,
            'url': self.url,
            'website_content': self.website_content.to_dict() if self.website_content else None,
            'analysis': self.analysis.to_dict() if self.analysis else None,
            'cached': self.cached,
            'crawl_time': self.crawl_time,
            'analyze_time': self.analyze_time,
            'total_time': self.total_time,
            'error': self.error
        }


class LLMPipeline:
    """
    End-to-End Pipeline für Branchen-Analyse
    
    1. Prüft Cache
    2. Crawlt Website (falls nicht gecached)
    3. Analysiert mit LLM (falls nicht gecached)
    4. Speichert im Cache
    """
    
    def __init__(self,
                 cache_db: str = "data/analysis_cache.db",
                 ollama_model: str = "llama3.2",
                 cache_ttl_days: int = 30,
                 crawler_delay: float = 1.0):
        """
        Args:
            cache_db: Pfad zur Cache-Datenbank
            ollama_model: Ollama Modell-Name
            cache_ttl_days: Cache Time-to-live
            crawler_delay: Sekunden zwischen Crawl-Requests
        """
        self.cache = AnalysisCache(db_path=cache_db, ttl_days=cache_ttl_days)
        self.crawler = WebsiteCrawler(delay=crawler_delay)
        self.analyzer = LLMAnalyzer(model=ollama_model, ollama_url="http://192.168.178.123:11434", timeout=300)
    
    def analyze_company(self, 
                       company_name: str, 
                       website_url: str) -> PipelineResult:
        """
        Analysiert ein einzelnes Unternehmen
        
        Args:
            company_name: Name des Unternehmens
            website_url: Website-URL
            
        Returns:
            PipelineResult mit Analyse oder Fehler
        """
        start_time = time.time()
        
        # 1. Cache prüfen
        cached_analysis = self.cache.get(website_url)
        if cached_analysis:
            # Konvertiere Cache-Dict zu CompanyAnalysis
            analysis = CompanyAnalysis(
                branch=cached_analysis['branch'],
                sub_branches=cached_analysis['sub_branches'],
                services=cached_analysis['services'],
                target_market=cached_analysis['target_market'],
                company_size_hint=cached_analysis['company_size_hint'],
                keywords=cached_analysis['keywords'],
                confidence=cached_analysis['confidence'],
                reasoning=cached_analysis['reasoning']
            )
            
            return PipelineResult(
                company_name=company_name,
                url=website_url,
                website_content=None,  # Nicht gecrawlt
                analysis=analysis,
                cached=True,
                crawl_time=0,
                analyze_time=0,
                total_time=time.time() - start_time
            )
        
        # 2. Website crawlen
        crawl_start = time.time()
        website_content = self.crawler.crawl(website_url)
        crawl_time = time.time() - crawl_start
        
        if website_content.error:
            return PipelineResult(
                company_name=company_name,
                url=website_url,
                website_content=website_content,
                analysis=None,
                cached=False,
                crawl_time=crawl_time,
                analyze_time=0,
                total_time=time.time() - start_time,
                error=f"Crawl fehlgeschlagen: {website_content.error}"
            )
        
        if website_content.word_count < 20:
            return PipelineResult(
                company_name=company_name,
                url=website_url,
                website_content=website_content,
                analysis=None,
                cached=False,
                crawl_time=crawl_time,
                analyze_time=0,
                total_time=time.time() - start_time,
                error="Zu wenig Content auf Website"
            )
        
        # 3. Mit LLM analysieren
        analyze_start = time.time()
        analysis = self.analyzer.analyze(company_name, website_content.to_dict())
        analyze_time = time.time() - analyze_start
        
        if not analysis:
            return PipelineResult(
                company_name=company_name,
                url=website_url,
                website_content=website_content,
                analysis=None,
                cached=False,
                crawl_time=crawl_time,
                analyze_time=analyze_time,
                total_time=time.time() - start_time,
                error="LLM-Analyse fehlgeschlagen"
            )
        
        # 4. Im Cache speichern
        self.cache.set(website_url, analysis.to_dict(), company_name)
        
        return PipelineResult(
            company_name=company_name,
            url=website_url,
            website_content=website_content,
            analysis=analysis,
            cached=False,
            crawl_time=crawl_time,
            analyze_time=analyze_time,
            total_time=time.time() - start_time
        )
    
    def analyze_companies(self, 
                         companies: List[Dict],
                         progress_callback=None) -> List[PipelineResult]:
        """
        Analysiert mehrere Unternehmen
        
        Args:
            companies: Liste von Dicts mit 'name' und 'website'
            progress_callback: Optional callback(current, total, result)
            
        Returns:
            Liste von PipelineResult
        """
        results = []
        total = len(companies)
        
        for i, company in enumerate(companies):
            name = company.get('name', 'Unknown')
            url = company.get('website', company.get('url', ''))
            
            if not url:
                result = PipelineResult(
                    company_name=name,
                    url='',
                    website_content=None,
                    analysis=None,
                    cached=False,
                    crawl_time=0,
                    analyze_time=0,
                    total_time=0,
                    error="Keine Website-URL"
                )
            else:
                result = self.analyze_company(name, url)
            
            results.append(result)
            
            if progress_callback:
                progress_callback(i + 1, total, result)
        
        return results
    
    def get_cache_stats(self) -> Dict:
        """Gibt Cache-Statistiken zurück"""
        return self.cache.get_stats()
    
    def clear_cache(self):
        """Löscht alle Cache-Einträge"""
        # Lösche alle Einträge (einfacher als einzelne invalidate)
        import sqlite3
        with sqlite3.connect(self.cache.db_path) as conn:
            conn.execute("DELETE FROM analysis_cache")
            conn.commit()


def analyze_single(company_name: str, website_url: str) -> Dict:
    """Hilfsfunktion für einfache Analyse"""
    pipeline = LLMPipeline()
    result = pipeline.analyze_company(company_name, website_url)
    return result.to_dict()


if __name__ == "__main__":
    print("=== LLM Pipeline Test ===\n")
    
    # Test-Unternehmen
    test_companies = [
        {
            'name': 'AKRAS Flavours',
            'website': 'https://www.akras.at'
        },
    ]
    
    pipeline = LLMPipeline()
    
    def progress(current, total, result):
        status = "✅" if result.analysis else "❌"
        cached = " (cached)" if result.cached else ""
        print(f"[{current}/{total}] {status} {result.company_name}{cached}")
    
    print("Starte Analyse...\n")
    results = pipeline.analyze_companies(test_companies, progress_callback=progress)
    
    print("\n" + "="*60)
    print("ERGEBNISSE:\n")
    
    for result in results:
        if result.analysis:
            print(f"🏢 {result.company_name}")
            print(f"   URL: {result.url}")
            print(f"   Branche: {result.analysis.branch}")
            print(f"   Services: {', '.join(result.analysis.services[:3])}")
            print(f"   Zielmarkt: {result.analysis.target_market}")
            print(f"   Confidence: {result.analysis.confidence:.2f}")
            print(f"   Zeit: {result.total_time:.1f}s (Crawl: {result.crawl_time:.1f}s, Analyze: {result.analyze_time:.1f}s)")
            if result.cached:
                print(f"   📦 Aus Cache")
            print()
        else:
            print(f"❌ {result.company_name}: {result.error}\n")
    
    # Cache-Stats
    print("="*60)
    print("CACHE-STATISTIKEN:")
    stats = pipeline.get_cache_stats()
    print(f"   Einträge: {stats['valid_entries']} (total: {stats['total_entries']})")
    print(f"   Ø Confidence: {stats['avg_confidence']:.2f}")
    if stats['top_branches']:
        print(f"   Top Branchen: {stats['top_branches']}")
