#!/bin/bash
# Environment setup script for Therapeutic Area Copilot

set -e  # Exit on error

echo "Setting up Therapeutic Area Copilot environment..."

# Check Python version compatibility
python_version=$(python3 --version 2>&1 | awk '{print $2}')
major_version=$(echo $python_version | cut -d'.' -f1)
minor_version=$(echo $python_version | cut -d'.' -f2)
echo "Python version detected: $python_version"

# Check for compatible Python version (3.8-3.12)
if [ "$major_version" -ne 3 ]; then
    echo "Error: Python 3 is required, found Python $major_version"
    exit 1
fi

if [ "$minor_version" -lt 8 ]; then
    echo "Error: Python 3.8 or higher is required, found Python $python_version"
    exit 1
fi

if [ "$minor_version" -gt 12 ]; then
    echo "Warning: Python $python_version detected"
    echo "Some AI/ML packages may not be compatible with Python 3.13+"
    echo "Recommended: Use Python 3.8-3.12 for best compatibility"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled. Please use Python 3.8-3.12"
        exit 1
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install core requirements
echo "Installing core Python packages..."
pip install --no-cache-dir \
    "requests>=2.31.0,<3.0.0" \
    "numpy>=1.24.0,<2.0.0" \
    "pandas>=1.5.0,<3.0.0"

# Install AI/ML packages for semantic search and embeddings
echo "Installing AI/ML packages..."
if [ "$minor_version" -le 12 ]; then
    # Full AI stack for Python 3.8-3.12
    pip install --no-cache-dir \
        "sentence-transformers>=2.2.0,<3.0.0" \
        "transformers>=4.21.0,<5.0.0" \
        "torch>=1.12.0,<3.0.0"

    # Install vector search (FAISS)
    echo "Installing FAISS for vector search..."
    pip install --no-cache-dir "faiss-cpu>=1.7.0,<2.0.0"

    # Install NLP packages (skip spaCy for Python 3.13+)
    echo "Installing NLP packages..."
    pip install --no-cache-dir "nltk>=3.8.0,<4.0.0"

    # Only install spaCy for Python 3.8-3.11 (compatibility issues with 3.12+)
    if [ "$minor_version" -le 11 ]; then
        pip install --no-cache-dir "spacy>=3.5.0,<4.0.0"
        SPACY_INSTALLED=true
    else
        echo "⚠ Skipping spaCy for Python 3.12+ (compatibility issues)"
        SPACY_INSTALLED=false
    fi
else
    # Limited AI stack for Python 3.13+
    echo "⚠ Installing basic AI packages only (Python 3.13+ has limited ML library support)"
    pip install --no-cache-dir \
        "nltk>=3.8.0,<4.0.0"
    SPACY_INSTALLED=false
fi

# Install scientific packages
echo "Installing scientific packages..."
pip install --no-cache-dir \
    "scikit-learn>=1.2.0,<2.0.0" \
    "scipy>=1.10.0,<2.0.0"

# Install data processing
echo "Installing data processing packages..."
pip install --no-cache-dir \
    "beautifulsoup4>=4.12.0,<5.0.0" \
    "lxml>=4.9.0,<5.0.0" \
    "python-dateutil>=2.8.2,<3.0.0"

# Install JSON/data validation
echo "Installing validation packages..."
pip install --no-cache-dir \
    "jsonschema>=4.17.0,<5.0.0"

# Install compatible pydantic version
if [ "$minor_version" -le 12 ]; then
    pip install --no-cache-dir "pydantic>=2.0.0,<3.0.0"
else
    pip install --no-cache-dir "pydantic>=2.5.0,<3.0.0"
fi

# Optional: Install Jupyter for analysis
echo "Installing Jupyter for interactive analysis..."
pip install --no-cache-dir \
    jupyter>=1.0.0 \
    jupyterlab>=3.6.0

