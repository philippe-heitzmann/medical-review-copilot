"""
Classification modules for publication relevance and therapeutic area classification
"""

import re
import logging
from typing import List, Dict, Tuple
from dataclasses import dataclass
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from src.pubmed_client import Publication

logger = logging.getLogger(__name__)

@dataclass
class ClassificationResult:
    """Classification result structure"""
    category: str
    confidence: float
    evidence: List[str]

class RelevanceClassifier:
    """Classifies publications by relevance to Meridian's therapeutic focus"""

    def __init__(self):
        """Initialize relevance classifier with scoring criteria"""
        self.relevance_keywords = {
            # High relevance - core therapeutic areas
            'high': {
                'oncology': ['cancer', 'tumor', 'neoplasm', 'carcinoma', 'sarcoma',
                           'lymphoma', 'leukemia', 'melanoma', 'metastasis'],
                'immunotherapy': ['immunotherapy', 'checkpoint inhibitor', 'pd-1', 'pd-l1',
                                'ctla-4', 'car-t', 'adoptive cell therapy', 'immune response'],
                'targeted_therapy': ['targeted therapy', 'precision medicine', 'biomarker',
                                   'companion diagnostic', 'molecular target'],
                'drug_development': ['clinical trial', 'drug development', 'pharmaceutical',
                                   'therapeutic', 'treatment', 'efficacy', 'safety']
            },
            # Medium relevance - related areas
            'medium': {
                'diagnostics': ['diagnostic', 'biomarker', 'imaging', 'screening'],
                'resistance': ['resistance', 'refractory', 'relapse', 'progression'],
                'combination': ['combination therapy', 'synergy', 'adjuvant', 'neoadjuvant'],
                'toxicity': ['adverse event', 'toxicity', 'side effect', 'safety profile']
            },
            # Low relevance - general medical
            'low': {
                'general': ['medicine', 'health', 'patient', 'clinical', 'medical']
            }
        }

        self.mesh_weights = {
            'Neoplasms': 3.0,
            'Immunotherapy': 3.0,
            'Antineoplastic Agents': 2.5,
            'Drug Therapy': 2.0,
            'Clinical Trials': 2.0,
            'Biomarkers': 1.5,
            'Precision Medicine': 2.5
        }

    def score_publication(self, publication: Publication) -> float:
        """
        Score publication relevance (0.0 to 1.0)

        Args:
            publication: Publication object to score

        Returns:
            Relevance score between 0.0 and 1.0
        """
        scores = []

        # Text-based scoring
        text_score = self._score_text_relevance(publication)
        scores.append(('text', text_score, 0.4))  # 40% weight

        # MeSH term scoring
        mesh_score = self._score_mesh_relevance(publication)
        scores.append(('mesh', mesh_score, 0.3))  # 30% weight

        # Journal relevance
        journal_score = self._score_journal_relevance(publication)
        scores.append(('journal', journal_score, 0.2))  # 20% weight

        # Publication type bonus
        pub_type_score = self._score_publication_type(publication)
        scores.append(('pub_type', pub_type_score, 0.1))  # 10% weight

        # Calculate weighted score
        total_score = sum(score * weight for _, score, weight in scores)
        normalized_score = min(total_score, 1.0)  # Cap at 1.0

        logger.debug(f"Relevance scoring for PMID {publication.pmid}: {normalized_score:.3f}")
        logger.debug(f"Score breakdown: {scores}")

        return normalized_score

    def _score_text_relevance(self, publication: Publication) -> float:
        """Score relevance based on title and abstract text"""
        text = (publication.title + " " + publication.abstract).lower()

        high_score = self._count_keyword_matches(text, self.relevance_keywords['high'])
        medium_score = self._count_keyword_matches(text, self.relevance_keywords['medium'])
        low_score = self._count_keyword_matches(text, self.relevance_keywords['low'])

        # Weighted scoring
        total_score = (high_score * 3.0 + medium_score * 1.5 + low_score * 0.5)

        # Normalize by text length (rough proxy for content amount)
        text_length_factor = min(len(text.split()) / 200.0, 1.0)  # Normalize to ~200 words

        normalized_score = min(total_score * text_length_factor / 10.0, 1.0)
        return normalized_score

    def _score_mesh_relevance(self, publication: Publication) -> float:
        """Score relevance based on MeSH terms"""
        if not publication.mesh_terms:
            return 0.0

        total_weight = 0.0
        matched_terms = 0

        for mesh_term in publication.mesh_terms:
            for key_mesh, weight in self.mesh_weights.items():
                if key_mesh.lower() in mesh_term.descriptor.lower():
                    # Major topic gets bonus
                    term_weight = weight * (1.5 if mesh_term.major_topic else 1.0)
                    total_weight += term_weight
                    matched_terms += 1

        # Normalize by number of MeSH terms
        if len(publication.mesh_terms) > 0:
            normalized_score = min(total_weight / (len(publication.mesh_terms) * 2.0), 1.0)
        else:
            normalized_score = 0.0

        return normalized_score

    def _score_journal_relevance(self, publication: Publication) -> float:
        """Score relevance based on journal"""
        high_impact_oncology_journals = [
            'nature', 'science', 'cell', 'new england journal of medicine',
            'lancet', 'journal of clinical oncology', 'cancer cell',
            'nature medicine', 'cancer research', 'clinical cancer research'
        ]

        medium_impact_journals = [
            'oncogene', 'cancer letters', 'international journal of cancer',
            'molecular cancer therapeutics', 'cancer immunology research'
        ]

        journal_name = publication.journal.lower()

        for journal in high_impact_oncology_journals:
            if journal in journal_name:
                return 1.0

        for journal in medium_impact_journals:
            if journal in journal_name:
                return 0.7

        # Generic oncology/medical relevance
        oncology_keywords = ['cancer', 'oncology', 'tumor', 'immunotherapy']
        if any(keyword in journal_name for keyword in oncology_keywords):
            return 0.5

        return 0.2  # Base score for any medical journal

    def _score_publication_type(self, publication: Publication) -> float:
        """Score based on publication type"""
        pub_types = [pt.lower() for pt in publication.publication_types]

        # Clinical studies and trials are highly relevant
        if any(pt in pub_types for pt in ['clinical trial', 'randomized controlled trial']):
            return 1.0

        # Reviews can be valuable for context
        if any(pt in pub_types for pt in ['review', 'systematic review', 'meta-analysis']):
            return 0.8

        # Original research
        if 'journal article' in pub_types:
            return 0.6

        return 0.3  # Default score

    def _count_keyword_matches(self, text: str, keyword_categories: Dict[str, List[str]]) -> int:
        """Count keyword matches in text"""
        total_matches = 0

        for category, keywords in keyword_categories.items():
            for keyword in keywords:
                # Use word boundaries to avoid partial matches
                pattern = r'\b' + re.escape(keyword) + r'\b'
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                total_matches += matches

        return total_matches

