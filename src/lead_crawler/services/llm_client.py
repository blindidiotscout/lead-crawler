"""
LLM Client Service
Abstraktion für LLM-Aufrufe (Ollama, Mock, etc.)
"""

import json
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

from lead_crawler.config import get_settings, OllamaConfig
from lead_crawler.models.analysis import BranchAnalysis


@dataclass
class LLMResponse:
    """LLM-Antwort"""
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_duration_ms: float = 0.0
    cached: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'content': self.content,
            'model': self.model,
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'total_duration_ms': self.total_duration_ms,
            'cached': self.cached,
            'error': self.error
        }


class LLMClient(ABC):
    """
    Abstrakte Basisklasse für LLM-Clients

    Ermöglicht verschiedene LLM-Backends (Ollama, OpenAI, etc.)
    """

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Generiert Text aus Prompt"""
        pass

    @abstractmethod
    def analyze_branch(self, company_name: str, website_content: Dict[str, Any],
                       **kwargs) -> Optional[BranchAnalysis]:
        """Analysiert Unternehmen und gibt Branchen-Ergebnis zurück"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Prüft ob LLM verfügbar ist"""
        pass


class OllamaClient(LLMClient):
    """
    Ollama LLM Client

    Unterstützt lokale Ollama-Instanzen für LLM-Inferenz.
    """

    def __init__(self, config: Optional[OllamaConfig] = None):
        """
        Initialisiert Ollama Client

        Args:
            config: OllamaConfig (default: aus get_settings())
        """
        if config is None:
            config = get_settings().ollama

        self.url = config.url
        self.model = config.model
        self.timeout = config.timeout
        self.max_retries = config.max_retries
        self.retry_delay = config.retry_delay

        # Requests-Session für Connection Pooling
        self._session = None

    def _get_session(self):
        """Lazy-init für requests Session"""
        if self._session is None:
            import requests
            self._session = requests.Session()
        return self._session

    def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Führt HTTP-Request gegen Ollama API aus

        Args:
            endpoint: API-Endpoint (z.B. '/api/generate')
            payload: Request-Payload

        Returns:
            Response Dict

        Raises:
            Exception: Bei Fehlern nach allen Retries
        """
        import requests

        session = self._get_session()
        url = f"{self.url.rstrip('/')}{endpoint}"

        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = session.post(
                    url,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()

            except requests.exceptions.Timeout:
                last_error = f"Timeout nach {self.timeout}s"
            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection Error: {e}"
            except requests.exceptions.HTTPError as e:
                last_error = f"HTTP Error: {e}"
                # Bei 4xx Fehlern nicht retry
                if 400 <= response.status_code < 500:
                    break
            except Exception as e:
                last_error = f"Unexpected Error: {e}"

            # Retry mit Delay
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))

        raise Exception(f"Ollama request failed after {self.max_retries} retries: {last_error}")

    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 temperature: float = 0.7, **kwargs) -> LLMResponse:
        """
        Generiert Text aus Prompt via Ollama

        Args:
            prompt: User Prompt
            system_prompt: Optional System Prompt
            temperature: Sampling Temperature (0.0 - 2.0)

        Returns:
            LLMResponse mit generiertem Text
        """
        start_time = time.time()

        # Payload bauen
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": kwargs.get('max_tokens', 2048),
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = self._make_request("/api/generate", payload)

            duration_ms = (time.time() - start_time) * 1000

            return LLMResponse(
                content=response.get('response', ''),
                model=self.model,
                prompt_tokens=response.get('prompt_eval_count', 0),
                completion_tokens=response.get('eval_count', 0),
                total_duration_ms=duration_ms
            )

        except Exception as e:
            return LLMResponse(
                content='',
                model=self.model,
                error=str(e)
            )

    def analyze_branch(self, company_name: str, website_content: Dict[str, Any],
                       **kwargs) -> Optional[BranchAnalysis]:
        """
        Analysiert Unternehmen und extrahiert Branchen-Informationen

        Args:
            company_name: Unternehmensname
            website_content: Dict mit Website-Texten (title, main_text, about_text, etc.)

        Returns:
            BranchAnalysis oder None bei Fehler
        """
        # Prompt bauen
        system_prompt = """Du bist ein Experte für Unternehmensanalyse.
Analysiere den Website-Text und extrahiere:
1. Die Hauptbranche des Unternehmens
2. Unterbranchen / Spezialisierungen
3. Angebotene Dienstleistungen
4. Zielmarkt (B2B/B2C)
5. Unternehmensgröße (Schätzung)
6. Wichtige Keywords
7. Confidence-Score (0-1)

