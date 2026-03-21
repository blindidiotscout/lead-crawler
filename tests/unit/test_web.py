"""
Unit Tests für Web Components
"""

import sys
from pathlib import Path

import pytest

# Add src directory to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


class TestUIComponents:
    """Tests für UI-Komponenten"""

    def test_render_score_badge_high(self):
        """Score-Badge für hohen Score"""
        from web.components.ui import render_score_badge

        html = render_score_badge(85)
        assert "A" in html
        assert "#4CAF50" in html  # Grün

    def test_render_score_badge_medium(self):
        """Score-Badge für mittleren Score"""
        from web.components.ui import render_score_badge

        html = render_score_badge(65)
        assert "B" in html
        assert "#FF9800" in html  # Orange

    def test_render_score_badge_low(self):
        """Score-Badge für niedrigen Score"""
        from web.components.ui import render_score_badge

        html = render_score_badge(30)
        assert "D" in html
        assert "#f44336" in html  # Rot

    def test_render_status_badge_running(self):
        """Status-Badge für 'running'"""
        from web.components.ui import render_status_badge

        html = render_status_badge("running")
        assert "RUNNING" in html
        assert "#2196F3" in html

    def test_render_status_badge_completed(self):
        """Status-Badge für 'completed'"""
        from web.components.ui import render_status_badge

        html = render_status_badge("completed")
        assert "COMPLETED" in html
        assert "#4CAF50" in html

    def test_render_status_badge_failed(self):
        """Status-Badge für 'failed'"""
        from web.components.ui import render_status_badge

        html = render_status_badge("failed")
        assert "FAILED" in html
        assert "#f44336" in html

    def test_render_status_badge_unknown(self):
        """Status-Badge für unbekannten Status"""
        from web.components.ui import render_status_badge

        html = render_status_badge("unknown")
        assert "UNKNOWN" in html
        assert "#9E9E9E" in html  # Grau


class TestCompanyData:
    """Tests für Company-Datenstrukturen"""

    def test_company_dict_creation(self):
        """Company-Dict erstellen"""
        company = {
            "name": "Test GmbH",
            "plz": "2351",
            "ort": "Guntramsdorf",
            "branche": "IT",
            "website": "https://test.com",
            "score_total": 85,
            "llm_analysis": {"branch": "Software", "confidence": 0.9},
        }

        assert company["name"] == "Test GmbH"
        assert company["plz"] == "2351"
        assert company["score_total"] == 85

    def test_company_with_score(self):
        """Company mit Score"""
        company = {"name": "Test GmbH", "score_total": 75, "score_grade": "B"}

        assert company["score_total"] >= 60
        assert company["score_grade"] == "B"

    def test_company_with_llm_analysis(self):
        """Company mit LLM-Analyse"""
        company = {
            "name": "Test GmbH",
            "llm_analysis": {
                "branch": "Softwareentwicklung",
                "services": ["Web Development", "Mobile Apps"],
                "confidence": 0.85,
            },
        }

        assert company["llm_analysis"]["branch"] == "Softwareentwicklung"
        assert len(company["llm_analysis"]["services"]) == 2


class TestExportFormats:
    """Tests für Export-Formate"""

    def test_csv_export_format(self):
        """CSV Export-Format"""
        import csv
        import io

        companies = [{"name": "Test1", "ort": "Wien"}, {"name": "Test2", "ort": "Graz"}]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["name", "ort"])
        writer.writeheader()
        writer.writerows(companies)

        result = output.getvalue()
        assert "name,ort" in result
        assert "Test1" in result
        assert "Test2" in result

    def test_json_export_format(self):
        """JSON Export-Format"""
        import json

        companies = [{"name": "Test1", "ort": "Wien"}, {"name": "Test2", "ort": "Graz"}]

        result = json.dumps(companies)
        parsed = json.loads(result)

        assert len(parsed) == 2
        assert parsed[0]["name"] == "Test1"


class TestFilterLogic:
    """Tests für Filter-Logik"""

    def test_filter_by_branch(self):
        """Nach Branche filtern"""
        companies = [
            {"name": "Test1", "branche": "IT"},
            {"name": "Test2", "branche": "Bau"},
            {"name": "Test3", "branche": "IT"},
        ]

        filtered = [c for c in companies if c.get("branche") == "IT"]
        assert len(filtered) == 2

    def test_filter_by_website(self):
        """Nach Website filtern"""
        companies = [
            {"name": "Test1", "website": "https://test.com"},
            {"name": "Test2", "website": None},
            {"name": "Test3", "website": "https://test3.com"},
        ]

        filtered = [c for c in companies if c.get("website")]
        assert len(filtered) == 2

    def test_filter_by_score(self):
        """Nach Score filtern"""
        companies = [
            {"name": "Test1", "score_total": 85},
            {"name": "Test2", "score_total": 50},
            {"name": "Test3", "score_total": 75},
        ]

        min_score = 60
        filtered = [c for c in companies if c.get("score_total", 0) >= min_score]
        assert len(filtered) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
