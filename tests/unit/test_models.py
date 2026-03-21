"""
Unit Tests für Domain Models
"""

import sys
from pathlib import Path

# Add src directory to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import pytest
from datetime import datetime

from lead_crawler.models import (
    Company,
    Address,
    ContactInfo,
    CompanyMetadata,
    CompanySource,
    BranchAnalysis,
    LLMAnalysisResult,
    LeadScore,
    ScoreBreakdown,
    PLZCoordinate,
    PLZInfo,
    PLZSearchResult,
    Bundesland,
    plz_to_bundesland,
    is_valid_plz,
)


class TestAddress:
    """Tests für Address Model"""

    def test_create_address(self):
        """Address erstellen"""
        addr = Address(
            street="Hauptstraße 1",
            plz="2351",
            ort="Guntramsdorf",
            bundesland="Niederösterreich"
        )
        assert addr.street == "Hauptstraße 1"
        assert addr.plz == "2351"
        assert addr.ort == "Guntramsdorf"

    def test_address_from_dict(self):
        """Address aus Dictionary erstellen"""
        data = {
            "street": "Teststraße 5",
            "plz": "1010",
            "ort": "Wien",
            "bundesland": "Wien"
        }
        addr = Address.from_dict(data)
        assert addr.street == "Teststraße 5"
        assert addr.plz == "1010"
        assert addr.ort == "Wien"

    def test_address_str(self):
        """Address String-Repräsentation"""
        addr = Address(street="Test 1", plz="2351", ort="Guntramsdorf")
        assert "Test 1" in str(addr)
        assert "2351" in str(addr)
        assert "Guntramsdorf" in str(addr)


class TestContactInfo:
    """Tests für ContactInfo Model"""

    def test_create_contact_info(self):
        """ContactInfo erstellen"""
        contact = ContactInfo(
            telefon="+43 123 456",
            email="test@example.com",
            website="https://example.com"
        )
        assert contact.telefon == "+43 123 456"
        assert contact.email == "test@example.com"

    def test_contact_score(self):
        """Contact-Qualitäts-Score"""
        # Alles vorhanden
        contact_full = ContactInfo(
            telefon="+43 123",
            email="test@example.com",
            website="https://example.com"
        )
        assert contact_full.contact_score == 25.0

        # Nur Email
        contact_email = ContactInfo(email="test@example.com")
        assert contact_email.contact_score == 10.0

        # Nichts
        contact_empty = ContactInfo()
        assert contact_empty.contact_score == 0.0

    def test_has_contact(self):
        """Prüft ob Kontakt vorhanden"""
        assert ContactInfo(email="test").has_contact is True
        assert ContactInfo().has_contact is False


class TestCompany:
    """Tests für Company Model"""

    def test_create_company(self):
        """Company erstellen"""
        company = Company(name="Test GmbH")
        assert company.name == "Test GmbH"
        assert company.address.plz is None
        assert company.contact.email is None

    def test_company_from_dict(self):
        """Company aus Dictionary (WKO-Format)"""
        data = {
            "name": "AKRAS Flavours GmbH",
            "street": "IZ-NÖ-SÜD Straße 1",
            "plz": "2351",
            "ort": "Biedermannsdorf",
            "bundesland": "Niederösterreich",
            "telefon": "+43 123 456",
            "email": "info@akras.at",
            "website": "https://www.akras.at",
            "source": "firmen.wko.at"
        }

        company = Company.from_dict(data)
        assert company.name == "AKRAS Flavours GmbH"
        assert company.address.plz == "2351"
        assert company.address.ort == "Biedermannsdorf"
        assert company.contact.email == "info@akras.at"
        assert company.contact.website == "https://www.akras.at"
        assert company.metadata.source == CompanySource.WKO

    def test_company_to_dict(self):
        """Company zu Dictionary"""
        company = Company(
            name="Test GmbH",
            address=Address(plz="2351", ort="Guntramsdorf"),
            contact=ContactInfo(email="test@example.com")
        )
        data = company.to_dict()
        assert data["name"] == "Test GmbH"
        assert data["plz"] == "2351"
        assert data["email"] == "test@example.com"

    def test_company_str(self):
        """Company String-Repräsentation"""
        company = Company(
            name="Test GmbH",
            address=Address(plz="2351", ort="Guntramsdorf")
        )
        assert "Test GmbH" in str(company)
        assert "2351" in str(company)