class TherapeuticAreaClassifier:
    """Classifies publications into therapeutic areas relevant to Meridian"""

    def __init__(self):
        """Initialize therapeutic area classifier"""
        self.therapeutic_areas = {
            'oncology': {
                'keywords': ['cancer', 'tumor', 'neoplasm', 'carcinoma', 'oncology',
                           'malignant', 'metastasis', 'chemotherapy', 'radiotherapy'],
                'mesh_terms': ['neoplasms', 'carcinoma', 'adenocarcinoma'],
                'confidence_threshold': 0.3
            },
            'immunotherapy': {
                'keywords': ['immunotherapy', 'immune checkpoint', 'pd-1', 'pd-l1',
                           'ctla-4', 'car-t', 'adoptive cell therapy', 'monoclonal antibody'],
                'mesh_terms': ['immunotherapy', 'antibodies, monoclonal'],
                'confidence_threshold': 0.4
            },
            'targeted_therapy': {
                'keywords': ['targeted therapy', 'precision medicine', 'personalized medicine',
                           'molecular target', 'kinase inhibitor', 'small molecule'],
                'mesh_terms': ['precision medicine', 'molecular targeted therapy'],
                'confidence_threshold': 0.35
            },
            'drug_development': {
                'keywords': ['drug development', 'pharmaceutical', 'clinical trial',
                           'phase i', 'phase ii', 'phase iii', 'drug discovery'],
                'mesh_terms': ['drug development', 'clinical trials as topic'],
                'confidence_threshold': 0.3
            },
            'biomarkers': {
                'keywords': ['biomarker', 'companion diagnostic', 'predictive marker',
                           'prognostic marker', 'molecular signature'],
                'mesh_terms': ['biomarkers', 'genetic markers'],
                'confidence_threshold': 0.4
            }
        }

    def classify_publication(self, publication: Publication) -> List[ClassificationResult]:
        """
        Classify publication into therapeutic areas

        Args:
            publication: Publication to classify

        Returns:
            List of classification results with confidence scores
        """
        results = []

        for area_name, area_config in self.therapeutic_areas.items():
            confidence, evidence = self._calculate_area_confidence(
                publication, area_config
            )

            if confidence >= area_config['confidence_threshold']:
                result = ClassificationResult(
                    category=area_name,
                    confidence=confidence,
                    evidence=evidence
                )
                results.append(result)

        # Sort by confidence
        results.sort(key=lambda x: x.confidence, reverse=True)

        logger.debug(f"Therapeutic area classification for PMID {publication.pmid}: "
                    f"{[r.category for r in results]}")

        return results

    def _calculate_area_confidence(self, publication: Publication,
                                 area_config: Dict) -> Tuple[float, List[str]]:
        """Calculate confidence score for a therapeutic area"""
        evidence = []

        # Text-based scoring
        text = (publication.title + " " + publication.abstract).lower()
        keyword_matches = 0

        for keyword in area_config['keywords']:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                keyword_matches += len(matches)
                evidence.append(f"Keyword: {keyword} ({len(matches)} matches)")

        text_score = min(keyword_matches / 5.0, 1.0)  # Normalize to 0-1

        # MeSH term scoring
        mesh_score = 0.0
        for mesh_term in publication.mesh_terms:
            for area_mesh in area_config['mesh_terms']:
                if area_mesh.lower() in mesh_term.descriptor.lower():
                    mesh_score += 0.3 * (1.5 if mesh_term.major_topic else 1.0)
                    evidence.append(f"MeSH: {mesh_term.descriptor}")

        mesh_score = min(mesh_score, 1.0)

        # Combined confidence
        confidence = (text_score * 0.7 + mesh_score * 0.3)

        return confidence, evidence

def main():
    """Test classification modules"""
    # This would be used for testing the classifiers
    pass

if __name__ == "__main__":
    main()