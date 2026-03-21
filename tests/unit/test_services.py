"""
Unit Tests für Services
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add src directory to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from lead_crawler.config import CacheConfig, PLZConfig
from lead_crawler.services.cache import SQLiteCache, get_cache, reset_cache
from lead_crawler.services.llm_client import LLMResponse, MockLLMClient
from lead_crawler.services.plz_service import (
    HaversineCalculator,
    PLZDatabase,
    PLZService,
    get_plz_service,
    reset_plz_service,
    seed_sample_data,
)
from lead_crawler.services.website_extractor import WebsiteContent


class TestSQLiteCache:
    """Tests für SQLiteCache"""

    def test_create_cache(self, tmp_path):
        """Cache erstellen"""
        cache = SQLiteCache(CacheConfig(db_path=tmp_path / "test_cache.db"))
        assert cache.db_path.exists()

    def test_set_and_get(self, tmp_path):
        """Wert setzen und abrufen"""
        cache = SQLiteCache(CacheConfig(db_path=tmp_path / "test_cache.db"))

        # Wert setzen
        cache.set("test_key", {"branch": "IT", "confidence": 0.9})

        # Wert abrufen
        result = cache.get("test_key")
        assert result is not None
        assert result["branch"] == "IT"
        assert result["confidence"] == 0.9
        assert result["_cached"] is True

    def test_get_nonexistent(self, tmp_path):
        """Nicht existierenden Key abrufen"""
        cache = SQLiteCache(CacheConfig(db_path=tmp_path / "test_cache.db"))
        result = cache.get("nonexistent_key")
        assert result is None

    def test_delete(self, tmp_path):
        """Eintrag löschen"""
        cache = SQLiteCache(CacheConfig(db_path=tmp_path / "test_cache.db"))

        cache.set("to_delete", {"data": "test"})
        assert cache.exists("to_delete")

        deleted = cache.delete("to_delete")
        assert deleted is True
        assert not cache.exists("to_delete")

    def test_clear(self, tmp_path):
        """Cache leeren"""
        cache = SQLiteCache(CacheConfig(db_path=tmp_path / "test_cache.db"))

        cache.set("key1", {"data": "test1"})
        cache.set("key2", {"data": "test2"})

        count = cache.clear()
        assert count == 2
        assert not cache.exists("key1")
        assert not cache.exists("key2")

    def test_ttl(self, tmp_path):
        """TTL (Time-to-Live)"""
        cache = SQLiteCache(CacheConfig(db_path=tmp_path / "test_cache.db", ttl_days=1))

        # Wert mit kurzer TTL
        cache.set("short_ttl", {"data": "test"}, ttl_seconds=1)

        # Sofort verfügbar
        assert cache.exists("short_ttl")

        # Nach Ablauf nicht mehr verfügbar (wir können nicht wirklich warten)
        # Wir testen nur, dass das Feld expires_at gesetzt wurde
        import sqlite3

        with sqlite3.connect(str(cache.db_path)) as conn:
            cursor = conn.execute(
                "SELECT expires_at FROM cache_entries WHERE key = ?", ("short_ttl",)
            )
            row = cursor.fetchone()
            assert row[0] is not None

    def test_get_stats(self, tmp_path):
        """Cache-Statistiken"""
        cache = SQLiteCache(CacheConfig(db_path=tmp_path / "test_cache.db"))

        # Einige Einträge
        cache.set("key1", {"branch": "IT", "confidence": 0.9})
        cache.set("key2", {"branch": "Bau", "confidence": 0.8})
        cache.set("key3", {"branch": "IT", "confidence": 0.85})

        stats = cache.get_stats()
        assert stats["total_entries"] == 3
        assert stats["valid_entries"] == 3
        assert "IT" in stats["top_branches"]

    def test_get_many(self, tmp_path):
        """Mehrere Werte gleichzeitig abrufen"""
        cache = SQLiteCache(CacheConfig(db_path=tmp_path / "test_cache.db"))

        cache.set("key1", {"data": "test1"})
        cache.set("key2", {"data": "test2"})
        cache.set("key3", {"data": "test3"})

        results = cache.get_many(["key1", "key2", "key3", "nonexistent"])
        assert results["key1"]["data"] == "test1"
        assert results["key2"]["data"] == "test2"
        assert results["key3"]["data"] == "test3"
        assert results["nonexistent"] is None

    def test_normalize_url(self, tmp_path):
        """URL-Normalisierung"""
        cache = SQLiteCache(CacheConfig(db_path=tmp_path / "test_cache.db"))

        # Verschiedene URL-Formen sollten denselben Key haben
        cache.set("https://example.com/", {"data": "test"})
        result1 = cache.get("https://example.com")

        cache.set("http://example.com/path/", {"data": "test2"})
        result2 = cache.get("example.com/path")

        assert result1 is not None
        assert result2 is not None


class TestMockLLMClient:
    """Tests für MockLLMClient"""

    def test_create_client(self):
        """Client erstellen"""
        client = MockLLMClient()
        assert client.branch == "IT"
        assert client.confidence == 0.85

    def test_custom_params(self):
        """Custom Parameter"""
        client = MockLLMClient(branch="Bau", confidence=0.95)
        assert client.branch == "Bau"
        assert client.confidence == 0.95

    def test_generate(self):
        """generate() Methode"""
        client = MockLLMClient(branch="IT")
        response = client.generate("Test prompt")

        assert response.error is None
        assert response.model == "mock"
        assert client.call_count == 1

        # Response ist JSON
        data = json.loads(response.content)
        assert data["branch"] == "IT"

    def test_analyze_branch(self):
        """analyze_branch() Methode"""
        client = MockLLMClient(branch="Bau", confidence=0.92)
        website_content = {"title": "Test Firma", "main_text": "Wir sind eine Baufirma"}

        analysis = client.analyze_branch("Test GmbH", website_content)

        assert analysis is not None
        assert analysis.branch == "Bau"
        assert analysis.confidence == 0.92
        assert client.call_count == 1

    def test_is_available(self):
        """is_available() ist immer True"""
        client = MockLLMClient()
        assert client.is_available() is True


class TestWebsiteContent:
    """Tests für WebsiteContent"""

    def test_create_content(self):
        """WebsiteContent erstellen"""
        content = WebsiteContent(
            url="https://example.com",
            title="Example Corp",
            meta_description="We do things",
            main_text="This is our company...",
            word_count=100,
            crawl_time=1.5,
        )

        assert content.url == "https://example.com"
        assert content.title == "Example Corp"
        assert content.word_count == 100

    def test_to_dict(self):
        """to_dict() Konvertierung"""
        content = WebsiteContent(
            url="https://example.com",
            title="Example",
            meta_description="Desc",
            main_text="Text",
            about_text="About",
            word_count=50,
            crawl_time=1.0,
        )

        data = content.to_dict()
        assert data["url"] == "https://example.com"
        assert data["about_text"] == "About"

    def test_from_dict(self):
        """from_dict() Erstellung"""
        data = {
            "url": "https://example.com",
            "title": "Example",
            "meta_description": "Desc",
            "main_text": "Text",
            "word_count": 50,
        }

        content = WebsiteContent.from_dict(data)
        assert content.url == "https://example.com"
        assert content.title == "Example"

    def test_is_valid(self):
        """is_valid Property"""
        valid = WebsiteContent(
            url="https://example.com",
            title="Test",
            meta_description="Desc",
            main_text="Text",
            word_count=100,
        )
        invalid_error = WebsiteContent(
            url="https://example.com",
            title="",
            meta_description="",
            main_text="",
            word_count=0,
            error="Failed",
        )
        invalid_empty = WebsiteContent(
            url="https://example.com", title="Test", meta_description="", main_text="", word_count=0
        )

        assert valid.is_valid is True
        assert invalid_error.is_valid is False
        assert invalid_empty.is_valid is False

    def test_combined_text(self):
        """combined_text Property"""
        content = WebsiteContent(
            url="https://example.com",
            title="Test",
            meta_description="Desc",
            main_text="Main content",
            about_text="About us",
            services_text="Our services",
            contact_text="Contact info",
            word_count=100,
        )

        combined = content.combined_text
        assert "Main content" in combined
        assert "About: About us" in combined
        assert "Services: Our services" in combined
        assert "Contact: Contact info" in combined


class TestPLZDatabase:
    """Tests für PLZDatabase"""

    def test_create_database(self, tmp_path):
        """Datenbank erstellen"""
        db = PLZDatabase(tmp_path / "test_plz.db")
        assert db.db_path.exists()

    def test_add_and_get_plz(self, tmp_path):
        """PLZ hinzufügen und abrufen"""
        db = PLZDatabase(tmp_path / "test_plz.db")

        db.add_plz("2351", "Guntramsdorf", 48.1067, 16.3256, "Niederösterreich")

        result = db.get_plz("2351")
        assert result is not None
        assert result.plz == "2351"
        assert result.ort == "Guntramsdorf"
        assert result.lat == 48.1067
        assert result.lon == 16.3256

    def test_get_nonexistent_plz(self, tmp_path):
        """Nicht existierende PLZ abrufen"""
        db = PLZDatabase(tmp_path / "test_plz.db")
        result = db.get_plz("9999")
        assert result is None

    def test_get_plz_by_ort(self, tmp_path):
        """PLZ nach Ort suchen"""
        db = PLZDatabase(tmp_path / "test_plz.db")

        db.add_plz("2351", "Guntramsdorf", 48.1067, 16.3256, "NÖ")
        db.add_plz("1010", "Wien Innere Stadt", 48.2082, 16.3719, "Wien")

        results = db.get_plz_by_ort("Wien")
        assert len(results) == 1
        assert results[0].ort == "Wien Innere Stadt"

    def test_add_many(self, tmp_path):
        """Mehrere PLZ hinzufügen"""
        db = PLZDatabase(tmp_path / "test_plz.db")

        entries = [
            {"plz": "2351", "ort": "Guntramsdorf", "lat": 48.1067, "lon": 16.3256},
            {"plz": "1010", "ort": "Wien", "lat": 48.2082, "lon": 16.3719},
        ]

        count = db.add_many(entries)
        assert count == 2
        assert db.count() == 2

    def test_get_all_plz(self, tmp_path):
        """Alle PLZ abrufen"""
        db = PLZDatabase(tmp_path / "test_plz.db")

        db.add_plz("2351", "Guntramsdorf", 48.1067, 16.3256)
        db.add_plz("1010", "Wien", 48.2082, 16.3719)

        all_plz = db.get_all_plz()
        assert len(all_plz) == 2


class TestHaversineCalculator:
    """Tests für HaversineCalculator"""

    def test_distance_same_point(self):
        """Distanz zum selben Punkt"""
        distance = HaversineCalculator.distance(48.2, 16.3, 48.2, 16.3)
        assert distance == 0.0

    def test_distance_vienna_graz(self):
        """Distanz Wien - Graz (ca. 145km)"""
        # Wien: 48.2082, 16.3719
        # Graz: 47.0707, 15.4395
        distance = HaversineCalculator.distance(48.2082, 16.3719, 47.0707, 15.4395)

        # Ca. 145km, Toleranz 10km
        assert 135 < distance < 155

    def test_distance_vienna_linz(self):
        """Distanz Wien - Linz (ca. 155km)"""
        # Wien: 48.2082, 16.3719
        # Linz: 48.3069, 14.2858
        distance = HaversineCalculator.distance(48.2082, 16.3719, 48.3069, 14.2858)

        # Ca. 155km, Toleranz 10km
        assert 145 < distance < 165


class TestPLZService:
    """Tests für PLZService"""

    def test_create_service(self, tmp_path):
        """Service erstellen"""
        service = PLZService(PLZConfig(db_path=tmp_path / "test_plz.db"))
        assert service.db is not None

    def test_find_in_radius(self, tmp_path):
        """PLZ im Radius finden"""
        service = PLZService(PLZConfig(db_path=tmp_path / "test_plz.db"))
        seed_sample_data(service.db)

        # Guntramsdorf (2351) im 10km Radius
        result = service.find_in_radius("2351", 10.0)

        assert result.center_plz == "2351"
        assert result.radius_km == 10.0
        # Mindestens Guntramsdorf selbst sollte gefunden werden
        assert result.count >= 1
        # Alle gefundenen PLZ sollten im Radius sein
        for coord, dist in result.results:
            assert dist <= 10.0

    def test_find_nearby_plz(self, tmp_path):
        """Nahegelegene PLZ finden (nur Codes)"""
        service = PLZService(PLZConfig(db_path=tmp_path / "test_plz.db"))
        seed_sample_data(service.db)

        plzs = service.find_nearby_plz("2351", 20.0)

        assert "2351" in plzs  # Guntramsdorf selbst

    def test_validate_plz(self, tmp_path):
        """PLZ validieren"""
        service = PLZService(PLZConfig(db_path=tmp_path / "test_plz.db"))
        seed_sample_data(service.db)

        assert service.validate_plz("2351") is True
        assert service.validate_plz("9999") is False

    def test_get_plz_info(self, tmp_path):
        """PLZ-Info abrufen"""
        service = PLZService(PLZConfig(db_path=tmp_path / "test_plz.db"))
        seed_sample_data(service.db)

        info = service.get_plz_info("2351")
        assert info is not None
        assert info.plz == "2351"
        assert len(info.coordinates) >= 1
        assert info.primary_ort == "Guntramsdorf"

    def test_max_radius_limit(self, tmp_path):
        """Max-Radius-Limit"""
        service = PLZService(PLZConfig(db_path=tmp_path / "test_plz.db", max_radius_km=50.0))
        seed_sample_data(service.db)

        with pytest.raises(ValueError) as exc_info:
            service.find_in_radius("2351", 100.0)

        assert "exceeds maximum" in str(exc_info.value)


class TestSingleton:
    """Tests für Singleton Pattern"""

    def test_cache_singleton(self):
        """Cache Singleton"""
        reset_cache()
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2
        reset_cache()

    def test_plz_service_singleton(self):
        """PLZ Service Singleton"""
        reset_plz_service()
        service1 = get_plz_service()
        service2 = get_plz_service()
        assert service1 is service2
        reset_plz_service()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
