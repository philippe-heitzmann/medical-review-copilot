#!/bin/bash
# Main runner script for Therapeutic Area Copilot

set -e  # Exit on error

echo "Starting Therapeutic Area Copilot..."
echo "==================================="

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

# Check knowledge base setup
echo ""
echo "Step 4: Checking knowledge base..."
CORPUS_PATH="${CORPUS_PATH:-data/approved_corpus}"

if [ ! -d "$CORPUS_PATH" ]; then
    echo "Creating corpus directory: $CORPUS_PATH"
    mkdir -p "$CORPUS_PATH"
fi

# Check for existing corpus
if [ "$(ls -A $CORPUS_PATH 2>/dev/null)" ]; then
    CORPUS_COUNT=$(ls "$CORPUS_PATH"/*.json 2>/dev/null | wc -l || echo "0")
    echo "✓ Found $CORPUS_COUNT corpus files in $CORPUS_PATH"
else
    echo "⚠ No corpus files found in $CORPUS_PATH"
    echo "  To populate the corpus:"
    echo "  1. Run the weekly-triage-workflow first to generate approved publications"
    echo "  2. Copy approved publications to $CORPUS_PATH"
    echo "  3. Or manually add publication JSON files to $CORPUS_PATH"
fi

# Check AI model availability
echo ""
echo "Step 5: Checking AI models..."
python3 -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA devices: {torch.cuda.device_count()}')

try:
    from sentence_transformers import SentenceTransformer
    print('✓ Sentence Transformers available')

    # Test model loading (this will download if not cached)
    print('Loading embedding model (may download on first run)...')
    model_name = '$EMBEDDING_MODEL' if '$EMBEDDING_MODEL' else 'sentence-transformers/all-mpnet-base-v2'
    model = SentenceTransformer(model_name)
    print(f'✓ Embedding model loaded: {model_name}')
    print(f'  Embedding dimension: {model.get_sentence_embedding_dimension()}')

except Exception as e:
    print(f'⚠ Embedding model issue: {e}')
    print('  The copilot will use fallback keyword search')

try:
    import faiss
    print('✓ FAISS vector search available')
except Exception as e:
    print(f'⚠ FAISS not available: {e}')
"

# Create session directory
SESSION_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SESSION_DIR="sessions/session_${SESSION_TIMESTAMP}"
mkdir -p "$SESSION_DIR"
export SESSION_DIR="$SESSION_DIR"

echo ""
echo "Step 6: Starting Therapeutic Area Copilot..."
echo "Session directory: $SESSION_DIR"
echo "Default therapeutic area: ${DEFAULT_THERAPEUTIC_AREA:-oncology}"
echo "Max search results: ${MAX_SEARCH_RESULTS:-20}"
echo "Confidence threshold: ${CONFIDENCE_THRESHOLD:-0.6}"
echo ""

# Check if running in interactive mode
if [ -t 0 ]; then
    echo "Starting interactive Q&A session..."
    echo "Type 'exit' to quit, 'help' for commands"
    echo ""

    # Run the main copilot in interactive mode
    python3 main.py

else
    echo "Non-interactive mode detected"
    echo "For interactive Q&A, run: ./run_copilot.sh"
    echo "For programmatic use, import the TherapeuticAreaCopilot class"
fi

# Check if copilot completed successfully
if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Copilot session completed!"

    # Show session summary if available
    if [ -d "$SESSION_DIR" ]; then
        echo ""
        echo "Session files:"
        ls -la "$SESSION_DIR" 2>/dev/null || echo "No session files saved"
    fi

    echo ""
    echo "Usage examples:"
    echo "==============="
    echo ""
    echo "Interactive mode:"
    echo "  Question: What is the efficacy of pembrolizumab in melanoma?"
    echo "  Question: Compare checkpoint inhibitors vs chemotherapy"
    echo "  Question: What are the safety concerns with CAR-T therapy?"
    echo ""
    echo "Commands:"
    echo "  'history' - Show conversation history"
    echo "  'clear' - Clear conversation history"
    echo "  'exit' - Quit the copilot"
    echo ""
    echo "Programmatic usage:"
    echo "  from therapeutic_area_copilot.main import TherapeuticAreaCopilot"
    echo "  copilot = TherapeuticAreaCopilot()"
    echo "  result = copilot.ask_question('your question')"

else
    echo ""
    echo "✗ Copilot failed to start!"
    echo "Check the logs above for error details"
    echo ""
    echo "Common issues:"
    echo "- Missing AI model dependencies (torch, transformers)"
    echo "- Insufficient memory for embedding models"
    echo "- Empty knowledge base corpus"
    echo "- Network issues downloading models"
    exit 1
fi