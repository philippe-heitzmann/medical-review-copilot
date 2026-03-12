"""
Question Answering Processor - Generates answers from retrieved evidence
Handles answer generation, confidence assessment, and response formatting
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

# Import Claude API integration
try:
    from claude_api import ClaudeAPIClient
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class AnswerComponent:
    """Component of an answer with source attribution"""
    text: str
    confidence: float
    source_pmids: List[str]
    evidence_strength: str
    supporting_quotes: List[str]

@dataclass
class GeneratedAnswer:
    """Complete generated answer with metadata"""
    answer_text: str
    confidence: float
    key_points: List[str]
    components: List[AnswerComponent]
    uncertainty_factors: List[str]
    limitations: List[str]
    answer_type: str  # direct, synthesized, insufficient_evidence

class QuestionAnsweringProcessor:
    """Processes questions and generates answers from medical evidence"""

    def __init__(self, config: Dict):
        """Initialize QA processor"""
        self.config = config
        self.min_confidence = config.get('min_confidence', 0.5)
        self.max_answer_length = config.get('max_answer_length', 200)

        # Initialize Claude API client
        self.claude_client = None
        if CLAUDE_AVAILABLE:
            try:
                self.claude_client = ClaudeAPIClient(config)
                if self.claude_client.is_available():
                    logger.info("QA Processor initialized with Claude API support")
                else:
                    logger.info("Claude API not configured - using fallback processing")
            except Exception as e:
                logger.warning(f"Failed to initialize Claude API: {e}")
        else:
            logger.info("Claude API package not available - using fallback processing")

        # Medical terminology patterns
        self.statistical_patterns = {
            'survival': r'(overall survival|progression[- ]free survival|disease[- ]free survival)',
            'response_rate': r'(response rate|complete response|partial response|objective response)',
            'hazard_ratio': r'(hazard ratio|hr)[:\s]*([\d\.]+)',
            'p_value': r'p[- ]?value?[:\s]*[<>=]?\s*([\d\.]+)',
            'confidence_interval': r'(\d+%?\s*confidence interval|ci)[:\s]*([\d\.\-\s,]+)'
        }

        # Answer templates for different question types
        self.answer_templates = {
            'efficacy': self._efficacy_answer_template,
            'safety': self._safety_answer_template,
            'mechanism': self._mechanism_answer_template,
            'comparison': self._comparison_answer_template,
            'general': self._general_answer_template
        }

    def generate_answer(self, question: str, evidence_pieces: List[Dict],
                       context: Optional[Dict] = None) -> GeneratedAnswer:
        """
        Generate answer from question and evidence

        Args:
            question: User's question
            evidence_pieces: Relevant evidence pieces from search
            context: Optional context for answer generation

        Returns:
            Generated answer with confidence and metadata
        """
        logger.info(f"Generating answer for: {question}")

        if not evidence_pieces:
            return self._generate_no_evidence_answer(question)

        # Try Claude API first if available
        if self.claude_client and self.claude_client.is_available():
            try:
                logger.info("Using Claude API for answer generation")
                claude_response = self.claude_client.generate_scientific_answer(
                    question, evidence_pieces, context
                )

                # Convert Claude response to GeneratedAnswer format
                return GeneratedAnswer(
                    answer_text=claude_response.answer_text,
                    confidence=claude_response.confidence,
                    key_points=claude_response.key_points,
                    components=[],  # Claude handles this internally
                    uncertainty_factors=self._assess_claude_uncertainty(claude_response, evidence_pieces),
                    limitations=self._identify_claude_limitations(question, evidence_pieces),
                    answer_type='claude_generated'
                )
            except Exception as e:
                logger.warning(f"Claude API failed, falling back to rule-based processing: {e}")

        # Fallback to original rule-based processing
        logger.info("Using rule-based answer generation")
        try:
            # Analyze question type and intent
            question_analysis = self._analyze_question(question)

            # Extract relevant information from evidence
            extracted_info = self._extract_information(evidence_pieces, question_analysis)

            # Generate answer components
            answer_components = self._generate_answer_components(
                question_analysis, extracted_info
            )

            # Synthesize final answer
            synthesized_answer = self._synthesize_answer(
                question, question_analysis, answer_components
            )

            # Assess confidence
            confidence = self._assess_answer_confidence(
                synthesized_answer, answer_components, evidence_pieces
            )

            # Identify limitations and uncertainty
            uncertainty_factors, limitations = self._identify_uncertainty_and_limitations(
                question_analysis, evidence_pieces, answer_components
            )

            # Generate key points
            key_points = self._extract_key_points(answer_components)

            return GeneratedAnswer(
                answer_text=synthesized_answer,
                confidence=confidence,
                key_points=key_points,
                components=answer_components,
                uncertainty_factors=uncertainty_factors,
                limitations=limitations,
                answer_type=self._determine_answer_type(answer_components, evidence_pieces)
            )

        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return self._generate_error_answer(str(e))

    def _analyze_question(self, question: str) -> Dict:
        """Analyze question to determine type and extract key elements"""
        question_lower = question.lower()

        # Determine question type
        question_type = 'general'
        if any(word in question_lower for word in ['efficacy', 'effective', 'response', 'survival']):
            question_type = 'efficacy'
        elif any(word in question_lower for word in ['safety', 'adverse', 'toxicity', 'side effects']):
            question_type = 'safety'
        elif any(word in question_lower for word in ['mechanism', 'how does', 'pathway']):
            question_type = 'mechanism'
        elif any(word in question_lower for word in ['compare', 'versus', 'vs', 'difference']):
            question_type = 'comparison'

        # Extract entities (drugs, diseases, etc.)
        entities = self._extract_entities(question)

        # Extract statistical interest
        statistical_interest = self._identify_statistical_interest(question)

        return {
            'type': question_type,
            'entities': entities,
            'statistical_interest': statistical_interest,
            'requires_comparison': 'comparison' in question_type,
            'temporal_aspect': self._identify_temporal_aspect(question)
        }

    def _extract_entities(self, question: str) -> Dict:
        """Extract medical entities from question"""
        entities = {
            'drugs': [],
            'diseases': [],
            'biomarkers': []
        }

        # Drug name patterns
        drug_patterns = [
            r'\b\w+mab\b',  # monoclonal antibodies
            r'\b\w+tinib\b',  # kinase inhibitors
            r'\bpembrolizumab\b', r'\bnivolumab\b', r'\bipilimumab\b'  # specific drugs
        ]

        for pattern in drug_patterns:
            matches = re.findall(pattern, question, re.IGNORECASE)
            entities['drugs'].extend([match.lower() for match in matches])

        # Disease patterns
        disease_patterns = [
            r'\b\w+\s*cancer\b',
            r'\b\w+\s*carcinoma\b',
            r'\bmelanoma\b', r'\blymphoma\b', r'\bleukemia\b'
        ]

        for pattern in disease_patterns:
            matches = re.findall(pattern, question, re.IGNORECASE)
            entities['diseases'].extend([match.lower() for match in matches])

        return entities

    def _identify_statistical_interest(self, question: str) -> List[str]:
        """Identify what statistical measures the question is asking about"""
        interests = []

        for measure, pattern in self.statistical_patterns.items():
            if re.search(pattern, question, re.IGNORECASE):
                interests.append(measure)

        return interests

    def _identify_temporal_aspect(self, question: str) -> Optional[str]:
        """Identify temporal aspects of the question"""
        temporal_keywords = {
            'recent': ['recent', 'latest', 'current', 'new'],
            'long_term': ['long-term', 'long term', 'duration', 'extended'],
            'comparative': ['before', 'after', 'during', 'versus']
        }

        for aspect, keywords in temporal_keywords.items():
            if any(keyword in question.lower() for keyword in keywords):
                return aspect

        return None

    def _extract_information(self, evidence_pieces: List[Dict],
                           question_analysis: Dict) -> Dict:
        """Extract relevant information from evidence pieces"""
        extracted = {
            'statistical_data': [],
            'clinical_findings': [],
            'mechanistic_insights': [],
            'safety_data': [],
            'comparative_data': [],
            'population_data': []
        }

        for piece in evidence_pieces:
            text = ' '.join(piece.get('relevant_text', []))

            # Extract statistical data
            stats = self._extract_statistical_data(text)
            if stats:
                extracted['statistical_data'].append({
                    'pmid': piece.get('pmid'),
                    'statistics': stats,
                    'study_type': piece.get('study_type'),
                    'evidence_quality': piece.get('evidence_quality')
                })

            # Extract clinical findings
            clinical = self._extract_clinical_findings(text, question_analysis)
            if clinical:
                extracted['clinical_findings'].append({
                    'pmid': piece.get('pmid'),
                    'findings': clinical,
                    'study_type': piece.get('study_type')
                })

            # Extract safety information
            safety = self._extract_safety_data(text)
            if safety:
                extracted['safety_data'].append({
                    'pmid': piece.get('pmid'),
                    'safety_findings': safety
                })

        return extracted

    def _extract_statistical_data(self, text: str) -> List[Dict]:
        """Extract statistical measures from text"""
        stats = []

        for measure, pattern in self.statistical_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                stat_data = {
                    'measure': measure,
                    'text': match.group(0),
                    'value': self._extract_numeric_value(match.group(0))
                }
                stats.append(stat_data)

        return stats

    def _extract_numeric_value(self, text: str) -> Optional[float]:
        """Extract numeric value from statistical text"""
        # Look for numbers in the text
        numbers = re.findall(r'[\d\.]+', text)
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                pass
        return None

    def _extract_clinical_findings(self, text: str, question_analysis: Dict) -> List[str]:
        """Extract clinical findings relevant to the question"""
        findings = []

        # Look for specific findings based on question type
        if question_analysis['type'] == 'efficacy':
            efficacy_patterns = [
                r'(response rate[^\.]+)',
                r'(overall survival[^\.]+)',
                r'(progression[^\.]+)',
                r'(efficacy[^\.]+)'
            ]

            for pattern in efficacy_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                findings.extend(matches)

        elif question_analysis['type'] == 'safety':
            safety_patterns = [
                r'(adverse events?[^\.]+)',
                r'(toxicity[^\.]+)',
                r'(safety[^\.]+)',
                r'(tolerat[^\.]+)'
            ]

            for pattern in safety_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                findings.extend(matches)

        return findings[:5]  # Limit findings

    def _extract_safety_data(self, text: str) -> List[Dict]:
        """Extract safety-related information"""
        safety_data = []

        safety_patterns = {
            'grade_3_4': r'grade\s*[34][^\.]+',
            'serious_ae': r'serious\s+adverse\s+events?[^\.]+',
            'discontinuation': r'discontinu[^\.]+',
            'dose_reduction': r'dose\s+reduction[^\.]+',
            'treatment_related': r'treatment[- ]related[^\.]+adverse[^\.]*'
        }

        for category, pattern in safety_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                safety_data.append({
                    'category': category,
                    'text': match.strip()
                })

        return safety_data

    def _generate_answer_components(self, question_analysis: Dict,
                                   extracted_info: Dict) -> List[AnswerComponent]:
        """Generate answer components from extracted information"""
        components = []
        question_type = question_analysis['type']

        if question_type == 'efficacy':
            components.extend(self._create_efficacy_components(extracted_info))
        elif question_type == 'safety':
            components.extend(self._create_safety_components(extracted_info))
        elif question_type == 'mechanism':
            components.extend(self._create_mechanism_components(extracted_info))
        elif question_type == 'comparison':
            components.extend(self._create_comparison_components(extracted_info))
        else:
            components.extend(self._create_general_components(extracted_info))

        return components

    def _create_efficacy_components(self, extracted_info: Dict) -> List[AnswerComponent]:
        """Create components for efficacy answers"""
        components = []

        # Statistical data component
        stats_data = extracted_info.get('statistical_data', [])
        if stats_data:
            stats_text = self._summarize_statistical_data(stats_data)
            component = AnswerComponent(
                text=stats_text,
                confidence=0.8,
                source_pmids=[data['pmid'] for data in stats_data],
                evidence_strength='strong' if len(stats_data) >= 3 else 'moderate',
                supporting_quotes=[data['statistics'][0]['text'] for data in stats_data
                                 if data['statistics']][:3]
            )
            components.append(component)

        # Clinical findings component
        clinical_data = extracted_info.get('clinical_findings', [])
        if clinical_data:
            clinical_text = self._summarize_clinical_findings(clinical_data)
            component = AnswerComponent(
                text=clinical_text,
                confidence=0.7,
                source_pmids=[data['pmid'] for data in clinical_data],
                evidence_strength='moderate',
                supporting_quotes=[finding for data in clinical_data
                                 for finding in data['findings']][:3]
            )
            components.append(component)

        return components

    def _create_safety_components(self, extracted_info: Dict) -> List[AnswerComponent]:
        """Create components for safety answers"""
        components = []

        safety_data = extracted_info.get('safety_data', [])
        if safety_data:
            safety_text = self._summarize_safety_data(safety_data)
            component = AnswerComponent(
                text=safety_text,
                confidence=0.75,
                source_pmids=[data['pmid'] for data in safety_data],
                evidence_strength='strong' if len(safety_data) >= 3 else 'moderate',
                supporting_quotes=[finding['text'] for data in safety_data
                                 for finding in data['safety_findings']][:3]
            )
            components.append(component)

        return components

    def _create_mechanism_components(self, extracted_info: Dict) -> List[AnswerComponent]:
        """Create components for mechanism answers"""
        # This would be enhanced with more sophisticated mechanism extraction
        components = []

        clinical_data = extracted_info.get('clinical_findings', [])
        if clinical_data:
            mechanism_text = "Based on available evidence, mechanistic insights are limited in the retrieved clinical studies."
            component = AnswerComponent(
                text=mechanism_text,
                confidence=0.4,  # Lower confidence for mechanism from clinical data
                source_pmids=[data['pmid'] for data in clinical_data],
                evidence_strength='weak',
                supporting_quotes=[]
            )
            components.append(component)

        return components

    def _create_comparison_components(self, extracted_info: Dict) -> List[AnswerComponent]:
        """Create components for comparison answers"""
        components = []

        comparative_data = extracted_info.get('comparative_data', [])
        if comparative_data:
            comparison_text = self._summarize_comparative_data(comparative_data)
            component = AnswerComponent(
                text=comparison_text,
                confidence=0.7,
                source_pmids=[data['pmid'] for data in comparative_data],
                evidence_strength='moderate',
                supporting_quotes=[]
            )
            components.append(component)

        return components

    def _create_general_components(self, extracted_info: Dict) -> List[AnswerComponent]:
        """Create components for general answers"""
        components = []

        # Combine available evidence
        all_findings = []
        all_pmids = []

        for category, data_list in extracted_info.items():
            for data in data_list[:2]:  # Limit to avoid too much
                all_pmids.append(data['pmid'])
                if 'findings' in data:
                    all_findings.extend(data['findings'][:2])

        if all_findings:
            general_text = "Based on available evidence: " + "; ".join(all_findings[:3])
            component = AnswerComponent(
                text=general_text,
                confidence=0.6,
                source_pmids=list(set(all_pmids)),
                evidence_strength='moderate',
                supporting_quotes=all_findings[:3]
            )
            components.append(component)

        return components

    def _summarize_statistical_data(self, stats_data: List[Dict]) -> str:
        """Summarize statistical findings"""
        summary_parts = []

        for data in stats_data[:3]:  # Limit to top 3
            stats = data['statistics']
            study_type = data.get('study_type', 'study')

            for stat in stats[:2]:  # Top 2 stats per study
                if stat['value']:
                    summary_parts.append(f"{stat['measure']} data from {study_type}")

        if summary_parts:
            return "Statistical evidence includes: " + ", ".join(summary_parts)
        else:
            return "Limited statistical data available from retrieved studies."

    def _summarize_clinical_findings(self, clinical_data: List[Dict]) -> str:
        """Summarize clinical findings"""
        all_findings = []

        for data in clinical_data[:3]:  # Limit studies
            findings = data['findings'][:2]  # Limit findings per study
            all_findings.extend(findings)

        if all_findings:
            return "Clinical evidence shows: " + "; ".join(all_findings[:3])
        else:
            return "Limited clinical evidence available."

    def _summarize_safety_data(self, safety_data: List[Dict]) -> str:
        """Summarize safety findings"""
        safety_categories = {}

        for data in safety_data:
            for finding in data['safety_findings']:
                category = finding['category']
                if category not in safety_categories:
                    safety_categories[category] = []
                safety_categories[category].append(finding['text'])

        summary_parts = []
        for category, findings in safety_categories.items():
            if findings:
                summary_parts.append(f"{category.replace('_', ' ')} events reported")

        if summary_parts:
            return "Safety profile: " + "; ".join(summary_parts[:3])
        else:
            return "Limited safety data available from retrieved studies."

    def _summarize_comparative_data(self, comparative_data: List[Dict]) -> str:
        """Summarize comparative findings"""
        return "Comparative data analysis would be implemented here."

    def _synthesize_answer(self, question: str, question_analysis: Dict,
                          components: List[AnswerComponent]) -> str:
        """Synthesize final answer from components"""
        if not components:
            return "Insufficient evidence available to provide a comprehensive answer to this question."

        question_type = question_analysis['type']
        template_func = self.answer_templates.get(question_type, self.answer_templates['general'])

        return template_func(components, question)

    def _efficacy_answer_template(self, components: List[AnswerComponent], question: str) -> str:
        """Template for efficacy answers"""
        if not components:
            return "Insufficient efficacy data available."

        answer_parts = []
        for component in components[:2]:  # Use top 2 components
            answer_parts.append(component.text)

        return " ".join(answer_parts)

    def _safety_answer_template(self, components: List[AnswerComponent], question: str) -> str:
        """Template for safety answers"""
        if not components:
            return "Insufficient safety data available."

        answer_parts = []
        for component in components[:2]:
            answer_parts.append(component.text)

        return " ".join(answer_parts)

    def _mechanism_answer_template(self, components: List[AnswerComponent], question: str) -> str:
        """Template for mechanism answers"""
        if not components:
            return "Mechanistic information not available in retrieved clinical literature."

        return components[0].text

    def _comparison_answer_template(self, components: List[AnswerComponent], question: str) -> str:
        """Template for comparison answers"""
        if not components:
            return "Insufficient data for direct comparison."

        return components[0].text

    def _general_answer_template(self, components: List[AnswerComponent], question: str) -> str:
        """Template for general answers"""
        if not components:
            return "Limited evidence available to address this question."

        return components[0].text

    def _assess_answer_confidence(self, answer: str, components: List[AnswerComponent],
                                 evidence_pieces: List[Dict]) -> float:
        """Assess confidence in the generated answer"""
        if not components:
            return 0.1

        # Average component confidence
        component_confidence = sum(comp.confidence for comp in components) / len(components)

        # Evidence quantity factor
        evidence_factor = min(len(evidence_pieces) / 5.0, 1.0)  # Normalize to 5 pieces

        # Evidence quality factor
        high_quality_count = sum(1 for piece in evidence_pieces
                               if piece.get('evidence_quality') == 'high')
        quality_factor = min(high_quality_count / len(evidence_pieces), 1.0)

        # Combine factors
        confidence = component_confidence * 0.5 + evidence_factor * 0.3 + quality_factor * 0.2

        return min(max(confidence, 0.1), 1.0)  # Clamp to [0.1, 1.0]

    def _identify_uncertainty_and_limitations(self, question_analysis: Dict,
                                             evidence_pieces: List[Dict],
                                             components: List[AnswerComponent]) -> Tuple[List[str], List[str]]:
        """Identify uncertainty factors and limitations"""
        uncertainty_factors = []
        limitations = []

        # Check evidence quantity
        if len(evidence_pieces) < 3:
            uncertainty_factors.append("Limited number of supporting studies")

        # Check evidence quality
        high_quality_count = sum(1 for piece in evidence_pieces
                               if piece.get('evidence_quality') == 'high')
        if high_quality_count < len(evidence_pieces) * 0.5:
            uncertainty_factors.append("Mixed quality of supporting evidence")

        # Check component confidence
        low_confidence_components = sum(1 for comp in components if comp.confidence < 0.6)
        if low_confidence_components > 0:
            uncertainty_factors.append("Some answer components have lower confidence")

        # Check for conflicting evidence
        # This would be enhanced with actual conflict detection

        # Limitations based on question type
        question_type = question_analysis['type']
        if question_type == 'mechanism':
            limitations.append("Clinical studies may not provide detailed mechanistic insights")
        if question_type == 'comparison':
            limitations.append("Direct head-to-head comparisons may be limited")

        # Evidence recency
        recent_evidence = sum(1 for piece in evidence_pieces
                            if self._is_evidence_recent(piece.get('publication_date')))
        if recent_evidence < len(evidence_pieces) * 0.3:
            limitations.append("Evidence base may not reflect recent developments")

        return uncertainty_factors, limitations

    def _extract_key_points(self, components: List[AnswerComponent]) -> List[str]:
        """Extract key points from answer components"""
        key_points = []

        for component in components:
            # Extract key quotes as points
            for quote in component.supporting_quotes[:2]:
                if len(quote) > 20:  # Skip very short quotes
                    key_points.append(quote.strip())

        return key_points[:5]  # Limit to 5 key points

    def _determine_answer_type(self, components: List[AnswerComponent],
                             evidence_pieces: List[Dict]) -> str:
        """Determine the type of answer generated"""
        if not components or not evidence_pieces:
            return 'insufficient_evidence'

        # Check if answer is directly supported
        high_confidence_components = sum(1 for comp in components if comp.confidence >= 0.7)
        if high_confidence_components >= len(components) * 0.8:
            return 'direct'
        else:
            return 'synthesized'

    def _is_evidence_recent(self, publication_date: str) -> bool:
        """Check if evidence is recent (within 3 years)"""
        try:
            if publication_date and publication_date != "Unknown":
                year = int(publication_date.split('-')[0])
                return (datetime.now().year - year) <= 3
        except:
            pass
        return False

    def _assess_claude_uncertainty(self, claude_response, evidence_pieces: List[Dict]) -> List[str]:
        """Assess uncertainty factors for Claude-generated answers"""
        uncertainty_factors = []

        # Check evidence quantity
        if len(evidence_pieces) < 3:
            uncertainty_factors.append("Limited number of supporting studies")

        # Check confidence level
        if claude_response.confidence < 0.7:
            uncertainty_factors.append("Moderate confidence in Claude-generated response")

        # Check evidence quality
        high_quality_count = sum(1 for piece in evidence_pieces
                               if piece.get('evidence_quality') == 'high')
        if high_quality_count < len(evidence_pieces) * 0.5:
            uncertainty_factors.append("Mixed quality of supporting evidence")

        return uncertainty_factors

    def _identify_claude_limitations(self, question: str, evidence_pieces: List[Dict]) -> List[str]:
        """Identify limitations for Claude-generated answers"""
        limitations = []

        # Question-specific limitations
        question_lower = question.lower()
        if any(word in question_lower for word in ['mechanism', 'pathway', 'molecular']):
            limitations.append("Clinical literature may not provide detailed mechanistic insights")

        if any(word in question_lower for word in ['compare', 'versus', 'difference']):
            limitations.append("Direct head-to-head comparisons may be limited")

        # Evidence recency
        recent_evidence = sum(1 for piece in evidence_pieces
                            if self._is_evidence_recent(piece.get('publication_date')))
        if recent_evidence < len(evidence_pieces) * 0.3:
            limitations.append("Evidence base may not reflect recent developments")

        # General AI limitation
        limitations.append("AI-generated response should be validated by medical professionals")

        return limitations

    def _generate_no_evidence_answer(self, question: str) -> GeneratedAnswer:
        """Generate answer when no evidence is available"""
        return GeneratedAnswer(
            answer_text="Insufficient evidence available to answer this question based on the current knowledge base.",
            confidence=0.1,
            key_points=["No relevant evidence found in knowledge base"],
            components=[],
            uncertainty_factors=["No supporting evidence available"],
            limitations=["Knowledge base may not contain relevant publications for this query"],
            answer_type='insufficient_evidence'
        )

    def _generate_error_answer(self, error_message: str) -> GeneratedAnswer:
        """Generate answer for error cases"""
        return GeneratedAnswer(
            answer_text=f"Unable to generate answer due to processing error: {error_message}",
            confidence=0.0,
            key_points=[],
            components=[],
            uncertainty_factors=["Processing error occurred"],
            limitations=["Technical issue prevented answer generation"],
            answer_type='error'
        )

def main():
    """Test QA processor functionality"""
    config = {
        'min_confidence': 0.5,
        'max_answer_length': 200
    }

    qa_processor = QuestionAnsweringProcessor(config)

    # Test question analysis
    test_question = "What is the efficacy of pembrolizumab in lung cancer?"
    analysis = qa_processor._analyze_question(test_question)

    print(f"Question Analysis for: {test_question}")
    print(f"Type: {analysis['type']}")
    print(f"Entities: {analysis['entities']}")
    print(f"Statistical Interest: {analysis['statistical_interest']}")

if __name__ == "__main__":
    main()