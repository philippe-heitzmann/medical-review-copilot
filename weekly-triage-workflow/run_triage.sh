#!/bin/bash
# Main runner script for Weekly Triage Workflow

set -e  # Exit on error

echo "Starting Weekly Triage Workflow..."
echo "=================================="

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Run environment setup
echo "Step 1: Setting up environment..."
chmod +x setup_env.sh
./setup_env.sh

echo ""
echo "Step 2: Loading environment variables..."
# Load environment variables if .env exists
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)
    echo "✓ Environment variables loaded"
else
    echo "⚠ No .env file found, using defaults"
fi

# Activate virtual environment
echo ""
echo "Step 3: Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"

# Set Python path
export PYTHONPATH="${PYTHONPATH}:${SCRIPT_DIR}:${SCRIPT_DIR}/.."

# Check PubMed configuration
echo ""
echo "Step 4: Checking configuration..."
if [ -z "$PUBMED_EMAIL" ]; then
    echo "⚠ Warning: PUBMED_EMAIL not set in .env file"
    echo "Using default: researcher@meridian.com"
    export PUBMED_EMAIL="researcher@meridian.com"
fi

if [ -z "$PUBMED_API_KEY" ]; then
    echo "⚠ Warning: PUBMED_API_KEY not set (rate limits will apply)"
else
    echo "✓ PubMed API key configured"
fi

echo "✓ Configuration check complete"

# Create output directory with timestamp
OUTPUT_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_DIR="output/triage_${OUTPUT_TIMESTAMP}"
mkdir -p "$OUTPUT_DIR"
export OUTPUT_DIR="$OUTPUT_DIR"

echo ""
echo "Step 5: Running Weekly Triage Workflow..."
echo "Output directory: $OUTPUT_DIR"
echo "PubMed email: $PUBMED_EMAIL"
echo "Max publications: ${MAX_PUBLICATIONS:-100}"
echo "Days back: ${DAYS_BACK:-7}"
echo ""

# Run the main workflow
python3 main.py

# Check if workflow completed successfully
if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Weekly Triage Workflow completed successfully!"
    echo ""
    echo "Results saved to: $OUTPUT_DIR"
    echo ""

    # Show summary of output files
    if [ -d "$OUTPUT_DIR" ]; then
        echo "Output files:"
        ls -la "$OUTPUT_DIR"
        echo ""

        # Show quick summary if available
        if [ -f "$OUTPUT_DIR/triage_summary_"*.json ]; then
            SUMMARY_FILE=$(ls "$OUTPUT_DIR"/triage_summary_*.json | head -1)
            echo "Quick Summary:"
            echo "============="
            python3 -c "
import json
try:
    with open('$SUMMARY_FILE', 'r') as f:
        summary = json.load(f)
    print(f\"Total Publications: {summary.get('summary_metrics', {}).get('total_publications', 0)}\")
    print(f\"High Priority: {summary.get('summary_metrics', {}).get('high_priority_publications', 0)}\")
    print(f\"Clinical Trials: {summary.get('summary_metrics', {}).get('clinical_trial_publications', 0)}\")
    print(f\"Full Text Available: {summary.get('summary_metrics', {}).get('full_text_available', 0)}\")
except Exception as e:
    print(f'Could not parse summary: {e}')
"
        fi
    fi

    echo ""
    echo "Next steps:"
    echo "1. Review results in: $OUTPUT_DIR"
    echo "2. Check triage_summary_*.json for executive summary"
    echo "3. Review individual publication summaries"
    echo "4. Process human review workflow as needed"

else
    echo ""
    echo "✗ Weekly Triage Workflow failed!"
    echo "Check the logs above for error details"
    echo ""
    echo "Common issues:"
    echo "- PubMed API connectivity problems"
    echo "- Missing environment variables in .env"
    echo "- Insufficient disk space for output"
    exit 1
fi