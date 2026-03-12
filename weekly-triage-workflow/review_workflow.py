"""
Review workflow management for scientist approval and quality control
Implements human approval gates and tracking for the weekly triage process
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class ReviewStatus(Enum):
    """Review status enumeration"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"
    ESCALATED = "escalated"

class Priority(Enum):
    """Priority level enumeration"""
    IMMEDIATE = "immediate"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class ReviewItem:
    """Individual item for scientist review"""
    review_id: str
    pmid: str
    title: str
    priority: Priority
    therapeutic_areas: List[str]
    ai_summary: Dict
    review_status: ReviewStatus
    assigned_reviewer: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[str] = None
    created_at: str = None
    due_date: str = None
    escalation_reason: Optional[str] = None

    def __post_init__(self):
        """Set defaults after initialization"""
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

        if self.due_date is None:
            # Set due date based on priority
            days_ahead = {
                Priority.IMMEDIATE: 1,
                Priority.HIGH: 2,
                Priority.MEDIUM: 5,
                Priority.LOW: 7
            }
            due_date = datetime.now() + timedelta(days=days_ahead[self.priority])
            self.due_date = due_date.isoformat()

@dataclass
class ReviewPackage:
    """Complete review package for weekly triage"""
    package_id: str
    created_at: str
    week_ending: str
    total_publications: int
    review_items: List[ReviewItem]
    statistics: Dict
    quality_metrics: Dict
    approval_required: bool = True

