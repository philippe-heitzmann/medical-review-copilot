#!/bin/bash
# Simple MVP setup for Therapeutic Area Copilot

set -e

echo "Simple MVP Setup for Therapeutic Area Copilot"
echo "============================================="

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install minimal required packages
echo "Installing core packages..."
pip install --upgrade pip

# Core requirements only - avoid AI packages that cause compilation issues
pip install \
    requests \
    beautifulsoup4 \
    pandas \
    numpy

echo "Installing JSON processing..."
pip install jsonschema

echo "Installing Claude API client..."
pip install anthropic

# Create minimal config
if [ ! -f ".env" ]; then
    echo "Creating basic .env file..."
    cat > .env << 'EOF'
# Medical Literature Review Configuration
COPILOT_ENV=ai
DEFAULT_THERAPEUTIC_AREA=oncology
MAX_SEARCH_RESULTS=10
CONFIDENCE_THRESHOLD=0.5
CORPUS_PATH=data/approved_corpus
CITATION_STYLE=ama

# Anthropic Claude API Configuration
# IMPORTANT: Replace with your own API key
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Claude API Settings
CLAUDE_MODEL=claude-3-haiku-20240307
CLAUDE_MAX_TOKENS=1000
CLAUDE_TEMPERATURE=0.1
EOF
fi

# Create directories
mkdir -p data/approved_corpus
mkdir -p sessions

echo ""
echo "✓ Simple setup complete!"
echo ""
echo "Note: This is MVP mode - no AI features, basic keyword search only"
echo ""
echo "To run:"
echo "  source venv/bin/activate"
echo "  python main.py"