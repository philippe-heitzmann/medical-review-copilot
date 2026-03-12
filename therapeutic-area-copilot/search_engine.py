"""
Medical Search Engine - Semantic search and information retrieval
Handles query processing, semantic search, and result ranking for medical literature
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import re
from dataclasses import dataclass
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))
from knowledge_base import MedicalKnowledgeBase, DocumentChunk

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Search result with relevance scoring and metadata"""
    pmid: str
    title: str
    authors: List[str]
    journal: str
    publication_date: str
    relevant_chunks: List[str]
    relevance_score: float
    study_type: str
    evidence_quality: str
    therapeutic_area: str
    abstract_snippet: str
    doi: Optional[str] = None
    full_text_available: bool = False
    highlight_text: Optional[str] = None

class QueryProcessor:
    """Processes and expands medical queries"""

    def __init__(self):
        """Initialize query processor"""
        self.medical_synonyms = {
            # Drug class synonyms
            'checkpoint inhibitor': ['pd-1', 'pd-l1', 'ctla-4', 'immune checkpoint'],
            'immunotherapy': ['checkpoint inhibitor', 'car-t', 'adoptive cell therapy'],
            'targeted therapy': ['precision medicine', 'molecular target', 'kinase inhibitor'],

            # Cancer type synonyms
            'lung cancer': ['nsclc', 'non-small cell lung cancer', 'small cell lung cancer', 'sclc'],
            'breast cancer': ['her2', 'triple negative', 'hormone receptor'],
            'melanoma': ['metastatic melanoma', 'cutaneous melanoma'],

            # Treatment terms
            'efficacy': ['response rate', 'overall survival', 'progression free survival'],
            'safety': ['adverse events', 'toxicity', 'side effects'],
            'biomarker': ['companion diagnostic', 'predictive marker', 'prognostic marker']
        }

        self.medical_abbreviations = {
            'os': 'overall survival',
            'pfs': 'progression free survival',
            'cr': 'complete response',
            'pr': 'partial response',
            'sd': 'stable disease',
            'pd': 'progressive disease',
            'aes': 'adverse events',
            'sae': 'serious adverse events'
        }

    def process_query(self, query: str, context: Optional[Dict] = None) -> Dict:
        """
        Process and expand medical query

        Args:
            query: Raw user query
            context: Optional context for query expansion

        Returns:
            Processed query information
        """
        # Clean and normalize query
        normalized_query = self._normalize_query(query)

        # Expand medical terms
        expanded_terms = self._expand_medical_terms(normalized_query)

        # Extract key concepts
        key_concepts = self._extract_key_concepts(normalized_query)

        # Determine query intent
        intent = self._determine_query_intent(normalized_query, context)

        # Generate search variants
        search_variants = self._generate_search_variants(normalized_query, expanded_terms)

        return {
            'original_query': query,
            'normalized_query': normalized_query,
            'expanded_terms': expanded_terms,
            'key_concepts': key_concepts,
            'intent': intent,
            'search_variants': search_variants,
            'therapeutic_areas': self._identify_therapeutic_areas(normalized_query)
        }

    def _normalize_query(self, query: str) -> str:
        """Normalize query text"""
        # Convert to lowercase
        normalized = query.lower()

        # Expand common abbreviations
        for abbr, full_form in self.medical_abbreviations.items():
            pattern = r'\b' + re.escape(abbr) + r'\b'
            normalized = re.sub(pattern, full_form, normalized)

        # Clean extra whitespace
        normalized = ' '.join(normalized.split())

        return normalized

    def _expand_medical_terms(self, query: str) -> List[str]:
        """Expand medical terms using synonyms"""
        expanded = []

        for term, synonyms in self.medical_synonyms.items():
            if term in query:
                expanded.extend(synonyms)

        return list(set(expanded))

    def _extract_key_concepts(self, query: str) -> List[str]:
        """Extract key medical concepts from query"""
        # Medical concept patterns
        drug_patterns = [
            r'\b\w+mab\b',  # monoclonal antibodies
            r'\b\w+tinib\b',  # kinase inhibitors
        ]

        cancer_patterns = [
            r'\b\w+ cancer\b',
            r'\b\w+ carcinoma\b',
            r'\b\w+ sarcoma\b'
        ]

        concepts = []

        # Extract drug names
        for pattern in drug_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            concepts.extend(matches)

        # Extract cancer types
        for pattern in cancer_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            concepts.extend(matches)

        return list(set(concepts))

    def _determine_query_intent(self, query: str, context: Optional[Dict]) -> str:
        """Determine the intent of the query"""
        # Efficacy questions
        if any(word in query for word in ['efficacy', 'effective', 'response', 'survival']):
            return 'efficacy'

        # Safety questions
        if any(word in query for word in ['safety', 'adverse', 'toxicity', 'side effects']):
            return 'safety'

        # Mechanism questions
        if any(word in query for word in ['mechanism', 'how does', 'pathway', 'target']):
            return 'mechanism'

        # Comparison questions
        if any(word in query for word in ['compare', 'versus', 'vs', 'difference']):
            return 'comparison'

        # General information
        return 'general'

    def _generate_search_variants(self, query: str, expanded_terms: List[str]) -> List[str]:
        """Generate query variants for comprehensive search"""
        variants = [query]

        # Add expanded term variants
        if expanded_terms:
            for term in expanded_terms[:3]:  # Limit to avoid too many variants
                variants.append(f"{query} {term}")

        return variants

    def _identify_therapeutic_areas(self, query: str) -> List[str]:
        """Identify therapeutic areas mentioned in query"""
        areas = []

        area_keywords = {
            'oncology': ['cancer', 'tumor', 'neoplasm', 'oncology', 'malignant'],
            'immunotherapy': ['immunotherapy', 'immune', 'checkpoint', 'car-t'],
            'targeted_therapy': ['targeted', 'precision', 'molecular', 'personalized'],
            'biomarkers': ['biomarker', 'diagnostic', 'predictive', 'prognostic']
        }

        for area, keywords in area_keywords.items():
            if any(keyword in query for keyword in keywords):
                areas.append(area)

        return areas

