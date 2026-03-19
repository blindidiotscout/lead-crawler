"""
LLM Analyzer
Analysiert Website-Inhalte mit Ollama für Branchen-Erkennung
"""

import json
import re
from typing import Dict, Optional, List
from dataclasses import dataclass
import requests


@dataclass
class CompanyAnalysis:
    """LLM-Analyse Ergebnis"""
    branch: str                    # Hauptbranche
    sub_branches: List[str]        # Unterbranchen
    services: List[str]            # Angebotene Dienstleistungen
    target_market: str             # Zielmarkt (B2B, B2C, etc.)
    company_size_hint: str         # Größenhinweis (Klein, Mittel, Groß)
    keywords: List[str]            # Extrahierte Keywords
    confidence: float              # Konfidenz 0-1
    reasoning: str                 # Kurze Begründung
    
    def to_dict(self) -> Dict:
        return {
            'branch': self.branch,
            'sub_branches': self.sub_branches,
            'services': self.services,
            'target_market': self.target_market,
            'company_size_hint': self.company_size_hint,
            'keywords': self.keywords,
            'confidence': self.confidence,
            'reasoning': self.reasoning
        }


class LLMAnalyzer:
    """
    Analysiert Unternehmens-Websites mit Ollama
    Nutzt strukturierte Prompts für konsistente JSON-Ausgaben
    """
    
    # Verfügbare Branchen für Klassifizierung
    BRANCHES = [
        "Bau", "Elektro", "Sanitär/Heizung", "Dachdecker", "Maler",
        "Tischler/Schreiner", "Schlosser", "Metallbau", "Garten/Landschaftsbau",
        "Reinigung", "Sicherheit", "IT/Digital", "Marketing", "Beratung",
        "Handel/Großhandel", "Industrie/Fertigung", "Transport/Logistik",
        "Gastronomie", "Tourismus", "Gesundheit", "Recht/Steuern",
        "Immobilien", "Finanzen/Versicherung", "Sonstige"
    ]
    
    def __init__(self, 
                 model: str = "qwen2.5:7b",
                 ollama_url: str = "http://192.168.178.123:11434",
                 timeout: int = 300):
        """
        Args:
            model: Ollama Modell-Name
            ollama_url: Ollama API URL
            timeout: Request timeout
        """
        self.model = model
        self.ollama_url = ollama_url
        self.timeout = timeout
        
        # Prompt Template - JSON-Beispiel mit {{ }} escaped
        self.prompt_template = """Du bist ein Experte für Unternehmensanalyse. Analysiere den folgenden Website-Text eines österreichischen Unternehmens und extrahiere strukturierte Informationen.

WEBSITE-TEXT:
{content}

UNTERNEHMENSNAME: {company_name}

Analysiere den Text und gib dein Ergebnis als JSON zurück:

{{
  "branch": "Hauptbranche aus der Liste",
  "sub_branches": ["Unterbranche 1", "Unterbranche 2"],
  "services": ["Dienstleistung 1", "Dienstleistung 2", "Dienstleistung 3"],
  "target_market": "B2B oder B2C oder Beides",
  "company_size_hint": "Klein (1-5 MA), Mittel (6-50 MA), oder Groß (50+ MA)",
  "keywords": ["Keyword1", "Keyword2", "Keyword3", "Keyword4", "Keyword5"],
  "confidence": 0.85,
  "reasoning": "Kurze Begründung der Einordnung"
}}

WICHTIG:
- Wähle die "branch" NUR aus dieser Liste: {branches}
- "confidence" ist eine Zahl zwischen 0.0 und 1.0
- Sei präzise und objektiv
- Wenn unklar, wähle "Sonstige" und niedrige confidence
- Antworte NUR mit dem JSON, keine Erklärung davor oder danach
"""
    
    def _build_prompt(self, company_name: str, content: str) -> str:
        """Erstellt den Prompt für das LLM"""
        # Content auf ~3000 Zeichen begrenzen (Token-Limit)
        if len(content) > 3000:
            content = content[:3000] + "..."
        
        branches_str = ", ".join(self.BRANCHES)
        
        return self.prompt_template.format(
            company_name=company_name,
            content=content,
            branches=branches_str
        )
    
    def _call_ollama(self, prompt: str) -> Optional[str]:
        """Ruft Ollama API auf"""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Niedrig für konsistente Ergebnisse
                        "num_predict": 500   # Max tokens für Antwort
                    }
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json().get("response", "")
            
        except requests.exceptions.Timeout:
            print(f"⚠️  Ollama Timeout nach {self.timeout}s")
            return None
        except Exception as e:
            print(f"⚠️  Ollama Fehler: {e}")
            return None
    
    def _parse_response(self, response: str) -> Optional[CompanyAnalysis]:
        """Parst JSON-Antwort vom LLM"""
        if not response:
            return None
        
        # Versuche JSON zu extrahieren (manchmal ist es in Markdown-Codeblocks)
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            response = json_match.group(0)
        
        try:
            data = json.loads(response)
            
            return CompanyAnalysis(
                branch=data.get('branch', 'Sonstige'),
                sub_branches=data.get('sub_branches', []),
                services=data.get('services', []),
                target_market=data.get('target_market', 'Unbekannt'),
                company_size_hint=data.get('company_size_hint', 'Unbekannt'),
                keywords=data.get('keywords', []),
                confidence=float(data.get('confidence', 0.5)),
                reasoning=data.get('reasoning', '')
            )
            
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON Parse Fehler: {e}")
            print(f"   Response: {response[:200]}...")
            return None
    
    def analyze(self, 
                company_name: str, 
                website_content: Dict) -> Optional[CompanyAnalysis]:
        """
        Analysiert ein Unternehmen
        
        Args:
            company_name: Name des Unternehmens
            website_content: Dict mit WebsiteContent (von WebsiteCrawler)
            
        Returns:
            CompanyAnalysis oder None bei Fehler
        """
        # Content zusammenstellen
        content_parts = []
        
        if website_content.get('title'):
            content_parts.append(f"Titel: {website_content['title']}")
        
        if website_content.get('meta_description'):
            content_parts.append(f"Beschreibung: {website_content['meta_description']}")
        
        if website_content.get('main_text'):
            content_parts.append(f"Inhalt: {website_content['main_text']}")
        
        if website_content.get('about_text'):
            content_parts.append(f"Über uns: {website_content['about_text']}")
        
        if website_content.get('services_text'):
            content_parts.append(f"Leistungen: {website_content['services_text']}")
        
        full_content = "\n\n".join(content_parts)
        
        if len(full_content) < 50:
            print(f"⚠️  Zu wenig Content für {company_name}")
            return None
        
        # Prompt erstellen und LLM aufrufen
        prompt = self._build_prompt(company_name, full_content)
        response = self._call_ollama(prompt)
        
        return self._parse_response(response)
    
    def analyze_batch(self, 
                     companies: List[Dict],
                     progress_callback=None) -> Dict[str, CompanyAnalysis]:
        """
        Analysiert mehrere Unternehmen
        
        Args:
            companies: Liste von Dicts mit 'name' und 'website_content'
            progress_callback: Optional callback(current, total)
            
        Returns:
            Dict: company_name -> CompanyAnalysis
        """
        results = {}
        total = len(companies)
        
        for i, company in enumerate(companies):
            if progress_callback:
                progress_callback(i + 1, total)
            
            name = company.get('name', 'Unknown')
            content = company.get('website_content', {})
            
            analysis = self.analyze(name, content)
            if analysis:
                results[name] = analysis
        
        return results
    
    def quick_analyze(self, company_name: str, text_snippet: str) -> Optional[CompanyAnalysis]:
        """Schnelle Analyse mit minimalem Text"""
        content = {
            'main_text': text_snippet[:1000]
        }
        return self.analyze(company_name, content)


