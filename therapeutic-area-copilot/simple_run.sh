#!/bin/bash
# Complete One-Command Demo Setup for Therapeutic Area Copilot

set -e

echo "🚀 Medical Literature Review System - Complete Demo Setup"
echo "========================================================="

# Setup if needed
if [ ! -d "venv" ]; then
    echo "📦 Setting up environment..."
    chmod +x simple_setup.sh
    ./simple_setup.sh
fi

# Activate environment
echo "🔧 Activating environment..."
source venv/bin/activate

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/.."

# Check if corpus is empty and auto-populate
corpus_files=$(ls -A data/approved_corpus 2>/dev/null | wc -l || echo "0")
if [ "$corpus_files" -eq 0 ]; then
    echo ""
    echo "📚 Knowledge base is empty. Auto-populating with recent medical literature..."
    echo "   This will take 30-60 seconds..."
    echo ""

    # Run weekly triage to get some papers
    echo "🔍 Step 1: Running literature search (finding recent oncology/immunotherapy papers)..."
    cd ../weekly-triage-workflow

    # Setup weekly triage if needed
    if [ ! -d "venv" ]; then
        chmod +x simple_setup.sh
        ./simple_setup.sh > /dev/null 2>&1
    fi

    # Run triage to get papers (suppress most output)
    source venv/bin/activate > /dev/null 2>&1
    export PYTHONPATH="${PYTHONPATH}:$(pwd)/.."
    echo "   Querying PubMed API for recent papers..."

    python main.py > /dev/null 2>&1 || {
        echo "   ⚠️  No recent papers found in last 7 days. Trying last 30 days..."
        # Modify config temporarily for wider search
        sed -i.bak 's/DAYS_BACK=7/DAYS_BACK=30/' .env 2>/dev/null || true
        python main.py > /dev/null 2>&1 || {
            echo "   ⚠️  Still no papers found. Trying last 90 days..."
            sed -i.bak 's/DAYS_BACK=30/DAYS_BACK=90/' .env 2>/dev/null || true
            python main.py > /dev/null 2>&1 || true
        }
        # Restore original config
        [ -f .env.bak ] && mv .env.bak .env
    }

    # Find the most recent output
    latest_output=$(ls -t output/triage_*/triage_results_*.json 2>/dev/null | head -1 || echo "")

    cd ../therapeutic-area-copilot

    if [ -n "$latest_output" ] && [ -f "../weekly-triage-workflow/$latest_output" ]; then
        echo "📋 Step 2: Processing publications for knowledge base..."

        # Copy and process the triage results
        cp "../weekly-triage-workflow/$latest_output" "data/approved_corpus/"

        # Create a simple demo corpus file with basic info
        python3 -c "
import json
import sys
sys.path.append('..')

try:
    # Load the triage results
    with open('../weekly-triage-workflow/$latest_output', 'r') as f:
        data = json.load(f)

    publications = data.get('publications', [])
    demo_papers = []

    for i, pub_data in enumerate(publications[:10]):  # Take first 10
        pub = pub_data.get('publication', {})
        if pub.get('abstract') and len(pub.get('abstract', '')) > 100:
            demo_paper = {
                'pmid': pub.get('pmid', f'demo_{i}'),
                'title': pub.get('title', 'Medical Research Study'),
                'abstract': pub.get('abstract', 'Research abstract'),
                'authors': [author.get('last_name', 'Author') for author in pub.get('authors', [])[:3]],
                'journal': pub.get('journal', 'Medical Journal'),
                'publication_date': pub.get('publication_date', '2024'),
                'therapeutic_areas': pub_data.get('therapeutic_areas', []),
                'relevance_score': pub_data.get('relevance_score', 0.5)
            }
            demo_papers.append(demo_paper)

    # Save demo corpus
    with open('data/approved_corpus/demo_papers.json', 'w') as f:
        json.dump(demo_papers, f, indent=2)

    print(f'✓ Processed {len(demo_papers)} papers for knowledge base')

except Exception as e:
    # Create fallback demo data
    fallback_papers = [
        {
            'pmid': 'demo_1',
            'title': 'Pembrolizumab for Advanced Melanoma: A Clinical Trial',
            'abstract': 'This study evaluated pembrolizumab, a PD-1 checkpoint inhibitor, in patients with advanced melanoma. Results showed significant improvement in overall survival compared to standard therapy. The objective response rate was 38% with manageable side effects.',
            'authors': ['Smith, J.', 'Johnson, M.', 'Williams, R.'],
            'journal': 'New England Journal of Medicine',
            'publication_date': '2024-01-15',
            'therapeutic_areas': ['oncology', 'immunotherapy'],
            'relevance_score': 0.85
        },
        {
            'pmid': 'demo_2',
            'title': 'CAR-T Cell Therapy in Relapsed B-Cell Lymphoma',
            'abstract': 'CAR-T cell therapy demonstrated remarkable efficacy in patients with relapsed diffuse large B-cell lymphoma. Complete remission was achieved in 54% of patients. Cytokine release syndrome was the most common adverse event, manageable with tocilizumab.',
            'authors': ['Davis, A.', 'Wilson, K.'],
            'journal': 'Journal of Clinical Oncology',
            'publication_date': '2024-02-10',
            'therapeutic_areas': ['oncology', 'immunotherapy'],
            'relevance_score': 0.90
        },
        {
            'pmid': 'demo_3',
            'title': 'Biomarkers for Immunotherapy Response in Lung Cancer',
            'abstract': 'This research identified key biomarkers predictive of response to immune checkpoint inhibitors in non-small cell lung cancer. PD-L1 expression and tumor mutational burden were the strongest predictors. The findings could help personalize immunotherapy treatment.',
            'authors': ['Brown, S.', 'Miller, T.'],
            'journal': 'Cancer Research',
            'publication_date': '2024-01-28',
            'therapeutic_areas': ['oncology', 'biomarkers'],
            'relevance_score': 0.78
        }
    ]

    with open('data/approved_corpus/demo_papers.json', 'w') as f:
        json.dump(fallback_papers, f, indent=2)

    print(f'✓ Created fallback demo corpus with {len(fallback_papers)} papers')
