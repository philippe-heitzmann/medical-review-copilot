"""
PubMed E-utilities API client for oncology/immunotherapy literature retrieval.
Focuses on MeSH terms: Neoplasms and Immunotherapy for Meridian Therapeutics pilot.
"""

import requests
import time
import json
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from urllib.parse import urlencode
import logging
import re

# Use built-in XML parser - avoid lxml dependency issues

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Author:
    """Author metadata structure"""
    last_name: Optional[str] = None
    fore_name: Optional[str] = None
    initials: Optional[str] = None
    affiliation: Optional[str] = None

@dataclass
class MeSHTerm:
    """MeSH term structure"""
    descriptor: str
    qualifier: Optional[str] = None
    major_topic: bool = False

@dataclass
class Publication:
    """Publication structure with all relevant metadata"""
    pmid: str
    title: str
    abstract: str
    publication_date: str
    journal: str
    authors: List[Author]
    mesh_terms: List[MeSHTerm]
    doi: Optional[str] = None
    pmc_id: Optional[str] = None
    publication_types: List[str] = None
    keywords: List[str] = None
    full_text_available: bool = False

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

class PubMedClient:
    """PubMed E-utilities API client for therapeutic area literature retrieval"""

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, email: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize PubMed client

        Args:
            email: Your email address (required by NCBI for courtesy)
            api_key: NCBI API key for increased rate limits
        """
        self.email = email
        self.api_key = api_key
        self.session = requests.Session()

    def _make_request(self, endpoint: str, params: Dict) -> requests.Response:
        """Make API request with rate limiting and error handling"""
        base_params = {
            'tool': 'meridian_literature_review',
            'email': self.email or 'researcher@meridian.com'
        }
        if self.api_key:
            base_params['api_key'] = self.api_key

        params.update(base_params)
        url = f"{self.BASE_URL}/{endpoint}.fcgi"

        # Rate limiting: 3 requests per second without API key, 10 with key
        time.sleep(0.34 if not self.api_key else 0.11)

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise

    def search_oncology_papers(self,
                             days_back: int = 7,
                             max_results: int = 100,
                             include_reviews: bool = True) -> List[str]:
        """
        Search for oncology/immunotherapy papers using MeSH terms

        Args:
            days_back: Number of days to look back for new publications
            max_results: Maximum number of results to return
            include_reviews: Whether to include review articles

        Returns:
            List of PMIDs
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Build search query focusing on Meridian's therapeutic areas
        mesh_terms = [
            '"Neoplasms"[MeSH]',  # Primary oncology MeSH term
            '"Immunotherapy"[MeSH]',  # Immunotherapy focus
            '"Antineoplastic Agents"[MeSH]',  # Cancer drugs
            '"Tumor Microenvironment"[MeSH]',  # Key research area
        ]

        # Additional relevant terms for oncology/immunotherapy
        keywords = [
            '"cancer immunotherapy"[Title/Abstract]',
            '"checkpoint inhibitor"[Title/Abstract]',
            '"CAR-T"[Title/Abstract]',
            '"monoclonal antibody"[Title/Abstract]',
            '"targeted therapy"[Title/Abstract]',
        ]

        # Combine MeSH terms and keywords
        query_parts = [f"({' OR '.join(mesh_terms)})"]
        query_parts.append(f"({' OR '.join(keywords)})")

        # Date filter
        date_filter = f'("{start_date.strftime("%Y/%m/%d")}"[Date - Publication] : "{end_date.strftime("%Y/%m/%d")}"[Date - Publication])'
        query_parts.append(date_filter)

        # Publication type filters
        pub_types = ['"Journal Article"[Publication Type]']
        if include_reviews:
            pub_types.extend(['"Review"[Publication Type]', '"Systematic Review"[Publication Type]'])

        query_parts.append(f"({' OR '.join(pub_types)})")

        # Combine all parts
        query = ' AND '.join(query_parts)

        logger.info(f"Searching PubMed with query: {query}")

        params = {
            'db': 'pubmed',
            'term': query,
            'retmax': max_results,
            'retmode': 'xml',
            'sort': 'pub date',
            'field': 'title,abstract'
        }

        response = self._make_request('esearch', params)

        # Parse XML response
        root = ET.fromstring(response.content)
        pmids = [id_elem.text for id_elem in root.findall('.//Id')]

        logger.info(f"Found {len(pmids)} publications")
        return pmids

    def fetch_publication_details(self, pmids: List[str]) -> List[Publication]:
        """
        Fetch detailed publication information for given PMIDs

        Args:
            pmids: List of PubMed IDs

        Returns:
            List of Publication objects with full metadata
        """
        if not pmids:
            return []

        # Batch PMIDs for efficiency (max 200 per request)
        batch_size = 200
        all_publications = []

        for i in range(0, len(pmids), batch_size):
            batch_pmids = pmids[i:i + batch_size]

            params = {
                'db': 'pubmed',
                'id': ','.join(batch_pmids),
                'retmode': 'xml',
                'rettype': 'abstract'
            }

            response = self._make_request('efetch', params)
            publications = self._parse_publications_xml(response.content)
            all_publications.extend(publications)

            logger.info(f"Processed batch {i//batch_size + 1}, {len(publications)} publications")

        return all_publications

    def _parse_publications_xml(self, xml_content: bytes) -> List[Publication]:
        """Parse PubMed XML response into Publication objects"""
        publications = []

        try:
            root = ET.fromstring(xml_content)

            for article in root.findall('.//PubmedArticle'):
                try:
                    pub = self._parse_single_article(article)
                    if pub:
                        publications.append(pub)
                except Exception as e:
                    logger.warning(f"Failed to parse article: {e}")
                    continue

        except ET.ParseError as e:
            logger.error(f"Failed to parse XML: {e}")

        return publications

    def _parse_single_article(self, article_elem) -> Optional[Publication]:
        """Parse a single PubmedArticle XML element"""
        try:
            # Basic identifiers
            pmid = article_elem.find('.//PMID').text

            # Title and abstract
            title_elem = article_elem.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else ""

            abstract_elem = article_elem.find('.//Abstract/AbstractText')
            abstract = abstract_elem.text if abstract_elem is not None else ""

            # Journal
            journal_elem = article_elem.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None else ""

            # Publication date
            pub_date = self._extract_publication_date(article_elem)

            # Authors
            authors = self._extract_authors(article_elem)

            # MeSH terms
            mesh_terms = self._extract_mesh_terms(article_elem)

            # DOI and PMC ID
            doi = self._extract_doi(article_elem)
            pmc_id = self._extract_pmc_id(article_elem)

            # Publication types
            pub_types = self._extract_publication_types(article_elem)

            # Keywords
            keywords = self._extract_keywords(article_elem)

            # Check if full text is available (basic heuristic)
            full_text_available = pmc_id is not None

            return Publication(
                pmid=pmid,
                title=title,
                abstract=abstract,
                publication_date=pub_date,
                journal=journal,
                authors=authors,
                mesh_terms=mesh_terms,
                doi=doi,
                pmc_id=pmc_id,
                publication_types=pub_types,
                keywords=keywords,
                full_text_available=full_text_available
            )

        except Exception as e:
            logger.error(f"Error parsing article: {e}")
            return None

    def _extract_publication_date(self, article_elem) -> str:
        """Extract publication date"""
        # Try PubDate first
        pub_date_elem = article_elem.find('.//PubDate')
        if pub_date_elem is not None:
            year = pub_date_elem.find('Year')
            month = pub_date_elem.find('Month')
            day = pub_date_elem.find('Day')

            if year is not None:
                date_parts = [year.text]
                if month is not None:
                    date_parts.append(month.text)
                if day is not None:
                    date_parts.append(day.text)
                return '-'.join(date_parts)

        return "Unknown"

    def _extract_authors(self, article_elem) -> List[Author]:
        """Extract author information"""
        authors = []

        for author_elem in article_elem.findall('.//AuthorList/Author'):
            last_name_elem = author_elem.find('LastName')
            fore_name_elem = author_elem.find('ForeName')
            initials_elem = author_elem.find('Initials')

            # Extract affiliation
            affiliation_elem = author_elem.find('.//Affiliation')
            affiliation = affiliation_elem.text if affiliation_elem is not None else None

            author = Author(
                last_name=last_name_elem.text if last_name_elem is not None else None,
                fore_name=fore_name_elem.text if fore_name_elem is not None else None,
                initials=initials_elem.text if initials_elem is not None else None,
                affiliation=affiliation
            )
            authors.append(author)

        return authors

    def _extract_mesh_terms(self, article_elem) -> List[MeSHTerm]:
        """Extract MeSH terms"""
        mesh_terms = []

        for mesh_elem in article_elem.findall('.//MeshHeadingList/MeshHeading'):
            descriptor_elem = mesh_elem.find('DescriptorName')
            if descriptor_elem is not None:
                descriptor = descriptor_elem.text
                major_topic = descriptor_elem.get('MajorTopicYN') == 'Y'

                # Handle qualifiers
                qualifier_elems = mesh_elem.findall('QualifierName')
                if qualifier_elems:
                    for qual_elem in qualifier_elems:
                        mesh_term = MeSHTerm(
                            descriptor=descriptor,
                            qualifier=qual_elem.text,
                            major_topic=major_topic or qual_elem.get('MajorTopicYN') == 'Y'
                        )
                        mesh_terms.append(mesh_term)
                else:
                    mesh_term = MeSHTerm(
                        descriptor=descriptor,
                        major_topic=major_topic
                    )
                    mesh_terms.append(mesh_term)

        return mesh_terms

    def _extract_doi(self, article_elem) -> Optional[str]:
        """Extract DOI"""
        for article_id in article_elem.findall('.//ArticleId'):
            if article_id.get('IdType') == 'doi':
                return article_id.text
        return None

    def _extract_pmc_id(self, article_elem) -> Optional[str]:
        """Extract PMC ID"""
        for article_id in article_elem.findall('.//ArticleId'):
            if article_id.get('IdType') == 'pmc':
                return article_id.text
        return None

    def _extract_publication_types(self, article_elem) -> List[str]:
        """Extract publication types"""
        pub_types = []
        for pub_type_elem in article_elem.findall('.//PublicationTypeList/PublicationType'):
            if pub_type_elem.text:
                pub_types.append(pub_type_elem.text)
        return pub_types

    def _extract_keywords(self, article_elem) -> List[str]:
        """Extract keywords"""
        keywords = []
        for keyword_elem in article_elem.findall('.//KeywordList/Keyword'):
            if keyword_elem.text:
                keywords.append(keyword_elem.text)
        return keywords

def main():
    """Example usage of PubMed client"""
    # Initialize client
    client = PubMedClient(email="researcher@meridian.com")

    # Search for recent oncology papers
    pmids = client.search_oncology_papers(days_back=7, max_results=50)

    if pmids:
        # Fetch detailed information
        publications = client.fetch_publication_details(pmids)

        # Save results
        output_file = f"oncology_papers_{datetime.now().strftime('%Y%m%d')}.json"
        with open(output_file, 'w') as f:
            json.dump([pub.to_dict() for pub in publications], f, indent=2)

        print(f"Retrieved {len(publications)} publications and saved to {output_file}")

        # Print summary statistics
        mesh_terms = set()
        journals = set()
        for pub in publications:
            journals.add(pub.journal)
            for mesh_term in pub.mesh_terms:
                mesh_terms.add(mesh_term.descriptor)

        print(f"Journals represented: {len(journals)}")
        print(f"Unique MeSH terms: {len(mesh_terms)}")
        print(f"Papers with full text available: {sum(1 for pub in publications if pub.full_text_available)}")
    else:
        print("No publications found for the specified criteria")

if __name__ == "__main__":
    main()