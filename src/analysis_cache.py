"""
Analysis Cache
SQLite-basierter Cache für LLM-Analysen
Vermeidet wiederholte LLM-Calls für dieselbe Website
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict
from pathlib import Path


class AnalysisCache:
    """
    Cache für LLM-Analysen
    - Key: URL (normalisiert)
    - Value: Analyse-Ergebnis (JSON)
    - TTL: 30 Tage (konfigurierbar)
    """
    
    def __init__(self, db_path: str = "data/analysis_cache.db", ttl_days: int = 30):
        """
        Args:
            db_path: Pfad zur SQLite-Datenbank
            ttl_days: Time-to-live in Tagen
        """
        self.db_path = db_path
        self.ttl_days = ttl_days
        self._ensure_db()
    
    def _ensure_db(self):
        """Erstellt Datenbank und Tabelle falls nicht vorhanden"""
        # Verzeichnis erstellen falls nötig
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_cache (
                    url TEXT PRIMARY KEY,
                    company_name TEXT,
                    branch TEXT,
                    sub_branches TEXT,  -- JSON array
                    services TEXT,      -- JSON array
                    target_market TEXT,
                    company_size_hint TEXT,
                    keywords TEXT,      -- JSON array
                    confidence REAL,
                    reasoning TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index für schnellen Lookup
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_url 
                ON analysis_cache(url)
            """)
            
            conn.commit()
    
    def _normalize_url(self, url: str) -> str:
        """Normalisiert URL für konsistenten Cache-Key"""
        # https:// und trailing slashes entfernen
        url = url.lower().strip()
        if url.startswith('https://'):
            url = url[8:]
        elif url.startswith('http://'):
            url = url[7:]
        url = url.rstrip('/')
        return url
    
    def get(self, url: str) -> Optional[Dict]:
        """
        Holt Analyse aus Cache
        
        Args:
            url: Website-URL
            
        Returns:
            Analyse-Dict oder None (nicht gefunden oder abgelaufen)
        """
        normalized_url = self._normalize_url(url)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Prüfe ob Eintrag existiert und nicht abgelaufen
            cursor = conn.execute("""
                SELECT * FROM analysis_cache 
                WHERE url = ? 
                AND created_at > datetime('now', '-{} days')
            """.format(self.ttl_days), (normalized_url,))
            
            row = cursor.fetchone()
            
            if row:
                # Update accessed_at
                conn.execute("""
                    UPDATE analysis_cache 
                    SET accessed_at = CURRENT_TIMESTAMP 
                    WHERE url = ?
                """, (normalized_url,))
                conn.commit()
                
                return {
                    'url': row['url'],
                    'company_name': row['company_name'],
                    'branch': row['branch'],
                    'sub_branches': json.loads(row['sub_branches'] or '[]'),
                    'services': json.loads(row['services'] or '[]'),
                    'target_market': row['target_market'],
                    'company_size_hint': row['company_size_hint'],
                    'keywords': json.loads(row['keywords'] or '[]'),
                    'confidence': row['confidence'],
                    'reasoning': row['reasoning'],
                    'created_at': row['created_at'],
                    'cached': True
                }
            
            return None
    
    def set(self, url: str, analysis: Dict, company_name: str = None):
        """
        Speichert Analyse im Cache
        
        Args:
            url: Website-URL
            analysis: Analyse-Ergebnis (CompanyAnalysis.to_dict())
            company_name: Optionaler Unternehmensname
        """
        normalized_url = self._normalize_url(url)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO analysis_cache (
                    url, company_name, branch, sub_branches, services,
                    target_market, company_size_hint, keywords, confidence, reasoning
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                normalized_url,
                company_name or analysis.get('company_name', ''),
                analysis.get('branch', ''),
                json.dumps(analysis.get('sub_branches', [])),
                json.dumps(analysis.get('services', [])),
                analysis.get('target_market', ''),
                analysis.get('company_size_hint', ''),
                json.dumps(analysis.get('keywords', [])),
                analysis.get('confidence', 0.0),
                analysis.get('reasoning', '')
            ))
            conn.commit()
    
    def get_or_analyze(self, 
                       url: str, 
                       company_name: str,
                       analyzer_func) -> Dict:
        """
        Holt aus Cache oder führt Analyse durch
        
        Args:
            url: Website-URL
            company_name: Unternehmensname
            analyzer_func: Funktion die (company_name, content) -> analysis aufruft
            
        Returns:
            Analyse-Ergebnis (mit 'cached': True/False Flag)
        """
        # Zuerst Cache prüfen
        cached = self.get(url)
        if cached:
            cached['cached'] = True
            return cached
        
        # Analyse durchführen
        analysis = analyzer_func(company_name, url)
        
        if analysis:
            # Im Cache speichern
            self.set(url, analysis, company_name)
            analysis['cached'] = False
            return analysis
        
        return None
    
    def invalidate(self, url: str):
        """Löscht Eintrag aus Cache"""
        normalized_url = self._normalize_url(url)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM analysis_cache WHERE url = ?", (normalized_url,))
            conn.commit()
    
    def clear_expired(self) -> int:
        """
        Löscht abgelaufene Einträge
        
        Returns:
            Anzahl gelöschter Einträge
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM analysis_cache 
                WHERE created_at < datetime('now', '-{} days')
            """.format(self.ttl_days))
            conn.commit()
            return cursor.rowcount
    
    def get_stats(self) -> Dict:
        """
        Cache-Statistiken
        
        Returns:
            Dict mit Statistiken
        """
        with sqlite3.connect(self.db_path) as conn:
            # Gesamtanzahl
            cursor = conn.execute("SELECT COUNT(*) FROM analysis_cache")
            total = cursor.fetchone()[0]
            
            # Abgelaufen
            cursor = conn.execute("""
                SELECT COUNT(*) FROM analysis_cache 
                WHERE created_at < datetime('now', '-{} days')
            """.format(self.ttl_days))
            expired = cursor.fetchone()[0]
            
            # Durchschnittliche Confidence
            cursor = conn.execute("SELECT AVG(confidence) FROM analysis_cache")
            avg_confidence = cursor.fetchone()[0] or 0
            
            # Top Branchen
            cursor = conn.execute("""
                SELECT branch, COUNT(*) as count 
                FROM analysis_cache 
                GROUP BY branch 
                ORDER BY count DESC 
                LIMIT 5
            """)
            top_branches = {row[0]: row[1] for row in cursor.fetchall()}
            
            return {
                'total_entries': total,
                'expired_entries': expired,
                'valid_entries': total - expired,
                'avg_confidence': round(avg_confidence, 2),
                'top_branches': top_branches
            }
    
    def get_all(self, limit: int = 100) -> list:
        """
        Holt alle Cache-Einträge
        
        Args:
            limit: Maximale Anzahl
            
        Returns:
            Liste von Analyse-Dicts
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM analysis_cache 
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'url': row['url'],
                    'company_name': row['company_name'],
                    'branch': row['branch'],
                    'sub_branches': json.loads(row['sub_branches'] or '[]'),
                    'services': json.loads(row['services'] or '[]'),
                    'target_market': row['target_market'],
                    'company_size_hint': row['company_size_hint'],
                    'keywords': json.loads(row['keywords'] or '[]'),
                    'confidence': row['confidence'],
                    'reasoning': row['reasoning'],
                    'created_at': row['created_at']
                })
            
            return results


if __name__ == "__main__":
    print("=== Analysis Cache Test ===\n")
    
    # Test-Cache
    cache = AnalysisCache(db_path="data/test_cache.db", ttl_days=30)
    
    # Test-Daten
    test_url = "https://example-bau.at"
    test_analysis = {
        'branch': 'Bau',
        'sub_branches': ['Trockenbau', 'Renovierung'],
        'services': ['Neubau', 'Sanierung', 'Innenausbau'],
        'target_market': 'B2C',
        'company_size_hint': 'Mittel (6-50 MA)',
        'keywords': ['Bau', 'Renovierung', 'Niederösterreich'],
        'confidence': 0.92,
        'reasoning': 'Klare Bau-Branche aus Services und Keywords'
    }
    
    # Speichern
    print("Speichere Test-Daten...")
    cache.set(test_url, test_analysis, "Example Bau GmbH")
    
    # Abrufen
    print("\nLese aus Cache...")
    result = cache.get(test_url)
    if result:
        print(f"✅ Gefunden: {result['company_name']} ({result['branch']})")
        print(f"   Cached: {result.get('cached', False)}")
    
    # Stats
    print("\nCache-Statistiken:")
    stats = cache.get_stats()
    print(f"   Einträge: {stats['total_entries']}")
    print(f"   Ø Confidence: {stats['avg_confidence']}")
    
    # Cleanup
    print("\nLösche Test-Cache...")
    cache.invalidate(test_url)
    print("✅ Fertig")