class TestBranchAnalysis:
    """Tests für BranchAnalysis Model"""

    def test_create_analysis(self):
        """BranchAnalysis erstellen"""
        analysis = BranchAnalysis(
            branch="Industrie/Fertigung",
            confidence=0.85,
            services=["Produktion", "Beratung"]
        )
        assert analysis.branch == "Industrie/Fertigung"
        assert analysis.confidence == 0.85
        assert len(analysis.services) == 2

    def test_confidence_helpers(self):
        """Confidence-Helper Methoden"""
        high = BranchAnalysis(branch="Test", confidence=0.9)
        medium = BranchAnalysis(branch="Test", confidence=0.6)
        low = BranchAnalysis(branch="Test", confidence=0.3)

        assert high.is_high_confidence is True
        assert medium.is_medium_confidence is True
        assert low.is_low_confidence is True

    def test_analysis_to_dict(self):
        """Analysis zu Dictionary"""
        analysis = BranchAnalysis(
            branch="IT",
            services=["Entwicklung", "Beratung"],
            confidence=0.75
        )
        data = analysis.to_dict()
        assert data["branch"] == "IT"
        assert "Entwicklung" in data["services"]
        assert data["confidence"] == 0.75


class TestLLMAnalysisResult:
    """Tests für LLMAnalysisResult Model"""

    def test_create_result(self):
        """LLMAnalysisResult erstellen"""
        result = LLMAnalysisResult(
            company_name="Test GmbH",
            website_url="https://example.com",
            analysis=BranchAnalysis(branch="IT", confidence=0.8),
            cached=False
        )
        assert result.company_name == "Test GmbH"
        assert result.is_successful is True
        assert result.is_cached is False

    def test_cached_result(self):
        """Cached Result"""
        result = LLMAnalysisResult(
            company_name="Test",
            analysis=BranchAnalysis(branch="Test"),
            cached=True
        )
        assert result.is_cached is True

    def test_error_result(self):
        """Result mit Error"""
        result = LLMAnalysisResult(
            company_name="Test",
            error="Crawl fehlgeschlagen"
        )
        assert result.is_successful is False
        assert result.analysis is None


class TestScoreBreakdown:
    """Tests für ScoreBreakdown Model"""

    def test_create_breakdown(self):
        """ScoreBreakdown erstellen"""
        breakdown = ScoreBreakdown(
            contact=20.0,
            location=15.0,
            branch=18.0,
            completeness=12.0,
            freshness=8.0,
            size=7.0
        )
        assert breakdown.contact == 20.0
        assert breakdown.total == 80.0
        assert breakdown.percentage == 80.0

    def test_breakdown_from_dict(self):
        """ScoreBreakdown aus Dictionary"""
        data = {
            "contact": 15.0,
            "location": 10.0,
            "branch": 18.0,
            "completeness": 10.0,
            "freshness": 5.0,
            "size": 5.0
        }
        breakdown = ScoreBreakdown.from_dict(data)
        assert breakdown.total == 63.0

    def test_weakest_category(self):
        """Schwächste Kategorie finden"""
        breakdown = ScoreBreakdown(
            contact=20.0,
            location=5.0,  # Schwächste
            branch=18.0,
            completeness=12.0,
            freshness=8.0,
            size=7.0
        )
        assert breakdown.get_weakest_category() == "location"

    def test_strongest_category(self):
        """Stärkste Kategorie finden"""
        breakdown = ScoreBreakdown(
            contact=25.0,  # Stärkste
            location=10.0,
            branch=18.0,
            completeness=12.0,
            freshness=8.0,
            size=5.0
        )
        assert breakdown.get_strongest_category() == "contact"