def analyze_company(company_name: str, website_text: str, 
                   model: str = "glm-5:cloud") -> Optional[Dict]:
    """Hilfsfunktion für einfache Analyse"""
    analyzer = LLMAnalyzer(model=model)
    content = {'main_text': website_text}
    result = analyzer.analyze(company_name, content)
    return result.to_dict() if result else None


if __name__ == "__main__":
    print("=== LLM Analyzer Test ===\n")
    
    # Test mit Beispiel-Content
    test_content = {
        'title': 'Müller Bau GmbH - Ihr Partner für Bau und Renovierung',
        'meta_description': 'Wir sind Ihr zuverlässiger Partner für Bauarbeiten, Renovierungen und Sanierungen in Niederösterreich.',
        'main_text': '''
            Müller Bau GmbH - Ihr zuverlässiger Partner für Bau und Renovierung
            
            Seit über 20 Jahren sind wir in Niederösterreich tätig und bieten 
            unseren Kunden erstklassige Bauleistungen. Unser Team von 15 Mitarbeitern 
            realisiert Projekte vom Einfamilienhaus bis zur Gewerbehalle.
            
            Unsere Leistungen:
            - Neubau von Einfamilienhäusern
            - Renovierung und Sanierung
            - Trockenbau und Innenausbau
            - Fundamentarbeiten
            - Maurerarbeiten
            
            Wir arbeiten für private Bauherren sowie für Gewerbekunden.
            Kontaktieren Sie uns für ein unverbindliches Angebot.
        '''
    }
    
    analyzer = LLMAnalyzer()
    result = analyzer.analyze("Müller Bau GmbH", test_content)
    
    if result:
        print(f"✅ Analyse erfolgreich!")
        print(f"   Branche: {result.branch}")
        print(f"   Unterbranchen: {', '.join(result.sub_branches)}")
        print(f"   Services: {', '.join(result.services[:3])}...")
        print(f"   Zielmarkt: {result.target_market}")
        print(f"   Größenhinweis: {result.company_size_hint}")
        print(f"   Keywords: {', '.join(result.keywords)}")
        print(f"   Confidence: {result.confidence:.2f}")
        print(f"   Reasoning: {result.reasoning}")
    else:
        print("❌ Analyse fehlgeschlagen")
