"""
Enhanced WKO Spider mit LLM-Analyse
Erweitert den Basis-Spider um Branchen-Erkennung via LLM
"""

import scrapy
from typing import Optional, Dict, List
from datetime import datetime
import time
import json

# Importiere Basis-Spider
from src.scraper import WkoSpider, run_spider, run_spider_radius, _deduplicate_companies, get_plz_lookup
from src.llm_pipeline import LLMPipeline, PipelineResult


class EnhancedWkoSpider(WkoSpider):
    """
    Erweiterter WKO Spider mit LLM-basierter Branchenanalyse
    
    Zusätzliche Features:
    - Crawlt Websites von gefundenen Unternehmen
    - Analysiert Branche mit lokalem LLM (Ollama)
    - Speichert Analysen im Cache
    - Erweitert Company-Daten mit LLM-Insights
    """
    
    name = "wko_enhanced"
    
    def __init__(self, 
                 plz: Optional[str] = None, 
                 ort: Optional[str] = None,
                 bundesland: Optional[str] = None, 
                 page: int = 1,
                 _urls: Optional[List[str]] = None,
                 # LLM-Optionen
                 use_llm: bool = True,
                 llm_model: str = "qwen2.5:7b",
                 analyze_websites: bool = True,
                 max_websites_per_batch: int = 10,  # Limit für Rate-Limiting
                 *args, **kwargs):
        """
        Args:
            use_llm: LLM-Analyse aktivieren
            llm_model: Ollama Modell-Name
            analyze_websites: Websites crawlen und analysieren
            max_websites_per_batch: Max Websites pro Batch (Rate-Limiting)
        """
        super().__init__(plz=plz, ort=ort, bundesland=bundesland, 
                        page=page, _urls=_urls, *args, **kwargs)
        
        self.use_llm = use_llm
        self.analyze_websites = analyze_websites
        self.max_websites_per_batch = max_websites_per_batch
        
        # LLM Pipeline initialisieren
        if self.use_llm:
            self.llm_pipeline = LLMPipeline(ollama_model=llm_model)
        else:
            self.llm_pipeline = None
        
        # Statistiken
        self.stats = {
            'companies_found': 0,
            'websites_crawled': 0,
            'llm_analyses': 0,
            'llm_cached': 0,
            'errors': 0
        }
    
    def parse(self, response):
        """Parse WKO Suchergebnisse mit optionaler LLM-Analyse"""
        
        # Basis-Parsing
        articles = response.css('article.search-result-article')
        self.logger.info(f"Gefunden: {len(articles)} Firmeneinträge auf {response.url}")
        
        companies_with_website = []
        
        for article in articles:
            company = self._parse_result_article(article, response)
            if company:
                self.stats['companies_found'] += 1
                
                # Sammle Unternehmen mit Website für Batch-Analyse
                if self.analyze_websites and company.get('website') and self.llm_pipeline:
                    companies_with_website.append(company)
                else:
                    # Keine Website oder LLM deaktiviert
                    company['llm_analysis'] = None
                    company['llm_cached'] = False
                    yield company
        
        # Batch-Analyse der Websites
        if companies_with_website and self.llm_pipeline:
            self.logger.info(f"Starte LLM-Analyse für {len(companies_with_website)} Websites...")
            
            # Limit für Rate-Limiting
            to_analyze = companies_with_website[:self.max_websites_per_batch]
            
            for company in to_analyze:
                result = self._analyze_company(company)
                
                # Ergebnis anreichern
                if result and result.analysis:
                    company['llm_analysis'] = result.analysis.to_dict()
                    company['llm_cached'] = result.cached
                    
                    # Kurze Pause zwischen Analysen
                    if not result.cached:
                        time.sleep(1)
                else:
                    company['llm_analysis'] = None
                    company['llm_cached'] = False
                    company['llm_error'] = result.error if result else "Analyse fehlgeschlagen"
                
                yield company
            
            # Restliche Unternehmen ohne LLM-Analyse
            for company in companies_with_website[self.max_websites_per_batch:]:
                company['llm_analysis'] = None
                company['llm_cached'] = False
                company['llm_skipped'] = True
                yield company
    
    def _analyze_company(self, company: Dict) -> Optional[PipelineResult]:
        """Analysiert ein Unternehmen mit LLM Pipeline"""
        try:
            result = self.llm_pipeline.analyze_company(
                company_name=company.get('name', 'Unknown'),
                website_url=company.get('website')
            )
            
            self.stats['websites_crawled'] += 1
            if result.cached:
                self.stats['llm_cached'] += 1
            else:
                self.stats['llm_analyses'] += 1
            
            return result
            
        except Exception as e:
            self.logger.error(f"LLM-Analyse fehlgeschlagen für {company.get('name')}: {e}")
            self.stats['errors'] += 1
            return None
    
    def closed(self, reason):
        """Wird aufgerufen wenn Spider fertig ist"""
        self.logger.info("=" * 60)
        self.logger.info("SPIDER STATISTIKEN:")
        self.logger.info(f"  Unternehmen gefunden: {self.stats['companies_found']}")
        self.logger.info(f"  Websites gecrawlt: {self.stats['websites_crawled']}")
        self.logger.info(f"  LLM-Analysen: {self.stats['llm_analyses']}")
        self.logger.info(f"  Aus Cache: {self.stats['llm_cached']}")
        self.logger.info(f"  Fehler: {self.stats['errors']}")
        self.logger.info("=" * 60)


