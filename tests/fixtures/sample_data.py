"""
Sample Data Fixtures für Tests
Wiederverwendbare Test-Daten
"""

from datetime import datetime
from typing import Dict, List, Any

# Sample Company
SAMPLE_COMPANY: Dict[str, Any] = {
    "name": "Test Firma GmbH",
    "address": {
        "street": "Teststraße 1",
        "plz": "2351",
        "ort": "Guntramsdorf",
        "bundesland": "Niederösterreich",
        "country": "Österreich"
    },
    "contact": {
        "telefon": "+43 2236 12345",
        "email": "info@testfirma.at",
        "website": "https://testfirma.at",
        "fax": "+43 2236 12346"
    },
    "branche": "IT-Dienstleistungen",
    "metadata": {
        "source": "firmen.wko.at",
        "source_url": "https://firmen.wko.at/testfirma",
        "crawled_at": "2026-03-21T12:00:00"
    }
}

# Sample Companies (Liste)
SAMPLE_COMPANIES: List[Dict[str, Any]] = [
    {
        "name": "Tech Solutions GmbH",
        "address": {"plz": "1010", "ort": "Wien", "bundesland": "Wien"},
        "contact": {"website": "https://techsolutions.at"},
        "branche": "IT"
    },
    {
        "name": "Bau Müller KG",
        "address": {"plz": "2351", "ort": "Guntramsdorf", "bundesland": "Niederösterreich"},
        "contact": {"telefon": "+43 2236 99999"},
        "branche": "Bau"
    },
    {
        "name": "Marketing Pro",
        "address": {"plz": "8010", "ort": "Graz", "bundesland": "Steiermark"},
        "contact": {"email": "info@marketingpro.at"},
        "branche": "Marketing"
    },
    {
        "name": "Handwerk Schmidt",
        "address": {"plz": "4020", "ort": "Linz", "bundesland": "Oberösterreich"},
        "contact": {"website": "https://handwerkschmidt.at"},
        "branche": "Handwerk"
    },
    {
        "name": "Consulting Group",
        "address": {"plz": "6020", "ort": "Innsbruck", "bundesland": "Tirol"},
        "contact": {"telefon": "+43 512 12345"},
        "branche": "Beratung"
    }
]

# Sample Analysis Result
SAMPLE_ANALYSIS: Dict[str, Any] = {
    "branch": "Softwareentwicklung",
    "confidence": 0.92,
    "services": [
        "Web Development",
        "Mobile Apps",
        "Cloud Solutions",
        "IT Consulting"
    ],
    "target_market": "KMU in Österreich",
    "company_size": "Mittel",
    "keywords": ["Software", "Digital", "IT", "Cloud"],
    "reasoning": "Basierend auf der Website-Analyse ist das Unternehmen in der Softwareentwicklung tätig..."
}

# Sample PLZ Data
SAMPLE_PLZ_DATA: List[Dict[str, Any]] = [
    {"plz": "1010", "ort": "Wien", "bundesland": "Wien", "lat": 48.2082, "lon": 16.3738},
    {"plz": "2351", "ort": "Guntramsdorf", "bundesland": "Niederösterreich", "lat": 48.0483, "lon": 16.3167},
    {"plz": "8010", "ort": "Graz", "bundesland": "Steiermark", "lat": 47.0707, "lon": 15.4395},
    {"plz": "4020", "ort": "Linz", "bundesland": "Oberösterreich", "lat": 48.3069, "lon": 14.2858},
    {"plz": "6020", "ort": "Innsbruck", "bundesland": "Tirol", "lat": 47.2692, "lon": 11.4041}
]

# Sample Cache Entry
SAMPLE_CACHE_ENTRY: Dict[str, Any] = {
    "url": "https://testfirma.at",
    "analysis": SAMPLE_ANALYSIS,
    "cached_at": "2026-03-21T12:00:00",
    "expires_at": "2026-04-20T12:00:00"
}

# Sample Crawler Result
SAMPLE_CRAWLER_RESULT: Dict[str, Any] = {
    "companies": SAMPLE_COMPANIES,
    "total": len(SAMPLE_COMPANIES),
    "source": "firmen.wko.at",
    "crawl_time": 12.5,
    "errors": []
}

