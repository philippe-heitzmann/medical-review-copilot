"""
Citation Manager - Handles citation formatting and reference management
Manages bibliographic information and citation styles for medical literature
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import re

logger = logging.getLogger(__name__)

@dataclass
class Citation:
    """Standardized citation structure"""
    pmid: str
    citation_text: str
    authors: List[str]
    title: str
    journal: str
    publication_date: str
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    citation_style: str = 'ama'  # AMA, Vancouver, etc.

@dataclass
class CitationContext:
    """Citation with contextual information about its use"""
    citation: Citation
    relevance_score: float
    supporting_text: str
    evidence_type: str  # primary, supporting, contradictory
    quote_used: Optional[str] = None

class CitationManager:
    """Manages citations and bibliographic references for medical literature"""

    def __init__(self, config: Dict):
        """Initialize citation manager"""
        self.config = config
        self.citation_style = config.get('citation_style', 'ama')
        self.max_citations = config.get('max_citations', 10)

        # Citation formatting templates
        self.citation_templates = {
            'ama': self._format_ama_citation,
            'vancouver': self._format_vancouver_citation,
            'apa': self._format_apa_citation
        }

        # Journal abbreviations (subset)
        self.journal_abbreviations = {
            'new england journal of medicine': 'N Engl J Med',
            'journal of clinical oncology': 'J Clin Oncol',
            'clinical cancer research': 'Clin Cancer Res',
            'cancer research': 'Cancer Res',
            'nature medicine': 'Nat Med',
            'lancet oncology': 'Lancet Oncol',
            'lancet': 'Lancet',
            'science': 'Science',
            'nature': 'Nature',
            'cell': 'Cell'
        }

    def format_citations(self, evidence_pieces: List[Dict]) -> List[str]:
        """
        Format citations from evidence pieces

        Args:
            evidence_pieces: List of evidence pieces with publication metadata

        Returns:
            List of formatted citation strings
        """
        citations = []
        seen_pmids = set()

        for piece in evidence_pieces[:self.max_citations]:
            pmid = piece.get('pmid')

            # Avoid duplicate citations
            if pmid in seen_pmids:
                continue

            seen_pmids.add(pmid)

            try:
                citation = self._create_citation_from_evidence(piece)
                formatted_citation = self._format_citation(citation)
                citations.append(formatted_citation)

            except Exception as e:
                logger.warning(f"Failed to format citation for PMID {pmid}: {e}")
                # Create fallback citation
                fallback = self._create_fallback_citation(piece)
                if fallback:
                    citations.append(fallback)

        logger.info(f"Formatted {len(citations)} citations")
        return citations

    def create_citation_contexts(self, evidence_pieces: List[Dict],
                                answer_components: List[Dict]) -> List[CitationContext]:
        """
        Create citation contexts with supporting information

        Args:
            evidence_pieces: Evidence pieces from search
            answer_components: Components used in answer generation

        Returns:
            List of citation contexts with usage information
        """
        citation_contexts = []

        for piece in evidence_pieces:
            try:
                # Create base citation
                citation = self._create_citation_from_evidence(piece)

                # Determine relevance and evidence type
                relevance_score = piece.get('relevance_score', 0.0)
                evidence_type = self._determine_evidence_type(piece, answer_components)

                # Extract supporting text
                supporting_text = self._extract_supporting_text(piece)

                # Find quote used in answer (if any)
                quote_used = self._find_used_quote(piece, answer_components)

                context = CitationContext(
                    citation=citation,
                    relevance_score=relevance_score,
                    supporting_text=supporting_text,
                    evidence_type=evidence_type,
                    quote_used=quote_used
                )

                citation_contexts.append(context)

            except Exception as e:
                logger.warning(f"Failed to create citation context for PMID {piece.get('pmid')}: {e}")

        # Sort by relevance
        citation_contexts.sort(key=lambda x: x.relevance_score, reverse=True)

        return citation_contexts[:self.max_citations]

    def generate_bibliography(self, citation_contexts: List[CitationContext]) -> Dict:
        """
        Generate formatted bibliography with sections

        Args:
            citation_contexts: List of citation contexts

        Returns:
            Structured bibliography
        """
        bibliography = {
            'primary_sources': [],
            'supporting_sources': [],
            'additional_sources': [],
            'total_citations': len(citation_contexts),
            'generated_at': datetime.now().isoformat()
        }

        for context in citation_contexts:
            formatted_citation = self._format_citation(context.citation)

            citation_entry = {
                'citation': formatted_citation,
                'relevance_score': context.relevance_score,
                'evidence_type': context.evidence_type,
                'supporting_text': context.supporting_text[:200] + '...' if len(context.supporting_text) > 200 else context.supporting_text,
                'pmid': context.citation.pmid,
                'doi': context.citation.doi
            }

            # Categorize citations
            if context.relevance_score >= 0.8 and context.evidence_type == 'primary':
                bibliography['primary_sources'].append(citation_entry)
            elif context.relevance_score >= 0.6:
                bibliography['supporting_sources'].append(citation_entry)
            else:
                bibliography['additional_sources'].append(citation_entry)

        return bibliography

    def validate_citations(self, citations: List[str]) -> Dict:
        """
        Validate citation format and completeness

        Args:
            citations: List of formatted citations

        Returns:
            Validation results
        """
        validation_results = {
            'valid_citations': 0,
            'incomplete_citations': 0,
            'missing_elements': [],
            'formatting_issues': []
        }

        for i, citation in enumerate(citations):
            issues = self._validate_single_citation(citation)

            if not issues:
                validation_results['valid_citations'] += 1
            else:
                validation_results['incomplete_citations'] += 1
                validation_results['missing_elements'].extend(issues)

        return validation_results

    def _create_citation_from_evidence(self, evidence_piece: Dict) -> Citation:
        """Create Citation object from evidence piece"""
        # Extract basic information
        pmid = evidence_piece.get('pmid', '')
        title = evidence_piece.get('title', '')
        authors = evidence_piece.get('authors', [])
        journal = evidence_piece.get('journal', '')
        publication_date = evidence_piece.get('publication_date', '')
        doi = evidence_piece.get('doi')

        # Format authors list
        formatted_authors = self._format_authors(authors)

        return Citation(
            pmid=pmid,
            citation_text='',  # Will be generated by formatter
            authors=formatted_authors,
            title=title,
            journal=journal,
            publication_date=publication_date,
            doi=doi,
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
            citation_style=self.citation_style
        )

    def _format_citation(self, citation: Citation) -> str:
        """Format citation using specified style"""
        formatter = self.citation_templates.get(self.citation_style, self.citation_templates['ama'])
        return formatter(citation)

    def _format_ama_citation(self, citation: Citation) -> str:
        """Format citation in AMA style"""
        parts = []

        # Authors
        if citation.authors:
            if len(citation.authors) <= 6:
                authors_str = ', '.join(citation.authors)
            else:
                authors_str = ', '.join(citation.authors[:3]) + ', et al'
            parts.append(authors_str + '.')

        # Title
        if citation.title:
            title = citation.title.rstrip('.')
            parts.append(title + '.')

        # Journal and publication info
        journal_info = []

        if citation.journal:
            # Use abbreviation if available
            journal_abbrev = self.journal_abbreviations.get(
                citation.journal.lower(), citation.journal
            )
            journal_info.append(journal_abbrev)

        if citation.publication_date:
            year = self._extract_year(citation.publication_date)
            if year:
                journal_info.append(year)

        if citation.volume:
            journal_info.append(f"{citation.volume}")
            if citation.issue:
                journal_info[-1] += f"({citation.issue})"

        if citation.pages:
            journal_info.append(citation.pages)

        if journal_info:
            parts.append(' '.join(journal_info) + '.')

        # DOI
        if citation.doi:
            parts.append(f"doi:{citation.doi}")

        # PMID
        if citation.pmid:
            parts.append(f"PMID: {citation.pmid}")

        return ' '.join(parts)

    def _format_vancouver_citation(self, citation: Citation) -> str:
        """Format citation in Vancouver style"""
        # Similar to AMA but with numbered references
        return self._format_ama_citation(citation)

    def _format_apa_citation(self, citation: Citation) -> str:
        """Format citation in APA style"""
        parts = []

        # Authors (Last, F. M.)
        if citation.authors:
            apa_authors = []
            for author in citation.authors[:20]:  # APA doesn't limit as strictly
                if ', ' in author:
                    last, first = author.split(', ', 1)
                    initials = '. '.join(first.split()[0:2]) + '.' if first else ''
                    apa_authors.append(f"{last}, {initials}")
                else:
                    apa_authors.append(author)

            authors_str = ', '.join(apa_authors)
            if len(citation.authors) > 20:
                authors_str = authors_str + ', ... et al'
            parts.append(authors_str)

        # Year
        year = self._extract_year(citation.publication_date)
        if year:
            parts.append(f"({year}).")

        # Title
        if citation.title:
            parts.append(citation.title.rstrip('.') + '.')

        # Journal
        if citation.journal:
            journal_part = f"*{citation.journal}*"
            if citation.volume:
                journal_part += f", *{citation.volume}*"
                if citation.issue:
                    journal_part += f"({citation.issue})"
            if citation.pages:
                journal_part += f", {citation.pages}"
            parts.append(journal_part + '.')

        # DOI
        if citation.doi:
            parts.append(f"https://doi.org/{citation.doi}")

        return ' '.join(parts)

    def _format_authors(self, authors: List[str]) -> List[str]:
        """Format author names consistently"""
        formatted_authors = []

        for author in authors:
            if not author:
                continue

            # Handle different author name formats
            if ', ' in author:
                # Already in "Last, First" format
                formatted_authors.append(author.strip())
            else:
                # Try to split and format
                name_parts = author.strip().split()
                if len(name_parts) >= 2:
                    last_name = name_parts[-1]
                    first_names = ' '.join(name_parts[:-1])
                    # Convert to initials
                    initials = ''.join([name[0].upper() + '.' for name in first_names.split()])
                    formatted_authors.append(f"{last_name} {initials}")
                else:
                    formatted_authors.append(author.strip())

        return formatted_authors

    def _extract_year(self, publication_date: str) -> Optional[str]:
        """Extract year from publication date"""
        if not publication_date or publication_date == "Unknown":
            return None

        # Try different date formats
        year_match = re.match(r'(\d{4})', publication_date)
        if year_match:
            return year_match.group(1)

        return None

    def _determine_evidence_type(self, evidence_piece: Dict, answer_components: List[Dict]) -> str:
        """Determine how evidence was used in the answer"""
        # For now, classify based on relevance score
        relevance = evidence_piece.get('relevance_score', 0.0)

        if relevance >= 0.8:
            return 'primary'
        elif relevance >= 0.6:
            return 'supporting'
        else:
            return 'additional'

    def _extract_supporting_text(self, evidence_piece: Dict) -> str:
        """Extract key supporting text from evidence"""
        relevant_chunks = evidence_piece.get('relevant_text', [])

        if relevant_chunks:
            # Take the first chunk or combine if short
            text = relevant_chunks[0] if isinstance(relevant_chunks[0], str) else str(relevant_chunks[0])
            return text[:500]  # Limit length

        return "Supporting evidence from this publication."

    def _find_used_quote(self, evidence_piece: Dict, answer_components: List[Dict]) -> Optional[str]:
        """Find specific quotes used from this evidence in the answer"""
        # This would be enhanced to actually track quote usage
        return None

    def _create_fallback_citation(self, evidence_piece: Dict) -> Optional[str]:
        """Create a simple fallback citation when full formatting fails"""
        pmid = evidence_piece.get('pmid')
        title = evidence_piece.get('title')
        authors = evidence_piece.get('authors', [])
        journal = evidence_piece.get('journal')

        if not any([pmid, title, journal]):
            return None

        parts = []

        if authors:
            first_author = authors[0] if authors else "Unknown"
            if len(authors) > 1:
                parts.append(f"{first_author}, et al.")
            else:
                parts.append(f"{first_author}.")

        if title:
            parts.append(f"{title.rstrip('.')}.")

        if journal:
            parts.append(f"{journal}.")

        if pmid:
            parts.append(f"PMID: {pmid}")

        return ' '.join(parts) if parts else None

    def _validate_single_citation(self, citation: str) -> List[str]:
        """Validate a single citation and return list of issues"""
        issues = []

        if not citation or len(citation.strip()) < 10:
            issues.append('Citation too short or empty')
            return issues

        # Check for PMID
        if 'PMID:' not in citation and 'pmid' not in citation.lower():
            issues.append('Missing PMID')

        # Check for author
        if not any(char.isupper() for char in citation[:50]):
            issues.append('Possible missing author information')

        # Check for journal/publication info
        if not any(year in citation for year in [str(y) for y in range(1990, 2030)]):
            issues.append('Missing publication year')

        return issues

    def export_citations(self, citation_contexts: List[CitationContext],
                        format: str = 'json') -> str:
        """
        Export citations in specified format

        Args:
            citation_contexts: List of citation contexts
            format: Export format ('json', 'bibtex', 'ris')

        Returns:
            Formatted citation export string
        """
        if format == 'json':
            return self._export_json(citation_contexts)
        elif format == 'bibtex':
            return self._export_bibtex(citation_contexts)
        elif format == 'ris':
            return self._export_ris(citation_contexts)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_json(self, citation_contexts: List[CitationContext]) -> str:
        """Export citations as JSON"""
        citations_data = []

        for context in citation_contexts:
            citation_data = {
                'pmid': context.citation.pmid,
                'title': context.citation.title,
                'authors': context.citation.authors,
                'journal': context.citation.journal,
                'publication_date': context.citation.publication_date,
                'doi': context.citation.doi,
                'url': context.citation.url,
                'relevance_score': context.relevance_score,
                'evidence_type': context.evidence_type
            }
            citations_data.append(citation_data)

        return json.dumps(citations_data, indent=2)

    def _export_bibtex(self, citation_contexts: List[CitationContext]) -> str:
        """Export citations as BibTeX"""
        bibtex_entries = []

        for i, context in enumerate(citation_contexts):
            citation = context.citation
            entry_key = f"pmid{citation.pmid}" if citation.pmid else f"ref{i+1}"

            # Create BibTeX entry
            entry = f"@article{{{entry_key},\n"

            if citation.title:
                entry += f"  title={{{citation.title}}},\n"

            if citation.authors:
                authors_str = ' and '.join(citation.authors)
                entry += f"  author={{{authors_str}}},\n"

            if citation.journal:
                entry += f"  journal={{{citation.journal}}},\n"

            year = self._extract_year(citation.publication_date)
            if year:
                entry += f"  year={{{year}}},\n"

            if citation.doi:
                entry += f"  doi={{{citation.doi}}},\n"

            if citation.pmid:
                entry += f"  pmid={{{citation.pmid}}},\n"

            entry += "}\n"
            bibtex_entries.append(entry)

        return '\n'.join(bibtex_entries)

    def _export_ris(self, citation_contexts: List[CitationContext]) -> str:
        """Export citations as RIS format"""
        ris_entries = []

        for context in citation_contexts:
            citation = context.citation
            entry = "TY  - JOUR\n"  # Journal article

            if citation.title:
                entry += f"TI  - {citation.title}\n"

            for author in citation.authors:
                entry += f"AU  - {author}\n"

            if citation.journal:
                entry += f"JO  - {citation.journal}\n"

            year = self._extract_year(citation.publication_date)
            if year:
                entry += f"PY  - {year}\n"

            if citation.doi:
                entry += f"DO  - {citation.doi}\n"

            if citation.pmid:
                entry += f"AN  - {citation.pmid}\n"

            entry += "ER  - \n\n"
            ris_entries.append(entry)

        return ''.join(ris_entries)

def main():
    """Test citation manager functionality"""
    config = {
        'citation_style': 'ama',
        'max_citations': 10
    }

    citation_manager = CitationManager(config)

    # Test with sample evidence
    sample_evidence = {
        'pmid': '12345678',
        'title': 'Efficacy of pembrolizumab in advanced melanoma',
        'authors': ['Smith, J.', 'Johnson, M.', 'Williams, R.'],
        'journal': 'New England Journal of Medicine',
        'publication_date': '2023-01-15',
        'doi': '10.1056/NEJMoa123456',
        'relevance_score': 0.85
    }

    citations = citation_manager.format_citations([sample_evidence])
    print("Formatted Citation:")
    print(citations[0])

if __name__ == "__main__":
    main()