def run_enhanced_spider(spider_name: str = "wko_enhanced", 
                       use_llm: bool = True,
                       llm_model: str = "qwen2.5:7b",
                       analyze_websites: bool = True,
                       **kwargs) -> List[Dict]:
    """
    Führt den Enhanced Spider aus
    
    Args:
        use_llm: LLM-Analyse aktivieren
        llm_model: Ollama Modell (z.B. "qwen2.5:7b", "llama3.1:8b")
        analyze_websites: Websites crawlen und analysieren
        **kwargs: Weitere Parameter (plz, ort, bundesland, etc.)
    
    Returns:
        Liste von Unternehmen mit LLM-Analyse
    """
    from scrapy.crawler import CrawlerProcess
    import tempfile
    import os
    
    # Temporäre Ausgabedatei
    output_file = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
    output_path = output_file.name
    output_file.close()
    
    # PLZ zu URLs auflösen
    if 'plz' in kwargs and '_urls' not in kwargs:
        lookup = get_plz_lookup()
        urls = lookup.get_wko_url(kwargs['plz'])
        if urls:
            kwargs['_urls'] = urls
            print(f"PLZ {kwargs['plz']} → {len(urls)} URLs")
    
    # Scrapy Einstellungen
    settings = {
        'FEEDS': {output_path: {'format': 'jsonlines'}},
        'LOG_LEVEL': 'INFO',
        'USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'ROBOTSTXT_OBEY': True,
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
    }
    
    # Spider-Parameter
    spider_kwargs = {
        'use_llm': use_llm,
        'llm_model': llm_model,
        'analyze_websites': analyze_websites,
    }
    spider_kwargs.update(kwargs)
    
    print(f"\n{'='*60}")
    print(f"Enhanced WKO Spider")
    print(f"{'='*60}")
    print(f"LLM: {'Aktiviert (' + llm_model + ')' if use_llm else 'Deaktiviert'}")
    print(f"Website-Analyse: {'Ja' if analyze_websites else 'Nein'}")
    print(f"{'='*60}\n")
    
    # Spider ausführen
    process = CrawlerProcess(settings)
    process.crawl(EnhancedWkoSpider, **spider_kwargs)
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


