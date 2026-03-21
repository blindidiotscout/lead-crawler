"""
Enhanced Scoring mit LLM
Erweitert die Scoring Engine mit LLM-basierter Branchenanalyse
"""

from typing import Dict, List, Optional
from src.scoring import ScoringEngine, LeadScore, SCORING_PROFILES
from src.llm_pipeline import LLMPipeline, PipelineResult


class EnhancedScoringEngine(ScoringEngine):
    """
    Erweiterte Scoring Engine mit LLM-Analyse
    
    Nutzt LLM für:
    - Bessere Branchen-Erkennung
    - Service-Extraktion
    - Zielmarkt-Erkennung
    - Größenschätzung
    """
    
    def __init__(self,
                 target_branches: List[str] = None,
                 center_plz: str = None,
                 max_distance_km: float = None,
                 min_score: float = 0.0,
                 use_llm: bool = True,
                 llm_confidence_threshold: float = 0.7):
        """
        Args:
            use_llm: LLM-Analyse aktivieren
            llm_confidence_threshold: Mindest-Confidence für LLM-Ergebnisse
        """
        super().__init__(
            target_branches=target_branches,
            center_plz=center_plz,
            max_distance_km=max_distance_km,
            min_score=min_score
        )
        
        self.use_llm = use_llm
        self.llm_confidence_threshold = llm_confidence_threshold
        
        if use_llm:
            self.llm_pipeline = LLMPipeline()
        else:
            self.llm_pipeline = None
        
        # Cache für LLM-Ergebnisse während einer Session
        self._llm_cache: Dict[str, PipelineResult] = {}
    
    def _score_branch(self, company: Dict) -> tuple:
        """
        Überschriebene Branchen-Bewertung mit LLM-Unterstützung
        """
        score = 0.0
        reasons = []
        max_score = self.weights['branch']
        
        if not self.target_branches:
            return max_score * 0.5, ["○ Keine Zielbranchen definiert"]
        
        # Zuerst klassische Methode (Name-basiert)
        name = (company.get('name') or '').lower()
        branche = (company.get('branche') or '').lower()
        
        name_matched_branches = []
        for branch in self.target_branches:
            branch_lower = branch.lower()
            if branch_lower in name or branch_lower in branche:
                name_matched_branches.append(branch)
        
        # LLM-Analyse wenn Website vorhanden und aktiviert
        website = company.get('website')
        llm_match = False
        llm_branch = None
        llm_confidence = 0.0
        
        if self.use_llm and website and self.llm_pipeline:
            # Cache-Lookup
            cache_key = f"{company.get('name')}:{website}"
            if cache_key not in self._llm_cache:
                result = self.llm_pipeline.analyze_company(
                    company.get('name', 'Unknown'),
                    website
                )
                self._llm_cache[cache_key] = result
            else:
                result = self._llm_cache[cache_key]
            
            if result.analysis and result.analysis.confidence >= self.llm_confidence_threshold:
                llm_branch = result.analysis.branch
                llm_confidence = result.analysis.confidence
                
                # Prüfe ob LLM-Branch in Zielbranchen
                for target in self.target_branches:
                    if target.lower() in llm_branch.lower() or llm_branch.lower() in target.lower():
                        llm_match = True
                        break
        
        # Scoring-Logik
        if name_matched_branches and llm_match:
            # Beide Methoden stimmen überein → volle Punkte
            score = max_score
            reasons.append(f"✓ Zielbranche (Name + LLM): {', '.join(name_matched_branches)}")
            if llm_branch:
                reasons.append(f"  LLM: {llm_branch} ({llm_confidence:.0%} confidence)")
                
        elif llm_match:
            # Nur LLM match
            score = max_score * 0.9
            reasons.append(f"✓ Zielbranche (LLM): {llm_branch} ({llm_confidence:.0%})")
            
        elif name_matched_branches:
            # Nur Name match
            score = max_score * 0.8
            reasons.append(f"○ Zielbranche (Name): {', '.join(name_matched_branches)}")
            if llm_branch:
                reasons.append(f"  LLM sagt: {llm_branch} (nicht in Zielbranchen)")
                
        else:
            # Kein Match
            score = max_score * 0.2
            reasons.append("✗ Nicht in Zielbranchen")
            if llm_branch:
                reasons.append(f"  LLM erkannt: {llm_branch}")
        
        return score, reasons
    
    def _score_size(self, company: Dict) -> tuple:
        """
        Überschriebene Größen-Bewertung mit LLM-Unterstützung
        """
        score = 0.0
        reasons = []
        max_score = self.weights['size']
        
        name = (company.get('name') or '').lower()
        
        # LLM-Größenhinweis prüfen
        website = company.get('website')
        llm_size_hint = None
        
        if self.use_llm and website and self.llm_pipeline:
            cache_key = f"{company.get('name')}:{website}"
            if cache_key in self._llm_cache:
                result = self._llm_cache[cache_key]
                if result.analysis:
                    llm_size_hint = result.analysis.company_size_hint
        
        # Kombinierte Bewertung: Name + LLM
        size_score_name = self._get_size_score_from_name(name)
        size_score_llm = self._get_size_score_from_llm(llm_size_hint)
        
        # Gewichtung: Name 60%, LLM 40%
        if size_score_llm is not None:
            combined_score = size_score_name * 0.6 + size_score_llm * 0.4
            
            if combined_score >= 0.9:
                score = max_score
                reasons.append(f"✓ Ideale Größe (Name+LLM)")
            elif combined_score >= 0.7:
                score = max_score * 0.8
                reasons.append(f"○ Gute Größe (Name+LLM)")
            else:
                score = max_score * combined_score
                reasons.append(f"○ Größe: {llm_size_hint or 'unbekannt'}")
        else:
            # Nur Name-basiert
            score = max_score * size_score_name
            if size_score_name >= 0.9:
                reasons.append("✓ Ideale Größe (GmbH)")
            elif size_score_name >= 0.7:
                reasons.append("○ Akzeptable Größe")
            else:
                reasons.append("✗ Größe nicht ideal")
        
        return score, reasons
    
    def _get_size_score_from_name(self, name: str) -> float:
        """Berechnet Größen-Score aus Rechtsform"""
        if 'gmbh & co kg' in name:
            return 0.7
        elif ' ag' in name or name.endswith(' ag') or name.startswith('ag '):
            return 0.3
        elif any(ind in name for ind in ['e.u.', ' e.u.', 'selbständig', 'ingenieur', 'architekt']):
            return 0.3
        elif 'gmbh' in name:
            return 1.0
        elif 'kg' in name:
            return 0.9
        elif 'og' in name:
            return 0.8
        elif 'eg' in name:
            return 0.8
        else:
            return 0.5
    
    def _get_size_score_from_llm(self, size_hint: Optional[str]) -> Optional[float]:
        """Konvertiert LLM-Größenhinweis zu Score"""
        if not size_hint:
            return None
        
        size_lower = size_hint.lower()
        
        if 'klein' in size_lower or '1-5' in size_lower:
            return 0.3
        elif 'mittel' in size_lower or '6-50' in size_lower:
            return 1.0  # Ideal
        elif 'groß' in size_lower or '50+' in size_lower or 'groß' in size_lower:
            return 0.4
        else:
            return 0.5
    
    def get_llm_insights(self, company: Dict) -> Optional[Dict]:
        """
        Gibt LLM-Insights für ein Unternehmen zurück
        
        Returns:
            Dict mit Analyse-Ergebnissen oder None
        """
        if not self.use_llm or not self.llm_pipeline:
            return None
        
        website = company.get('website')
        if not website:
            return None
        
        cache_key = f"{company.get('name')}:{website}"
        if cache_key in self._llm_cache:
            result = self._llm_cache[cache_key]
            if result.analysis:
                return {
                    'branch': result.analysis.branch,
                    'sub_branches': result.analysis.sub_branches,
                    'services': result.analysis.services,
                    'target_market': result.analysis.target_market,
                    'company_size_hint': result.analysis.company_size_hint,
                    'keywords': result.analysis.keywords,
                    'confidence': result.analysis.confidence,
                    'reasoning': result.analysis.reasoning,
                    'cached': result.cached
                }
        
        return None


