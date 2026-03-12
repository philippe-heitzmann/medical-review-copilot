"""
Therapeutic Area Copilot - Main application
Searchable Q&A assistant over approved medical literature corpus
Provides citation-grounded answers with evidence digests for oncology/immunotherapy
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import uuid

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging first
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Check for AI dependencies
try:
    import sentence_transformers
    import transformers
    AI_DEPENDENCIES_AVAILABLE = True
    logger.info("AI dependencies available - full features enabled")
except ImportError:
    AI_DEPENDENCIES_AVAILABLE = False
    logger.info("AI dependencies not available - using basic text processing")

# Import core modules
try:
    from knowledge_base import MedicalKnowledgeBase
    from search_engine import MedicalSearchEngine
    from qa_processor import QuestionAnsweringProcessor
    from citation_manager import CitationManager
    from evidence_synthesizer import EvidenceSynthesizer
    CORE_MODULES_AVAILABLE = True
    logger.info("Core modules imported successfully")
except ImportError as e:
    logger.error(f"Failed to import core modules: {e}")
    CORE_MODULES_AVAILABLE = False

class TherapeuticAreaCopilot:
    """Main copilot application for medical literature Q&A"""

    def __init__(self, config_path: str = "config/copilot_config.json"):
        """Initialize therapeutic area copilot"""
        self.config = self._load_config(config_path)
        self.session_id = str(uuid.uuid4())

        # Check system capabilities
        self.ai_enabled = AI_DEPENDENCIES_AVAILABLE

        if not CORE_MODULES_AVAILABLE:
            raise ImportError("Core modules not available. Please run setup_env.sh to install dependencies.")

        # Initialize components with error handling
        try:
            self.knowledge_base = MedicalKnowledgeBase(self.config.get('knowledge_base', {}))
            self.search_engine = MedicalSearchEngine(self.config.get('search_engine', {}))
            self.qa_processor = QuestionAnsweringProcessor(self.config.get('qa_processor', {}))
            self.citation_manager = CitationManager(self.config.get('citation_manager', {}))
            self.evidence_synthesizer = EvidenceSynthesizer(self.config.get('evidence_synthesizer', {}))
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise

        # Session tracking
        self.conversation_history = []
        self.session_metadata = {
            'session_id': self.session_id,
            'started_at': datetime.now().isoformat(),
            'therapeutic_area': self.config.get('default_therapeutic_area', 'oncology'),
            'user_context': {},
            'ai_enabled': self.ai_enabled
        }

        capability_msg = "with AI features" if self.ai_enabled else "with basic features (AI packages not available)"
        logger.info(f"Initialized Therapeutic Area Copilot {capability_msg} (Session: {self.session_id})")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return self._default_config()

    def _default_config(self) -> Dict:
        """Default configuration for copilot"""
        return {
            "default_therapeutic_area": "oncology",
            "max_search_results": 20,
            "citation_limit": 10,
            "confidence_threshold": 0.6,
            "enable_uncertainty_signaling": True,
            "knowledge_base": {
                "corpus_path": "data/approved_corpus",
                "embedding_model": "sentence-transformers/all-mpnet-base-v2",
                "chunk_size": 512,
                "overlap_size": 50
            },
            "search_engine": {
                "similarity_threshold": 0.7,
                "max_chunks": 10,
                "reranking_enabled": True
            },
            "qa_processor": {
                "model_name": "microsoft/BioBERT-pubmed-pmc-base",
                "max_answer_length": 200,
                "min_confidence": 0.5
            },
            "evidence_synthesizer": {
                "max_evidence_pieces": 5,
                "synthesis_method": "weighted_consensus",
                "conflict_detection": True
            }
        }

    def ask_question(self, question: str, context: Optional[Dict] = None) -> Dict:
        """
        Process a question and return citation-grounded answer

        Args:
            question: User's question about therapeutic area
            context: Optional context for the question

        Returns:
            Dictionary containing answer, evidence, citations, and metadata
        """
        logger.info(f"Processing question: {question}")

        try:
            # Step 1: Search for relevant literature
            search_results = self.search_engine.search(question, context)

            # Step 2: Extract evidence pieces
            evidence_pieces = self._extract_evidence(question, search_results)

            # Step 3: Generate answer with citations
            answer_result = self.qa_processor.generate_answer(
                question, evidence_pieces, context
            )

            # Step 4: Synthesize evidence and detect conflicts
            evidence_synthesis = self.evidence_synthesizer.synthesize_evidence(
                question, evidence_pieces
            )

            # Step 5: Format citations
            citations = self.citation_manager.format_citations(evidence_pieces)

            # Step 6: Assess confidence and uncertainty
            uncertainty_assessment = self._assess_uncertainty(
                answer_result, evidence_synthesis, search_results
            )

            # Compile response
            response = self._compile_response(
                question=question,
                answer=answer_result,
                evidence_synthesis=evidence_synthesis,
                citations=citations,
                uncertainty=uncertainty_assessment,
                search_metadata=search_results.get('metadata', {})
            )

            # Track conversation
            self._track_conversation(question, response)

            logger.info(f"Successfully processed question with {len(citations)} citations")
            return response

        except Exception as e:
            logger.error(f"Error processing question: {e}")
            return self._create_error_response(str(e))

    def search_literature(self, query: str, filters: Optional[Dict] = None) -> Dict:
        """
        Search literature corpus without generating answer

        Args:
            query: Search query
            filters: Optional filters (date range, publication type, etc.)

        Returns:
            Search results with relevant publications
        """
        logger.info(f"Literature search: {query}")

        search_results = self.search_engine.search(query, filters)
        formatted_results = self._format_search_results(search_results)

        return {
            'query': query,
            'results': formatted_results,
            'metadata': search_results.get('metadata', {}),
            'total_results': len(formatted_results)
        }

    def get_evidence_digest(self, topic: str, max_papers: int = 10) -> Dict:
        """
        Generate evidence digest for a specific topic

        Args:
            topic: Topic for evidence compilation
            max_papers: Maximum number of papers to include

        Returns:
            Evidence digest with key findings and consensus
        """
        logger.info(f"Generating evidence digest for: {topic}")

        # Search for comprehensive evidence
        search_results = self.search_engine.search(
            topic,
            {'max_results': max_papers * 2}  # Get more for filtering
        )

        # Extract and synthesize evidence
        evidence_pieces = self._extract_evidence(topic, search_results)
        evidence_synthesis = self.evidence_synthesizer.synthesize_evidence(
            topic, evidence_pieces
        )

        # Create evidence digest
        digest = {
            'topic': topic,
            'generated_at': datetime.now().isoformat(),
            'key_findings': evidence_synthesis.key_findings if hasattr(evidence_synthesis, 'key_findings') else [],
            'consensus_areas': evidence_synthesis.consensus if hasattr(evidence_synthesis, 'consensus') else [],
            'conflicting_evidence': evidence_synthesis.conflicts if hasattr(evidence_synthesis, 'conflicts') else [],
            'evidence_strength': evidence_synthesis.strength_assessment if hasattr(evidence_synthesis, 'strength_assessment') else {},
            'clinical_implications': self._extract_clinical_implications(evidence_pieces),
            'citations': self.citation_manager.format_citations(evidence_pieces),
            'evidence_gaps': evidence_synthesis.gaps if hasattr(evidence_synthesis, 'gaps') else [],
            'recommendation_confidence': evidence_synthesis.confidence if hasattr(evidence_synthesis, 'confidence') else 'medium'
        }

        return digest

    def validate_answer(self, answer: str, evidence: List[Dict]) -> Dict:
        """
        Validate an answer against evidence base

        Args:
            answer: Answer text to validate
            evidence: Supporting evidence pieces

        Returns:
            Validation results with confidence scoring
        """
        # This would implement answer validation logic
        validation_result = {
            'is_supported': True,  # Placeholder
            'support_strength': 'strong',  # Placeholder
            'conflicting_evidence': [],
            'missing_citations': [],
            'confidence_score': 0.85  # Placeholder
        }

        return validation_result

    def get_conversation_history(self) -> List[Dict]:
        """Get conversation history for current session"""
        return self.conversation_history.copy()

    def clear_conversation(self):
        """Clear conversation history"""
        self.conversation_history.clear()
        logger.info("Conversation history cleared")

    def export_session(self, file_path: Optional[str] = None) -> str:
        """Export session data to JSON file"""
        if file_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = f"session_export_{timestamp}.json"

        session_data = {
            'session_metadata': self.session_metadata,
            'conversation_history': self.conversation_history,
            'exported_at': datetime.now().isoformat()
        }

        with open(file_path, 'w') as f:
            json.dump(session_data, f, indent=2)

        logger.info(f"Session exported to {file_path}")
        return file_path

    def _extract_evidence(self, question: str, search_results: Dict) -> List[Dict]:
        """Extract relevant evidence pieces from search results"""
        evidence_pieces = []

        for result in search_results.get('results', []):
            # Ensure we have proper relevance scores
            relevance_score = result.relevance_score or 0
            if relevance_score <= 0:
                # Assign a minimal relevance score based on quality and recency
                relevance_score = 0.1
                if hasattr(result, 'evidence_quality') and result.evidence_quality == 'high':
                    relevance_score += 0.1
                # Boost for recent publications
                try:
                    if hasattr(result, 'publication_date') and result.publication_date and result.publication_date != "Unknown":
                        year = int(result.publication_date.split('-')[0])
                        if (datetime.now().year - year) <= 3:
                            relevance_score += 0.05
                except:
                    pass

            evidence_piece = {
                'pmid': result.pmid,
                'title': result.title,
                'authors': result.authors or [],
                'journal': result.journal,
                'publication_date': result.publication_date,
                'relevant_text': result.relevant_chunks or [getattr(result, 'abstract_snippet', '')],
                'relevance_score': relevance_score,
                'study_type': result.study_type,
                'evidence_quality': result.evidence_quality or 'medium',
                'therapeutic_area': result.therapeutic_area
            }
            evidence_pieces.append(evidence_piece)

        # Sort by relevance
        evidence_pieces.sort(key=lambda x: x['relevance_score'], reverse=True)

        # Ensure we return at least 5 papers for proper citation generation
        min_evidence = 5
        max_evidence = self.config.get('max_search_results', 20)

        # If we have fewer than minimum, still return what we have
        if len(evidence_pieces) >= min_evidence:
            return evidence_pieces[:max_evidence]
        else:
            return evidence_pieces  # Return all available evidence

    def _assess_uncertainty(self, answer_result, evidence_synthesis: Dict, search_results: Dict) -> Dict:
        """Assess uncertainty and confidence in the answer"""
        uncertainty_factors = []

        # Check answer confidence - handle both dict and dataclass
        if hasattr(answer_result, 'confidence'):
            answer_confidence = answer_result.confidence
        else:
            answer_confidence = answer_result.get('confidence', 0.5) if isinstance(answer_result, dict) else 0.5

        if answer_confidence < self.config.get('confidence_threshold', 0.6):
            uncertainty_factors.append('Low answer generation confidence')

        # Check evidence consensus - handle both dict and dataclass
        if hasattr(evidence_synthesis, 'conflicts'):
            conflicts = evidence_synthesis.conflicts
        else:
            conflicts = evidence_synthesis.get('conflicts', []) if isinstance(evidence_synthesis, dict) else []

        if conflicts:
            uncertainty_factors.append('Conflicting evidence identified')

        # Check evidence quantity
        num_sources = len(search_results.get('results', []))
        if num_sources < 3:
            uncertainty_factors.append('Limited number of supporting sources')

        # Check recency of evidence
        recent_evidence = sum(1 for result in search_results.get('results', [])
                            if self._is_recent(result.publication_date))
        if recent_evidence < num_sources * 0.3:
            uncertainty_factors.append('Evidence may not reflect recent developments')

        # Overall uncertainty level
        if len(uncertainty_factors) == 0:
            uncertainty_level = 'low'
        elif len(uncertainty_factors) <= 2:
            uncertainty_level = 'medium'
        else:
            uncertainty_level = 'high'

        return {
            'uncertainty_level': uncertainty_level,
            'uncertainty_factors': uncertainty_factors,
            'confidence_score': max(0.1, answer_confidence - (len(uncertainty_factors) * 0.1)),
            'recommendations': self._get_uncertainty_recommendations(uncertainty_factors)
        }

    def _compile_response(self, question: str, answer,
                         evidence_synthesis: Dict, citations: List[Dict],
                         uncertainty: Dict, search_metadata: Dict) -> Dict:
        """Compile final response to user"""
        return {
            'question': question,
            'answer': {
                'text': answer.answer_text if hasattr(answer, 'answer_text') else '',
                'confidence': answer.confidence if hasattr(answer, 'confidence') else 0.5,
                'key_points': answer.key_points if hasattr(answer, 'key_points') else []
            },
            'evidence': {
                'synthesis': evidence_synthesis.summary if hasattr(evidence_synthesis, 'summary') else '',
                'key_findings': evidence_synthesis.key_findings if hasattr(evidence_synthesis, 'key_findings') else [],
                'consensus_areas': evidence_synthesis.consensus if hasattr(evidence_synthesis, 'consensus') else [],
                'conflicting_evidence': evidence_synthesis.conflicts if hasattr(evidence_synthesis, 'conflicts') else [],
                'strength_assessment': evidence_synthesis.strength_assessment if hasattr(evidence_synthesis, 'strength_assessment') else {}
            },
            'citations': citations,
            'uncertainty': uncertainty,
            'metadata': {
                'search_results_count': search_metadata.get('total_results', 0),
                'search_time': search_metadata.get('search_time', 0),
                'therapeutic_area': search_metadata.get('therapeutic_area'),
                'evidence_recency': search_metadata.get('evidence_recency'),
                'session_id': self.session_id,
                'timestamp': datetime.now().isoformat()
            },
            'recommendations': self._generate_follow_up_recommendations(question, answer, evidence_synthesis)
        }

    def _format_search_results(self, search_results: Dict) -> List[Dict]:
        """Format search results for display"""
        formatted_results = []

        for result in search_results.get('results', []):
            formatted_result = {
                'pmid': result.get('pmid'),
                'title': result.get('title'),
                'authors': result.get('authors', [])[:3],  # First 3 authors
                'journal': result.get('journal'),
                'publication_date': result.get('publication_date'),
                'relevance_score': result.get('relevance_score', 0),
                'study_type': result.get('study_type'),
                'abstract_snippet': result.get('abstract_snippet', '')[:200] + '...',
                'doi': result.get('doi'),
                'full_text_available': result.get('full_text_available', False)
            }
            formatted_results.append(formatted_result)

        return formatted_results

    def _extract_clinical_implications(self, evidence_pieces: List[Dict]) -> List[str]:
        """Extract clinical implications from evidence"""
        implications = []

        # This would be enhanced with more sophisticated extraction
        for piece in evidence_pieces[:5]:  # Top 5 pieces
            if 'clinical trial' in piece.get('study_type', '').lower():
                implications.append(f"Clinical trial evidence from {piece.get('title', '')}")

        return implications[:3]  # Limit to top 3

    def _track_conversation(self, question: str, response: Dict):
        """Track conversation for session history"""
        conversation_entry = {
            'timestamp': datetime.now().isoformat(),
            'question': question,
            'answer_summary': response['answer']['text'][:200],
            'confidence': response['answer']['confidence'],
            'citations_count': len(response['citations']),
            'uncertainty_level': response['uncertainty']['uncertainty_level']
        }

        self.conversation_history.append(conversation_entry)

        # Limit conversation history size
        max_history = 50
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]

    def _create_error_response(self, error_message: str) -> Dict:
        """Create error response"""
        return {
            'error': True,
            'message': error_message,
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id
        }

    def _is_recent(self, publication_date: str) -> bool:
        """Check if publication is recent (within 3 years)"""
        try:
            if publication_date and publication_date != "Unknown":
                year = int(publication_date.split('-')[0])
                return (datetime.now().year - year) <= 3
        except:
            pass
        return False

    def _get_uncertainty_recommendations(self, uncertainty_factors: List[str]) -> List[str]:
        """Get recommendations based on uncertainty factors"""
        recommendations = []

        if 'Low answer generation confidence' in uncertainty_factors:
            recommendations.append("Consider consulting additional sources or domain experts")

        if 'Conflicting evidence identified' in uncertainty_factors:
            recommendations.append("Review conflicting studies for methodological differences")

        if 'Limited number of supporting sources' in uncertainty_factors:
            recommendations.append("Expand search criteria or consult specialized databases")

        return recommendations

    def _generate_follow_up_recommendations(self, question: str, answer,
                                          evidence_synthesis: Dict) -> List[str]:
        """Generate follow-up recommendations"""
        recommendations = []

        # Based on evidence gaps
        if hasattr(evidence_synthesis, 'gaps') and evidence_synthesis.gaps:
            recommendations.append("Consider searching for additional evidence in identified gap areas")

        # Based on conflicting evidence
        if hasattr(evidence_synthesis, 'conflicts') and evidence_synthesis.conflicts:
            recommendations.append("Investigate conflicting findings for potential resolution")

        # Based on answer confidence
        answer_confidence = answer.confidence if hasattr(answer, 'confidence') else 0
        if answer_confidence < 0.7:
            recommendations.append("Validate findings with domain expert review")

        return recommendations

def main():
    """Main entry point for therapeutic area copilot"""
    import sys

    # Check for demo mode
    demo_mode = '--demo' in sys.argv

    copilot = TherapeuticAreaCopilot()

    print("Therapeutic Area Copilot - Medical Literature Q&A Assistant")
    print("="*60)
    print("Ask questions about oncology, immunotherapy, and related therapeutic areas.")
    print("Type 'exit' to quit, 'history' to see conversation history.")
    print()

    # Run demo question first if in demo mode
    if demo_mode:
        print("🚀 Demo Question: 'What is the efficacy of pembrolizumab in cancer treatment?'")
        print("=" * 80)

        demo_question = "What is the efficacy of pembrolizumab in cancer treatment?"
        response = copilot.ask_question(demo_question)

        if response.get('error'):
            print(f"Demo Error: {response['message']}\n")
        else:
            # Display demo response
            print(f"\nAnswer: {response['answer']['text']}")
            print(f"Confidence: {response['answer']['confidence']:.2f}")

            if response['uncertainty']['uncertainty_level'] != 'low':
                print(f"Uncertainty: {response['uncertainty']['uncertainty_level']}")

            print(f"\nCitations ({len(response['citations'])}):")
            for i, citation in enumerate(response['citations'][:5], 1):
                print(f"{i}. {citation}")

            if response['evidence']['conflicting_evidence']:
                print("\nConflicting evidence noted:")
                for conflict in response['evidence']['conflicting_evidence']:
                    print(f"  - {conflict}")

        print()
        print("=" * 80)
        print("✅ Demo completed! Now you can ask your own questions:")
        print()

    while True:
        try:
            question = input("Question: ").strip()

            if question.lower() == 'exit':
                # Export session before exit
                export_path = copilot.export_session()
                print(f"Session exported to: {export_path}")
                break

            elif question.lower() == 'history':
                history = copilot.get_conversation_history()
                print(f"\nConversation History ({len(history)} questions):")
                for i, entry in enumerate(history[-5:], 1):  # Last 5 questions
                    print(f"{i}. {entry['question']}")
                    print(f"   Answer: {entry['answer_summary']}...")
                    print(f"   Confidence: {entry['confidence']:.2f}, Citations: {entry['citations_count']}")
                print()
                continue

            elif question.lower() == 'clear':
                copilot.clear_conversation()
                print("Conversation history cleared.\n")
                continue

            if not question:
                continue

            # Process question
            response = copilot.ask_question(question)

            if response.get('error'):
                print(f"Error: {response['message']}\n")
                continue

            # Display response
            print(f"\nAnswer: {response['answer']['text']}")
            print(f"Confidence: {response['answer']['confidence']:.2f}")

            if response['uncertainty']['uncertainty_level'] != 'low':
                print(f"Uncertainty: {response['uncertainty']['uncertainty_level']}")
                if response['uncertainty']['uncertainty_factors']:
                    print("Uncertainty factors:")
                    for factor in response['uncertainty']['uncertainty_factors']:
                        print(f"  - {factor}")

            print(f"\nCitations ({len(response['citations'])}):")
            for i, citation in enumerate(response['citations'][:5], 1):
                print(f"{i}. {citation}")

            if response['evidence']['conflicting_evidence']:
                print("\nConflicting evidence noted:")
                for conflict in response['evidence']['conflicting_evidence']:
                    print(f"  - {conflict}")

            print()

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except EOFError:
            print("\n✅ Demo completed! The copilot is now ready for your questions.")
            break
        except Exception as e:
            print(f"Unexpected error: {e}\n")

if __name__ == "__main__":
    main()