"""
Unit Tests für Crawler Module
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add src directory to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from lead_crawler.crawlers.base import (
    BaseCrawler,
    CrawlerResult,
    CrawlerStatus,
    CrawlerFactory,
)
from lead_crawler.crawlers.wko import WKOCrawler, BUNDESLAENDER, PLZ_BUNDESLAND
from lead_crawler.models import Company, CompanySource


class TestCrawlerResult:
    """Tests für CrawlerResult"""

    def test_create_result(self):
        """CrawlerResult erstellen"""
        result = CrawlerResult()
        assert result.total == 0
        assert result.success_rate == 0.0
        assert result.status == CrawlerStatus.COMPLETED

    def test_result_with_companies(self):
        """CrawlerResult mit Unternehmen"""
        company1 = Company(name="Test GmbH")
        company2 = Company(name="Test AG")

        result = CrawlerResult(companies=[company1, company2])
        assert result.total == 2
        assert result.success_rate == 1.0

    def test_result_with_errors(self):
        """CrawlerResult mit Fehlern"""
        company = Company(name="Test GmbH")
        error = {'error': 'Test error'}

        result = CrawlerResult(companies=[company], errors=[error])
        assert result.total == 1
        assert result.success_rate == 0.5

    def test_result_to_dict(self):
        """CrawlerResult zu Dictionary"""
        result = CrawlerResult()
        data = result.to_dict()

        assert 'companies' in data
        assert 'errors' in data
        assert 'stats' in data
        assert 'total_companies' in data
        assert data['total_companies'] == 0


class TestCrawlerFactory:
    """Tests für CrawlerFactory"""

    def test_list_crawlers(self):
        """Verfügbare Crawler auflisten"""
        crawlers = CrawlerFactory.list_crawlers()
        assert 'wko' in crawlers

    def test_create_wko_crawler(self):
        """WKO Crawler erstellen"""
        crawler = CrawlerFactory.create('wko')
        assert isinstance(crawler, WKOCrawler)
        assert crawler.name == 'wko'
        assert crawler.source == CompanySource.WKO

    def test_create_nonexistent_crawler(self):
        """Nicht existierenden Crawler erstellen"""
        with pytest.raises(ValueError) as exc_info:
            CrawlerFactory.create('nonexistent')

        assert 'not found' in str(exc_info.value)


class TestWKOCrawler:
    """Tests für WKOCrawler"""

    def test_create_crawler(self):
        """WKOCrawler erstellen"""
        crawler = WKOCrawler()
        assert crawler.name == 'wko'
        assert crawler.BASE_URL == 'https://firmen.wko.at'

    def test_normalize_bundesland(self):
        """Bundesland-Normalisierung"""
        assert BUNDESLAENDER['noe'] == 'niederösterreich'
        assert BUNDESLAENDER['ooe'] == 'oberösterreich'
        assert BUNDESLAENDER['stmk'] == 'steiermark'
        assert BUNDESLAENDER['wien'] == 'wien'

    def test_plz_to_bundesland(self):
        """PLZ zu Bundesland"""
        assert PLZ_BUNDESLAND['1'] == 'wien'
        assert PLZ_BUNDESLAND['2'] == 'niederösterreich'
        assert PLZ_BUNDESLAND['4'] == 'oberösterreich'

    def test_build_urls_with_plz(self, tmp_path):
        """URLs mit PLZ erstellen"""
        # PLZ-Service mocken
        from lead_crawler.services.plz_service import PLZCoordinate, PLZInfo

        crawler = WKOCrawler()

        # PLZ-Service mocken
        mock_info = PLZInfo(
            plz="2351",
            coordinates=[
                PLZCoordinate(plz="2351", ort="Guntramsdorf", bundesland="Niederösterreich", lat=48.1, lon=16.3)
            ]
        )

        with patch.object(crawler.plz_service, 'get_plz_info', return_value=mock_info):
            urls = crawler._build_urls(plz="2351", ort=None, bundesland=None)
            assert len(urls) == 1
            assert 'guntramsdorf' in urls[0].lower()

    def test_build_urls_with_ort(self):
        """URLs mit Ort erstellen"""
        crawler = WKOCrawler()

        urls = crawler._build_urls(plz=None, ort="Wien", bundesland="wien")
        assert len(urls) == 1
        assert 'wien' in urls[0].lower()

    def test_build_urls_with_ort_no_bundesland(self):
        """URLs mit Ort ohne Bundesland erstellen"""
        crawler = WKOCrawler()

        urls = crawler._build_urls(plz=None, ort="Guntramsdorf", bundesland=None)
        assert len(urls) == 1
        assert 'guntramsdorf' in urls[0].lower()

    def test_parse_item_valid(self):
        """Item valid parsen"""
        crawler = WKOCrawler()

        data = {
            'name': 'Test GmbH',
            'street': 'Teststraße 1',
            'plz': '2351',
            'ort': 'Guntramsdorf',
            'bundesland': 'Niederösterreich',
            'telefon': '+43 123 456',
            'email': 'test@example.com',
            'website': 'https://example.com'
        }

        company = crawler._parse_item(data)
        assert company is not None
        assert company.name == 'Test GmbH'
        assert company.address.street == 'Teststraße 1'
        assert company.address.plz == '2351'
        assert company.contact.email == 'test@example.com'

    def test_parse_item_no_name(self):
        """Item ohne Name"""
        crawler = WKOCrawler()

        data = {
            'street': 'Teststraße 1',
            'plz': '2351'
        }

        company = crawler._parse_item(data)
        assert company is None  # Kein Name = None

    def test_deduplicate(self):
        """Duplikate entfernen"""
        crawler = WKOCrawler()

        companies = [
            Company(name="Test GmbH", address=Address(street="Teststraße 1", plz="2351")),
            Company(name="Test GmbH", address=Address(street="Teststraße 1", plz="2351")),  # Duplikat
            Company(name="Andere AG", address=Address(street="Andere Straße 2", plz="1010")),
            Company(name="Test GmbH", address=Address(street="Andere Straße 3", plz="2351")),  # Anderer Ort
        ]

        unique = crawler._deduplicate(companies)
        assert len(unique) == 3  # 4 - 1 Duplikat


class TestBaseCrawler:
    """Tests für BaseCrawler"""

    def test_normalize_phone(self):
        """Telefonnummer normalisieren"""
        crawler = WKOCrawler()

        assert crawler._normalize_phone("+43 123 456") == "+43123456"
        assert crawler._normalize_phone("01 / 234 567") == "01234567"
        assert crawler._normalize_phone(None) is None

    def test_normalize_email(self):
        """E-Mail normalisieren"""
        crawler = WKOCrawler()

        assert crawler._normalize_email("TEST@Example.COM") == "test@example.com"
        assert crawler._normalize_email("invalid") is None
        assert crawler._normalize_email(None) is None

    def test_normalize_url(self):
        """URL normalisieren"""
        crawler = WKOCrawler()

        assert crawler._normalize_url("example.com") == "https://example.com"
        assert crawler._normalize_url("https://example.com") == "https://example.com"
        assert crawler._normalize_url(None) is None

    def test_normalize_plz(self):
        """PLZ normalisieren"""
        crawler = WKOCrawler()

        assert crawler._normalize_plz("2351") == "2351"
        assert crawler._normalize_plz("A-2351") == "2351"
        assert crawler._normalize_plz("123") is None  # Zu kurz
        assert crawler._normalize_plz(None) is None

    def test_clean_string(self):
        """String bereinigen"""
        crawler = WKOCrawler()

        assert crawler._clean_string("  Test  ") == "Test"
        assert crawler._clean_string("Test   String") == "Test String"
        assert crawler._clean_string("") is None
        assert crawler._clean_string(None) is None

    def test_create_company(self):
        """Company erstellen"""
        crawler = WKOCrawler()

        company = crawler.create_company(
            name="Test GmbH",
            address={'street': 'Teststraße 1', 'plz': '2351', 'ort': 'Guntramsdorf'},
            contact={'telefon': '+43 123', 'email': 'test@example.com'}
        )

        assert company.name == "Test GmbH"
        assert company.address.street == "Teststraße 1"
        assert company.address.plz == "2351"
        assert company.contact.email == "test@example.com"
        assert company.metadata.source == CompanySource.WKO


class TestCrawlerStats:
    """Tests für Crawler Statistiken"""

    def test_stats_tracking(self):
        """Statistiken tracken"""
        crawler = WKOCrawler()

        # Initial
        assert crawler._stats['companies_found'] == 0
        assert crawler._stats['errors'] == 0

        # Track success
        crawler._track_success()
        assert crawler._stats['companies_found'] == 1

        # Track error
        crawler._track_error("Test error")
        assert crawler._stats['errors'] == 1

        # Track skip
        crawler._track_skip("No website")
        assert crawler._stats['skipped'] == 1


# Import für Address
from lead_crawler.models import Address


if __name__ == "__main__":
    pytest.main([__file__, "-v"])