"""
Structured summary generation for publications
Creates AI-drafted summaries for scientist review
"""

import logging
import re
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from src.pubmed_client import Publication

logger = logging.getLogger(__name__)

@dataclass
class StructuredSummary:
    """Structured summary format for publication triage"""
    executive_summary: str
    key_findings: List[str]
    clinical_relevance: str
    therapeutic_implications: str
    methodology_assessment: str
    limitations: List[str]
    meridian_relevance: str
    recommended_actions: List[str]
    confidence_level: str
    ai_generated_flag: bool = True

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

class StructuredSummarizer:
    """Generates structured summaries for publications in triage workflow"""

    def __init__(self):
        """Initialize summarizer with templates and patterns"""
        self.summary_templates = {
            'clinical_trial': self._clinical_trial_template,
            'review_article': self._review_article_template,
            'preclinical': self._preclinical_template,
            'observational': self._observational_template,
            'default': self._default_template
        }

        # Key information extraction patterns
        self.extraction_patterns = {
            'sample_size': [
                r'n\s*=\s*(\d+)',
                r'(\d+)\s+patients',
                r'(\d+)\s+subjects'
            ],
            'primary_endpoint': [
                r'primary\s+endpoint[:\s]+([^\.]+)',
                r'primary\s+outcome[:\s]+([^\.]+)'
            ],
            'results': [
                r'(overall\s+survival[^\.]+)',
                r'(progression[^\.]+survival[^\.]+)',
                r'(response\s+rate[^\.]+)',
                r'(hazard\s+ratio[^\.]+)'
            ],
            'statistical_significance': [
                r'p\s*[<>=]\s*[\d\.]+',
                r'statistical[ly]?\s+significant',
                r'confidence\s+interval'
            ]
        }

    def generate_summary(self, publication_data: Dict) -> StructuredSummary:
        """
        Generate structured summary for a publication

        Args:
            publication_data: Dictionary containing publication and classification data

        Returns:
            StructuredSummary object
        """
        publication = publication_data['publication']
        classification_data = publication_data.get('classification_metadata', {})

        # Determine publication type for template selection
        pub_type = self._classify_publication_type(publication, classification_data)

        # Generate summary using appropriate template
        summary = self.summary_templates[pub_type](publication_data)

        logger.debug(f"Generated summary for PMID {publication.pmid} (type: {pub_type})")

        return summary

    def _classify_publication_type(self, publication: Publication,
                                 classification_data: Dict) -> str:
        """Classify publication type for summary template selection"""
        pub_types = [pt.lower() for pt in publication.publication_types]
        text = (publication.title + " " + publication.abstract).lower()

        # Check for clinical trial
        if (any(pt in pub_types for pt in ['clinical trial', 'randomized controlled trial']) or
            classification_data.get('has_clinical_data', False)):
            return 'clinical_trial'

        # Check for review articles
        if any(pt in pub_types for pt in ['review', 'systematic review', 'meta-analysis']):
            return 'review_article'

        # Check for observational studies
        if any(keyword in text for keyword in ['retrospective', 'observational', 'cohort', 'case series']):
            return 'observational'

        # Check for preclinical
        if any(keyword in text for keyword in ['in vitro', 'in vivo', 'cell line', 'xenograft']):
            return 'preclinical'

        return 'default'

    def _clinical_trial_template(self, publication_data: Dict) -> StructuredSummary:
        """Template for clinical trial summaries"""
        publication = publication_data['publication']
        text = publication.title + " " + publication.abstract

        # Extract key trial information
        sample_size = self._extract_sample_size(text)
        primary_endpoint = self._extract_primary_endpoint(text)
        key_results = self._extract_key_results(text)
        significance = self._extract_statistical_significance(text)

        # Executive summary
        exec_summary = self._generate_executive_summary(
            publication, "clinical trial", sample_size, primary_endpoint, key_results
        )

        # Key findings
        key_findings = []
        if sample_size:
            key_findings.append(f"Study enrolled {sample_size} patients")
        if primary_endpoint:
            key_findings.append(f"Primary endpoint: {primary_endpoint}")
        key_findings.extend(key_results[:3])  # Top 3 results

        # Clinical relevance
        clinical_relevance = self._assess_clinical_relevance(publication_data, 'clinical_trial')

        # Therapeutic implications
        therapeutic_implications = self._assess_therapeutic_implications(publication_data)

        # Methodology assessment
        methodology = self._assess_methodology(publication_data, 'clinical_trial')

        # Limitations
        limitations = self._identify_limitations(publication_data, 'clinical_trial')

        # Meridian relevance
        meridian_relevance = self._assess_meridian_relevance(publication_data)

        # Recommended actions
        recommended_actions = self._generate_recommendations(publication_data)

        # Confidence assessment
        confidence = self._assess_confidence(publication_data)

        return StructuredSummary(
            executive_summary=exec_summary,
            key_findings=key_findings,
            clinical_relevance=clinical_relevance,
            therapeutic_implications=therapeutic_implications,
            methodology_assessment=methodology,
            limitations=limitations,
            meridian_relevance=meridian_relevance,
            recommended_actions=recommended_actions,
            confidence_level=confidence
        )

    def _review_article_template(self, publication_data: Dict) -> StructuredSummary:
        """Template for review article summaries"""
        publication = publication_data['publication']

        exec_summary = self._generate_executive_summary(
            publication, "review article", None, None, []
        )

        # Key findings from review
        key_findings = self._extract_review_key_points(publication)

        clinical_relevance = self._assess_clinical_relevance(publication_data, 'review')
        therapeutic_implications = self._assess_therapeutic_implications(publication_data)
        methodology = self._assess_methodology(publication_data, 'review')
        limitations = self._identify_limitations(publication_data, 'review')
        meridian_relevance = self._assess_meridian_relevance(publication_data)
        recommended_actions = self._generate_recommendations(publication_data)
        confidence = self._assess_confidence(publication_data)

        return StructuredSummary(
            executive_summary=exec_summary,
            key_findings=key_findings,
            clinical_relevance=clinical_relevance,
            therapeutic_implications=therapeutic_implications,
            methodology_assessment=methodology,
            limitations=limitations,
            meridian_relevance=meridian_relevance,
            recommended_actions=recommended_actions,
            confidence_level=confidence
        )

    def _preclinical_template(self, publication_data: Dict) -> StructuredSummary:
        """Template for preclinical study summaries"""
        publication = publication_data['publication']

        exec_summary = self._generate_executive_summary(
            publication, "preclinical study", None, None, []
        )

        key_findings = self._extract_preclinical_findings(publication)
        clinical_relevance = self._assess_clinical_relevance(publication_data, 'preclinical')
        therapeutic_implications = self._assess_therapeutic_implications(publication_data)
        methodology = self._assess_methodology(publication_data, 'preclinical')
        limitations = self._identify_limitations(publication_data, 'preclinical')
        meridian_relevance = self._assess_meridian_relevance(publication_data)
        recommended_actions = self._generate_recommendations(publication_data)
        confidence = self._assess_confidence(publication_data)

        return StructuredSummary(
            executive_summary=exec_summary,
            key_findings=key_findings,
            clinical_relevance=clinical_relevance,
            therapeutic_implications=therapeutic_implications,
            methodology_assessment=methodology,
            limitations=limitations,
            meridian_relevance=meridian_relevance,
            recommended_actions=recommended_actions,
            confidence_level=confidence
        )

    def _observational_template(self, publication_data: Dict) -> StructuredSummary:
        """Template for observational study summaries"""
        publication = publication_data['publication']

        exec_summary = self._generate_executive_summary(
            publication, "observational study", None, None, []
        )

        key_findings = self._extract_observational_findings(publication)
        clinical_relevance = self._assess_clinical_relevance(publication_data, 'observational')
        therapeutic_implications = self._assess_therapeutic_implications(publication_data)
        methodology = self._assess_methodology(publication_data, 'observational')
        limitations = self._identify_limitations(publication_data, 'observational')
        meridian_relevance = self._assess_meridian_relevance(publication_data)
        recommended_actions = self._generate_recommendations(publication_data)
        confidence = self._assess_confidence(publication_data)

        return StructuredSummary(
            executive_summary=exec_summary,
            key_findings=key_findings,
            clinical_relevance=clinical_relevance,
            therapeutic_implications=therapeutic_implications,
            methodology_assessment=methodology,
            limitations=limitations,
            meridian_relevance=meridian_relevance,
            recommended_actions=recommended_actions,
            confidence_level=confidence
        )

    def _default_template(self, publication_data: Dict) -> StructuredSummary:
        """Default template for unclassified publications"""
        publication = publication_data['publication']

        exec_summary = f"Study titled '{publication.title}' published in {publication.journal}. " \
                      f"Further classification needed to determine study type and clinical relevance."

        key_findings = ["Study requires manual review for proper classification"]
        clinical_relevance = "Unknown - requires manual assessment"
        therapeutic_implications = "To be determined upon detailed review"
        methodology = "Assessment pending detailed review"
        limitations = ["Classification uncertainty limits automatic assessment"]
        meridian_relevance = self._assess_meridian_relevance(publication_data)
        recommended_actions = ["Manual review and classification required"]
        confidence = "Low - requires human review"

        return StructuredSummary(
            executive_summary=exec_summary,
            key_findings=key_findings,
            clinical_relevance=clinical_relevance,
            therapeutic_implications=therapeutic_implications,
            methodology_assessment=methodology,
            limitations=limitations,
            meridian_relevance=meridian_relevance,
            recommended_actions=recommended_actions,
            confidence_level=confidence
        )

    def _generate_executive_summary(self, publication: Publication, study_type: str,
                                  sample_size: Optional[int], primary_endpoint: Optional[str],
                                  key_results: List[str]) -> str:
        """Generate executive summary based on publication data"""
        summary_parts = []

        # Basic study description
        summary_parts.append(f"This {study_type} titled '{publication.title}' "
                           f"was published in {publication.journal}")

        # Add study details if available
        if sample_size:
            summary_parts.append(f"involving {sample_size} patients")

        if primary_endpoint:
            summary_parts.append(f"with primary endpoint of {primary_endpoint}")

        # Add key results if available
        if key_results:
            summary_parts.append(f"Key findings include: {'. '.join(key_results[:2])}")

        return ". ".join(summary_parts) + "."

    def _extract_sample_size(self, text: str) -> Optional[int]:
        """Extract sample size from text"""
        for pattern in self.extraction_patterns['sample_size']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    return int(matches[0])
                except ValueError:
                    continue
        return None

    def _extract_primary_endpoint(self, text: str) -> Optional[str]:
        """Extract primary endpoint from text"""
        for pattern in self.extraction_patterns['primary_endpoint']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        return None

    def _extract_key_results(self, text: str) -> List[str]:
        """Extract key results from text"""
        results = []
        for pattern in self.extraction_patterns['results']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            results.extend(matches)
        return results[:5]  # Limit to top 5 results

    def _extract_statistical_significance(self, text: str) -> List[str]:
        """Extract statistical significance information"""
        significance = []
        for pattern in self.extraction_patterns['statistical_significance']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            significance.extend(matches)
        return significance

    def _extract_review_key_points(self, publication: Publication) -> List[str]:
        """Extract key points from review articles"""
        # This would be enhanced with more sophisticated NLP
        abstract = publication.abstract.lower()

        key_points = []
        if 'meta-analysis' in abstract:
            key_points.append("Meta-analysis of multiple studies")
        if 'systematic review' in abstract:
            key_points.append("Systematic review of literature")
        if 'current evidence' in abstract:
            key_points.append("Synthesis of current evidence")

        return key_points or ["Review article - detailed analysis required"]

    def _extract_preclinical_findings(self, publication: Publication) -> List[str]:
        """Extract key findings from preclinical studies"""
        abstract = publication.abstract.lower()
        findings = []

        if 'in vitro' in abstract:
            findings.append("In vitro experimental data")
        if 'in vivo' in abstract:
            findings.append("In vivo animal model data")
        if 'mechanism' in abstract:
            findings.append("Mechanistic insights provided")

        return findings or ["Preclinical study - detailed review needed"]

    def _extract_observational_findings(self, publication: Publication) -> List[str]:
        """Extract key findings from observational studies"""
        abstract = publication.abstract.lower()
        findings = []

        if 'retrospective' in abstract:
            findings.append("Retrospective analysis")
        if 'cohort' in abstract:
            findings.append("Cohort study design")
        if 'real world' in abstract:
            findings.append("Real-world evidence")

        return findings or ["Observational study findings"]

    def _assess_clinical_relevance(self, publication_data: Dict, study_type: str) -> str:
        """Assess clinical relevance based on study type and data"""
        priority_score = publication_data.get('priority_score', 0)
        therapeutic_areas = publication_data.get('therapeutic_areas', [])

        if priority_score >= 8:
            relevance = "High clinical relevance"
        elif priority_score >= 6:
            relevance = "Moderate clinical relevance"
        else:
            relevance = "Limited clinical relevance"

        # Add context based on study type
        if study_type == 'clinical_trial':
            relevance += " - Clinical trial data directly applicable to patient care"
        elif study_type == 'review':
            relevance += " - Provides comprehensive overview of current knowledge"

        return relevance

    def _assess_therapeutic_implications(self, publication_data: Dict) -> str:
        """Assess therapeutic implications for Meridian's pipeline"""
        therapeutic_areas = publication_data.get('therapeutic_areas', [])
        priority_score = publication_data.get('priority_score', 0)

        if not therapeutic_areas:
            return "Therapeutic implications unclear - requires further assessment"

        implications = []
        for area_result in therapeutic_areas:
            area_name = area_result.category if hasattr(area_result, 'category') else area_result

            if area_name == 'immunotherapy':
                implications.append("Relevant to immunotherapy development")
            elif area_name == 'targeted_therapy':
                implications.append("Insights for targeted therapy approaches")
            elif area_name == 'biomarkers':
                implications.append("Potential biomarker applications")

        if priority_score >= 7:
            implications.append("May inform strategic pipeline decisions")

        return ". ".join(implications) or "General therapeutic relevance"

    def _assess_methodology(self, publication_data: Dict, study_type: str) -> str:
        """Assess study methodology quality"""
        ranking_criteria = publication_data.get('ranking_criteria')

        if ranking_criteria:
            methodology_score = getattr(ranking_criteria, 'methodology_score', 0)

            if methodology_score >= 0.8:
                assessment = "Strong methodology"
            elif methodology_score >= 0.6:
                assessment = "Adequate methodology"
            else:
                assessment = "Methodology requires careful evaluation"
        else:
            assessment = "Methodology assessment pending"

        # Add study-type specific notes
        if study_type == 'clinical_trial':
            assessment += " - Clinical trial design and execution should be reviewed"
        elif study_type == 'review':
            assessment += " - Review methodology and source selection criteria important"

        return assessment

    def _identify_limitations(self, publication_data: Dict, study_type: str) -> List[str]:
        """Identify study limitations"""
        limitations = []

        priority_score = publication_data.get('priority_score', 0)
        if priority_score < 5:
            limitations.append("Lower priority score suggests significant limitations")

        # Study-type specific limitations
        if study_type == 'observational':
            limitations.append("Observational design limits causal inference")
        elif study_type == 'preclinical':
            limitations.append("Preclinical findings may not translate to human patients")

        # General limitation assessment
        limitations.append("Detailed limitation assessment requires full-text review")

        return limitations

    def _assess_meridian_relevance(self, publication_data: Dict) -> str:
        """Assess specific relevance to Meridian Therapeutics"""
        therapeutic_areas = publication_data.get('therapeutic_areas', [])
        priority_score = publication_data.get('priority_score', 0)

        if not therapeutic_areas:
            return "Meridian relevance unclear - therapeutic area not well-defined"

        relevance_factors = []

        # Check for key therapeutic areas
        for area_result in therapeutic_areas:
            area_name = area_result.category if hasattr(area_result, 'category') else area_result

            if area_name in ['oncology', 'immunotherapy']:
                relevance_factors.append(f"Direct relevance to {area_name} focus")
            elif area_name == 'targeted_therapy':
                relevance_factors.append("Aligns with precision medicine approach")

        if priority_score >= 8:
            relevance_factors.append("High priority for competitive intelligence")

        return ". ".join(relevance_factors) or "General relevance to therapeutic development"

    def _generate_recommendations(self, publication_data: Dict) -> List[str]:
        """Generate recommended actions based on publication analysis"""
        recommendations = []
        priority_score = publication_data.get('priority_score', 0)
        priority_category = publication_data.get('priority_category', 'Low')

        if priority_category == 'High':
            recommendations.append("Immediate scientist review recommended")
            recommendations.append("Consider for competitive intelligence briefing")
        elif priority_category == 'Medium':
            recommendations.append("Schedule for weekly team review")

        # Study-specific recommendations
        publication = publication_data['publication']
        if publication.full_text_available:
            recommendations.append("Full-text review available for detailed analysis")

        if not recommendations:
            recommendations.append("Add to weekly literature monitoring")

        return recommendations

    def _assess_confidence(self, publication_data: Dict) -> str:
        """Assess confidence in the AI-generated summary"""
        relevance_score = publication_data.get('relevance_score', 0)
        priority_score = publication_data.get('priority_score', 0)

        if relevance_score >= 0.8 and priority_score >= 7:
            return "High confidence in assessment"
        elif relevance_score >= 0.6 and priority_score >= 5:
            return "Moderate confidence - human review recommended"
        else:
            return "Low confidence - requires human expert review"

def main():
    """Test summarizer module"""
    # This would be used for testing the summarizer
    pass

if __name__ == "__main__":
    main()