class TestLeadScore:
    """Tests für LeadScore Model"""

    def test_create_score(self):
        """LeadScore erstellen"""
        score = LeadScore(
            name="Test GmbH",
            total_score=75.0,
            breakdown=ScoreBreakdown(contact=20.0, location=15.0, branch=15.0,
                                     completeness=12.0, freshness=8.0, size=5.0),
            percentage=75.0,
            grade="B",
            priority="MEDIUM"
        )
        assert score.name == "Test GmbH"
        assert score.grade == "B"
        assert score.priority == "MEDIUM"

    def test_grade_calculation(self):
        """Grade berechnen"""
        assert LeadScore.calculate_grade(85) == "A"
        assert LeadScore.calculate_grade(75) == "B"
        assert LeadScore.calculate_grade(55) == "C"
        assert LeadScore.calculate_grade(30) == "D"
        assert LeadScore.calculate_grade(10) == "F"

    def test_priority_calculation(self):
        """Priority berechnen"""
        # HIGH: >= 70% und contact >= 15
        breakdown_high = ScoreBreakdown(contact=18.0, location=18.0, branch=18.0,
                                        completeness=12.0, freshness=10.0, size=10.0)
        assert LeadScore.calculate_priority(86.0, breakdown_high) == "HIGH"

        # MEDIUM: >= 50% und contact >= 10
        breakdown_medium = ScoreBreakdown(contact=12.0, location=10.0, branch=10.0,
                                         completeness=8.0, freshness=5.0, size=5.0)
        assert LeadScore.calculate_priority(50.0, breakdown_medium) == "MEDIUM"

        # LOW: Rest
        breakdown_low = ScoreBreakdown(contact=5.0, location=5.0, branch=5.0,
                                      completeness=3.0, freshness=2.0, size=0.0)
        assert LeadScore.calculate_priority(20.0, breakdown_low) == "LOW"

    def test_quality_helpers(self):
        """Quality Helper Methoden"""
        score_a = LeadScore(name="Test", total_score=85, breakdown=ScoreBreakdown(),
                           percentage=85, grade="A", priority="HIGH")
        score_c = LeadScore(name="Test", total_score=55, breakdown=ScoreBreakdown(),
                           percentage=55, grade="C", priority="MEDIUM")
        score_f = LeadScore(name="Test", total_score=10, breakdown=ScoreBreakdown(),
                           percentage=10, grade="F", priority="LOW")

        assert score_a.is_high_quality is True
        assert score_c.is_medium_quality is True
        assert score_f.is_low_quality is True
        assert score_a.is_followup_candidate is True


class TestPLZCoordinate:
    """Tests für PLZCoordinate Model"""

    def test_create_coordinate(self):
        """PLZCoordinate erstellen"""
        coord = PLZCoordinate(
            plz="2351",
            ort="Guntramsdorf",
            bundesland="Niederösterreich",
            lat=48.0475,
            lon=16.3167
        )
        assert coord.plz == "2351"
        assert coord.ort == "Guntramsdorf"

    def test_distance_calculation(self):
        """Distanz-Berechnung (Haversine)"""
        # Wien (1010)
        wien = PLZCoordinate(plz="1010", ort="Wien", bundesland="Wien",
                            lat=48.2082, lon=16.3738)

        # Guntramsdorf (2351)
        guntramsdorf = PLZCoordinate(plz="2351", ort="Guntramsdorf",
                                    bundesland="Niederösterreich",
                                    lat=48.0475, lon=16.3167)

        # Distanz sollte ca. 18km sein
        distance = wien.distance_to(guntramsdorf)
        assert 15 < distance < 25

    def test_bundesland_enum(self):
        """Bundesland als Enum"""
        coord = PLZCoordinate(plz="1010", ort="Wien", bundesland="Wien")
        assert coord.bundesland_enum == Bundesland.WIEN


class TestPLZInfo:
    """Tests für PLZInfo Model"""

    def test_create_plz_info(self):
        """PLZInfo erstellen"""
        coords = [
            PLZCoordinate(plz="2351", ort="Guntramsdorf", bundesland="Niederösterreich"),
            PLZCoordinate(plz="2351", ort="Pfaffstätten", bundesland="Niederösterreich"),
        ]
        info = PLZInfo(plz="2351", coordinates=coords)
        assert info.plz == "2351"
        assert len(info.orte) == 2

    def test_wko_urls(self):
        """WKO URLs generieren"""
        coords = [
            PLZCoordinate(plz="2351", ort="Guntramsdorf", bundesland="Niederösterreich"),
        ]
        info = PLZInfo(plz="2351", coordinates=coords)
        urls = info.get_wko_urls()
        assert len(urls) == 1
        assert "guntramsdorf" in urls[0]
        assert "niederösterreich" in urls[0]


class TestPLZHelpers:
    """Tests für PLZ Helper Functions"""

    def test_plz_to_bundesland(self):
        """PLZ zu Bundesland"""
        assert plz_to_bundesland("1010") == Bundesland.WIEN
        assert plz_to_bundesland("2351") == Bundesland.NIEDEROESTERREICH
        assert plz_to_bundesland("4020") == Bundesland.OBEROESTERREICH
        assert plz_to_bundesland("5020") == Bundesland.SALZBURG
        assert plz_to_bundesland("8010") == Bundesland.VORARLBERG

    def test_is_valid_plz(self):
        """PLZ Validierung"""
        assert is_valid_plz("2351") is True
        assert is_valid_plz("1010") is True
        assert is_valid_plz("0000") is False  # Keine gültige PLZ
        assert is_valid_plz("123") is False   # Zu kurz
        assert is_valid_plz("12345") is False  # Zu lang
        assert is_valid_plz("ABCD") is False   # Keine Zahlen


if __name__ == "__main__":
    pytest.main([__file__, "-v"])