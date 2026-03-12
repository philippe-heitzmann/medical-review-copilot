"""
Medical Knowledge Base - Manages approved literature corpus
Handles document storage, indexing, and retrieval for the therapeutic area copilot
"""

import json
import logging
import pickle
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
import hashlib
import numpy as np
from dataclasses import dataclass, asdict

# Check for AI libraries - use fallback if not available
EMBEDDINGS_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    # MVP mode - no AI libraries, just use keyword search
    EMBEDDINGS_AVAILABLE = False
    SentenceTransformer = None
    faiss = None
    logging.info("Running in MVP mode - keyword search only (no AI embeddings)")

logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """Document chunk with metadata for retrieval"""
    chunk_id: str
    pmid: str
    title: str
    authors: List[str]
    journal: str
    publication_date: str
    text: str
    chunk_index: int
    section_type: str  # abstract, introduction, results, etc.
    therapeutic_areas: List[str]
    mesh_terms: List[str]
    study_type: str
    evidence_quality: str
    embedding: Optional[np.ndarray] = None
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Convert to dictionary, excluding embedding for serialization"""
        data = asdict(self)
        data.pop('embedding', None)  # Remove embedding for JSON serialization
        return data

@dataclass
class CorpusStatistics:
    """Statistics about the knowledge base corpus"""
    total_documents: int
    total_chunks: int
    therapeutic_areas: Dict[str, int]
    publication_years: Dict[str, int]
    journals: Dict[str, int]
    study_types: Dict[str, int]
    last_updated: str
    embedding_model: Optional[str] = None
    index_size_mb: float = 0.0

class MedicalKnowledgeBase:
    """Medical literature knowledge base with semantic search capabilities"""

    def __init__(self, config: Dict):
        """Initialize knowledge base"""
        self.config = config
        self.corpus_path = Path(config.get('corpus_path', 'data/approved_corpus'))
        self.corpus_path.mkdir(parents=True, exist_ok=True)

        # Initialize embedding model if available
        self.embedding_model = None
        self.embedding_dimension = 0
        if EMBEDDINGS_AVAILABLE and config.get('embedding_model'):
            self._initialize_embeddings(config['embedding_model'])

        # Initialize document storage
        self.documents = {}  # pmid -> document metadata
        self.chunks = {}     # chunk_id -> DocumentChunk
        self.chunk_index = None  # FAISS index for semantic search

        # Load existing corpus
        self._load_corpus()

        # Load demo papers if corpus is empty
        if len(self.chunks) == 0:
            self._load_demo_corpus()

        logger.info(f"Knowledge base initialized with {len(self.chunks)} chunks")

    def _initialize_embeddings(self, model_name: str):
        """Initialize sentence embedding model"""
        try:
            self.embedding_model = SentenceTransformer(model_name)
            self.embedding_dimension = self.embedding_model.get_sentence_embedding_dimension()
            logger.info(f"Initialized embedding model: {model_name} (dim: {self.embedding_dimension})")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            self.embedding_model = None

    def add_publications(self, publications: List[Dict]) -> int:
        """
        Add publications to the knowledge base

        Args:
            publications: List of publication dictionaries from weekly triage

        Returns:
            Number of publications successfully added
        """
        added_count = 0

        for pub_data in publications:
            try:
                publication = pub_data['publication']
                pmid = publication.pmid

                # Check if already exists
                if pmid in self.documents:
                    logger.debug(f"Publication {pmid} already exists, skipping")
                    continue

                # Create document chunks
                chunks = self._create_document_chunks(pub_data)
                if chunks:
                    # Add to storage
                    self.documents[pmid] = self._extract_document_metadata(pub_data)
                    for chunk in chunks:
                        self.chunks[chunk.chunk_id] = chunk

                    added_count += 1
                    logger.debug(f"Added publication {pmid} with {len(chunks)} chunks")

            except Exception as e:
                logger.error(f"Failed to add publication: {e}")
                continue

        # Rebuild index if publications were added
        if added_count > 0:
            self._rebuild_embeddings_index()
            self._save_corpus()
            logger.info(f"Added {added_count} publications to knowledge base")

        return added_count

    def search_semantic(self, query: str, top_k: int = 10,
                       filters: Optional[Dict] = None) -> List[Tuple[DocumentChunk, float]]:
        """
        Perform semantic search over the corpus

        Args:
            query: Search query
            top_k: Number of top results to return
            filters: Optional filters (therapeutic_area, date_range, etc.)

        Returns:
            List of (DocumentChunk, similarity_score) tuples
        """
        if not self.embedding_model or not self.chunk_index:
            logger.warning("Semantic search not available - embeddings not initialized")
            return self._fallback_keyword_search(query, top_k, filters)

        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0]

            # Search index
            similarities, indices = self.chunk_index.search(
                query_embedding.reshape(1, -1), top_k * 2  # Get more for filtering
            )

            # Convert to results
            results = []
            chunk_list = list(self.chunks.values())

            for similarity, idx in zip(similarities[0], indices[0]):
                if idx < len(chunk_list):
                    chunk = chunk_list[idx]

                    # Apply filters
                    if self._passes_filters(chunk, filters):
                        results.append((chunk, float(similarity)))

            # Sort by similarity and limit
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return self._fallback_keyword_search(query, top_k, filters)

    def search_by_pmid(self, pmid: str) -> Optional[Dict]:
        """Get document by PMID"""
        return self.documents.get(pmid)

    def get_document_chunks(self, pmid: str) -> List[DocumentChunk]:
        """Get all chunks for a specific document"""
        return [chunk for chunk in self.chunks.values() if chunk.pmid == pmid]

    def get_corpus_statistics(self) -> CorpusStatistics:
        """Get statistics about the corpus"""
        therapeutic_areas = {}
        publication_years = {}
        journals = {}
        study_types = {}

        for chunk in self.chunks.values():
            # Count therapeutic areas
            for area in chunk.therapeutic_areas:
                therapeutic_areas[area] = therapeutic_areas.get(area, 0) + 1

            # Count publication years
            try:
                year = chunk.publication_date.split('-')[0]
                publication_years[year] = publication_years.get(year, 0) + 1
            except:
                pass

            # Count journals
            journals[chunk.journal] = journals.get(chunk.journal, 0) + 1

            # Count study types
            study_types[chunk.study_type] = study_types.get(chunk.study_type, 0) + 1

        # Calculate index size
        index_size_mb = 0.0
        if self.chunk_index:
            try:
                index_size_mb = self.chunk_index.ntotal * self.embedding_dimension * 4 / (1024 * 1024)  # Rough estimate
            except:
                pass

        return CorpusStatistics(
            total_documents=len(self.documents),
            total_chunks=len(self.chunks),
            therapeutic_areas=therapeutic_areas,
            publication_years=publication_years,
            journals=dict(sorted(journals.items(), key=lambda x: x[1], reverse=True)[:20]),
            study_types=study_types,
            last_updated=datetime.now().isoformat(),
            embedding_model=self.config.get('embedding_model'),
            index_size_mb=index_size_mb
        )

    def remove_publication(self, pmid: str) -> bool:
        """Remove publication and its chunks"""
        if pmid not in self.documents:
            return False

        # Remove chunks
        chunks_to_remove = [chunk_id for chunk_id, chunk in self.chunks.items()
                           if chunk.pmid == pmid]

        for chunk_id in chunks_to_remove:
            del self.chunks[chunk_id]

        # Remove document
        del self.documents[pmid]

        # Rebuild index
        self._rebuild_embeddings_index()
        self._save_corpus()

        logger.info(f"Removed publication {pmid} and {len(chunks_to_remove)} chunks")
        return True

    def update_publication_metadata(self, pmid: str, metadata: Dict) -> bool:
        """Update publication metadata"""
        if pmid not in self.documents:
            return False

        self.documents[pmid].update(metadata)

        # Update chunks if needed
        for chunk in self.chunks.values():
            if chunk.pmid == pmid:
                # Update relevant chunk metadata
                for key, value in metadata.items():
                    if hasattr(chunk, key):
                        setattr(chunk, key, value)

        self._save_corpus()
        return True

    def export_corpus(self, output_path: str, format: str = 'json') -> str:
        """Export corpus to file"""
        output_file = Path(output_path)

        if format == 'json':
            corpus_data = {
                'documents': self.documents,
                'chunks': {chunk_id: chunk.to_dict() for chunk_id, chunk in self.chunks.items()},
                'statistics': asdict(self.get_corpus_statistics()),
                'exported_at': datetime.now().isoformat()
            }

            with open(output_file, 'w') as f:
                json.dump(corpus_data, f, indent=2)

        elif format == 'csv':
            # Export chunks as CSV
            import csv
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'chunk_id', 'pmid', 'title', 'journal', 'publication_date',
                    'text', 'section_type', 'therapeutic_areas', 'study_type'
                ])
                writer.writeheader()
                for chunk in self.chunks.values():
                    row = chunk.to_dict()
                    row['therapeutic_areas'] = ';'.join(row['therapeutic_areas'])
                    writer.writerow(row)

        logger.info(f"Corpus exported to {output_file}")
        return str(output_file)

    def _create_document_chunks(self, pub_data: Dict) -> List[DocumentChunk]:
        """Create document chunks from publication data"""
        publication = pub_data['publication']
        chunks = []

        # Extract metadata
        therapeutic_areas = [
            area.category if hasattr(area, 'category') else area
            for area in pub_data.get('therapeutic_areas', [])
        ]

        mesh_terms = [term.descriptor for term in publication.mesh_terms]
        study_type = self._determine_study_type(pub_data)
        evidence_quality = self._assess_evidence_quality(pub_data)

        # Create abstract chunk
        if publication.abstract:
            chunk = self._create_chunk(
                publication=publication,
                text=publication.abstract,
                chunk_index=0,
                section_type='abstract',
                therapeutic_areas=therapeutic_areas,
                mesh_terms=mesh_terms,
                study_type=study_type,
                evidence_quality=evidence_quality
            )
            chunks.append(chunk)

        # For now, just use abstract. Full-text chunking would be added here
        # when PMC full-text access is implemented

        return chunks

    def _create_chunk(self, publication, text: str, chunk_index: int,
                     section_type: str, therapeutic_areas: List[str],
                     mesh_terms: List[str], study_type: str,
                     evidence_quality: str) -> DocumentChunk:
        """Create a single document chunk"""

        # Generate unique chunk ID
        chunk_content = f"{publication.pmid}_{chunk_index}_{text[:50]}"
        chunk_id = hashlib.md5(chunk_content.encode()).hexdigest()

        # Generate embedding if model available
        embedding = None
        if self.embedding_model:
            try:
                embedding = self.embedding_model.encode([text])[0]
            except Exception as e:
                logger.warning(f"Failed to generate embedding for chunk {chunk_id}: {e}")

        return DocumentChunk(
            chunk_id=chunk_id,
            pmid=publication.pmid,
            title=publication.title,
            authors=[f"{author.last_name}, {author.fore_name}"
                    for author in publication.authors if author.last_name],
            journal=publication.journal,
            publication_date=publication.publication_date,
            text=text,
            chunk_index=chunk_index,
            section_type=section_type,
            therapeutic_areas=therapeutic_areas,
            mesh_terms=mesh_terms,
            study_type=study_type,
            evidence_quality=evidence_quality,
            embedding=embedding
        )

    def _determine_study_type(self, pub_data: Dict) -> str:
        """Determine study type from publication data"""
        publication = pub_data['publication']
        classification_metadata = pub_data.get('classification_metadata', {})

        pub_types = [pt.lower() for pt in publication.publication_types]

        if any(pt in pub_types for pt in ['clinical trial', 'randomized controlled trial']):
            return 'clinical_trial'
        elif any(pt in pub_types for pt in ['meta-analysis']):
            return 'meta_analysis'
        elif any(pt in pub_types for pt in ['systematic review']):
            return 'systematic_review'
        elif any(pt in pub_types for pt in ['review']):
            return 'review'
        elif classification_metadata.get('has_clinical_data'):
            return 'observational'
        else:
            return 'research_article'

    def _assess_evidence_quality(self, pub_data: Dict) -> str:
        """Assess evidence quality"""
        priority_score = pub_data.get('priority_score', 0)

        if priority_score >= 8:
            return 'high'
        elif priority_score >= 6:
            return 'medium'
        else:
            return 'low'

    def _extract_document_metadata(self, pub_data: Dict) -> Dict:
        """Extract document metadata for storage"""
        publication = pub_data['publication']

        return {
            'pmid': publication.pmid,
            'title': publication.title,
            'authors': [f"{author.last_name}, {author.fore_name}"
                       for author in publication.authors if author.last_name],
            'journal': publication.journal,
            'publication_date': publication.publication_date,
            'doi': publication.doi,
            'pmc_id': publication.pmc_id,
            'therapeutic_areas': [
                area.category if hasattr(area, 'category') else area
                for area in pub_data.get('therapeutic_areas', [])
            ],
            'priority_score': pub_data.get('priority_score', 0),
            'relevance_score': pub_data.get('relevance_score', 0),
            'added_at': datetime.now().isoformat()
        }

    def _rebuild_embeddings_index(self):
        """Rebuild FAISS index from chunks"""
        if not self.embedding_model or not EMBEDDINGS_AVAILABLE:
            return

        try:
            # Collect embeddings
            embeddings = []
            valid_chunks = []

            for chunk in self.chunks.values():
                if chunk.embedding is not None:
                    embeddings.append(chunk.embedding)
                    valid_chunks.append(chunk)
                else:
                    # Generate missing embedding
                    try:
                        embedding = self.embedding_model.encode([chunk.text])[0]
                        chunk.embedding = embedding
                        embeddings.append(embedding)
                        valid_chunks.append(chunk)
                    except Exception as e:
                        logger.warning(f"Failed to generate embedding for chunk {chunk.chunk_id}: {e}")

            if not embeddings:
                logger.warning("No embeddings available for index")
                return

            # Create FAISS index
            embeddings_array = np.array(embeddings).astype('float32')
            self.chunk_index = faiss.IndexFlatIP(self.embedding_dimension)  # Inner product for similarity

            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings_array)
            self.chunk_index.add(embeddings_array)

            logger.info(f"Rebuilt embeddings index with {len(embeddings)} vectors")

        except Exception as e:
            logger.error(f"Failed to rebuild embeddings index: {e}")
            self.chunk_index = None

    def _load_corpus(self):
        """Load corpus from persistent storage"""
        documents_file = self.corpus_path / 'documents.json'
        chunks_file = self.corpus_path / 'chunks.pkl'
        index_file = self.corpus_path / 'index.faiss'

        # Load documents
        if documents_file.exists():
            try:
                with open(documents_file, 'r') as f:
                    self.documents = json.load(f)
                logger.debug(f"Loaded {len(self.documents)} documents")
            except Exception as e:
                logger.error(f"Failed to load documents: {e}")

        # Load chunks
        if chunks_file.exists():
            try:
                with open(chunks_file, 'rb') as f:
                    self.chunks = pickle.load(f)
                logger.debug(f"Loaded {len(self.chunks)} chunks")
            except Exception as e:
                logger.error(f"Failed to load chunks: {e}")

        # Load index
        if index_file.exists() and EMBEDDINGS_AVAILABLE and self.embedding_model:
            try:
                self.chunk_index = faiss.read_index(str(index_file))
                logger.debug("Loaded FAISS index")
            except Exception as e:
                logger.warning(f"Failed to load index, will rebuild: {e}")
                self._rebuild_embeddings_index()

    def _save_corpus(self):
        """Save corpus to persistent storage"""
        # Save documents
        documents_file = self.corpus_path / 'documents.json'
        with open(documents_file, 'w') as f:
            json.dump(self.documents, f, indent=2)

        # Save chunks
        chunks_file = self.corpus_path / 'chunks.pkl'
        with open(chunks_file, 'wb') as f:
            pickle.dump(self.chunks, f)

        # Save index
        if self.chunk_index and EMBEDDINGS_AVAILABLE:
            index_file = self.corpus_path / 'index.faiss'
            faiss.write_index(self.chunk_index, str(index_file))

        logger.debug("Corpus saved to disk")

    def _passes_filters(self, chunk: DocumentChunk, filters: Optional[Dict]) -> bool:
        """Check if chunk passes filter criteria"""
        if not filters:
            return True

        # Therapeutic area filter
        if 'therapeutic_area' in filters:
            required_area = filters['therapeutic_area']
            if required_area not in chunk.therapeutic_areas:
                return False

        # Date range filter
        if 'date_from' in filters or 'date_to' in filters:
            try:
                pub_date = datetime.fromisoformat(chunk.publication_date.split('T')[0])
                if 'date_from' in filters:
                    date_from = datetime.fromisoformat(filters['date_from'])
                    if pub_date < date_from:
                        return False
                if 'date_to' in filters:
                    date_to = datetime.fromisoformat(filters['date_to'])
                    if pub_date > date_to:
                        return False
            except:
                pass

        # Study type filter
        if 'study_type' in filters:
            if chunk.study_type != filters['study_type']:
                return False

        # Evidence quality filter
        if 'min_evidence_quality' in filters:
            quality_levels = {'low': 1, 'medium': 2, 'high': 3}
            min_quality = quality_levels.get(filters['min_evidence_quality'], 1)
            chunk_quality = quality_levels.get(chunk.evidence_quality, 1)
            if chunk_quality < min_quality:
                return False

        return True

    def _load_demo_corpus(self):
        """Load demo corpus from JSON files in corpus directory"""
        corpus_dir = Path(self.corpus_path)
        if not corpus_dir.exists():
            return

        logger.info("Loading demo corpus from JSON files...")

        for json_file in corpus_dir.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)

                # Handle both single papers and arrays of papers
                if isinstance(data, list):
                    papers = data
                elif isinstance(data, dict) and 'publications' in data:
                    # Handle triage output format
                    papers = [pub_data['publication'] for pub_data in data['publications']]
                else:
                    # Single paper
                    papers = [data]

                for paper in papers:
                    self._add_demo_paper(paper)

                logger.info(f"Loaded {len(papers)} papers from {json_file.name}")

            except Exception as e:
                logger.warning(f"Failed to load {json_file}: {e}")
                continue

    def _add_demo_paper(self, paper: Dict):
        """Add a demo paper to the knowledge base"""
        try:
            # Extract basic info
            pmid = paper.get('pmid', str(uuid.uuid4()))
            title = paper.get('title', 'Unknown Title')
            abstract = paper.get('abstract', '')
            authors = paper.get('authors', [])
            journal = paper.get('journal', 'Unknown Journal')
            pub_date = paper.get('publication_date', '2024')

            if not abstract or len(abstract) < 50:
                return  # Skip papers without meaningful abstracts

            # Create a simple chunk
            chunk_id = f"demo_{pmid}_{hashlib.md5(abstract.encode()).hexdigest()[:8]}"

            chunk = DocumentChunk(
                chunk_id=chunk_id,
                pmid=pmid,
                title=title,
                authors=authors if isinstance(authors, list) else [str(authors)],
                journal=journal,
                publication_date=pub_date,
                text=abstract,
                chunk_index=0,
                section_type='abstract',
                therapeutic_areas=paper.get('therapeutic_areas', ['oncology']),
                mesh_terms=[],
                study_type='clinical_trial',
                evidence_quality='high'
            )

            self.chunks[chunk_id] = chunk

            # Add to documents index
            self.documents[pmid] = {
                'pmid': pmid,
                'title': title,
                'authors': authors,
                'journal': journal,
                'publication_date': pub_date,
                'added_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.warning(f"Failed to add demo paper: {e}")

    def _fallback_keyword_search(self, query: str, top_k: int,
                                filters: Optional[Dict]) -> List[Tuple[DocumentChunk, float]]:
        """Fallback keyword-based search when embeddings unavailable"""
        query_terms = query.lower().split()
        results = []

        for chunk in self.chunks.values():
            if not self._passes_filters(chunk, filters):
                continue

            # Simple TF-IDF-like scoring
            text_lower = chunk.text.lower()
            title_lower = chunk.title.lower()

            score = 0.0
            for term in query_terms:
                # Title matches get higher weight
                if term in title_lower:
                    score += 2.0
                # Text matches
                score += text_lower.count(term) * 0.1

            # Always include chunks, even if no exact matches
            # This ensures we return results for any query
            if score > 0:
                results.append((chunk, score))
            else:
                # Give a small baseline score based on quality and recency
                baseline_score = 0.1
                if chunk.evidence_quality == 'high':
                    baseline_score += 0.05
                # Add slight boost for recent publications
                try:
                    if chunk.publication_date and chunk.publication_date != "Unknown":
                        year = int(chunk.publication_date.split('-')[0])
                        if (datetime.now().year - year) <= 3:
                            baseline_score += 0.02
                except:
                    pass
                results.append((chunk, baseline_score))

        # Sort by score and return top results
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

def main():
    """Test knowledge base functionality"""
    config = {
        'corpus_path': 'data/test_corpus',
        'embedding_model': 'sentence-transformers/all-mpnet-base-v2',
        'chunk_size': 512
    }

    kb = MedicalKnowledgeBase(config)
    stats = kb.get_corpus_statistics()

    print(f"Knowledge Base Statistics:")
    print(f"Documents: {stats.total_documents}")
    print(f"Chunks: {stats.total_chunks}")
    print(f"Therapeutic Areas: {stats.therapeutic_areas}")

if __name__ == "__main__":
    main()