#!/bin/bash
# Cleanup script to remove corrupted environments and packages

set -e

echo "Environment Cleanup Script"
echo "========================="

# Function to clean up a specific directory
cleanup_directory() {
    local dir=$1
    echo "Cleaning up: $dir"

    if [ -d "$dir" ]; then
        cd "$dir"

        # Remove virtual environment
        if [ -d "venv" ]; then
            echo "  Removing virtual environment..."
            rm -rf venv
        fi

        # Remove any corrupted package directories
        echo "  Cleaning up corrupted packages..."
        find . -maxdepth 1 -name "*=*" -type d -exec rm -rf {} \; 2>/dev/null || true
        find . -maxdepth 1 -name "*>=*" -type d -exec rm -rf {} \; 2>/dev/null || true

        # Remove Python cache
        echo "  Removing Python cache..."
        find . -name "__pycache__" -type d -exec rm -rf {} \; 2>/dev/null || true
        find . -name "*.pyc" -delete 2>/dev/null || true

        # Clean up any pip cache issues
        if command -v pip3 &> /dev/null; then
            echo "  Clearing pip cache..."
            pip3 cache purge 2>/dev/null || true
        fi

        echo "  ✓ Cleanup complete for $dir"
    else
        echo "  Directory $dir not found, skipping..."
    fi
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Clean up both components
cleanup_directory "$SCRIPT_DIR/weekly-triage-workflow"
cleanup_directory "$SCRIPT_DIR/therapeutic-area-copilot"

echo ""
echo "Global cleanup..."

# Clean up global pip cache
if command -v pip3 &> /dev/null; then
    echo "Clearing global pip cache..."
    pip3 cache purge 2>/dev/null || true
fi

# Clean up any system-wide Python cache in current user directory
echo "Cleaning Python cache in current directory..."
find "$SCRIPT_DIR" -name "__pycache__" -type d -exec rm -rf {} \; 2>/dev/null || true
find "$SCRIPT_DIR" -name "*.pyc" -delete 2>/dev/null || true

echo ""
echo "✓ Environment cleanup complete!"
echo ""
echo "Next steps:"
echo "1. Run: cd weekly-triage-workflow && ./run_triage.sh"
echo "2. Or run: cd therapeutic-area-copilot && ./run_copilot.sh"
echo ""
echo "This will create fresh, clean environments."