# Sample Website Content
SAMPLE_WEBSITE_CONTENT: Dict[str, Any] = {
    "url": "https://testfirma.at",
    "title": "Test Firma GmbH - IT Lösungen",
    "meta_description": "Ihr Partner für IT-Lösungen in Österreich",
    "main_text": "Test Firma GmbH bietet professionelle IT-Dienstleistungen...",
    "about_text": "Über uns: Seit 2010 sind wir Ihr IT-Partner...",
    "services_text": "Unsere Services: Web Development, Mobile Apps, Cloud...",
    "contact_text": "Kontakt: +43 2236 12345, info@testfirma.at",
    "word_count": 500,
    "crawl_time": 1.2
}

# Sample Score Result
SAMPLE_SCORE_RESULT: Dict[str, Any] = {
    "total_score": 85,
    "percentage": 85.0,
    "grade": "A",
    "priority": "HIGH",
    "breakdown": {
        "has_website": 15,
        "has_email": 15,
        "has_phone": 10,
        "branch_relevance": 25,
        "location_match": 20
    }
}

# Sample LLM Response
SAMPLE_LLM_RESPONSE: str = """
Basierend auf der Analyse der Website:

Branche: Softwareentwicklung
Confidence: 0.92
Services: Web Development, Mobile Apps, Cloud Solutions, IT Consulting
Target Market: KMU in Österreich
Company Size: Mittel
Keywords: Software, Digital, IT, Cloud

Begründung: Das Unternehmen bietet Softwareentwicklung und IT-Dienstleistungen an.
"""

# Sample WKO HTML (für Crawler Tests)
SAMPLE_WKO_HTML: str = """
<html>
<body>
<div class="company-item">
    <h3 class="company-name">Test Firma GmbH</h3>
    <p class="address">Teststraße 1, 2351 Guntramsdorf</p>
    <p class="branch">IT-Dienstleistungen</p>
    <a class="website" href="https://testfirma.at">Website</a>
    <span class="phone">+43 2236 12345</span>
    <span class="email">info@testfirma.at</span>
</div>
</body>
</html>
"""

# Export-Fixtures
EXPORT_TEST_DATA: List[Dict[str, Any]] = [
    {
        "name": "Export Test 1",
        "plz": "1010",
        "ort": "Wien",
        "score_total": 85,
        "score_grade": "A"
    },
    {
        "name": "Export Test 2",
        "plz": "2351",
        "ort": "Guntramsdorf",
        "score_total": 65,
        "score_grade": "B"
    },
    {
        "name": "Export Test 3",
        "plz": "8010",
        "ort": "Graz",
        "score_total": 45,
        "score_grade": "C"
    }
]


def get_sample_company(name: str = None) -> Dict[str, Any]:
    """Gibt eine Sample Company zurück (optional mit angepasstem Namen)"""
    company = SAMPLE_COMPANY.copy()
    if name:
        company["name"] = name
    return company


def get_sample_companies(count: int = 5) -> List[Dict[str, Any]]:
    """Gibt eine Liste von Sample Companies zurück"""
    return SAMPLE_COMPANIES[:count]


def get_sample_plz_data() -> List[Dict[str, Any]]:
    """Gibt Sample PLZ-Daten zurück"""
    return SAMPLE_PLZ_DATA.copy()


__all__ = [
    'SAMPLE_COMPANY',
    'SAMPLE_COMPANIES',
    'SAMPLE_ANALYSIS',
    'SAMPLE_PLZ_DATA',
    'SAMPLE_CACHE_ENTRY',
    'SAMPLE_CRAWLER_RESULT',
    'SAMPLE_WEBSITE_CONTENT',
    'SAMPLE_SCORE_RESULT',
    'SAMPLE_LLM_RESPONSE',
    'SAMPLE_WKO_HTML',
    'EXPORT_TEST_DATA',
    'get_sample_company',
    'get_sample_companies',
    'get_sample_plz_data',
]