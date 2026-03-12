#!/bin/bash
# Simple MVP runner for Weekly Triage Workflow

set -e

echo "Starting Weekly Triage Workflow (MVP Mode)"
echo "=========================================="

# Setup if needed
if [ ! -d "venv" ]; then
    echo "Setting up environment..."
    chmod +x simple_setup.sh
    ./simple_setup.sh
fi

# Activate environment
echo "Activating environment..."
source venv/bin/activate

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/.."

# Create timestamped output
timestamp=$(date +"%Y%m%d_%H%M%S")
output_dir="output/triage_${timestamp}"
mkdir -p "$output_dir"

echo "Running triage workflow..."
echo "Output: $output_dir"

# Run workflow
python main.py

echo ""
echo "✓ Workflow complete! Check: $output_dir"