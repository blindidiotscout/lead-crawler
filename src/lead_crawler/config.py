"""
Lead Crawler Configuration
Zentrale Konfiguration für alle Komponenten
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class OllamaConfig:
    """Ollama LLM Konfiguration"""

    url: str = "http://192.168.178.123:11434"
    model: str = "qwen2.5:7b"
    embedding_model: str = "nomic-embed-text"
    timeout: int = 300  # Sekunden
    max_retries: int = 3
    retry_delay: float = 1.0  # Sekunden

    @classmethod
    def from_env(cls) -> "OllamaConfig":
        """Lädt Konfiguration aus Umgebungsvariablen"""
        return cls(
            url=os.getenv("OLLAMA_URL", "http://192.168.178.123:11434"),
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
            embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
            timeout=int(os.getenv("OLLAMA_TIMEOUT", "300")),
            max_retries=int(os.getenv("OLLAMA_MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("OLLAMA_RETRY_DELAY", "1.0")),
        )


@dataclass
class CacheConfig:
    """Cache Konfiguration"""

    db_path: Path = field(default_factory=lambda: Path("data/analysis_cache.db"))
    ttl_days: int = 30
    max_entries: int = 100000
    cleanup_interval_hours: int = 24

    @classmethod
    def from_env(cls) -> "CacheConfig":
        """Lädt Konfiguration aus Umgebungsvariablen"""
        return cls(
            db_path=Path(os.getenv("CACHE_DB_PATH", "data/analysis_cache.db")),
            ttl_days=int(os.getenv("CACHE_TTL_DAYS", "30")),
            max_entries=int(os.getenv("CACHE_MAX_ENTRIES", "100000")),
            cleanup_interval_hours=int(os.getenv("CACHE_CLEANUP_HOURS", "24")),
        )


@dataclass
class PLZConfig:
    """PLZ-Datenbank Konfiguration"""

    db_path: Path = field(default_factory=lambda: Path("data/plz_austria.db"))
    default_radius_km: float = 20.0
    max_radius_km: float = 100.0

    @classmethod
    def from_env(cls) -> "PLZConfig":
        """Lädt Konfiguration aus Umgebungsvariablen"""
        return cls(
            db_path=Path(os.getenv("PLZ_DB_PATH", "data/plz_austria.db")),
            default_radius_km=float(os.getenv("PLZ_DEFAULT_RADIUS", "20.0")),
            max_radius_km=float(os.getenv("PLZ_MAX_RADIUS", "100.0")),
        )


@dataclass
class CrawlerConfig:
    """Crawler Konfiguration"""

    user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    rate_limit: float = 2.0  # Sekunden zwischen Requests
    concurrent_requests: int = 1
    timeout: int = 30  # Sekunden
    respect_robots_txt: bool = True
    max_retries: int = 3
    retry_delay: float = 5.0

    # WKO-spezifisch
    wko_base_url: str = "https://firmen.wko.at"
    wko_timeout: int = 30

    # Website-Crawler
    website_timeout: int = 15
    website_max_words: int = 800
    website_delay: float = 1.0

    @classmethod
    def from_env(cls) -> "CrawlerConfig":
        """Lädt Konfiguration aus Umgebungsvariablen"""
        return cls(
            user_agent=os.getenv(
                "CRAWLER_USER_AGENT", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            ),
            rate_limit=float(os.getenv("CRAWLER_RATE_LIMIT", "2.0")),
            concurrent_requests=int(os.getenv("CRAWLER_CONCURRENT", "1")),
            timeout=int(os.getenv("CRAWLER_TIMEOUT", "30")),
            respect_robots_txt=os.getenv("CRAWLER_RESPECT_ROBOTS", "true").lower() == "true",
            max_retries=int(os.getenv("CRAWLER_MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("CRAWLER_RETRY_DELAY", "5.0")),
            wko_base_url=os.getenv("WKO_BASE_URL", "https://firmen.wko.at"),
            wko_timeout=int(os.getenv("WKO_TIMEOUT", "30")),
            website_timeout=int(os.getenv("WEBSITE_TIMEOUT", "15")),
            website_max_words=int(os.getenv("WEBSITE_MAX_WORDS", "800")),
            website_delay=float(os.getenv("WEBSITE_DELAY", "1.0")),
        )


@dataclass
class ScoringConfig:
    """Scoring Konfiguration"""

    # Gewichtungen (Summe = 100)
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "contact": 25.0,  # Email, Telefon, Website
            "location": 20.0,  # Distanz
            "branch": 20.0,  # Branchen-Relevanz
            "completeness": 15.0,  # Datenvollständigkeit
            "freshness": 10.0,  # Aktualität
            "size": 10.0,  # Unternehmensgröße
        }
    )

    # Grade-Schwellenwerte
    grade_thresholds: dict[str, float] = field(
        default_factory=lambda: {
            "A": 80.0,  # >= 80%
            "B": 60.0,  # >= 60%
            "C": 40.0,  # >= 40%
            "D": 20.0,  # >= 20%
            # F: < 20%
        }
    )

    # Prioritäts-Schwellenwerte
    priority_thresholds: dict[str, dict[str, float]] = field(
        default_factory=lambda: {
            "HIGH": {"score": 70.0, "contact": 15.0},
            "MEDIUM": {"score": 50.0, "contact": 10.0},
            # LOW: alles andere
        }
    )

    @classmethod
    def from_env(cls) -> "ScoringConfig":
        """Lädt Konfiguration aus Umgebungsvariablen (optional)"""
        # Für Scoring sind Defaults meist ausreichend
        return cls()


@dataclass
class APIConfig:
    """API Server Konfiguration"""

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    api_key_header: str = "X-API-Key"
    api_keys: list[str] = field(default_factory=list)
    cors_origins: list[str] = field(default_factory=lambda: ["*"])

    @classmethod
    def from_env(cls) -> "APIConfig":
        """Lädt Konfiguration aus Umgebungsvariablen"""
        api_keys = []
        keys_env = os.getenv("API_KEYS", "")
        if keys_env:
            api_keys = [k.strip() for k in keys_env.split(",") if k.strip()]

        cors_origins = ["*"]
        cors_env = os.getenv("CORS_ORIGINS", "")
        if cors_env:
            cors_origins = [o.strip() for o in cors_env.split(",") if o.strip()]

        return cls(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            debug=os.getenv("API_DEBUG", "false").lower() == "true",
            api_key_header=os.getenv("API_KEY_HEADER", "X-API-Key"),
            api_keys=api_keys,
            cors_origins=cors_origins,
        )


@dataclass
class Settings:
    """
    Haupt-Konfigurationsklasse

    Vereinigt alle Sub-Konfigurationen und stellt Factory-Methoden bereit.
    """

    # Sub-Konfigurationen
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    plz: PLZConfig = field(default_factory=PLZConfig)
    crawler: CrawlerConfig = field(default_factory=CrawlerConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    api: APIConfig = field(default_factory=APIConfig)

    # Projekt-Pfade
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent)
    data_dir: Path = field(default_factory=lambda: Path("data"))
    output_dir: Path = field(default_factory=lambda: Path("output"))

    # Default-Werte
    default_plz: str = "2351"  # Guntramsdorf
    default_radius_km: float = 20.0

    @classmethod
    def from_env(cls) -> "Settings":
        """Lädt alle Konfigurationen aus Umgebungsvariablen"""
        project_root = Path(__file__).parent.parent.parent

        return cls(
            ollama=OllamaConfig.from_env(),
            cache=CacheConfig.from_env(),
            plz=PLZConfig.from_env(),
            crawler=CrawlerConfig.from_env(),
            scoring=ScoringConfig.from_env(),
            api=APIConfig.from_env(),
            project_root=project_root,
            data_dir=Path(os.getenv("DATA_DIR", str(project_root / "data"))),
            output_dir=Path(os.getenv("OUTPUT_DIR", str(project_root / "output"))),
            default_plz=os.getenv("DEFAULT_PLZ", "2351"),
            default_radius_km=float(os.getenv("DEFAULT_RADIUS", "20.0")),
        )

    @classmethod
    def from_file(cls, path: Path) -> "Settings":
        """Lädt Konfiguration aus JSON-Datei"""
        with open(path) as f:
            data = json.load(f)

        # Scoring Config braucht Sonderbehandlung wegen weights dict
        scoring_data = data.get("scoring", {})
        scoring_config = ScoringConfig()
        if scoring_data:
            scoring_config.weights = scoring_data.get("weights", scoring_config.weights)
            scoring_config.grade_thresholds = scoring_data.get(
                "grade_thresholds", scoring_config.grade_thresholds
            )
            scoring_config.priority_thresholds = scoring_data.get(
                "priority_thresholds", scoring_config.priority_thresholds
            )

        return cls(
            ollama=OllamaConfig(**data.get("ollama", {})),
            cache=CacheConfig(**data.get("cache", {})),
            plz=PLZConfig(**data.get("plz", {})),
            crawler=CrawlerConfig(**data.get("crawler", {})),
            scoring=scoring_config,
            api=APIConfig(**data.get("api", {})),
            project_root=Path(data.get("project_root", str(Path(__file__).parent.parent.parent))),
            data_dir=Path(data.get("data_dir", "data")),
            output_dir=Path(data.get("output_dir", "output")),
            default_plz=data.get("default_plz", "2351"),
            default_radius_km=data.get("default_radius_km", 20.0),
        )

    def to_file(self, path: Path) -> None:
        """Speichert Konfiguration in JSON-Datei"""
        data = {
            "ollama": {
                "url": self.ollama.url,
                "model": self.ollama.model,
                "embedding_model": self.ollama.embedding_model,
                "timeout": self.ollama.timeout,
                "max_retries": self.ollama.max_retries,
                "retry_delay": self.ollama.retry_delay,
            },
            "cache": {
                "db_path": str(self.cache.db_path),
                "ttl_days": self.cache.ttl_days,
                "max_entries": self.cache.max_entries,
                "cleanup_interval_hours": self.cache.cleanup_interval_hours,
            },
            "plz": {
                "db_path": str(self.plz.db_path),
                "default_radius_km": self.plz.default_radius_km,
                "max_radius_km": self.plz.max_radius_km,
            },
            "crawler": {
                "user_agent": self.crawler.user_agent,
                "rate_limit": self.crawler.rate_limit,
                "concurrent_requests": self.crawler.concurrent_requests,
                "timeout": self.crawler.timeout,
                "respect_robots_txt": self.crawler.respect_robots_txt,
            },
            "scoring": {
                "weights": self.scoring.weights,
                "grade_thresholds": self.scoring.grade_thresholds,
                "priority_thresholds": self.scoring.priority_thresholds,
            },
            "api": {
                "host": self.api.host,
                "port": self.api.port,
                "debug": self.api.debug,
                "api_key_header": self.api.api_key_header,
                "cors_origins": self.api.cors_origins,
            },
            "project_root": str(self.project_root),
            "data_dir": str(self.data_dir),
            "output_dir": str(self.output_dir),
            "default_plz": self.default_plz,
            "default_radius_km": self.default_radius_km,
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def ensure_directories(self) -> None:
        """Stellt sicher, dass alle Verzeichnisse existieren"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def resolve_path(self, path: Path | str) -> Path:
        """Löst einen Pfad relativ zum Projekt-Root auf"""
        p = Path(path)
        if p.is_absolute():
            return p
        return self.project_root / p


# Global Settings Instance (Lazy)
_settings: Settings | None = None


def get_settings() -> Settings:
    """
    Gibt die globalen Settings zurück (Singleton Pattern)

    Lädt beim ersten Aufruf aus Umgebungsvariablen.

    Returns:
        Settings Instanz
    """
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def reset_settings() -> None:
    """Setzt die globalen Settings zurück (für Tests)"""
    global _settings
    _settings = None
