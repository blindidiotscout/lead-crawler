"""
Cache Service
SQLite-basierter Cache für LLM-Analysen und andere Daten
"""

import sqlite3
import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Protocol
from pathlib import Path
from dataclasses import dataclass

from lead_crawler.config import get_settings, CacheConfig
from lead_crawler.models.analysis import BranchAnalysis, CacheEntry


class CacheService(Protocol):
    """
    Protocol für Cache-Service
    Definiert die Schnittstelle für alle Cache-Implementierungen
    """

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Holt Wert aus Cache"""
        ...

    def set(self, key: str, value: Dict[str, Any], ttl_seconds: Optional[int] = None) -> None:
        """Setzt Wert im Cache"""
        ...

    def delete(self, key: str) -> bool:
        """Löscht Eintrag aus Cache"""
        ...

    def exists(self, key: str) -> bool:
        """Prüft ob Key existiert"""
        ...

    def clear(self) -> int:
        """Löscht alle Einträge, gibt Anzahl zurück"""
        ...

    def get_stats(self) -> Dict[str, Any]:
        """Gibt Cache-Statistiken zurück"""
        ...


class SQLiteCache:
    """
    SQLite-basierter Cache für LLM-Analysen

    Features:
    - TTL (Time-to-Live) für Einträge
    - Automatische Bereinigung abgelaufener Einträge
    - Statistiken und Metriken
    - Thread-safe via SQLite

    Usage:
        cache = SQLiteCache()
        cache.set("https://example.com", {"branch": "IT", "confidence": 0.9})
        result = cache.get("https://example.com")
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialisiert Cache

        Args:
            config: CacheConfig (default: aus get_settings())
        """
        if config is None:
            config = get_settings().cache

        self.db_path = Path(config.db_path)
        self.ttl_days = config.ttl_days
        self.max_entries = config.max_entries

        self._ensure_db()

    def _ensure_db(self) -> None:
        """Erstellt Datenbank und Tabellen falls nicht vorhanden"""
        # Verzeichnis erstellen
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(str(self.db_path)) as conn:
            # Haupt-Cache-Tabelle
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    metadata TEXT
                )
            """)

            # Index für schnellen Lookup
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_key ON cache_entries(key)
            """)

            # Index für Cleanup
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires ON cache_entries(expires_at)
            """)

            conn.commit()

    def _normalize_key(self, key: str) -> str:
        """Normalisiert Key für konsistenten Cache-Lookup"""
        # URLs normalisieren
        key = key.lower().strip()
        if key.startswith('https://'):
            key = key[8:]
        elif key.startswith('http://'):
            key = key[7:]
        key = key.rstrip('/')
        return key

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Holt Wert aus Cache

        Args:
            key: Cache-Key (z.B. URL)

        Returns:
            Cached Dict oder None (nicht gefunden oder abgelaufen)
        """
        normalized_key = self._normalize_key(key)

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            # Prüfe ob Eintrag existiert und nicht abgelaufen
            cursor = conn.execute("""
                SELECT value, created_at, accessed_at, expires_at, metadata
                FROM cache_entries
                WHERE key = ?
                AND (expires_at IS NULL OR expires_at > datetime('now'))
            """, (normalized_key,))

            row = cursor.fetchone()

            if row:
                # Update accessed_at
                conn.execute("""
                    UPDATE cache_entries
                    SET accessed_at = CURRENT_TIMESTAMP
                    WHERE key = ?
                """, (normalized_key,))
                conn.commit()

                value = json.loads(row['value'])
                value['_cached'] = True
                value['_cached_at'] = row['created_at']
                return value

            return None

    def set(self, key: str, value: Dict[str, Any],
            ttl_seconds: Optional[int] = None,
            metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Speichert Wert im Cache

        Args:
            key: Cache-Key
            value: Zu speicherndes Dict
            ttl_seconds: Optional TTL in Sekunden (default: aus Config)
            metadata: Optional Metadaten
        """
        normalized_key = self._normalize_key(key)

        # TTL berechnen
        if ttl_seconds is None:
            ttl_seconds = self.ttl_days * 24 * 60 * 60

        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

        # Value ohne interne Felder speichern
        clean_value = {k: v for k, v in value.items() if not k.startswith('_')}

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cache_entries (
                    key, value, created_at, accessed_at, expires_at, metadata
                ) VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?, ?)
            """, (
                normalized_key,
                json.dumps(clean_value),
                expires_at.isoformat() if ttl_seconds else None,
                json.dumps(metadata) if metadata else None
            ))
            conn.commit()

    def delete(self, key: str) -> bool:
        """
        Löscht Eintrag aus Cache

        Args:
            key: Cache-Key

        Returns:
            True wenn gelöscht, False wenn nicht gefunden
        """
        normalized_key = self._normalize_key(key)

        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "DELETE FROM cache_entries WHERE key = ?",
                (normalized_key,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def exists(self, key: str) -> bool:
        """Prüft ob Key im Cache existiert (und nicht abgelaufen ist)"""
        return self.get(key) is not None

    def clear(self) -> int:
        """
        Löscht alle Einträge

        Returns:
            Anzahl gelöschter Einträge
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("DELETE FROM cache_entries")
            conn.commit()
            return cursor.rowcount

    def clear_expired(self) -> int:
        """
        Löscht abgelaufene Einträge

        Returns:
            Anzahl gelöschter Einträge
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("""
                DELETE FROM cache_entries
                WHERE expires_at IS NOT NULL
                AND expires_at < datetime('now')
            """)
            conn.commit()
            return cursor.rowcount

    def get_stats(self) -> Dict[str, Any]:
        """
        Cache-Statistiken

        Returns:
            Dict mit total, valid, expired, avg_confidence, etc.
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            # Gesamtanzahl
            cursor = conn.execute("SELECT COUNT(*) FROM cache_entries")
            total = cursor.fetchone()[0]

            # Abgelaufen
            cursor = conn.execute("""
                SELECT COUNT(*) FROM cache_entries
                WHERE expires_at IS NOT NULL
                AND expires_at < datetime('now')
            """)
            expired = cursor.fetchone()[0]

            # Valid
            valid = total - expired

            # Durchschnittliche Confidence (falls vorhanden)
            cursor = conn.execute("""
                SELECT AVG(CAST(json_extract(value, '$.confidence') AS REAL))
                FROM cache_entries
                WHERE json_extract(value, '$.confidence') IS NOT NULL
            """)
            avg_confidence = cursor.fetchone()[0] or 0.0

            # Top Branchen (falls vorhanden)
            cursor = conn.execute("""
                SELECT json_extract(value, '$.branch') as branch, COUNT(*) as count
                FROM cache_entries
                WHERE json_extract(value, '$.branch') IS NOT NULL
                GROUP BY branch
                ORDER BY count DESC
                LIMIT 5
            """)
            top_branches = {row[0]: row[1] for row in cursor.fetchall() if row[0]}

            return {
                'total_entries': total,
                'expired_entries': expired,
                'valid_entries': valid,
                'avg_confidence': round(avg_confidence, 2),
                'top_branches': top_branches,
                'db_path': str(self.db_path),
                'ttl_days': self.ttl_days,
                'max_entries': self.max_entries
            }

    def get_all_keys(self, limit: int = 100) -> List[str]:
        """
        Holt alle Cache-Keys

        Args:
            limit: Maximale Anzahl

        Returns:
            Liste von Keys
        """
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "SELECT key FROM cache_entries ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            return [row[0] for row in cursor.fetchall()]

    def get_many(self, keys: List[str]) -> Dict[str, Optional[Dict]]:
        """
        Holt mehrere Werte gleichzeitig

        Args:
            keys: Liste von Cache-Keys

        Returns:
            Dict mit key -> value Mapping
        """
        return {key: self.get(key) for key in keys}

    def set_many(self, items: Dict[str, Dict],
                 ttl_seconds: Optional[int] = None) -> None:
        """
        Setzt mehrere Werte gleichzeitig

        Args:
            items: Dict mit key -> value Mapping
            ttl_seconds: Optional TTL
        """
        for key, value in items.items():
            self.set(key, value, ttl_seconds=ttl_seconds)

    # Legacy-Kompatibilität für LLM-Analysen

    def get_analysis(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Holt LLM-Analyse aus Cache (Legacy-Methode)

        Args:
            url: Website-URL

        Returns:
            Analyse-Dict oder None
        """
        result = self.get(url)
        if result:
            result['cached'] = True
        return result

    def set_analysis(self, url: str, analysis: Dict[str, Any],
                     company_name: Optional[str] = None) -> None:
        """
        Speichert LLM-Analyse im Cache (Legacy-Methode)

        Args:
            url: Website-URL
            analysis: Analyse-Ergebnis
            company_name: Optionaler Unternehmensname
        """
        if company_name:
            analysis['company_name'] = company_name
        self.set(url, analysis)

    def invalidate(self, key: str) -> bool:
        """Alias für delete() (Legacy-Kompatibilität)"""
        return self.delete(key)


# Singleton-Instanz (Lazy)
_cache_instance: Optional[SQLiteCache] = None


def get_cache() -> SQLiteCache:
    """
    Gibt die globale Cache-Instanz zurück (Singleton Pattern)

    Returns:
        SQLiteCache Instanz
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SQLiteCache()
    return _cache_instance


def reset_cache() -> None:
    """Setzt die globale Cache-Instanz zurück (für Tests)"""
    global _cache_instance
    _cache_instance = None