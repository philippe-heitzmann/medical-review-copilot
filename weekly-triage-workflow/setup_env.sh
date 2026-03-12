#!/bin/bash
# Environment setup script for Weekly Triage Workflow

set -e  # Exit on error

echo "Setting up Weekly Triage Workflow environment..."

# Check Python version compatibility
python_version=$(python3 --version 2>&1 | awk '{print $2}')
major_version=$(echo $python_version | cut -d'.' -f1)
minor_version=$(echo $python_version | cut -d'.' -f2)
echo "Python version detected: $python_version"

# Check for compatible Python version
if [ "$major_version" -ne 3 ]; then
    echo "Error: Python 3 is required, found Python $major_version"
    exit 1
fi

if [ "$minor_version" -lt 8 ]; then
    echo "Error: Python 3.8 or higher is required, found Python $python_version"
    exit 1
fi

if [ "$minor_version" -gt 12 ]; then
    echo "Note: Python $python_version detected"
    echo "Weekly triage workflow should work fine with newer Python versions"
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
    "beautifulsoup4>=4.12.0,<5.0.0" \
    "lxml>=4.9.0,<5.0.0" \
    "pandas>=1.5.0,<3.0.0" \
    "numpy>=1.24.0,<2.0.0"

# Install date/time handling
echo "Installing date/time packages..."
pip install --no-cache-dir "python-dateutil>=2.8.2,<3.0.0"

# Install JSON/data processing
echo "Installing data processing packages..."
pip install --no-cache-dir \
    "jsonschema>=4.17.0,<5.0.0"

# Install compatible pydantic version
if [ "$minor_version" -le 12 ]; then
    pip install --no-cache-dir "pydantic>=2.0.0,<3.0.0"
else
    pip install --no-cache-dir "pydantic>=2.5.0,<3.0.0"
fi

# Optional: Install data science packages for enhanced analytics
echo "Installing data science packages..."
pip install --no-cache-dir \
    "matplotlib>=3.6.0,<4.0.0" \
    "seaborn>=0.12.0,<1.0.0" \
    "plotly>=5.12.0,<6.0.0"

# Create necessary directories
echo "Creating output directories..."
mkdir -p output
mkdir -p logs
mkdir -p data

# Set environment variables
echo "Setting environment variables..."
export PYTHONPATH="${PYTHONPATH}:$(pwd):$(pwd)/.."
export TRIAGE_ENV="production"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# PubMed API Configuration
PUBMED_EMAIL=researcher@meridian.com
PUBMED_API_KEY=

# Workflow Configuration
TRIAGE_ENV=production
MAX_PUBLICATIONS=100
DAYS_BACK=7
MIN_RELEVANCE_SCORE=0.3

# Output Configuration
OUTPUT_DIR=output
LOG_LEVEL=INFO

# Email notifications (optional)
SMTP_SERVER=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
NOTIFICATION_EMAIL=

EOF
    echo "Please configure your .env file with appropriate values"
fi

# Test imports
echo "Testing Python imports..."
python3 -c "
import requests
import json
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
print('✓ All core imports successful')
"

echo "✓ Weekly Triage Workflow environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Configure your .env file with PubMed credentials"
echo "2. Run: ./run_triage.sh"
echo ""
echo "To manually activate the environment:"
echo "source venv/bin/activate"