# Lead Crawler Configuration

# Supabase Connection
SUPABASE_URL = "http://192.168.178.100:8000"  # Deine lokale Supabase-VM
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyAgCiAgICAicm9sZSI6ICJhbm9uIiwKICAgICJpc3MiOiAic3VwYWJhc2UtZGVtbyIsCiAgICAiaWF0IjogMTY0MTc2OTIwMCwKICAgICJleHAiOiAxNzk5NTM1NjAwCn0.dc_X5iR_VP_qT0zsiyj_I_OZ2T9FtRU2BBNWN8Bu4GE"  #Aus Supabase Dashboard anon Key

# Ollama Endpoint
OLLAMA_HOST = "http://192.168.178.123:11434"
OLLAMA_MODEL = "qwen3.5:397b-cloud"
EMBEDDING_MODEL = "qwen3-embedding:4b"

# Qdrant Vector Store
QDRANT_HOST = "http://192.168.178.123:6333"
QDRANT_COLLECTION = "lead_crawler"

# Crawler Settings
CRAWLER_RATE_LIMIT = 1.0  # Requests pro Sekunde
CRAWLER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
CRAWLER_ROBOTS_TXT = True  # robots.txt einhalten

# API Settings
API_PORT = 8000
API_HOST = "0.0.0.0"
API_KEY_HEADER = "X-API-Key"

# Default Values
DEFAULT_PLZ = "2351"  # Guntramsdorf
DEFAULT_RADIUS_KM = 50

# Branches (für Checkbox-UI)
BRANCHES = [
    "Rechtsanwaltskanzleien",
    "Pharma-Dienstleister",
    "Medizinprodukte",
    "Healthcare",
    "Treuhand/Steuerberatung",
    "Industrie/Fertigung",
    "Logistik",
    "IT/Software",
    "Immobilien",
    "Finanzdienstleister",
]
