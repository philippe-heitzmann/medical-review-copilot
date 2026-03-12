"""
Weekly Triage Workflow - Main orchestration script
Ingests new publications weekly, classifies, ranks, and drafts structured summaries for scientist review
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from src.pubmed_client import PubMedClient, Publication

from classifiers import RelevanceClassifier, TherapeuticAreaClassifier
from rankers import ClinicalRelevanceRanker
from summarizers import StructuredSummarizer
from review_workflow import ReviewWorkflow

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WeeklyTriageWorkflow:
    """Main workflow orchestrator for weekly publication triage"""

    def __init__(self, config_path: str = "config/workflow_config.json"):
        """Initialize workflow with configuration"""
        self.config = self._load_config(config_path)
        self.pubmed_client = PubMedClient(
            email=self.config.get('pubmed_email'),
            api_key=self.config.get('pubmed_api_key')
        )

        # Initialize components
        self.relevance_classifier = RelevanceClassifier()
        self.therapeutic_classifier = TherapeuticAreaClassifier()
        self.ranker = ClinicalRelevanceRanker()
        self.summarizer = StructuredSummarizer()
        self.review_workflow = ReviewWorkflow()

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return self._default_config()

    def _default_config(self) -> Dict:
        """Default configuration for workflow"""
        return {
            "pubmed_email": "researcher@meridian.com",
            "pubmed_api_key": None,
            "days_back": 7,
            "max_publications": 100,
            "min_relevance_score": 0.3,
            "therapeutic_areas": ["oncology", "immunotherapy", "targeted_therapy"],
            "output_directory": "output",
            "review_required": True
        }

    def run_weekly_triage(self) -> Dict:
        """Execute complete weekly triage workflow"""
        logger.info("Starting weekly triage workflow")

        try:
            # Step 1: Ingestion
            logger.info("Step 1: Ingesting new publications")
            publications = self._ingest_publications()

            # Step 2: Classification
            logger.info("Step 2: Classifying publications")
            classified_publications = self._classify_publications(publications)

            # Step 3: Relevance filtering
            logger.info("Step 3: Filtering by relevance")
            relevant_publications = self._filter_relevant(classified_publications)

            # Step 4: Ranking
            logger.info("Step 4: Ranking publications by clinical relevance")
            ranked_publications = self._rank_publications(relevant_publications)

            # Step 5: Summary generation
            logger.info("Step 5: Generating structured summaries")
            summarized_publications = self._generate_summaries(ranked_publications)

            # Step 6: Prepare for review
            logger.info("Step 6: Preparing review workflow")
            review_package = self._prepare_review_package(summarized_publications)

            # Step 7: Save results
            self._save_results(review_package)

            logger.info("Weekly triage workflow completed successfully")
            return self._generate_workflow_summary(review_package)

        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            raise

    def _ingest_publications(self) -> List[Publication]:
        """Ingest new publications from PubMed"""
        pmids = self.pubmed_client.search_oncology_papers(
            days_back=self.config['days_back'],
            max_results=self.config['max_publications']
        )

        if not pmids:
            logger.warning("No new publications found")
            return []

        publications = self.pubmed_client.fetch_publication_details(pmids)
        logger.info(f"Ingested {len(publications)} publications")

        return publications

    def _classify_publications(self, publications: List[Publication]) -> List[Dict]:
        """Classify publications by therapeutic area and type"""
        classified = []

        for pub in publications:
            # Relevance classification
            relevance_score = self.relevance_classifier.score_publication(pub)

            # Therapeutic area classification
            therapeutic_areas = self.therapeutic_classifier.classify_publication(pub)

            # Publication type analysis
            pub_analysis = {
                'publication': pub,
                'relevance_score': relevance_score,
                'therapeutic_areas': therapeutic_areas,
                'classification_metadata': {
                    'has_clinical_data': self._has_clinical_data(pub),
                    'is_review': 'Review' in pub.publication_types,
                    'has_drug_mention': self._has_drug_mention(pub),
                    'mesh_oncology_focus': self._count_oncology_mesh_terms(pub)
                }
            }

            classified.append(pub_analysis)

        logger.info(f"Classified {len(classified)} publications")
        return classified

    def _filter_relevant(self, classified_publications: List[Dict]) -> List[Dict]:
        """Filter publications by relevance threshold"""
        relevant = [
            pub for pub in classified_publications
            if pub['relevance_score'] >= self.config['min_relevance_score']
        ]

        logger.info(f"Filtered to {len(relevant)} relevant publications")
        return relevant

    def _rank_publications(self, publications: List[Dict]) -> List[Dict]:
        """Rank publications by clinical relevance"""
        ranked = self.ranker.rank_publications(publications)
        logger.info(f"Ranked {len(ranked)} publications")
        return ranked

    def _generate_summaries(self, publications: List[Dict]) -> List[Dict]:
        """Generate structured summaries for publications"""
        summarized = []

        for pub_data in publications:
            summary = self.summarizer.generate_summary(pub_data)
            pub_data['structured_summary'] = summary
            summarized.append(pub_data)

        logger.info(f"Generated summaries for {len(summarized)} publications")
        return summarized

    def _prepare_review_package(self, publications: List[Dict]) -> Dict:
        """Prepare package for scientist review"""
        return self.review_workflow.prepare_review_package(publications)

    def _save_results(self, review_package: Dict):
        """Save workflow results to files"""
        output_dir = Path(self.config['output_directory'])
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save full review package
        with open(output_dir / f'triage_results_{timestamp}.json', 'w') as f:
            json.dump(review_package, f, indent=2, default=str)

        # Save summary report
        summary_report = self._generate_summary_report(review_package)
        with open(output_dir / f'triage_summary_{timestamp}.json', 'w') as f:
            json.dump(summary_report, f, indent=2)

        logger.info(f"Results saved to {output_dir}")

    def _generate_workflow_summary(self, review_package: Dict) -> Dict:
        """Generate summary of workflow execution"""
        stats = review_package.get('statistics', {})

        return {
            'execution_timestamp': datetime.now().isoformat(),
            'total_publications_processed': stats.get('total_publications', 0),
            'high_priority_publications': stats.get('high_priority_count', 0),
            'medium_priority_publications': stats.get('medium_priority_count', 0),
            'low_priority_publications': stats.get('low_priority_count', 0),
            'therapeutic_areas_covered': stats.get('therapeutic_areas', []),
            'review_required': len(review_package.get('review_queue', [])),
            'workflow_status': 'completed'
        }

    def _generate_summary_report(self, review_package: Dict) -> Dict:
        """Generate executive summary report"""
        publications = review_package.get('publications', [])

        # Key metrics
        total_pubs = len(publications)
        high_priority = len([p for p in publications if p.get('priority_rank', 0) >= 8])
        clinical_trials = len([p for p in publications
                             if p.get('classification_metadata', {}).get('has_clinical_data')])

        # Therapeutic area breakdown
        therapeutic_breakdown = {}
        for pub in publications:
            for area in pub.get('therapeutic_areas', []):
                therapeutic_breakdown[area] = therapeutic_breakdown.get(area, 0) + 1

        # Top journals
        journal_counts = {}
        for pub in publications:
            journal = pub['publication'].journal
            journal_counts[journal] = journal_counts.get(journal, 0) + 1

        top_journals = sorted(journal_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            'summary_metrics': {
                'total_publications': total_pubs,
                'high_priority_publications': high_priority,
                'clinical_trial_publications': clinical_trials,
                'full_text_available': len([p for p in publications
                                          if p['publication'].full_text_available])
            },
            'therapeutic_area_breakdown': therapeutic_breakdown,
            'top_journals': dict(top_journals),
            'key_findings': self._extract_key_findings(publications),
            'recommendations': self._generate_recommendations(publications)
        }

    def _has_clinical_data(self, publication: Publication) -> bool:
        """Check if publication contains clinical data"""
        clinical_keywords = [
            'clinical trial', 'phase i', 'phase ii', 'phase iii',
            'randomized', 'efficacy', 'safety', 'adverse events'
        ]

        text = (publication.title + " " + publication.abstract).lower()
        return any(keyword in text for keyword in clinical_keywords)

    def _has_drug_mention(self, publication: Publication) -> bool:
        """Check if publication mentions specific drugs"""
        drug_keywords = [
            'pembrolizumab', 'nivolumab', 'ipilimumab', 'atezolizumab',
            'durvalumab', 'cemiplimab', 'trastuzumab', 'bevacizumab'
        ]

        text = (publication.title + " " + publication.abstract).lower()
        return any(keyword in text for keyword in drug_keywords)

    def _count_oncology_mesh_terms(self, publication: Publication) -> int:
        """Count oncology-related MeSH terms"""
        oncology_mesh = {
            'neoplasms', 'carcinoma', 'adenocarcinoma', 'sarcoma',
            'lymphoma', 'leukemia', 'melanoma', 'tumor', 'cancer'
        }

        count = 0
        for mesh_term in publication.mesh_terms:
            if any(term in mesh_term.descriptor.lower() for term in oncology_mesh):
                count += 1

        return count

    def _extract_key_findings(self, publications: List[Dict]) -> List[str]:
        """Extract key findings from the week's publications"""
        # This would be enhanced with more sophisticated analysis
        findings = []

        high_priority_pubs = [p for p in publications if p.get('priority_rank', 0) >= 8]
        if high_priority_pubs:
            findings.append(f"{len(high_priority_pubs)} high-priority publications identified")

        clinical_pubs = [p for p in publications
                        if p.get('classification_metadata', {}).get('has_clinical_data')]
        if clinical_pubs:
            findings.append(f"{len(clinical_pubs)} publications with clinical trial data")

        return findings

    def _generate_recommendations(self, publications: List[Dict]) -> List[str]:
        """Generate recommendations based on publications"""
        recommendations = []

        # Priority review recommendations
        high_priority = [p for p in publications if p.get('priority_rank', 0) >= 8]
        if high_priority:
            recommendations.append(
                f"Immediate review recommended for {len(high_priority)} high-priority publications"
            )

        # Therapeutic area focus recommendations
        therapeutic_counts = {}
        for pub in publications:
            for area in pub.get('therapeutic_areas', []):
                therapeutic_counts[area] = therapeutic_counts.get(area, 0) + 1

        if therapeutic_counts:
            top_area = max(therapeutic_counts.items(), key=lambda x: x[1])
            recommendations.append(
                f"Increased activity in {top_area[0]} ({top_area[1]} publications)"
            )

        return recommendations

def main():
    """Main entry point for weekly triage workflow"""
    try:
        workflow = WeeklyTriageWorkflow()
        results = workflow.run_weekly_triage()

        print("Weekly Triage Workflow Completed Successfully")
        print("="*50)
        print(f"Total Publications: {results['total_publications_processed']}")
        print(f"High Priority: {results['high_priority_publications']}")
        print(f"Requiring Review: {results['review_required']}")
        print(f"Therapeutic Areas: {', '.join(results.get('therapeutic_areas_covered', []))}")

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()