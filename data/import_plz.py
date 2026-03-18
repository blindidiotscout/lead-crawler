#!/usr/bin/env python3
"""
Import Austrian PLZ data from CSV into SQLite database
Source: https://github.com/zauberware/postal-codes-json-xml-csv
"""

import csv
import sqlite3
from pathlib import Path
from datetime import datetime


# Bundesland mapping (state_code → name)
STATE_CODE_MAP = {
    "01": "Burgenland",
    "02": "Kärnten",
    "03": "Niederösterreich",
    "04": "Oberösterreich",
    "05": "Salzburg",
    "06": "Steiermark",
    "07": "Tirol",
    "08": "Vorarlberg",
    "09": "Wien",
}


def create_database(db_path: str):
    """Create PLZ database with optimized schema"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Drop existing table to start fresh
    cursor.execute("DROP TABLE IF EXISTS plz_coordinates")
    
    # Create optimized table
    cursor.execute("""
        CREATE TABLE plz_coordinates (
            plz TEXT NOT NULL,
            ort TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            bundesland TEXT NOT NULL,
            bundesland_code TEXT,
            bezirk TEXT,
            bezirk_code TEXT,
            gemeinde TEXT,
            gemeinde_code TEXT,
            PRIMARY KEY (plz, ort)
        )
    """)
    
    # Create indexes for fast lookups
    cursor.execute("CREATE INDEX idx_plz ON plz_coordinates(plz)")
    cursor.execute("CREATE INDEX idx_bundesland ON plz_coordinates(bundesland)")
    cursor.execute("CREATE INDEX idx_ort ON plz_coordinates(ort)")
    
    conn.commit()
    return conn


def import_csv(csv_path: str, db_path: str):
    """Import CSV data into SQLite database"""
    
    conn = create_database(db_path)
    cursor = conn.cursor()
    
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"❌ CSV file not found: {csv_path}")
        return
    
    print(f"📥 Importiere {csv_path}...")
    
    imported = 0
    duplicates = 0
    errors = 0
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                plz = row['zipcode']
                ort = row['place']
                lat = float(row['latitude'])
                lon = float(row['longitude'])
                bundesland_code = row['state_code']
                bundesland = STATE_CODE_MAP.get(bundesland_code, row['state'])
                bezirk = row['province']
                bezirk_code = row['province_code']
                gemeinde = row['community']
                gemeinde_code = row['community_code']
                
                cursor.execute("""
                    INSERT OR IGNORE INTO plz_coordinates 
                    (plz, ort, lat, lon, bundesland, bundesland_code, bezirk, bezirk_code, gemeinde, gemeinde_code)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (plz, ort, lat, lon, bundesland, bundesland_code, bezirk, bezirk_code, gemeinde, gemeinde_code))
                
                if cursor.rowcount == 0:
                    duplicates += 1
                else:
                    imported += 1
                    
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"⚠️ Error bei Zeile: {row.get('zipcode', 'unknown')}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Import abgeschlossen:")
    print(f"   Importiert: {imported:,}")
    print(f"   Duplikate übersprungen: {duplicates:,}")
    print(f"   Fehler: {errors:,}")
    print(f"   Gesamt: {imported + duplicates:,}")
    
    return imported


def verify_database(db_path: str):
    """Verify imported data"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Count total
    cursor.execute("SELECT COUNT(*) FROM plz_coordinates")
    total = cursor.fetchone()[0]
    
    # Count by Bundesland
    cursor.execute("""
        SELECT bundesland, COUNT(*) as cnt 
        FROM plz_coordinates 
        GROUP BY bundesland 
        ORDER BY cnt DESC
    """)
    by_state = cursor.fetchall()
    
    # Count unique PLZ
    cursor.execute("SELECT COUNT(DISTINCT plz) FROM plz_coordinates")
    unique_plz = cursor.fetchone()[0]
    
    # Sample entries
    cursor.execute("""
        SELECT plz, ort, bundesland, lat, lon 
        FROM plz_coordinates 
        WHERE plz = '2351'
        LIMIT 5
    """)
    sample = cursor.fetchall()
    
    conn.close()
    
    print(f"\n📊 Datenbank-Statistik:")
    print(f"   Einträge gesamt: {total:,}")
    print(f"   Einzigartige PLZ: {unique_plz:,}")
    print(f"\n   Nach Bundesland:")
    for state, count in by_state:
        print(f"   {state:20} {count:>6,}")
    
    print(f"\n   Beispiel (PLZ 2351 - Guntramsdorf):")
    for plz, ort, bundesland, lat, lon in sample:
        print(f"   {plz} {ort:30} {bundesland:15} ({lat}, {lon})")


if __name__ == "__main__":
    db_path = Path(__file__).parent / "plz_austria.db"
    csv_path = Path(__file__).parent / "zipcodes.at.csv"
    
    print(f"🚀 Starte PLZ-Import...")
    print(f"   CSV: {csv_path}")
    print(f"   DB: {db_path}")
    print()
    
    start_time = datetime.now()
    imported = import_csv(str(csv_path), str(db_path))
    elapsed = datetime.now() - start_time
    
    print(f"\n⏱️ Dauer: {elapsed.total_seconds():.2f}s")
    
    verify_database(str(db_path))