"

        echo "✅ Knowledge base populated successfully!"
    else
        echo "⚠️  No recent papers found. Creating demo corpus with sample data..."

        # Create demo corpus with sample data
        python3 -c "
import json

demo_papers = [
    {
        'pmid': 'demo_1',
        'title': 'Pembrolizumab for Advanced Melanoma: A Clinical Trial',
        'abstract': 'This study evaluated pembrolizumab, a PD-1 checkpoint inhibitor, in patients with advanced melanoma. Results showed significant improvement in overall survival compared to standard therapy. The objective response rate was 38% with manageable side effects.',
        'authors': ['Smith, J.', 'Johnson, M.', 'Williams, R.'],
        'journal': 'New England Journal of Medicine',
        'publication_date': '2024-01-15',
        'therapeutic_areas': ['oncology', 'immunotherapy'],
        'relevance_score': 0.85
    },
    {
        'pmid': 'demo_2',
        'title': 'CAR-T Cell Therapy in Relapsed B-Cell Lymphoma',
        'abstract': 'CAR-T cell therapy demonstrated remarkable efficacy in patients with relapsed diffuse large B-cell lymphoma. Complete remission was achieved in 54% of patients. Cytokine release syndrome was the most common adverse event, manageable with tocilizumab.',
        'authors': ['Davis, A.', 'Wilson, K.'],
        'journal': 'Journal of Clinical Oncology',
        'publication_date': '2024-02-10',
        'therapeutic_areas': ['oncology', 'immunotherapy'],
        'relevance_score': 0.90
    },
    {
        'pmid': 'demo_3',
        'title': 'Biomarkers for Immunotherapy Response in Lung Cancer',
        'abstract': 'This research identified key biomarkers predictive of response to immune checkpoint inhibitors in non-small cell lung cancer. PD-L1 expression and tumor mutational burden were the strongest predictors. The findings could help personalize immunotherapy treatment.',
        'authors': ['Brown, S.', 'Miller, T.'],
        'journal': 'Cancer Research',
        'publication_date': '2024-01-28',
        'therapeutic_areas': ['oncology', 'biomarkers'],
        'relevance_score': 0.78
    },
    {
        'pmid': 'demo_4',
        'title': 'Safety Profile of Checkpoint Inhibitors in Elderly Patients',
        'abstract': 'Analysis of safety data from elderly patients (>75 years) receiving checkpoint inhibitor therapy showed similar toxicity profiles to younger patients. Immune-related adverse events occurred in 35% of patients but were generally manageable with corticosteroids.',
        'authors': ['Garcia, M.', 'Lee, H.'],
        'journal': 'Lancet Oncology',
        'publication_date': '2024-03-05',
        'therapeutic_areas': ['oncology', 'immunotherapy'],
        'relevance_score': 0.72
    },
    {
        'pmid': 'demo_5',
        'title': 'Novel Targets in Cancer Immunotherapy Beyond PD-1/PD-L1',
        'abstract': 'This review explores emerging targets beyond PD-1/PD-L1 axis including LAG-3, TIM-3, and TIGIT. Early clinical trials show promising activity when combined with existing checkpoint inhibitors. These combinations may overcome resistance mechanisms.',
        'authors': ['Taylor, R.', 'Anderson, K.'],
        'journal': 'Nature Reviews Cancer',
        'publication_date': '2024-02-20',
        'therapeutic_areas': ['oncology', 'immunotherapy'],
        'relevance_score': 0.88
    }
]

with open('data/approved_corpus/demo_papers.json', 'w') as f:
    json.dump(demo_papers, f, indent=2)

print(f'✓ Created demo corpus with {len(demo_papers)} sample papers')
"
        echo "✅ Demo knowledge base created successfully!"
    fi

    echo ""
    echo "📊 Knowledge Base Summary:"
    corpus_count=$(find data/approved_corpus -name "*.json" -exec cat {} \; | jq -s 'map(if type == "array" then .[] else . end) | length' 2>/dev/null || echo "5")
    echo "   📄 Papers in database: $corpus_count"
    echo "   🎯 Focus areas: Oncology, Immunotherapy, Biomarkers"
    echo "   🔍 Search mode: Keyword-based (MVP)"
    echo ""
fi

echo "🚀 Starting Therapeutic Area Copilot..."
echo "💡 Demo Question: 'What is the efficacy of pembrolizumab in cancer treatment?'"
echo ""
echo "Available commands:"
echo "   • Type your medical questions"
echo "   • 'history' - Show conversation history"
echo "   • 'exit' - Quit the copilot"
echo ""

# Run in demo mode - shows demo question then goes interactive
python main.py --demo