# Optional: Install visualization packages
echo "Installing visualization packages..."
pip install --no-cache-dir \
    matplotlib>=3.6.0 \
    seaborn>=0.12.0 \
    plotly>=5.12.0

# Download spaCy model for NLP (only if spaCy was installed)
if [ "$SPACY_INSTALLED" = true ]; then
    echo "Downloading spaCy English model..."
    python3 -m spacy download en_core_web_sm
else
    echo "⚠ Skipping spaCy model download (spaCy not installed)"
fi

# Create necessary directories
echo "Creating data directories..."
mkdir -p data/approved_corpus
mkdir -p data/embeddings
mkdir -p logs
mkdir -p exports
mkdir -p sessions

# Set environment variables
echo "Setting environment variables..."
export PYTHONPATH="${PYTHONPATH}:$(pwd):$(pwd)/.."
export COPILOT_ENV="production"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# Copilot Configuration
COPILOT_ENV=production
DEFAULT_THERAPEUTIC_AREA=oncology
MAX_SEARCH_RESULTS=20
CITATION_LIMIT=10
CONFIDENCE_THRESHOLD=0.6

# Knowledge Base Configuration
CORPUS_PATH=data/approved_corpus
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
CHUNK_SIZE=512
OVERLAP_SIZE=50

# Search Engine Configuration
SIMILARITY_THRESHOLD=0.7
MAX_CHUNKS=10
RERANKING_ENABLED=true

# Q&A Processor Configuration
QA_MODEL=microsoft/BioBERT-pubmed-pmc-base
MAX_ANSWER_LENGTH=300
MIN_CONFIDENCE=0.5

# Citation Configuration
CITATION_STYLE=ama
MAX_CITATIONS=15

# Performance Configuration
ENABLE_CACHING=true
CACHE_TTL_SECONDS=3600
MAX_CONCURRENT_SEARCHES=5
TIMEOUT_SECONDS=30

# Logging Configuration
LOG_LEVEL=INFO
ENABLE_AUDIT_TRAIL=true

EOF
    echo "Please configure your .env file with appropriate values"
fi

# Test imports
echo "Testing Python imports..."
python3 -c "
# Test core packages
import numpy as np
import pandas as pd
import nltk
from datetime import datetime
from pathlib import Path
print('✓ Core packages imported successfully')

# Test AI packages if available
try:
    import sentence_transformers
    import transformers
    import torch
    print('✓ AI/ML packages imported successfully')
    AI_AVAILABLE = True
except ImportError as e:
    print(f'⚠ Some AI packages unavailable: {e}')
    print('  Basic functionality will work, advanced AI features may be limited')
    AI_AVAILABLE = False

# Test FAISS if available
try:
    import faiss
    print('✓ FAISS vector search available')
except ImportError:
    print('⚠ FAISS not available - will use fallback search')

# Test spaCy if available
try:
    import spacy
    print('✓ spaCy NLP package available')
except ImportError:
    print('⚠ spaCy not available - basic text processing will be used')
"

# Test spaCy model if installed
if [ "$SPACY_INSTALLED" = true ]; then
    python3 -c "
try:
    import spacy
    nlp = spacy.load('en_core_web_sm')
    print('✓ spaCy model loaded successfully')
except Exception as e:
    print(f'⚠ spaCy model issue: {e}')
    print('  Text processing will use basic methods')
"
fi

# Initialize NLTK data (if needed)
python3 -c "
import nltk
import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    print('✓ NLTK data downloaded')
except:
    print('⚠ NLTK data download failed (optional)')
"

echo "✓ Therapeutic Area Copilot environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Configure your .env file with appropriate settings"
echo "2. Add approved literature to data/approved_corpus/"
echo "3. Run: ./run_copilot.sh"
echo ""
echo "To manually activate the environment:"
echo "source venv/bin/activate"
echo ""
echo "To start Jupyter Lab for development:"
echo "source venv/bin/activate && jupyter lab"