"""
Lead Crawler Crawlers Package
Spider und Crawler für verschiedene Datenquellen
"""

from lead_crawler.crawlers.base import (
    BaseCrawler,
    CrawlerFactory,
    CrawlerResult,
    CrawlerStatus,
)
from lead_crawler.crawlers.wko import (
    WKOCrawler,
    crawl_wko,
)

# Wird später hinzugefügt:
# from lead_crawler.crawlers.ecoplus import EcoPlusCrawler, crawl_ecoplus

__all__ = [
    # Base
    "BaseCrawler",
    "CrawlerResult",
    "CrawlerStatus",
    "CrawlerFactory",
    # WKO
    "WKOCrawler",
    "crawl_wko",
    # EcoPlus (später)
    # "EcoPlusCrawler",
    # "crawl_ecoplus",
]