def run_enhanced_radius(center_plz: str, 
                       radius_km: float = 20,
                       max_plz: int = None,
                       use_llm: bool = True,
                       llm_model: str = "qwen2.5:7b",
                       dedup: bool = True) -> List[Dict]:
    """
    Crawlt Unternehmen im Radius mit LLM-Analyse
    
    Args:
        center_plz: Zentrale PLZ
        radius_km: Radius in km
        max_plz: Maximale Anzahl PLZs
        use_llm: LLM-Analyse aktivieren
        llm_model: Ollama Modell
        dedup: Duplikate entfernen
    
    Returns:
        Liste von Unternehmen mit LLM-Daten
    """
    from src.plz_radius import PLZRadiusService
    
    # PLZs im Radius finden
    plz_service = PLZRadiusService('data/plz_austria.db')
    plz_list = plz_service.find_plz_in_radius(center_plz, radius_km)
    
    if not plz_list:
        print(f"Keine PLZ im {radius_km}km Radius um {center_plz} gefunden")
        return []
    
    print(f"PLZ {center_plz}: {len(plz_list)} PLZ im {radius_km}km Radius")
    
    if max_plz:
        plz_list = plz_list[:max_plz]
        print(f"  (limitiert auf {max_plz} PLZ)")
    
    # Alle PLZs crawlen
    all_results = []
    unique_plzs = set()
    
    for i, item in enumerate(plz_list, 1):
        plz = item['plz']
        ort = item['ort']
        distance = item['distance_km']
        
        if plz in unique_plzs:
            continue
        unique_plzs.add(plz)
        
        print(f"\n[{i}/{len(plz_list)}] PLZ {plz} ({ort}) - {distance:.1f}km")
        
        try:
            results = run_enhanced_spider(
                plz=plz,
                use_llm=use_llm,
                llm_model=llm_model,
                analyze_websites=True,
                max_websites_per_batch=5  # Limit pro PLZ
            )
            print(f"  → {len(results)} Unternehmen")
            all_results.extend(results)
            
        except Exception as e:
            print(f"  ⚠️ Fehler: {e}")
            continue
    
    # Deduplizierung
    if dedup and all_results:
        print(f"\nDedupliziere {len(all_results)} Ergebnisse...")
        all_results = _deduplicate_companies(all_results)
        print(f"  → {len(all_results)} einzigartige Unternehmen")
    
    # Statistik
    with_llm = sum(1 for c in all_results if c.get('llm_analysis'))
    cached = sum(1 for c in all_results if c.get('llm_cached'))
    
    print(f"\n{'='*60}")
    print(f"ERGEBNIS:")
    print(f"  Gesamt: {len(all_results)} Unternehmen")
    print(f"  Mit LLM-Analyse: {with_llm}")
    print(f"  Aus Cache: {cached}")
    print(f"{'='*60}")
    
    return all_results


if __name__ == "__main__":
    print("=== Enhanced WKO Spider Test ===\n")
    
    # Test: Einzelne PLZ mit LLM
    print("Test: PLZ 2351 (Guntramsdorf) mit LLM-Analyse\n")
    
    results = run_enhanced_spider(
        plz="2351",
        use_llm=True,
        llm_model="qwen2.5:7b",
        analyze_websites=True,
        max_websites_per_batch=3  # Limit für Test
    )
    
    print(f"\n{'='*60}")
    print(f"Gefundene Unternehmen: {len(results)}\n")
    
    for i, c in enumerate(results[:5], 1):
        print(f"{i}. {c.get('name')}")
        print(f"   {c.get('street')}, {c.get('plz')} {c.get('ort')}")
        if c.get('website'):
            print(f"   🌐 {c.get('website')}")
        if c.get('llm_analysis'):
            analysis = c['llm_analysis']
            print(f"   🤖 {analysis.get('branch')} ({analysis.get('confidence', 0):.0%})")
            print(f"      Services: {', '.join(analysis.get('services', [])[:3])}")
        print()
