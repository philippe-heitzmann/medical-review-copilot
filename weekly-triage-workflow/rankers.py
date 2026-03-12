"""
Ranking modules for prioritizing publications by clinical relevance and impact
"""

import logging
import math
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from src.pubmed_client import Publication

logger = logging.getLogger(__name__)

@dataclass
class RankingCriteria:
    """Criteria for ranking publications"""
    clinical_impact: float = 0.0
    novelty_score: float = 0.0
    methodology_score: float = 0.0
    relevance_to_pipeline: float = 0.0
    publication_quality: float = 0.0
    recency_score: float = 0.0

class ClinicalRelevanceRanker:
    """Ranks publications by clinical relevance and strategic importance to Meridian"""

    def __init__(self):
        """Initialize ranker with scoring parameters"""
        self.clinical_keywords = {
            'phase_3': ['phase iii', 'phase 3', 'pivotal trial', 'registration trial'],
            'phase_2': ['phase ii', 'phase 2', 'dose finding', 'proof of concept'],
            'phase_1': ['phase i', 'phase 1', 'first in human', 'dose escalation'],
            'real_world': ['real world', 'retrospective', 'observational', 'registry'],
            'meta_analysis': ['meta-analysis', 'systematic review', 'pooled analysis']
        }

        self.impact_indicators = {
            'primary_endpoint': ['primary endpoint', 'overall survival', 'progression free survival'],
            'regulatory': ['fda approval', 'ema approval', 'breakthrough designation'],
            'biomarker': ['companion diagnostic', 'predictive biomarker', 'precision medicine'],
            'safety_signals': ['adverse event', 'black box warning', 'safety signal']
        }

        self.methodology_indicators = {
            'randomized': ['randomized', 'rct', 'controlled trial'],
            'double_blind': ['double blind', 'double-blind', 'placebo controlled'],
            'multicenter': ['multicenter', 'multi-center', 'international'],
            'large_sample': ['n=', 'patients=', 'subjects=']  # Will check for large N
        }

        # Journal impact factors (simplified scoring)
        self.journal_tiers = {
            'tier_1': {
                'journals': ['new england journal of medicine', 'nature', 'science',
                           'cell', 'lancet', 'jama'],
                'score': 1.0
            },
            'tier_2': {
                'journals': ['journal of clinical oncology', 'nature medicine',
                           'cancer cell', 'clinical cancer research'],
                'score': 0.9
            },
            'tier_3': {
                'journals': ['cancer research', 'oncogene', 'molecular cancer therapeutics'],
                'score': 0.7
            },
            'tier_4': {
                'journals': ['cancer letters', 'international journal of cancer'],
                'score': 0.5
            }
        }

    def rank_publications(self, classified_publications: List[Dict]) -> List[Dict]:
        """
        Rank publications by clinical relevance

        Args:
            classified_publications: List of classified publication dictionaries

        Returns:
            List of ranked publications with priority scores
        """
        ranked_publications = []

        for pub_data in classified_publications:
            publication = pub_data['publication']

            # Calculate ranking criteria
            criteria = self._calculate_ranking_criteria(pub_data)

            # Calculate overall priority score
            priority_score = self._calculate_priority_score(criteria)

            # Add ranking information
            pub_data.update({
                'ranking_criteria': criteria,
                'priority_score': priority_score,
                'priority_rank': self._score_to_rank(priority_score),
                'priority_category': self._categorize_priority(priority_score)
            })

            ranked_publications.append(pub_data)

        # Sort by priority score (highest first)
        ranked_publications.sort(key=lambda x: x['priority_score'], reverse=True)

        # Add rank position
        for i, pub_data in enumerate(ranked_publications):
            pub_data['rank_position'] = i + 1

        logger.info(f"Ranked {len(ranked_publications)} publications")
        return ranked_publications

    def _calculate_ranking_criteria(self, pub_data: Dict) -> RankingCriteria:
        """Calculate individual ranking criteria for publication"""
        publication = pub_data['publication']
        text = (publication.title + " " + publication.abstract).lower()

        criteria = RankingCriteria()

        # Clinical impact scoring
        criteria.clinical_impact = self._score_clinical_impact(text, publication)

        # Novelty scoring
        criteria.novelty_score = self._score_novelty(text, publication)

        # Methodology scoring
        criteria.methodology_score = self._score_methodology(text, publication)

        # Pipeline relevance (based on therapeutic areas)
        criteria.relevance_to_pipeline = self._score_pipeline_relevance(pub_data)

        # Publication quality (journal + pub type)
        criteria.publication_quality = self._score_publication_quality(publication)

        # Recency scoring
        criteria.recency_score = self._score_recency(publication)

        return criteria

    def _score_clinical_impact(self, text: str, publication: Publication) -> float:
        """Score clinical impact based on study phase and endpoints"""
        impact_score = 0.0

        # Phase scoring (higher phases = higher impact)
        phase_scores = {
            'phase_3': 1.0,
            'phase_2': 0.7,
            'phase_1': 0.4,
            'meta_analysis': 0.9,
            'real_world': 0.6
        }

        for phase_type, keywords in self.clinical_keywords.items():
            if any(keyword in text for keyword in keywords):
                impact_score = max(impact_score, phase_scores[phase_type])

        # Impact indicator bonuses
        for indicator_type, keywords in self.impact_indicators.items():
            if any(keyword in text for keyword in keywords):
                if indicator_type == 'primary_endpoint':
                    impact_score += 0.3
                elif indicator_type == 'regulatory':
                    impact_score += 0.4
                elif indicator_type == 'biomarker':
                    impact_score += 0.2
                elif indicator_type == 'safety_signals':
                    impact_score += 0.2

        # Sample size bonus (for clinical trials)
        sample_size_bonus = self._extract_sample_size_bonus(text)
        impact_score += sample_size_bonus

        return min(impact_score, 1.0)  # Cap at 1.0

    def _score_novelty(self, text: str, publication: Publication) -> float:
        """Score novelty based on new mechanisms, targets, or approaches"""
        novelty_keywords = [
            'novel', 'first', 'new', 'unprecedented', 'breakthrough',
            'innovative', 'first-in-class', 'best-in-class'
        ]

        mechanism_keywords = [
            'mechanism of action', 'target', 'pathway', 'biomarker',
            'resistance mechanism', 'novel target'
        ]

        novelty_score = 0.0

        # Basic novelty indicators
        novelty_count = sum(1 for keyword in novelty_keywords if keyword in text)
        novelty_score += min(novelty_count * 0.15, 0.6)

        # Mechanism/target novelty
        mechanism_count = sum(1 for keyword in mechanism_keywords if keyword in text)
        novelty_score += min(mechanism_count * 0.1, 0.4)

        # Publication date bonus (more recent = potentially more novel)
        if publication.publication_date != "Unknown":
            try:
                # Simple year extraction
                year = int(publication.publication_date.split('-')[0])
                current_year = datetime.now().year
                if year >= current_year:
                    novelty_score += 0.2
                elif year >= current_year - 1:
                    novelty_score += 0.1
            except:
                pass

        return min(novelty_score, 1.0)

    def _score_methodology(self, text: str, publication: Publication) -> float:
        """Score study methodology quality"""
        methodology_score = 0.0

        # Study design quality
        design_scores = {
            'randomized': 0.4,
            'double_blind': 0.3,
            'multicenter': 0.2
        }

        for design_type, keywords in self.methodology_indicators.items():
            if design_type in design_scores:
                if any(keyword in text for keyword in keywords):
                    methodology_score += design_scores[design_type]

        # Sample size consideration
        if self._has_large_sample_size(text):
            methodology_score += 0.1

        return min(methodology_score, 1.0)

    def _score_pipeline_relevance(self, pub_data: Dict) -> float:
        """Score relevance to Meridian's pipeline based on therapeutic areas"""
        therapeutic_areas = pub_data.get('therapeutic_areas', [])

        # Prioritize areas based on Meridian's focus
        area_priorities = {
            'oncology': 1.0,
            'immunotherapy': 0.95,
            'targeted_therapy': 0.9,
            'biomarkers': 0.7,
            'drug_development': 0.6
        }

        if not therapeutic_areas:
            return 0.0

        # Take highest priority area
        max_priority = 0.0
        for area_result in therapeutic_areas:
            area_name = area_result.category if hasattr(area_result, 'category') else area_result
            priority = area_priorities.get(area_name, 0.3)

            # Weight by confidence if available
            if hasattr(area_result, 'confidence'):
                priority *= area_result.confidence

            max_priority = max(max_priority, priority)

        return max_priority

    def _score_publication_quality(self, publication: Publication) -> float:
        """Score publication quality based on journal and publication type"""
        journal_name = publication.journal.lower()

        # Journal tier scoring
        journal_score = 0.3  # Default score

        for tier_name, tier_data in self.journal_tiers.items():
            for journal in tier_data['journals']:
                if journal in journal_name:
                    journal_score = tier_data['score']
                    break

        # Publication type bonus
        pub_type_bonus = 0.0
        pub_types = [pt.lower() for pt in publication.publication_types]

        if any(pt in pub_types for pt in ['clinical trial', 'randomized controlled trial']):
            pub_type_bonus = 0.3
        elif any(pt in pub_types for pt in ['meta-analysis', 'systematic review']):
            pub_type_bonus = 0.25
        elif 'review' in pub_types:
            pub_type_bonus = 0.15

        return min(journal_score + pub_type_bonus, 1.0)

    def _score_recency(self, publication: Publication) -> float:
        """Score based on publication recency"""
        if publication.publication_date == "Unknown":
            return 0.5  # Default score

        try:
            # Extract year from publication date
            year = int(publication.publication_date.split('-')[0])
            current_year = datetime.now().year

            years_ago = current_year - year

            if years_ago <= 0:
                return 1.0  # Current year
            elif years_ago == 1:
                return 0.8
            elif years_ago == 2:
                return 0.6
            elif years_ago <= 5:
                return 0.4
            else:
                return 0.1  # Older than 5 years

        except:
            return 0.5  # Default if date parsing fails

    def _calculate_priority_score(self, criteria: RankingCriteria) -> float:
        """Calculate overall priority score from criteria"""
        # Weighted combination of criteria
        weights = {
            'clinical_impact': 0.35,
            'relevance_to_pipeline': 0.25,
            'publication_quality': 0.15,
            'methodology_score': 0.10,
            'novelty_score': 0.10,
            'recency_score': 0.05
        }

        weighted_score = (
            criteria.clinical_impact * weights['clinical_impact'] +
            criteria.relevance_to_pipeline * weights['relevance_to_pipeline'] +
            criteria.publication_quality * weights['publication_quality'] +
            criteria.methodology_score * weights['methodology_score'] +
            criteria.novelty_score * weights['novelty_score'] +
            criteria.recency_score * weights['recency_score']
        )

        # Scale to 0-10 for easier interpretation
        return weighted_score * 10.0

    def _score_to_rank(self, score: float) -> int:
        """Convert priority score to 1-10 rank"""
        return min(max(round(score), 1), 10)

    def _categorize_priority(self, score: float) -> str:
        """Categorize priority level"""
        if score >= 8.0:
            return "High"
        elif score >= 6.0:
            return "Medium"
        elif score >= 4.0:
            return "Low"
        else:
            return "Very Low"

    def _extract_sample_size_bonus(self, text: str) -> float:
        """Extract sample size and give bonus for large studies"""
        import re

        # Look for sample size patterns
        patterns = [
            r'n\s*=\s*(\d+)',
            r'(\d+)\s+patients',
            r'(\d+)\s+subjects',
            r'sample\s+size\s+of\s+(\d+)'
        ]

        max_n = 0
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    n = int(match)
                    max_n = max(max_n, n)
                except ValueError:
                    continue

        # Bonus based on sample size
        if max_n >= 1000:
            return 0.3
        elif max_n >= 500:
            return 0.2
        elif max_n >= 100:
            return 0.1
        else:
            return 0.0

    def _has_large_sample_size(self, text: str) -> bool:
        """Check if study has large sample size (>100)"""
        return self._extract_sample_size_bonus(text) > 0.0

def main():
    """Test ranking module"""
    # This would be used for testing the ranker
    pass

if __name__ == "__main__":
    main()