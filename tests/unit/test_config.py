"""
Unit Tests für Configuration
"""

import os
import sys
from pathlib import Path
import pytest

# Add src directory to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from lead_crawler.config import (
    Settings,
    OllamaConfig,
    CacheConfig,
    PLZConfig,
    CrawlerConfig,
    ScoringConfig,
    APIConfig,
    get_settings,
    reset_settings,
)


class TestOllamaConfig:
    """Tests für OllamaConfig"""

    def test_create_default(self):
        """Default OllamaConfig erstellen"""
        config = OllamaConfig()
        assert config.url == "http://localhost:11434"
        assert config.model == "qwen2.5:7b"
        assert config.timeout == 300

    def test_from_env(self, monkeypatch):
        """OllamaConfig aus Umgebungsvariablen"""
        monkeypatch.setenv("OLLAMA_URL", "http://192.168.1.100:11434")
        monkeypatch.setenv("OLLAMA_MODEL", "llama3:8b")
        monkeypatch.setenv("OLLAMA_TIMEOUT", "600")

        config = OllamaConfig.from_env()
        assert config.url == "http://192.168.1.100:11434"
        assert config.model == "llama3:8b"
        assert config.timeout == 600


class TestCacheConfig:
    """Tests für CacheConfig"""

    def test_create_default(self):
        """Default CacheConfig erstellen"""
        config = CacheConfig()
        assert str(config.db_path) == "data/analysis_cache.db"
        assert config.ttl_days == 30
        assert config.max_entries == 100000

    def test_custom_path(self):
        """CacheConfig mit custom path"""
        config = CacheConfig(db_path=Path("/custom/cache.db"))
        assert config.db_path == Path("/custom/cache.db")


class TestPLZConfig:
    """Tests für PLZConfig"""

    def test_create_default(self):
        """Default PLZConfig erstellen"""
        config = PLZConfig()
        assert str(config.db_path) == "data/plz_austria.db"
        assert config.default_radius_km == 20.0
        assert config.max_radius_km == 100.0


class TestCrawlerConfig:
    """Tests für CrawlerConfig"""

    def test_create_default(self):
        """Default CrawlerConfig erstellen"""
        config = CrawlerConfig()
        assert config.rate_limit == 2.0
        assert config.concurrent_requests == 1
        assert config.respect_robots_txt is True
        assert "Mozilla" in config.user_agent

    def test_custom_settings(self):
        """CrawlerConfig mit custom settings"""
        config = CrawlerConfig(
            rate_limit=1.0,
            concurrent_requests=2,
            timeout=60
        )
        assert config.rate_limit == 1.0
        assert config.concurrent_requests == 2
        assert config.timeout == 60


class TestScoringConfig:
    """Tests für ScoringConfig"""

    def test_create_default(self):
        """Default ScoringConfig erstellen"""
        config = ScoringConfig()
        assert config.weights["contact"] == 25.0
        assert config.weights["location"] == 20.0
        assert config.grade_thresholds["A"] == 80.0

    def test_weights_sum_to_100(self):
        """Gewichtungen sollten 100 ergeben"""
        config = ScoringConfig()
        total = sum(config.weights.values())
        assert total == 100.0


class TestAPIConfig:
    """Tests für APIConfig"""

    def test_create_default(self):
        """Default APIConfig erstellen"""
        config = APIConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.debug is False
        assert config.api_key_header == "X-API-Key"

    def test_from_env(self, monkeypatch):
        """APIConfig aus Umgebungsvariablen"""
        monkeypatch.setenv("API_HOST", "127.0.0.1")
        monkeypatch.setenv("API_PORT", "9000")
        monkeypatch.setenv("API_DEBUG", "true")

        config = APIConfig.from_env()
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.debug is True


class TestSettings:
    """Tests für Settings"""

    def test_create_default(self):
        """Default Settings erstellen"""
        settings = Settings()
        assert settings.ollama.model == "qwen2.5:7b"
        assert settings.cache.ttl_days == 30
        assert settings.default_plz == "2351"

    def test_from_env(self, monkeypatch):
        """Settings aus Umgebungsvariablen"""
        monkeypatch.setenv("OLLAMA_URL", "http://custom:11434")
        monkeypatch.setenv("DEFAULT_PLZ", "1010")

        settings = Settings.from_env()
        assert settings.ollama.url == "http://custom:11434"
        assert settings.default_plz == "1010"

    def test_ensure_directories(self, tmp_path):
        """ensure_directories erstellt Verzeichnisse"""
        settings = Settings(
            data_dir=tmp_path / "data",
            output_dir=tmp_path / "output"
        )
        settings.ensure_directories()

        assert settings.data_dir.exists()
        assert settings.output_dir.exists()

    def test_resolve_path_absolute(self):
        """resolve_path mit absolutem Pfad"""
        settings = Settings()
        abs_path = Path("/tmp/test")

        result = settings.resolve_path(abs_path)
        assert result == abs_path

    def test_resolve_path_relative(self):
        """resolve_path mit relativem Pfad"""
        settings = Settings()
        rel_path = "data/test.db"

        result = settings.resolve_path(rel_path)
        assert str(result).endswith("data/test.db")

    def test_to_and_from_file(self, tmp_path):
        """Settings speichern und laden"""
        settings = Settings(
            ollama=OllamaConfig(url="http://test:11434", model="test-model"),
            default_plz="4020"
        )

        # Speichern
        config_file = tmp_path / "config.json"
        settings.to_file(config_file)

        # Laden
        loaded = Settings.from_file(config_file)
        assert loaded.ollama.url == "http://test:11434"
        assert loaded.ollama.model == "test-model"
        assert loaded.default_plz == "4020"


class TestGetSettings:
    """Tests für get_settings Singleton"""

    def test_get_settings_returns_singleton(self):
        """get_settings gibt Singleton zurück"""
        reset_settings()  # Reset vor Test

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_reset_settings(self):
        """reset_settings erstellt neue Instanz"""
        reset_settings()

        settings1 = get_settings()
        reset_settings()
        settings2 = get_settings()

        assert settings1 is not settings2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])