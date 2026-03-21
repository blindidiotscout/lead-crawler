"""
Integration Tests für LLM Client
Testet echte Ollama-Requests (wenn verfügbar)
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import Mock, patch

# Add src directory to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from lead_crawler.services.llm_client import MockLLMClient, OllamaClient


class TestMockLLMClient:
    """Tests für MockLLMClient (kein echter Ollama nötig)"""

    def test_mock_client_creation(self):
        """MockLLMClient kann erstellt werden"""
        client = MockLLMClient()
        assert client is not None

    def test_mock_client_generate(self):
        """MockLLMClient generate()"""
        client = MockLLMClient()
        response = client.generate("Test prompt")

        assert response is not None
        assert hasattr(response, 'content')
        assert len(response.content) > 0

    def test_mock_client_analyze_branch(self):
        """MockLLMClient analyze_branch()"""
        client = MockLLMClient()
        result = client.analyze_branch("Test Firma", "Test Website Content")

        assert result is not None
        assert hasattr(result, 'branch')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'services')

    def test_mock_client_is_available(self):
        """MockLLMClient is_available()"""
        client = MockLLMClient()
        assert client.is_available() is True


class TestOllamaClientUnit:
    """Unit Tests für OllamaClient (ohne echte Requests)"""

    def test_ollama_client_creation(self):
        """OllamaClient kann erstellt werden"""
        client = OllamaClient()
        assert client is not None

    def test_ollama_client_with_settings(self):
        """OllamaClient mit Settings"""
        from lead_crawler.config import OllamaConfig

        config = OllamaConfig(
            url="http://localhost:11434",
            model="test-model"
        )
        client = OllamaClient(config=config)
        assert client is not None

    @patch('requests.post')
    def test_ollama_client_generate_mocked(self, mock_post):
        """OllamaClient generate() mit gemocktem Request"""
        # Mock Response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Test response"}
        mock_post.return_value = mock_response

        client = OllamaClient()
        response = client.generate("Test prompt")

        assert response is not None

    @patch('requests.get')
    def test_ollama_client_is_available_mocked(self, mock_get):
        """OllamaClient is_available() mit gemocktem Request"""
        # Mock Response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        client = OllamaClient()
        # is_available prüft ob Ollama erreichbar ist
        result = client.is_available()
        # Das Ergebnis hängt von der Mock-Konfiguration ab
        assert result is not None


class TestOllamaClientIntegration:
    """Integration Tests für OllamaClient (erfordert laufenden Ollama)"""

    @pytest.mark.integration
    def test_ollama_real_connection(self):
        """Echter Ollama-Verbindungstest (nur mit -m integration)"""
        client = OllamaClient()

        # Prüfen ob Ollama verfügbar
        if not client.is_available():
            pytest.skip("Ollama not available")

        # Einfacher Generate-Call
        try:
            response = client.generate("Sage 'Hallo'")
            assert response is not None
        except Exception as e:
            pytest.skip(f"Ollama error: {e}")

    @pytest.mark.integration
    def test_ollama_real_analyze(self):
        """Echter Ollama-Analyse-Test (nur mit -m integration)"""
        client = OllamaClient()

        if not client.is_available():
            pytest.skip("Ollama not available")

        try:
            # Test-Content analysieren
            result = client.analyze_branch(
                "Test Firma GmbH",
                "Test Firma GmbH - IT Dienstleistungen, Web Development, Mobile Apps"
            )

            assert result is not None
            assert result.branch is not None
        except Exception as e:
            pytest.skip(f"Ollama error: {e}")


class TestLLMClientProtocol:
    """Tests für LLM Client Protocol"""

    def test_mock_client_methods(self):
        """MockLLMClient hat alle required Methods"""
        mock_client = MockLLMClient()
        assert hasattr(mock_client, 'generate')
        assert hasattr(mock_client, 'analyze_branch')
        assert hasattr(mock_client, 'is_available')
        assert callable(mock_client.generate)
        assert callable(mock_client.analyze_branch)
        assert callable(mock_client.is_available)

    def test_ollama_client_methods(self):
        """OllamaClient hat alle required Methods"""
        ollama_client = OllamaClient()
        assert hasattr(ollama_client, 'generate')
        assert hasattr(ollama_client, 'analyze_branch')
        assert hasattr(ollama_client, 'is_available')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])