class MedicalSearchEngine:
    """Medical literature search engine with semantic capabilities"""

    def __init__(self, config: Dict):
        """Initialize search engine"""
        self.config = config
        self.query_processor = QueryProcessor()

        # Initialize knowledge base (would be injected in production)
        self.knowledge_base = None
        self._initialize_knowledge_base()

    def _initialize_knowledge_base(self):
        """Initialize knowledge base connection"""
        # In production, this would be injected
        kb_config = self.config.get('knowledge_base', {})
        if not kb_config:
            kb_config = {
                'corpus_path': 'data/approved_corpus',
                'embedding_model': 'sentence-transformers/all-mpnet-base-v2'
            }

        try:
            self.knowledge_base = MedicalKnowledgeBase(kb_config)
        except Exception as e:
            logger.error(f"Failed to initialize knowledge base: {e}")
            self.knowledge_base = None

    def search(self, query: str, context: Optional[Dict] = None,
              max_results: int = 10) -> Dict:
        """
        Perform comprehensive search over medical literature

        Args:
            query: Search query
            context: Optional search context
            max_results: Maximum number of results to return

        Returns:
            Search results with metadata
        """
        search_start_time = time.time()

        if not self.knowledge_base:
            return self._create_error_response("Knowledge base not available")

        try:
            # Process query
            processed_query = self.query_processor.process_query(query, context)

            # Determine search strategy
            search_strategy = self._determine_search_strategy(processed_query, context)

            # Execute search
            raw_results = self._execute_search(processed_query, search_strategy, max_results)

            # Post-process and rank results
            ranked_results = self._rank_results(raw_results, processed_query)

            # Format results
            formatted_results = self._format_results(ranked_results, processed_query)

            # Calculate search metadata
            search_time = time.time() - search_start_time

            return {
                'results': formatted_results,
                'metadata': {
                    'total_results': len(formatted_results),
                    'search_time': search_time,
                    'query_processed': processed_query,
                    'search_strategy': search_strategy,
                    'therapeutic_area': processed_query.get('therapeutic_areas', ['general'])[0]
                        if processed_query.get('therapeutic_areas') else 'general',
                    'evidence_recency': self._assess_evidence_recency(formatted_results),
                    'search_timestamp': datetime.now().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return self._create_error_response(str(e))

    def _determine_search_strategy(self, processed_query: Dict,
                                  context: Optional[Dict]) -> Dict:
        """Determine optimal search strategy"""
        strategy = {
            'method': 'semantic',  # or 'keyword' or 'hybrid'
            'filters': {},
            'boost_factors': {},
            'reranking': True
        }

        # Determine search method
        if self.knowledge_base and self.knowledge_base.embedding_model:
            strategy['method'] = 'semantic'
        else:
            strategy['method'] = 'keyword'

        # Add filters based on context
        if context:
            if 'date_range' in context:
                strategy['filters']['date_range'] = context['date_range']
            if 'therapeutic_area' in context:
                strategy['filters']['therapeutic_area'] = context['therapeutic_area']
            if 'study_type' in context:
                strategy['filters']['study_type'] = context['study_type']

        # Add therapeutic area filters from query
        therapeutic_areas = processed_query.get('therapeutic_areas', [])
        if therapeutic_areas and 'therapeutic_area' not in strategy['filters']:
            strategy['filters']['therapeutic_area'] = therapeutic_areas[0]

        # Set boost factors based on query intent
        intent = processed_query.get('intent', 'general')
        if intent == 'efficacy':
            strategy['boost_factors']['clinical_trial'] = 1.5
            strategy['boost_factors']['meta_analysis'] = 1.3
        elif intent == 'safety':
            strategy['boost_factors']['clinical_trial'] = 1.5
            strategy['boost_factors']['observational'] = 1.2

        return strategy

    def _execute_search(self, processed_query: Dict, strategy: Dict,
                       max_results: int) -> List[Tuple[DocumentChunk, float]]:
        """Execute search with specified strategy"""
        search_variants = processed_query.get('search_variants', [processed_query['normalized_query']])
        all_results = []

        for variant in search_variants:
            if strategy['method'] == 'semantic':
                results = self.knowledge_base.search_semantic(
                    variant,
                    top_k=max_results * 2,  # Get more for reranking
                    filters=strategy['filters']
                )
            else:
                # Fallback keyword search
                results = self.knowledge_base._fallback_keyword_search(
                    variant,
                    max_results * 2,
                    strategy['filters']
                )

            all_results.extend(results)

        # Remove duplicates (same chunk appearing multiple times)
        seen_chunks = set()
        unique_results = []
        for chunk, score in all_results:
            if chunk.chunk_id not in seen_chunks:
                unique_results.append((chunk, score))
                seen_chunks.add(chunk.chunk_id)

        # If we have very few results, ensure we return at least some papers from knowledge base
        if len(unique_results) < max_results and self.knowledge_base and len(self.knowledge_base.chunks) > 0:
            # Get all chunks and add them with low baseline scores
            all_chunks = list(self.knowledge_base.chunks.values())
            for chunk in all_chunks:
                if chunk.chunk_id not in seen_chunks and len(unique_results) < max_results:
                    baseline_score = 0.05  # Very low score for non-matching results
                    if chunk.evidence_quality == 'high':
                        baseline_score += 0.02
                    unique_results.append((chunk, baseline_score))
                    seen_chunks.add(chunk.chunk_id)

        return unique_results

    def _rank_results(self, raw_results: List[Tuple[DocumentChunk, float]],
                     processed_query: Dict) -> List[Tuple[DocumentChunk, float]]:
        """Apply additional ranking logic to search results"""
        if not raw_results:
            return []

        reranked_results = []

        for chunk, base_score in raw_results:
            # Calculate additional scoring factors
            recency_boost = self._calculate_recency_boost(chunk.publication_date)
            quality_boost = self._calculate_quality_boost(chunk.evidence_quality)
            intent_boost = self._calculate_intent_boost(chunk, processed_query.get('intent', 'general'))
            journal_boost = self._calculate_journal_boost(chunk.journal)

            # Combine scores
            final_score = base_score * (1 + recency_boost + quality_boost + intent_boost + journal_boost)

            reranked_results.append((chunk, final_score))

        # Sort by final score
        reranked_results.sort(key=lambda x: x[1], reverse=True)

        return reranked_results

    def _calculate_recency_boost(self, publication_date: str) -> float:
        """Calculate boost factor based on publication recency"""
        try:
            if publication_date == "Unknown":
                return 0.0

            pub_year = int(publication_date.split('-')[0])
            current_year = datetime.now().year
            years_ago = current_year - pub_year

            if years_ago <= 1:
                return 0.2  # 20% boost for very recent
            elif years_ago <= 3:
                return 0.1  # 10% boost for recent
            elif years_ago <= 5:
                return 0.0  # No boost
            else:
                return -0.1  # Slight penalty for older
        except:
            return 0.0

    def _calculate_quality_boost(self, evidence_quality: str) -> float:
        """Calculate boost based on evidence quality"""
        quality_boosts = {
            'high': 0.15,
            'medium': 0.05,
            'low': 0.0
        }
        return quality_boosts.get(evidence_quality, 0.0)

    def _calculate_intent_boost(self, chunk: DocumentChunk, intent: str) -> float:
        """Calculate boost based on query intent matching"""
        text = chunk.text.lower()

        intent_keywords = {
            'efficacy': ['efficacy', 'effective', 'response', 'survival', 'outcome'],
            'safety': ['safety', 'adverse', 'toxicity', 'tolerability'],
            'mechanism': ['mechanism', 'pathway', 'target', 'molecular'],
            'comparison': ['versus', 'compared', 'comparison']
        }

        if intent in intent_keywords:
            keywords = intent_keywords[intent]
            matches = sum(1 for keyword in keywords if keyword in text)
            return min(matches * 0.05, 0.2)  # Max 20% boost

        return 0.0

    def _calculate_journal_boost(self, journal: str) -> float:
        """Calculate boost based on journal impact"""
        high_impact_journals = [
            'new england journal of medicine', 'nature', 'science', 'cell',
            'lancet', 'journal of clinical oncology', 'cancer cell'
        ]

        medium_impact_journals = [
            'clinical cancer research', 'cancer research', 'nature medicine'
        ]

        journal_lower = journal.lower()

        if any(j in journal_lower for j in high_impact_journals):
            return 0.1
        elif any(j in journal_lower for j in medium_impact_journals):
            return 0.05

        return 0.0

    def _format_results(self, ranked_results: List[Tuple[DocumentChunk, float]],
                       processed_query: Dict) -> List[SearchResult]:
        """Format search results for return"""
        formatted_results = []

        for chunk, score in ranked_results:
            # Create abstract snippet with highlighting
            snippet = self._create_snippet(chunk.text, processed_query['normalized_query'])

            # Determine primary therapeutic area
            primary_therapeutic_area = chunk.therapeutic_areas[0] if chunk.therapeutic_areas else 'general'

            result = SearchResult(
                pmid=chunk.pmid,
                title=chunk.title,
                authors=chunk.authors,
                journal=chunk.journal,
                publication_date=chunk.publication_date,
                relevant_chunks=[chunk.text],
                relevance_score=score,
                study_type=chunk.study_type,
                evidence_quality=chunk.evidence_quality,
                therapeutic_area=primary_therapeutic_area,
                abstract_snippet=snippet,
                doi=None,  # Would be populated from document metadata
                full_text_available=False,  # Would be determined from PMC availability
                highlight_text=self._generate_highlights(chunk.text, processed_query['normalized_query'])
            )

            formatted_results.append(result)

        return formatted_results

    def _create_snippet(self, text: str, query: str, max_length: int = 200) -> str:
        """Create text snippet with query context"""
        query_terms = query.split()
        text_lower = text.lower()

        # Find best position for snippet
        best_pos = 0
        best_score = 0

        for i in range(0, len(text) - max_length, 50):
            snippet = text[i:i + max_length].lower()
            score = sum(1 for term in query_terms if term in snippet)
            if score > best_score:
                best_score = score
                best_pos = i

        snippet = text[best_pos:best_pos + max_length]
        if best_pos > 0:
            snippet = "..." + snippet
        if best_pos + max_length < len(text):
            snippet = snippet + "..."

        return snippet

    def _generate_highlights(self, text: str, query: str) -> str:
        """Generate highlighted text for display"""
        query_terms = query.split()
        highlighted = text

        for term in query_terms:
            if len(term) > 2:  # Skip very short terms
                pattern = r'\b' + re.escape(term) + r'\b'
                highlighted = re.sub(pattern, f"**{term}**", highlighted, flags=re.IGNORECASE)

        return highlighted

    def _assess_evidence_recency(self, results: List[SearchResult]) -> str:
        """Assess overall recency of evidence"""
        if not results:
            return 'unknown'

        recent_count = 0
        for result in results:
            try:
                if result.publication_date != "Unknown":
                    pub_year = int(result.publication_date.split('-')[0])
                    if (datetime.now().year - pub_year) <= 3:
                        recent_count += 1
            except:
                continue

        if recent_count / len(results) >= 0.7:
            return 'recent'
        elif recent_count / len(results) >= 0.3:
            return 'mixed'
        else:
            return 'older'

    def _create_error_response(self, error_message: str) -> Dict:
        """Create error response"""
        return {
            'error': True,
            'message': error_message,
            'results': [],
            'metadata': {
                'total_results': 0,
                'search_time': 0,
                'search_timestamp': datetime.now().isoformat()
            }
        }

def main():
    """Test search engine functionality"""
    config = {
        'similarity_threshold': 0.7,
        'max_chunks': 10,
        'reranking_enabled': True
    }

    search_engine = MedicalSearchEngine(config)

    # Test query
    test_query = "What is the efficacy of pembrolizumab in lung cancer?"
    results = search_engine.search(test_query, max_results=5)

    print(f"Search Results for: {test_query}")
    print(f"Found {results['metadata']['total_results']} results")
    for result in results['results']:
        print(f"- {result.title} ({result.journal})")
        print(f"  Relevance: {result.relevance_score:.3f}")

if __name__ == "__main__":
    main()