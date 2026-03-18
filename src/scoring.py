"""
Lead Scoring Engine
Bewertet Unternehmen basierend auf verschiedenen Kriterien

Score: 0-100 (höher = besserer Lead)
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import re


@dataclass
class LeadScore:
    """Scoring-Ergebnis für ein Unternehmen"""
    name: str
    total_score: float
    max_score: float
    percentage: float
    breakdown: Dict[str, float]
    grade: str  # A, B, C, D, F
    priority: str  # HIGH, MEDIUM, LOW
    reasons: List[str]
    
    def to_dict(self) -> Dict:
        return asdict(self)


class ScoringEngine:
    """Bewertet Leads basierend auf konfigurierbaren Kriterien"""
    
    def __init__(self, 
                 target_branches: List[str] = None,
                 center_plz: str = None,
                 max_distance_km: float = None,
                 min_score: float = 0.0):
        """
        Initialisiert Scoring Engine
        
        Args:
            target_branches: Zielbranchen (z.B. ["Bau", "Elektro", "Dachdecker"])
            center_plz: Zentrale PLZ für Distanz-Berechnung
            max_distance_km: Maximale Distanz (weitere = niedrigerer Score)
            min_score: Mindestscore für Lead (0-100)
        """
        self.target_branches = target_branches or []
        self.center_plz = center_plz
        self.max_distance_km = max_distance_km
        self.min_score = min_score
        
        # PLZ-Service für Distanz-Berechnung
        self.plz_service = None
        if center_plz:
            try:
                from src.plz_radius import PLZRadiusService
                self.plz_service = PLZRadiusService('data/plz_austria.db')
            except ImportError:
                from plz_radius import PLZRadiusService
                self.plz_service = PLZRadiusService('data/plz_austria.db')
        
        # Scoring-Gewichte (Summe = 100)
        self.weights = {
            'contact': 25,      # Kontakt-Infos (Email, Telefon, Website)
            'location': 20,     # Standort (Distanz)
            'branch': 20,       # Branchen-Relevanz
            'completeness': 15, # Datenvollständigkeit
            'freshness': 10,    # Aktualität (Website-Impressum)
            'size': 10,         # Unternehmensgröße (Schätzung)
        }
    
    def score(self, company: Dict) -> LeadScore:
        """
        Bewertet ein Unternehmen
        
        Args:
            company: Dict mit Unternehmensdaten (name, plz, ort, email, website, etc.)
        
        Returns:
            LeadScore mit Gesamtscore, Aufschlüsselung und Empfehlung
        """
        scores = {}
        reasons = []
        
        # 1. Kontakt-Score (0-25)
        scores['contact'], contact_reasons = self._score_contact(company)
        reasons.extend(contact_reasons)
        
        # 2. Location-Score (0-20)
        scores['location'], location_reasons = self._score_location(company)
        reasons.extend(location_reasons)
        
        # 3. Branchen-Score (0-20)
        scores['branch'], branch_reasons = self._score_branch(company)
        reasons.extend(branch_reasons)
        
        # 4. Vollständigkeits-Score (0-15)
        scores['completeness'], complete_reasons = self._score_completeness(company)
        reasons.extend(complete_reasons)
        
        # 5. Freshness-Score (0-10)
        scores['freshness'], fresh_reasons = self._score_freshness(company)
        reasons.extend(fresh_reasons)
        
        # 6. Größen-Score (0-10)
        scores['size'], size_reasons = self._score_size(company)
        reasons.extend(size_reasons)
        
        # Gesamtscore berechnen
        total_score = sum(scores.values())
        max_score = sum(self.weights.values())
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        
        # Grade berechnen
        grade = self._calculate_grade(percentage)
        
        # Priorität
        priority = self._calculate_priority(percentage, scores)
        
        return LeadScore(
            name=company.get('name', 'Unknown'),
            total_score=total_score,
            max_score=max_score,
            percentage=percentage,
            breakdown=scores,
            grade=grade,
            priority=priority,
            reasons=reasons
        )
    
    def _score_contact(self, company: Dict) -> tuple:
        """Bewertet Kontakt-Infos (Email, Telefon, Website)"""
        score = 0.0
        reasons = []
        max_score = self.weights['contact']
        
        # Email (10 Punkte)
        if company.get('email'):
            score += 10
            reasons.append("✓ Email vorhanden")
        else:
            reasons.append("✗ Keine Email")
        
        # Telefon (8 Punkte)
        if company.get('telefon'):
            score += 8
            reasons.append("✓ Telefon vorhanden")
        else:
            reasons.append("✗ Kein Telefon")
        
        # Website (7 Punkte)
        if company.get('website'):
            score += 7
            reasons.append("✓ Website vorhanden")
        else:
            reasons.append("✗ Keine Website")
        
        return min(score, max_score), reasons
    
    def _score_location(self, company: Dict) -> tuple:
        """Bewertet Standort basierend auf Distanz"""
        score = 0.0
        reasons = []
        max_score = self.weights['location']
        
        if not self.plz_service or not self.center_plz:
            # Keine Distanz-Bewertung → Neutrale Punktzahl
            return max_score * 0.5, ["○ Keine Distanz-Bewertung"]
        
        company_plz = company.get('plz')
        if not company_plz:
            return 0, ["✗ Keine PLZ"]
        
        try:
            # Distanz berechnen
            distance = self.plz_service.calculate_distance(self.center_plz, company_plz)
            
            if distance is None:
                return max_score * 0.5, ["○ PLZ nicht in Datenbank"]
            
            # Score basierend auf Distanz
            if distance <= 5:
                score = max_score
                reasons.append(f"✓ Sehr nah: {distance:.1f}km")
            elif distance <= 10:
                score = max_score * 0.85
                reasons.append(f"✓ Nah: {distance:.1f}km")
            elif distance <= 20:
                score = max_score * 0.7
                reasons.append(f"○ Mittlere Distanz: {distance:.1f}km")
            elif distance <= 30:
                score = max_score * 0.5
                reasons.append(f"○ Weit: {distance:.1f}km")
            else:
                score = max_score * 0.3
                reasons.append(f"✗ Sehr weit: {distance:.1f}km")
            
            # Bonus für max_distance_km
            if self.max_distance_km and distance > self.max_distance_km:
                score = 0
                reasons.append(f"✗ Außerhalb Radius ({self.max_distance_km}km)")
                
        except Exception as e:
            return max_score * 0.5, [f"⚠ Fehler bei Distanz: {e}"]
        
        return score, reasons
    
    def _score_branch(self, company: Dict) -> tuple:
        """Bewertet Branchen-Relevanz"""
        score = 0.0
        reasons = []
        max_score = self.weights['branch']
        
        if not self.target_branches:
            # Keine Zielbranchen → Neutrale Punktzahl
            return max_score * 0.5, ["○ Keine Zielbranchen definiert"]
        
        # Name auf Branchen prüfen
        name = (company.get('name') or '').lower()
        branche = (company.get('branche') or '').lower()
        
        matched_branches = []
        for branch in self.target_branches:
            branch_lower = branch.lower()
            if branch_lower in name or branch_lower in branche:
                matched_branches.append(branch)
        
        if matched_branches:
            score = max_score
            reasons.append(f"✓ Zielbranche: {', '.join(matched_branches)}")
        else:
            score = max_score * 0.3
            reasons.append("✗ Nicht in Zielbranchen")
        
        return score, reasons
    
    def _score_completeness(self, company: Dict) -> tuple:
        """Bewertet Datenvollständigkeit"""
        score = 0.0
        reasons = []
        max_score = self.weights['completeness']
        
        # Pflichtfelder prüfen
        fields = ['name', 'street', 'plz', 'ort', 'url']
        filled = sum(1 for f in fields if company.get(f))
        
        score = (filled / len(fields)) * max_score
        
        if filled == len(fields):
            reasons.append(f"✓ Alle {len(fields)} Pflichtfelder")
        elif filled >= len(fields) * 0.8:
            reasons.append(f"○ {filled}/{len(fields)} Pflichtfelder")
        else:
            reasons.append(f"✗ Nur {filled}/{len(fields)} Pflichtfelder")
        
        return score, reasons
    
    def _score_freshness(self, company: Dict) -> tuple:
        """Bewertet Aktualität (basierend auf crawled_at)"""
        score = 0.0
        reasons = []
        max_score = self.weights['freshness']
        
        crawled_at = company.get('crawled_at')
        if not crawled_at:
            return max_score * 0.5, ["○ Kein Crawling-Datum"]
        
        try:
            # Alter berechnen
            crawled_date = datetime.fromisoformat(crawled_at.replace('Z', '+00:00'))
            age_days = (datetime.now(crawled_date.tzinfo) - crawled_date).days
            
            if age_days <= 7:
                score = max_score
                reasons.append(f"✓ Sehr frisch: {age_days} Tage alt")
            elif age_days <= 30:
                score = max_score * 0.8
                reasons.append(f"○ Frisch: {age_days} Tage alt")
            elif age_days <= 90:
                score = max_score * 0.6
                reasons.append(f"○ Mittleres Alter: {age_days} Tage alt")
            else:
                score = max_score * 0.4
                reasons.append(f"✗ Veraltet: {age_days} Tage alt")
                
        except Exception:
            return max_score * 0.5, ["○ Ungültiges Crawling-Datum"]
        
        return score, reasons
    
    def _score_size(self, company: Dict) -> tuple:
        """Bewertet Unternehmensgröße (Schätzung basierend auf Name/Infos)"""
        score = 0.0
        reasons = []
        max_score = self.weights['size']
        
        name = (company.get('name') or '').lower()
        
        # KMU-Indikatoren im Namen
        if any(ind in name for ind in ['gmbh', 'ges.mbh', 'kg', 'og', 'eg']):
            score = max_score * 0.7
            reasons.append("○ KMU (GmbH/KG/EG)")
        elif 'ag' in name:
            score = max_score
            reasons.append("✓ Großunternehmen (AG)")
        elif any(ind in name for ind in ['e.u.', 'eu', 'selbständig', 'ingenieur']):
            score = max_score * 0.5
            reasons.append("○ Einzelperson/Einzelunternehmen")
        elif 'gmbh & co kg' in name:
            score = max_score * 0.8
            reasons.append("○ Mittelgroßes Unternehmen (GmbH & Co KG)")
        else:
            score = max_score * 0.5
            reasons.append("○ Größe unbekannt")
        
        return score, reasons
    
    def _calculate_grade(self, percentage: float) -> str:
        """Berechnet Grade basierend auf Percentage"""
        if percentage >= 90:
            return 'A'
        elif percentage >= 80:
            return 'B'
        elif percentage >= 70:
            return 'C'
        elif percentage >= 60:
            return 'D'
        else:
            return 'F'
    
    def _calculate_priority(self, percentage: float, scores: Dict) -> str:
        """Berechnet Priorität basierend auf Score und Kontext"""
        if percentage >= 80:
            return 'HIGH'
        elif percentage >= 60:
            # Prüfe ob wichtige Kriterien erfüllt sind
            contact_score = scores.get('contact', 0)
            location_score = scores.get('location', 0)
            
            if contact_score >= self.weights['contact'] * 0.7:
                return 'HIGH'
            elif location_score >= self.weights['location'] * 0.7:
                return 'MEDIUM'
            else:
                return 'MEDIUM'
        else:
            return 'LOW'
    
    def score_batch(self, companies: List[Dict], 
                    min_score: float = None,
                    sort_by: str = 'percentage') -> List[LeadScore]:
        """
        Bewertet mehrere Unternehmen und sortiert nach Score
        
        Args:
            companies: Liste von Unternehmens-Dicts
            min_score: Mindestscore (optional)
            sort_by: 'percentage', 'total_score', oder 'priority'
        
        Returns:
            Sortierte Liste von LeadScore-Objekten
        """
        results = []
        
        for company in companies:
            score = self.score(company)
            
            # Filter nach Mindestscore
            threshold = min_score if min_score is not None else self.min_score
            if score.percentage >= threshold:
                results.append(score)
        
        # Sortieren
        if sort_by == 'percentage':
            results.sort(key=lambda x: x.percentage, reverse=True)
        elif sort_by == 'total_score':
            results.sort(key=lambda x: x.total_score, reverse=True)
        elif sort_by == 'priority':
            priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
            results.sort(key=lambda x: (priority_order.get(x.priority, 99), -x.percentage))
        
        return results
    
    def get_summary(self, scores: List[LeadScore]) -> Dict:
        """
        Erstellt Zusammenfassung der Scores
        
        Returns:
            Dict mit Statistiken (total, by_grade, by_priority, avg_score)
        """
        if not scores:
            return {
                'total': 0,
                'by_grade': {},
                'by_priority': {},
                'avg_score': 0,
                'high_priority': 0
            }
        
        grades = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
        priorities = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        
        for score in scores:
            grades[score.grade] = grades.get(score.grade, 0) + 1
            priorities[score.priority] = priorities.get(score.priority, 0) + 1
        
        avg_score = sum(s.percentage for s in scores) / len(scores)
        
        return {
            'total': len(scores),
            'by_grade': grades,
            'by_priority': priorities,
            'avg_score': round(avg_score, 1),
            'high_priority': priorities['HIGH']
        }


# Vordefinierte Profile
SCORING_PROFILES = {
    'default': {
        'weights': {
            'contact': 25,
            'location': 20,
            'branch': 20,
            'completeness': 15,
            'freshness': 10,
            'size': 10,
        }
    },
    'bau': {
        'weights': {
            'contact': 30,
            'location': 25,
            'branch': 20,
            'completeness': 15,
            'freshness': 5,
            'size': 5,
        },
        'target_branches': ['bau', 'baus', 'dach', 'elektro', 'sanitär', 'heiz', 'mal', 'zimmer']
    },
    'handwerk': {
        'weights': {
            'contact': 30,
            'location': 25,
            'branch': 25,
            'completeness': 10,
            'freshness': 5,
            'size': 5,
        },
        'target_branches': ['schloss', 'schmied', 'tischler', 'zimmer', 'elektro', 'sanitär']
    },
    'local': {
        'weights': {
            'contact': 25,
            'location': 35,
            'branch': 15,
            'completeness': 15,
            'freshness': 5,
            'size': 5,
        }
    }
}


def create_scorer(profile: str = 'default', **kwargs) -> ScoringEngine:
    """
    Erstellt Scoring Engine mit vordefiniertem Profil
    
    Args:
        profile: 'default', 'bau', 'handwerk', 'local'
        **kwargs: Zusätzliche Parameter überschreiben Profil
    
    Returns:
        ScoringEngine Instanz
    """
    config = SCORING_PROFILES.get(profile, SCORING_PROFILES['default'])
    
    # Merge config mit kwargs
    final_config = {**config, **kwargs}
    
    return ScoringEngine(
        target_branches=final_config.get('target_branches'),
        center_plz=final_config.get('center_plz'),
        max_distance_km=final_config.get('max_distance_km'),
        min_score=final_config.get('min_score', 0)
    )


if __name__ == "__main__":
    print("=== Scoring Engine Test ===\n")
    
    # Test-Unternehmen
    test_companies = [
        {
            'name': 'Müller Bau GmbH',
            'street': 'Hauptstraße 10',
            'plz': '2351',
            'ort': 'Wiener Neudorf',
            'email': 'info@mueller-bau.at',
            'telefon': '02236 12345',
            'website': 'https://mueller-bau.at',
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
        {
            'name': 'AKRAS Flavours GmbH',
            'street': 'IZ-NÖ-SÜD Straße 1',
            'plz': '2351',
            'ort': 'Biedermannsdorf',
            'email': 'office@akras.at',
            'telefon': '02236 62550-0',
            'website': 'https://www.akras.at/',
            'url': 'https://firmen.wko.at/akras',
        }
    ]
    
    # Scorer mit Bau-Profil
    scorer = create_scorer(
        profile='bau',
        center_plz='2351',
        max_distance_km=30
    )
    
    # Unternehmen bewerten
    scores = scorer.score_batch(test_companies)
    
    # Zusammenfassung
    summary = scorer.get_summary(scores)
    
    print(f"Gefundene Unternehmen: {summary['total']}")
    print(f"Durchschnittlicher Score: {summary['avg_score']}%")
    print(f"Nach Priorität: {summary['by_priority']}")
    print(f"Nach Grade: {summary['by_grade']}\n")
    
    print("="*60)
    print("TOP LEADS:\n")
    
    for i, score in enumerate(scores, 1):
        print(f"{i}. {score.name}")
        print(f"   Score: {score.percentage:.1f}% ({score.grade}) - {score.priority}")
        print(f"   Gründe: {', '.join(score.reasons[:3])}")
        print()