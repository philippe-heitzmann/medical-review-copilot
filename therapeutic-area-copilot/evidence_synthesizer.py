"""
Evidence Synthesizer - Synthesizes evidence from multiple sources
Handles consensus building, conflict detection, and strength assessment
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re
from collections import defaultdict, Counter
import statistics

logger = logging.getLogger(__name__)

@dataclass
class EvidenceItem:
    """Individual piece of evidence with metadata"""
    pmid: str
    study_type: str
    evidence_quality: str
    finding: str
    confidence: float
    population_size: Optional[int] = None
    statistical_significance: Optional[bool] = None
    effect_size: Optional[float] = None
    journal_impact: Optional[str] = None

@dataclass
class Consensus:
    """Consensus finding across multiple studies"""
    finding: str
    supporting_studies: List[str]
    confidence_level: str
    strength_of_evidence: str
    consistency_score: float
    statistical_summary: Optional[Dict] = None

@dataclass
class Conflict:
    """Conflicting evidence between studies"""
    conflicting_findings: List[str]
    study_groups: List[List[str]]
    potential_explanations: List[str]
    resolution_suggestions: List[str]

@dataclass
class EvidenceSynthesis:
    """Complete evidence synthesis result"""
    summary: str
    key_findings: List[str]
    consensus: List[Consensus]
    conflicts: List[Conflict]
    strength_assessment: Dict
    gaps: List[str]
    confidence: str
    recommendations: List[str]

class EvidenceSynthesizer:
    """Synthesizes evidence from multiple medical literature sources"""

    def __init__(self, config: Dict):
        """Initialize evidence synthesizer"""
        self.config = config
        self.max_evidence_pieces = config.get('max_evidence_pieces', 10)
        self.synthesis_method = config.get('synthesis_method', 'weighted_consensus')
        self.conflict_detection = config.get('conflict_detection', True)

        # Evidence quality weights
        self.quality_weights = {
            'high': 1.0,
            'medium': 0.7,
            'low': 0.4
        }

        # Study type hierarchy
        self.study_type_hierarchy = {
            'meta_analysis': 1.0,
            'systematic_review': 0.9,
            'clinical_trial': 0.8,
            'observational': 0.6,
            'research_article': 0.5,
            'review': 0.3
        }

        # Statistical significance patterns
        self.stat_patterns = {
            'p_value': r'p\s*[<>=]\s*([\d\.]+)',
            'ci': r'(\d+)%\s*(?:confidence\s+interval|ci)[:\s]*([\d\.\-\s,\(\)]+)',
            'hr': r'(?:hazard\s+ratio|hr)[:\s]*([\d\.]+)',
            'or': r'(?:odds\s+ratio|or)[:\s]*([\d\.]+)',
            'rr': r'(?:relative\s+risk|rr)[:\s]*([\d\.]+)'
        }

    def synthesize_evidence(self, topic: str, evidence_pieces: List[Dict]) -> EvidenceSynthesis:
        """
        Synthesize evidence from multiple sources

        Args:
            topic: Topic being synthesized
            evidence_pieces: List of evidence pieces

        Returns:
            Comprehensive evidence synthesis
        """
        logger.info(f"Synthesizing evidence for topic: {topic}")

        if not evidence_pieces:
            return self._create_empty_synthesis(topic)

        try:
            # Convert to standardized evidence items
            evidence_items = self._standardize_evidence(evidence_pieces)

            # Extract findings and group similar ones
            grouped_findings = self._group_similar_findings(evidence_items)

            # Build consensus for each finding group
            consensus_results = self._build_consensus(grouped_findings)

            # Detect conflicts
            conflicts = self._detect_conflicts(grouped_findings) if self.conflict_detection else []

            # Assess overall strength of evidence
            strength_assessment = self._assess_evidence_strength(evidence_items)

            # Identify evidence gaps
            gaps = self._identify_evidence_gaps(evidence_items, topic)

            # Generate synthesis summary
            summary = self._generate_synthesis_summary(consensus_results, conflicts, strength_assessment)

            # Extract key findings
            key_findings = self._extract_key_findings(consensus_results)

            # Assess overall confidence
            overall_confidence = self._assess_overall_confidence(
                consensus_results, conflicts, strength_assessment
            )

            # Generate recommendations
            recommendations = self._generate_recommendations(
                consensus_results, conflicts, gaps, strength_assessment
            )

            return EvidenceSynthesis(
                summary=summary,
                key_findings=key_findings,
                consensus=consensus_results,
                conflicts=conflicts,
                strength_assessment=strength_assessment,
                gaps=gaps,
                confidence=overall_confidence,
                recommendations=recommendations
            )

        except Exception as e:
            logger.error(f"Evidence synthesis failed: {e}")
            return self._create_error_synthesis(topic, str(e))

    def _standardize_evidence(self, evidence_pieces: List[Dict]) -> List[EvidenceItem]:
        """Convert evidence pieces to standardized format"""
        evidence_items = []

        for piece in evidence_pieces:
            try:
                # Extract key information
                pmid = piece.get('pmid', '')
                study_type = piece.get('study_type', 'research_article')
                evidence_quality = piece.get('evidence_quality', 'medium')

                # Extract findings from relevant text
                relevant_text = piece.get('relevant_text', [])
                if isinstance(relevant_text, list):
                    text = ' '.join(relevant_text)
                else:
                    text = str(relevant_text)

                findings = self._extract_findings_from_text(text)

                # Extract statistical information
                population_size = self._extract_population_size(text)
                statistical_significance = self._check_statistical_significance(text)
                effect_size = self._extract_effect_size(text)

                # Create evidence items for each finding
                for finding in findings:
                    evidence_item = EvidenceItem(
                        pmid=pmid,
                        study_type=study_type,
                        evidence_quality=evidence_quality,
                        finding=finding,
                        confidence=self._calculate_evidence_confidence(piece),
                        population_size=population_size,
                        statistical_significance=statistical_significance,
                        effect_size=effect_size,
                        journal_impact=self._assess_journal_impact(piece.get('journal', ''))
                    )
                    evidence_items.append(evidence_item)

            except Exception as e:
                logger.warning(f"Failed to standardize evidence piece {piece.get('pmid', 'unknown')}: {e}")
                continue

        return evidence_items

    def _extract_findings_from_text(self, text: str) -> List[str]:
        """Extract key findings from text"""
        findings = []

        # Split text into sentences
        sentences = re.split(r'[.!?]+', text)

        # Look for sentences with key medical indicators
        finding_indicators = [
            'showed', 'demonstrated', 'found', 'observed', 'reported',
            'indicated', 'suggested', 'revealed', 'confirmed', 'associated'
        ]

        outcome_keywords = [
            'survival', 'response', 'efficacy', 'safety', 'toxicity',
            'adverse', 'benefit', 'improvement', 'reduction', 'increase'
        ]

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:  # Skip very short sentences
                continue

            # Check if sentence contains finding indicators and outcomes
            has_indicator = any(indicator in sentence.lower() for indicator in finding_indicators)
            has_outcome = any(keyword in sentence.lower() for keyword in outcome_keywords)

            if has_indicator and has_outcome:
                findings.append(sentence)

        return findings[:5]  # Limit to avoid too many findings

    def _calculate_evidence_confidence(self, evidence_piece: Dict) -> float:
        """Calculate confidence score for evidence piece"""
        base_confidence = evidence_piece.get('relevance_score', 0.5)

        # Quality adjustment
        quality = evidence_piece.get('evidence_quality', 'medium')
        quality_multiplier = self.quality_weights.get(quality, 0.7)

        # Study type adjustment
        study_type = evidence_piece.get('study_type', 'research_article')
        study_multiplier = self.study_type_hierarchy.get(study_type, 0.5)

        # Combine factors
        confidence = base_confidence * quality_multiplier * study_multiplier

        return min(max(confidence, 0.1), 1.0)  # Clamp to [0.1, 1.0]

    def _extract_population_size(self, text: str) -> Optional[int]:
        """Extract population/sample size from text"""
        patterns = [
            r'n\s*=\s*(\d+)',
            r'(\d+)\s+patients',
            r'(\d+)\s+subjects',
            r'sample\s+size\s+of\s+(\d+)'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    return int(matches[0])
                except ValueError:
                    continue

        return None

    def _check_statistical_significance(self, text: str) -> Optional[bool]:
        """Check if findings are statistically significant"""
        # Look for p-values
        p_value_pattern = r'p\s*[<>=]\s*([\d\.]+)'
        p_matches = re.findall(p_value_pattern, text, re.IGNORECASE)

        if p_matches:
            try:
                p_value = float(p_matches[0])
                return p_value < 0.05
            except ValueError:
                pass

        # Look for explicit significance statements
        if any(phrase in text.lower() for phrase in [
            'statistically significant', 'significantly', 'p<0.05', 'p < 0.05'
        ]):
            return True

        if any(phrase in text.lower() for phrase in [
            'not significant', 'no significant', 'p>0.05', 'p > 0.05'
        ]):
            return False

        return None

    def _extract_effect_size(self, text: str) -> Optional[float]:
        """Extract effect size measures from text"""
        # Look for hazard ratios, odds ratios, etc.
        for measure, pattern in self.stat_patterns.items():
            if measure in ['hr', 'or', 'rr']:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    try:
                        return float(matches[0])
                    except ValueError:
                        continue

        return None

    def _assess_journal_impact(self, journal: str) -> str:
        """Assess journal impact level"""
        high_impact = [
            'new england journal of medicine', 'nature', 'science', 'cell',
            'lancet', 'journal of clinical oncology'
        ]

        medium_impact = [
            'clinical cancer research', 'cancer research', 'nature medicine',
            'oncogene', 'molecular cancer therapeutics'
        ]

        journal_lower = journal.lower()

        if any(j in journal_lower for j in high_impact):
            return 'high'
        elif any(j in journal_lower for j in medium_impact):
            return 'medium'
        else:
            return 'low'

    def _group_similar_findings(self, evidence_items: List[EvidenceItem]) -> Dict[str, List[EvidenceItem]]:
        """Group similar findings together"""
        groups = defaultdict(list)

        for item in evidence_items:
            # Simple grouping by key terms (would be enhanced with semantic similarity)
            finding_key = self._extract_finding_key(item.finding)
            groups[finding_key].append(item)

        return dict(groups)

    def _extract_finding_key(self, finding: str) -> str:
        """Extract key terms from finding for grouping"""
        # Extract key medical terms
        finding_lower = finding.lower()

        # Look for outcome measures
        if 'survival' in finding_lower:
            return 'survival_outcomes'
        elif any(term in finding_lower for term in ['response', 'efficacy']):
            return 'efficacy_outcomes'
        elif any(term in finding_lower for term in ['safety', 'adverse', 'toxicity']):
            return 'safety_outcomes'
        elif any(term in finding_lower for term in ['mechanism', 'pathway']):
            return 'mechanistic_findings'
        else:
            return 'other_findings'

    def _build_consensus(self, grouped_findings: Dict[str, List[EvidenceItem]]) -> List[Consensus]:
        """Build consensus from grouped findings"""
        consensus_results = []

        for finding_type, items in grouped_findings.items():
            if len(items) < 2:  # Skip groups with only one item
                continue

            # Calculate consensus metrics
            supporting_studies = [item.pmid for item in items]
            confidence_scores = [item.confidence for item in items]
            avg_confidence = statistics.mean(confidence_scores)

            # Assess consistency
            consistency_score = self._calculate_consistency(items)

            # Determine confidence level
            if avg_confidence >= 0.8 and consistency_score >= 0.7:
                confidence_level = 'high'
            elif avg_confidence >= 0.6 and consistency_score >= 0.5:
                confidence_level = 'medium'
            else:
                confidence_level = 'low'

            # Assess strength of evidence
            strength = self._assess_group_strength(items)

            # Create representative finding
            representative_finding = self._create_representative_finding(items)

            # Calculate statistical summary
            statistical_summary = self._calculate_statistical_summary(items)

            consensus = Consensus(
                finding=representative_finding,
                supporting_studies=supporting_studies,
                confidence_level=confidence_level,
                strength_of_evidence=strength,
                consistency_score=consistency_score,
                statistical_summary=statistical_summary
            )

            consensus_results.append(consensus)

        return consensus_results

    def _calculate_consistency(self, items: List[EvidenceItem]) -> float:
        """Calculate consistency score for a group of findings"""
        if len(items) < 2:
            return 1.0

        # Simple consistency based on statistical significance agreement
        sig_results = [item.statistical_significance for item in items
                      if item.statistical_significance is not None]

        if len(sig_results) < 2:
            return 0.7  # Default when insufficient data

        # Calculate agreement rate
        positive_results = sum(1 for result in sig_results if result)
        agreement_rate = max(positive_results, len(sig_results) - positive_results) / len(sig_results)

        return agreement_rate

    def _assess_group_strength(self, items: List[EvidenceItem]) -> str:
        """Assess strength of evidence for a group"""
        # Consider study types, quality, and sample sizes
        high_quality_count = sum(1 for item in items if item.evidence_quality == 'high')
        clinical_trial_count = sum(1 for item in items if item.study_type == 'clinical_trial')
        meta_analysis_count = sum(1 for item in items if item.study_type == 'meta_analysis')

        total_items = len(items)

        if meta_analysis_count > 0 or (high_quality_count >= total_items * 0.5):
            return 'strong'
        elif clinical_trial_count >= total_items * 0.3:
            return 'moderate'
        else:
            return 'weak'

    def _create_representative_finding(self, items: List[EvidenceItem]) -> str:
        """Create a representative finding from multiple items"""
        # For now, take the finding from the highest confidence item
        best_item = max(items, key=lambda x: x.confidence)
        return best_item.finding

    def _calculate_statistical_summary(self, items: List[EvidenceItem]) -> Dict:
        """Calculate statistical summary for a group"""
        summary = {
            'total_studies': len(items),
            'significant_results': sum(1 for item in items
                                     if item.statistical_significance is True),
            'total_sample_size': sum(item.population_size for item in items
                                   if item.population_size is not None),
            'average_effect_size': None
        }

        # Calculate average effect size if available
        effect_sizes = [item.effect_size for item in items if item.effect_size is not None]
        if effect_sizes:
            summary['average_effect_size'] = statistics.mean(effect_sizes)

        return summary

    def _detect_conflicts(self, grouped_findings: Dict[str, List[EvidenceItem]]) -> List[Conflict]:
        """Detect conflicts between evidence"""
        conflicts = []

        for finding_type, items in grouped_findings.items():
            if len(items) < 2:
                continue

            # Check for statistical significance conflicts
            sig_results = [(item.pmid, item.statistical_significance) for item in items
                          if item.statistical_significance is not None]

            if len(sig_results) >= 2:
                positive_studies = [pmid for pmid, sig in sig_results if sig]
                negative_studies = [pmid for pmid, sig in sig_results if not sig]

                if positive_studies and negative_studies:
                    # Conflict detected
                    conflict = Conflict(
                        conflicting_findings=[
                            f"Statistically significant results ({len(positive_studies)} studies)",
                            f"Non-significant results ({len(negative_studies)} studies)"
                        ],
                        study_groups=[positive_studies, negative_studies],
                        potential_explanations=self._suggest_conflict_explanations(items),
                        resolution_suggestions=self._suggest_conflict_resolutions(items)
                    )
                    conflicts.append(conflict)

        return conflicts

    def _suggest_conflict_explanations(self, items: List[EvidenceItem]) -> List[str]:
        """Suggest potential explanations for conflicts"""
        explanations = []

        # Check for different study types
        study_types = set(item.study_type for item in items)
        if len(study_types) > 1:
            explanations.append("Different study methodologies")

        # Check for different population sizes
        pop_sizes = [item.population_size for item in items if item.population_size is not None]
        if len(pop_sizes) >= 2:
            size_range = max(pop_sizes) / min(pop_sizes) if min(pop_sizes) > 0 else 1
            if size_range > 3:
                explanations.append("Substantial differences in sample sizes")

        # Check for different evidence quality
        quality_levels = set(item.evidence_quality for item in items)
        if len(quality_levels) > 1:
            explanations.append("Varying study quality levels")

        return explanations or ["Methodological differences may explain conflicting results"]

    def _suggest_conflict_resolutions(self, items: List[EvidenceItem]) -> List[str]:
        """Suggest approaches to resolve conflicts"""
        suggestions = [
            "Conduct systematic review of methodological differences",
            "Consider patient population characteristics",
            "Evaluate study quality and risk of bias"
        ]

        # Add specific suggestions based on evidence
        clinical_trials = [item for item in items if item.study_type == 'clinical_trial']
        if clinical_trials:
            suggestions.append("Focus analysis on randomized controlled trials")

        return suggestions

    def _assess_evidence_strength(self, evidence_items: List[EvidenceItem]) -> Dict:
        """Assess overall strength of evidence base"""
        if not evidence_items:
            return {'overall_strength': 'insufficient'}

        # Quality distribution
        quality_counts = Counter(item.evidence_quality for item in evidence_items)

        # Study type distribution
        study_type_counts = Counter(item.study_type for item in evidence_items)

        # Calculate overall strength score
        strength_score = 0.0
        total_items = len(evidence_items)

        for item in evidence_items:
            item_weight = (self.quality_weights.get(item.evidence_quality, 0.5) *
                          self.study_type_hierarchy.get(item.study_type, 0.5))
            strength_score += item_weight

        avg_strength = strength_score / total_items

        # Determine overall strength
        if avg_strength >= 0.7 and total_items >= 3:
            overall_strength = 'strong'
        elif avg_strength >= 0.5 and total_items >= 2:
            overall_strength = 'moderate'
        else:
            overall_strength = 'weak'

        return {
            'overall_strength': overall_strength,
            'strength_score': avg_strength,
            'evidence_count': total_items,
            'quality_distribution': dict(quality_counts),
            'study_type_distribution': dict(study_type_counts)
        }

    def _identify_evidence_gaps(self, evidence_items: List[EvidenceItem], topic: str) -> List[str]:
        """Identify gaps in the evidence base"""
        gaps = []

        # Check for missing study types
        present_study_types = set(item.study_type for item in evidence_items)

        if 'meta_analysis' not in present_study_types and len(evidence_items) >= 3:
            gaps.append("No meta-analyses identified")

        if 'clinical_trial' not in present_study_types:
            gaps.append("Limited randomized controlled trial data")

        # Check for outcome measure gaps
        findings_text = ' '.join(item.finding.lower() for item in evidence_items)

        if 'safety' not in findings_text and 'adverse' not in findings_text:
            gaps.append("Limited safety data")

        if 'long-term' not in findings_text and 'follow-up' not in findings_text:
            gaps.append("Limited long-term outcome data")

        # Check for population diversity
        # This would be enhanced with actual population analysis

        return gaps

    def _generate_synthesis_summary(self, consensus_results: List[Consensus],
                                   conflicts: List[Conflict],
                                   strength_assessment: Dict) -> str:
        """Generate overall synthesis summary"""
        summary_parts = []

        # Evidence base description
        evidence_count = strength_assessment.get('evidence_count', 0)
        overall_strength = strength_assessment.get('overall_strength', 'unknown')

        summary_parts.append(
            f"Evidence synthesis from {evidence_count} studies with {overall_strength} overall strength."
        )

        # Consensus findings
        high_confidence_consensus = [c for c in consensus_results if c.confidence_level == 'high']
        if high_confidence_consensus:
            summary_parts.append(
                f"{len(high_confidence_consensus)} high-confidence consensus findings identified."
            )

        # Conflicts
        if conflicts:
            summary_parts.append(
                f"{len(conflicts)} areas of conflicting evidence require further investigation."
            )

        return ' '.join(summary_parts)

    def _extract_key_findings(self, consensus_results: List[Consensus]) -> List[str]:
        """Extract key findings from consensus results"""
        key_findings = []

        # Sort by confidence and strength
        sorted_consensus = sorted(consensus_results,
                                key=lambda x: (x.confidence_level == 'high',
                                             x.strength_of_evidence == 'strong'),
                                reverse=True)

        for consensus in sorted_consensus[:5]:  # Top 5 findings
            finding_summary = f"{consensus.finding} (Confidence: {consensus.confidence_level}, "
            finding_summary += f"Strength: {consensus.strength_of_evidence})"
            key_findings.append(finding_summary)

        return key_findings

    def _assess_overall_confidence(self, consensus_results: List[Consensus],
                                  conflicts: List[Conflict],
                                  strength_assessment: Dict) -> str:
        """Assess overall confidence in synthesis"""
        if not consensus_results:
            return 'very_low'

        high_confidence_count = sum(1 for c in consensus_results if c.confidence_level == 'high')
        total_consensus = len(consensus_results)
        conflict_count = len(conflicts)

        overall_strength = strength_assessment.get('overall_strength', 'weak')

        # Calculate confidence
        if (high_confidence_count >= total_consensus * 0.8 and
            conflict_count == 0 and overall_strength == 'strong'):
            return 'high'
        elif (high_confidence_count >= total_consensus * 0.5 and
              conflict_count <= 1 and overall_strength in ['strong', 'moderate']):
            return 'medium'
        elif high_confidence_count > 0 and overall_strength != 'weak':
            return 'low'
        else:
            return 'very_low'

    def _generate_recommendations(self, consensus_results: List[Consensus],
                                 conflicts: List[Conflict], gaps: List[str],
                                 strength_assessment: Dict) -> List[str]:
        """Generate recommendations based on synthesis"""
        recommendations = []

        # Evidence-based recommendations
        high_strength_consensus = [c for c in consensus_results
                                 if c.strength_of_evidence == 'strong']
        if high_strength_consensus:
            recommendations.append("Consider clinical implementation based on strong consensus evidence")

        # Conflict resolution recommendations
        if conflicts:
            recommendations.append("Address conflicting evidence through additional research")

        # Gap-based recommendations
        if gaps:
            if "No meta-analyses identified" in gaps:
                recommendations.append("Systematic review and meta-analysis recommended")

            if "Limited safety data" in gaps:
                recommendations.append("Enhanced safety monitoring in future studies")

        # Overall strength recommendations
        overall_strength = strength_assessment.get('overall_strength', 'weak')
        if overall_strength == 'weak':
            recommendations.append("Additional high-quality studies needed before clinical decisions")

        return recommendations or ["Continue monitoring emerging evidence"]

    def _create_empty_synthesis(self, topic: str) -> EvidenceSynthesis:
        """Create synthesis for no evidence"""
        return EvidenceSynthesis(
            summary=f"No evidence available for synthesis on topic: {topic}",
            key_findings=["No evidence identified"],
            consensus=[],
            conflicts=[],
            strength_assessment={'overall_strength': 'insufficient'},
            gaps=["Comprehensive evidence base needed"],
            confidence='very_low',
            recommendations=["Conduct systematic literature search for relevant evidence"]
        )

    def _create_error_synthesis(self, topic: str, error_message: str) -> EvidenceSynthesis:
        """Create synthesis for error cases"""
        return EvidenceSynthesis(
            summary=f"Evidence synthesis failed for topic: {topic}. Error: {error_message}",
            key_findings=[],
            consensus=[],
            conflicts=[],
            strength_assessment={'overall_strength': 'error'},
            gaps=[],
            confidence='very_low',
            recommendations=["Review synthesis process and retry"]
        )

def main():
    """Test evidence synthesizer functionality"""
    config = {
        'max_evidence_pieces': 5,
        'synthesis_method': 'weighted_consensus',
        'conflict_detection': True
    }

    synthesizer = EvidenceSynthesizer(config)

    # Test with sample evidence
    sample_evidence = [
        {
            'pmid': '12345',
            'study_type': 'clinical_trial',
            'evidence_quality': 'high',
            'relevant_text': ['Study showed significant improvement in overall survival'],
            'relevance_score': 0.9,
            'journal': 'New England Journal of Medicine'
        },
        {
            'pmid': '12346',
            'study_type': 'observational',
            'evidence_quality': 'medium',
            'relevant_text': ['Patients demonstrated good response rates'],
            'relevance_score': 0.7,
            'journal': 'Journal of Clinical Oncology'
        }
    ]

    synthesis = synthesizer.synthesize_evidence("drug efficacy", sample_evidence)

    print("Evidence Synthesis Results:")
    print(f"Summary: {synthesis.summary}")
    print(f"Key Findings: {synthesis.key_findings}")
    print(f"Confidence: {synthesis.confidence}")

if __name__ == "__main__":
    main()