def create_enhanced_scorer(profile: str = 'default', 
                          use_llm: bool = True,
                          ollama_model: str = "llama3.2",
                          **kwargs) -> EnhancedScoringEngine:
    """
    Erstellt Enhanced Scoring Engine mit Profil
    
    Args:
        profile: 'default', 'bau', 'handwerk', 'local'
        use_llm: LLM-Analyse aktivieren
        **kwargs: Zusätzliche Parameter
    """
    config = SCORING_PROFILES.get(profile, SCORING_PROFILES['default'])
    final_config = {**config, **kwargs}
    
    return EnhancedScoringEngine(
        target_branches=final_config.get('target_branches'),
        center_plz=final_config.get('center_plz'),
        max_distance_km=final_config.get('max_distance_km'),
        min_score=final_config.get('min_score', 0),
        use_llm=use_llm,
        llm_confidence_threshold=kwargs.get('llm_confidence_threshold', 0.7)
    )


if __name__ == "__main__":
    print("=== Enhanced Scoring Engine Test ===\n")
    
    # Test-Unternehmen mit Websites
    test_companies = [
        {
            'name': 'Müller Bau GmbH',
            'street': 'Hauptstraße 10',
            'plz': '2351',
            'ort': 'Wiener Neudorf',
            'email': 'info@mueller-bau.at',
            'telefon': '02236 12345',
            'website': 'https://www.akras.at',  # Beispiel-URL
            'url': 'https://firmen.wko.at/mueller-bau',
        },
        {
            'name': 'Elektro Schmidt e.U.',
            'street': 'Dorfplatz 5',
            'plz': '2340',
            'ort': 'Mödling',
            'email': None,
            'telefon': '0664 123456',
            'website': None,
            'url': 'https://firmen.wko.at/elektro-schmidt',
        },
    ]
    
    print("Teste Enhanced Scoring (mit LLM)...\n")
    
    # Enhanced Scorer mit LLM
    enhanced_scorer = create_enhanced_scorer(
        profile='bau',
        center_plz='2351',
        max_distance_km=30,
        use_llm=True
    )
    
    scores = enhanced_scorer.score_batch(test_companies)
    
    for score in scores:
        print(f"🏢 {score.name}")
        print(f"   Score: {score.percentage:.1f}% ({score.grade}) - {score.priority}")
        print(f"   Breakdown: {score.breakdown}")
        print(f"   Gründe:")
        for reason in score.reasons:
            print(f"      {reason}")
        
        # LLM Insights
        insights = enhanced_scorer.get_llm_insights({'name': score.name, 'website': test_companies[0].get('website')})
        if insights:
            print(f"   🤖 LLM: {insights['branch']} ({insights['confidence']:.0%})")
        
        print()
    
    print("="*60)
    print("\nVergleich: Ohne LLM...\n")
    
    # Standard Scorer ohne LLM
    standard_scorer = create_enhanced_scorer(
        profile='bau',
        center_plz='2351',
        max_distance_km=30,
        use_llm=False
    )
    
    scores_std = standard_scorer.score_batch(test_companies)
    
    for score in scores_std:
        print(f"🏢 {score.name}: {score.percentage:.1f}% ({score.grade})")
        print(f"   Gründe: {', '.join(score.reasons[:3])}")
        print()