class ReviewWorkflow:
    """Manages the scientist review workflow for weekly triage"""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize review workflow"""
        self.config = self._load_review_config(config_path)
        self.quality_thresholds = {
            'high_priority_auto_escalate': 8.0,
            'low_confidence_escalate': 0.3,
            'mesh_term_minimum': 2,
            'abstract_length_minimum': 100
        }

    def _load_review_config(self, config_path: Optional[str]) -> Dict:
        """Load review workflow configuration"""
        default_config = {
            'auto_approve_threshold': 9.0,
            'escalation_threshold': 8.5,
            'max_reviews_per_scientist': 20,
            'review_sla_days': {
                'immediate': 1,
                'high': 2,
                'medium': 5,
                'low': 7
            },
            'default_reviewers': ['scientist1@meridian.com', 'scientist2@meridian.com'],
            'enable_auto_approval': False  # Conservative default
        }

        if config_path:
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    default_config.update(config)
            except FileNotFoundError:
                logger.warning(f"Review config file {config_path} not found, using defaults")

        return default_config

    def prepare_review_package(self, ranked_publications: List[Dict]) -> Dict:
        """
        Prepare publications for scientist review

        Args:
            ranked_publications: List of ranked and summarized publications

        Returns:
            Review package dictionary
        """
        package_id = str(uuid.uuid4())
        week_ending = (datetime.now() + timedelta(days=(6 - datetime.now().weekday()))).strftime('%Y-%m-%d')

        # Create review items
        review_items = []
        for pub_data in ranked_publications:
            review_item = self._create_review_item(pub_data)
            review_items.append(review_item)

        # Calculate statistics
        statistics = self._calculate_package_statistics(ranked_publications)

        # Calculate quality metrics
        quality_metrics = self._calculate_quality_metrics(ranked_publications)

        # Create review package
        review_package = ReviewPackage(
            package_id=package_id,
            created_at=datetime.now().isoformat(),
            week_ending=week_ending,
            total_publications=len(ranked_publications),
            review_items=review_items,
            statistics=statistics,
            quality_metrics=quality_metrics,
            approval_required=True
        )

        # Process auto-approvals and escalations
        self._process_automated_decisions(review_package)

        logger.info(f"Created review package {package_id} with {len(review_items)} items")

        return {
            'review_package': asdict(review_package),
            'publications': ranked_publications,
            'review_summary': self._generate_review_summary(review_package),
            'quality_assessment': self._assess_package_quality(quality_metrics)
        }

    def _create_review_item(self, pub_data: Dict) -> ReviewItem:
        """Create review item from publication data"""
        publication = pub_data['publication']
        priority = self._determine_priority(pub_data)
        therapeutic_areas = [
            area.category if hasattr(area, 'category') else area
            for area in pub_data.get('therapeutic_areas', [])
        ]

        review_item = ReviewItem(
            review_id=str(uuid.uuid4()),
            pmid=publication.pmid,
            title=publication.title,
            priority=priority,
            therapeutic_areas=therapeutic_areas,
            ai_summary=pub_data.get('structured_summary', {}).to_dict() if hasattr(pub_data.get('structured_summary', {}), 'to_dict') else pub_data.get('structured_summary', {}),
            review_status=ReviewStatus.PENDING
        )

        return review_item

    def _determine_priority(self, pub_data: Dict) -> Priority:
        """Determine review priority based on publication data"""
        priority_score = pub_data.get('priority_score', 0)
        priority_category = pub_data.get('priority_category', 'Low')

        if priority_score >= 9.0 or priority_category == 'High':
            return Priority.IMMEDIATE
        elif priority_score >= 7.0:
            return Priority.HIGH
        elif priority_score >= 5.0:
            return Priority.MEDIUM
        else:
            return Priority.LOW

    def _calculate_package_statistics(self, publications: List[Dict]) -> Dict:
        """Calculate statistics for the publication package"""
        total_pubs = len(publications)

        # Priority distribution
        priority_counts = {
            'immediate': 0,
            'high': 0,
            'medium': 0,
            'low': 0
        }

        # Therapeutic area distribution
        therapeutic_area_counts = {}

        # Journal distribution
        journal_counts = {}

        # Quality metrics
        high_confidence_count = 0
        clinical_trial_count = 0
        full_text_available_count = 0

        for pub_data in publications:
            publication = pub_data['publication']
            priority_category = pub_data.get('priority_category', 'Low').lower()

            # Count priorities
            if priority_category in priority_counts:
                priority_counts[priority_category] += 1

            # Count therapeutic areas
            therapeutic_areas = pub_data.get('therapeutic_areas', [])
            for area in therapeutic_areas:
                area_name = area.category if hasattr(area, 'category') else area
                therapeutic_area_counts[area_name] = therapeutic_area_counts.get(area_name, 0) + 1

            # Count journals
            journal = publication.journal
            journal_counts[journal] = journal_counts.get(journal, 0) + 1

            # Quality metrics
            structured_summary = pub_data.get('structured_summary', {})
            if hasattr(structured_summary, 'confidence_level'):
                if 'high' in structured_summary.confidence_level.lower():
                    high_confidence_count += 1

            if pub_data.get('classification_metadata', {}).get('has_clinical_data', False):
                clinical_trial_count += 1

            if publication.full_text_available:
                full_text_available_count += 1

        return {
            'total_publications': total_pubs,
            'priority_distribution': priority_counts,
            'therapeutic_area_distribution': therapeutic_area_counts,
            'top_journals': dict(sorted(journal_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            'high_confidence_summaries': high_confidence_count,
            'clinical_trial_publications': clinical_trial_count,
            'full_text_available': full_text_available_count,
            'high_priority_count': priority_counts['immediate'] + priority_counts['high'],
            'medium_priority_count': priority_counts['medium'],
            'low_priority_count': priority_counts['low'],
            'therapeutic_areas': list(therapeutic_area_counts.keys())
        }

    def _calculate_quality_metrics(self, publications: List[Dict]) -> Dict:
        """Calculate quality metrics for the package"""
        total_pubs = len(publications)
        if total_pubs == 0:
            return {}

        # Abstract completeness
        abstracts_with_content = sum(1 for pub_data in publications
                                   if len(pub_data['publication'].abstract) >= 100)

        # MeSH term coverage
        mesh_term_coverage = sum(1 for pub_data in publications
                               if len(pub_data['publication'].mesh_terms) >= 2)

        # Relevance score distribution
        relevance_scores = [pub_data.get('relevance_score', 0) for pub_data in publications]
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0

        # Priority score distribution
        priority_scores = [pub_data.get('priority_score', 0) for pub_data in publications]
        avg_priority = sum(priority_scores) / len(priority_scores) if priority_scores else 0

        return {
            'abstract_completeness_rate': abstracts_with_content / total_pubs,
            'mesh_term_coverage_rate': mesh_term_coverage / total_pubs,
            'average_relevance_score': avg_relevance,
            'average_priority_score': avg_priority,
            'data_quality_score': self._calculate_data_quality_score(publications),
            'classification_confidence': self._calculate_classification_confidence(publications)
        }

    def _calculate_data_quality_score(self, publications: List[Dict]) -> float:
        """Calculate overall data quality score (0-1)"""
        if not publications:
            return 0.0

        quality_factors = []

        # Factor 1: Abstract completeness
        abstract_scores = [
            1.0 if len(pub_data['publication'].abstract) >= 200 else
            0.7 if len(pub_data['publication'].abstract) >= 100 else
            0.3 if len(pub_data['publication'].abstract) >= 50 else 0.0
            for pub_data in publications
        ]
        quality_factors.append(sum(abstract_scores) / len(abstract_scores))

        # Factor 2: MeSH term coverage
        mesh_scores = [
            1.0 if len(pub_data['publication'].mesh_terms) >= 5 else
            0.7 if len(pub_data['publication'].mesh_terms) >= 3 else
            0.3 if len(pub_data['publication'].mesh_terms) >= 1 else 0.0
            for pub_data in publications
        ]
        quality_factors.append(sum(mesh_scores) / len(mesh_scores))

        # Factor 3: Author information completeness
        author_scores = [
            1.0 if len(pub_data['publication'].authors) >= 3 else
            0.5 if len(pub_data['publication'].authors) >= 1 else 0.0
            for pub_data in publications
        ]
        quality_factors.append(sum(author_scores) / len(author_scores))

        return sum(quality_factors) / len(quality_factors)

    def _calculate_classification_confidence(self, publications: List[Dict]) -> float:
        """Calculate overall classification confidence"""
        if not publications:
            return 0.0

        confidence_scores = []
        for pub_data in publications:
            relevance_score = pub_data.get('relevance_score', 0)
            therapeutic_areas = pub_data.get('therapeutic_areas', [])

            # Base confidence on relevance score
            confidence = relevance_score

            # Boost confidence if multiple therapeutic areas identified
            if len(therapeutic_areas) > 1:
                confidence += 0.1

            # Reduce confidence if no clear therapeutic area
            if not therapeutic_areas:
                confidence *= 0.5

            confidence_scores.append(min(confidence, 1.0))

        return sum(confidence_scores) / len(confidence_scores)

    def _process_automated_decisions(self, review_package: ReviewPackage):
        """Process auto-approvals and escalations"""
        auto_approved = 0
        escalated = 0

        for item in review_package.review_items:
            # Auto-escalate high priority items
            if (item.priority == Priority.IMMEDIATE and
                self.config.get('escalation_threshold', 8.5) <= 9.0):
                item.review_status = ReviewStatus.ESCALATED
                item.escalation_reason = "High priority publication requires immediate attention"
                escalated += 1

            # Auto-approve if enabled and criteria met
            elif (self.config.get('enable_auto_approval', False) and
                  self._should_auto_approve(item)):
                item.review_status = ReviewStatus.APPROVED
                item.reviewed_at = datetime.now().isoformat()
                item.review_notes = "Auto-approved based on high confidence criteria"
                auto_approved += 1

        logger.info(f"Automated decisions: {auto_approved} auto-approved, {escalated} escalated")

    def _should_auto_approve(self, review_item: ReviewItem) -> bool:
        """Determine if item should be auto-approved"""
        # Conservative auto-approval criteria
        ai_summary = review_item.ai_summary

        # Check confidence level
        confidence_level = ai_summary.get('confidence_level', '').lower()
        if 'high' not in confidence_level:
            return False

        # Check if it's low priority
        if review_item.priority not in [Priority.LOW, Priority.MEDIUM]:
            return False

        # Additional safety checks could be added here
        return True

    def _generate_review_summary(self, review_package: ReviewPackage) -> Dict:
        """Generate executive summary for review package"""
        stats = review_package.statistics

        return {
            'package_overview': {
                'package_id': review_package.package_id,
                'week_ending': review_package.week_ending,
                'total_publications': review_package.total_publications,
                'review_items_pending': len([item for item in review_package.review_items
                                           if item.review_status == ReviewStatus.PENDING])
            },
            'priority_summary': {
                'immediate_attention_required': stats.get('priority_distribution', {}).get('immediate', 0),
                'high_priority': stats.get('priority_distribution', {}).get('high', 0),
                'total_high_priority': stats.get('high_priority_count', 0)
            },
            'therapeutic_focus': {
                'primary_areas': list(stats.get('therapeutic_area_distribution', {}).keys())[:3],
                'area_counts': stats.get('therapeutic_area_distribution', {})
            },
            'quality_indicators': {
                'clinical_trial_data': stats.get('clinical_trial_publications', 0),
                'full_text_available': stats.get('full_text_available', 0),
                'high_confidence_summaries': stats.get('high_confidence_summaries', 0)
            }
        }

    def _assess_package_quality(self, quality_metrics: Dict) -> Dict:
        """Assess overall package quality"""
        data_quality = quality_metrics.get('data_quality_score', 0)
        classification_confidence = quality_metrics.get('classification_confidence', 0)
        avg_relevance = quality_metrics.get('average_relevance_score', 0)

        overall_quality = (data_quality + classification_confidence + avg_relevance) / 3

        quality_level = "High" if overall_quality >= 0.8 else "Medium" if overall_quality >= 0.6 else "Low"

        recommendations = []
        if data_quality < 0.6:
            recommendations.append("Consider improving data extraction processes")
        if classification_confidence < 0.7:
            recommendations.append("Review classification algorithms for accuracy")
        if avg_relevance < 0.5:
            recommendations.append("Refine search criteria to improve relevance")

        return {
            'overall_quality_score': overall_quality,
            'quality_level': quality_level,
            'data_quality_score': data_quality,
            'classification_confidence': classification_confidence,
            'average_relevance': avg_relevance,
            'recommendations': recommendations
        }

    def submit_review(self, review_id: str, status: ReviewStatus,
                     reviewer: str, notes: Optional[str] = None) -> bool:
        """Submit scientist review for an item"""
        # This would integrate with a review system
        # For now, just log the review
        logger.info(f"Review submitted for {review_id}: {status.value} by {reviewer}")
        if notes:
            logger.info(f"Review notes: {notes}")
        return True

    def get_review_dashboard_data(self, package_id: str) -> Dict:
        """Get data for review dashboard"""
        # This would retrieve actual review package data
        # For now, return structure for dashboard
        return {
            'package_summary': {},
            'pending_reviews': [],
            'completed_reviews': [],
            'overdue_reviews': [],
            'reviewer_workload': {},
            'quality_metrics': {}
        }

def main():
    """Test review workflow module"""
    # This would be used for testing the review workflow
    pass

if __name__ == "__main__":
    main()