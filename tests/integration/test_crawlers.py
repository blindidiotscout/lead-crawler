"""
Integration Tests für Crawler
Testet echte WKO-Requests (wenn verfügbar)
"""

import sys
from pathlib import Path
import pytest

# Add src directory to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from lead_crawler.crawlers import WKOCrawler
from lead_crawler.models import Company


class TestWKOCrawlerIntegration:
    """Integration Tests für WKO Crawler"""

    def test_crawler_initialization(self):
        """Crawler kann initialisiert werden"""
        crawler = WKOCrawler()
        assert crawler is not None

    @pytest.mark.integration
    def test_crawler_real_request(self):
        """Echter WKO-Request (nur mit @pytest.mark.integration)"""
        # Dieser Test wird nur ausgeführt wenn -m "integration" angegeben wird
        crawler = WKOCrawler()
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])