Antworte NUR im JSON-Format ohne Markdown:
{
  "branch": "Hauptbranche",
  "sub_branches": ["Unterbranche1", "Unterbranche2"],
  "services": ["Service1", "Service2"],
  "target_market": "B2B/B2C/B2B&B2C",
  "company_size_hint": "Micro/Small/Medium/Large",
  "keywords": ["keyword1", "keyword2"],
  "confidence": 0.85,
  "reasoning": "Kurze Begründung"
}"""

        # Website-Content zusammenfassen
        content_parts = []
        if website_content.get('title'):
            content_parts.append(f"Website-Titel: {website_content['title']}")
        if website_content.get('meta_description'):
            content_parts.append(f"Meta: {website_content['meta_description']}")
        if website_content.get('main_text'):
            content_parts.append(f"Haupttext: {website_content['main_text'][:2000]}")
        if website_content.get('about_text'):
            content_parts.append(f"About: {website_content['about_text'][:500]}")

        prompt = f"""Analysiere das folgende Unternehmen:

Firmenname: {company_name}

Website-Inhalt:
{chr(10).join(content_parts)}

Extrahiere Branchen-Informationen im JSON-Format."""

        # LLM aufrufen
        response = self.generate(prompt, system_prompt=system_prompt, temperature=0.3)

        if response.error:
            return None

        # JSON parsen
        try:
            # Entferne eventuelle Markdown-Formatierung
            content = response.content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]

            data = json.loads(content)

            return BranchAnalysis(
                branch=data.get('branch', 'Unknown'),
                sub_branches=data.get('sub_branches', []),
                services=data.get('services', []),
                target_market=data.get('target_market', 'Unknown'),
                company_size_hint=data.get('company_size_hint', 'Unknown'),
                keywords=data.get('keywords', []),
                confidence=float(data.get('confidence', 0.0)),
                reasoning=data.get('reasoning', ''),
                model=self.model
            )

        except json.JSONDecodeError:
            return None
        except Exception:
            return None

    def is_available(self) -> bool:
        """Prüft ob Ollama-Server erreichbar ist"""
        import requests

        try:
            response = self._get_session().get(
                f"{self.url.rstrip('/')}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False

    def get_available_models(self) -> List[str]:
        """
        Listet verfügbare Modelle auf

        Returns:
            Liste von Modell-Namen
        """
        import requests

        try:
            response = self._get_session().get(
                f"{self.url.rstrip('/')}/api/tags",
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            return [model['name'] for model in data.get('models', [])]

        except Exception:
            return []


class MockLLMClient(LLMClient):
    """
    Mock LLM Client für Tests

    Gibt vordefinierte Antworten zurück ohne echtes LLM.
    """

    def __init__(self, branch: str = "IT", confidence: float = 0.85):
        """
        Initialisiert Mock Client

        Args:
            branch: Branchen-Name für Mock-Antworten
            confidence: Confidence für Mock-Antworten
        """
        self.branch = branch
        self.confidence = confidence
        self.call_count = 0

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """Gibt Mock-Antwort zurück"""
        self.call_count += 1

        return LLMResponse(
            content=json.dumps({
                "branch": self.branch,
                "sub_branches": ["Software", "Beratung"],
                "services": ["Entwicklung", "Support"],
                "target_market": "B2B",
                "company_size_hint": "Medium",
                "keywords": ["IT", "Software"],
                "confidence": self.confidence,
                "reasoning": "Mock analysis"
            }),
            model="mock",
            prompt_tokens=0,
            completion_tokens=0
        )

    def analyze_branch(self, company_name: str, website_content: Dict[str, Any],
                       **kwargs) -> BranchAnalysis:
        """Gibt Mock-BranchAnalysis zurück"""
        self.call_count += 1

        return BranchAnalysis(
            branch=self.branch,
            sub_branches=["Software", "Beratung"],
            services=["Entwicklung", "Support"],
            target_market="B2B",
            company_size_hint="Medium",
            keywords=["IT", "Software"],
            confidence=self.confidence,
            reasoning="Mock analysis",
            model="mock"
        )

    def is_available(self) -> bool:
        """Mock ist immer verfügbar"""
        return True


# Singleton-Instanz (Lazy)
_llm_client_instance: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    Gibt die globale LLM-Client Instanz zurück (Singleton Pattern)

    Returns:
        LLMClient Instanz (OllamaClient oder MockLLMClient)
    """
    global _llm_client_instance
    if _llm_client_instance is None:
        settings = get_settings()
        try:
            _llm_client_instance = OllamaClient(settings.ollama)
        except Exception:
            # Fallback zu Mock
            _llm_client_instance = MockLLMClient()
    return _llm_client_instance


def reset_llm_client() -> None:
    """Setzt die globale LLM-Client Instanz zurück (für Tests)"""
    global _llm_client_instance
    _llm_client_instance = None