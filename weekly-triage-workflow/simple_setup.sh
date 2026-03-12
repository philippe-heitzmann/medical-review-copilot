#!/bin/bash
# Simple MVP setup for Weekly Triage Workflow

set -e

echo "Simple MVP Setup for Weekly Triage Workflow"
echo "==========================================="

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install minimal required packages
echo "Installing core packages..."
pip install --upgrade pip

# Core requirements only - avoid problematic packages
pip install \
    requests \
    beautifulsoup4 \
    pandas \
    numpy

echo "Installing JSON processing..."
pip install jsonschema

# Create minimal config
if [ ! -f ".env" ]; then
    echo "Creating basic .env file..."
    cat > .env << 'EOF'
PUBMED_EMAIL=researcher@meridian.com
PUBMED_API_KEY=
MAX_PUBLICATIONS=50
DAYS_BACK=7
MIN_RELEVANCE_SCORE=0.3
EOF
fi

# Create output directory
mkdir -p output

echo ""
echo "✓ Simple setup complete!"
echo ""
echo "To run:"
echo "  source venv/bin/activate"
echo "  python main.py"