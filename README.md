# Medical Literature Review System for Meridian Therapeutics

A comprehensive AI-powered system for medical literature ingestion, triage, and Q&A designed specifically for pharmaceutical research teams. Built for Meridian Therapeutics' pilot program focusing on oncology and immunotherapy literature.

## 🏗️ System Overview

This system implements two core components:

### 1. Weekly Triage Workflow (`weekly-triage-workflow/`)
**Purpose**: Ingests new publications weekly; classifies, ranks, and drafts structured summaries for scientist review

**Key Features**:
- Automated PubMed querying for oncology/immunotherapy papers
- AI-powered relevance classification and ranking
- Structured summary generation
- Human approval workflow with explicit gates
- Quality metrics and instrumentation

### 2. Therapeutic Area Copilot (`therapeutic-area-copilot/`)
**Purpose**: Searchable Q&A assistant over approved corpus; citation-grounded answers and evidence digests

**Key Features**:
- Semantic search over approved literature corpus
- Citation-grounded answer generation
- Uncertainty signaling and confidence assessment
- Evidence synthesis and conflict detection
- Export capabilities for research documentation

## 📁 Repository Structure

```
medical-reviewer/
├── src/
│   └── pubmed_client.py              # PubMed E-utilities API client
├── weekly-triage-workflow/
│   ├── main.py                       # Main workflow orchestrator
│   ├── classifiers.py                # Publication classification
│   ├── rankers.py                    # Clinical relevance ranking
│   ├── summarizers.py                # Structured summary generation
│   ├── review_workflow.py            # Human review workflow
│   └── config/
│       └── workflow_config.json      # Workflow configuration
├── therapeutic-area-copilot/
│   ├── main.py                       # Main copilot application
│   ├── knowledge_base.py             # Medical corpus management
│   ├── search_engine.py              # Semantic search engine
│   ├── qa_processor.py               # Question answering
│   ├── citation_manager.py           # Citation formatting
│   ├── evidence_synthesizer.py       # Evidence synthesis
│   └── config/
│       └── copilot_config.json       # Copilot configuration
└── README.md                         # This file
```

## 🚀 One-Command Complete Demo Setup

### **🎯 For New Users - Complete Demo (Recommended)**

Get a working medical literature review system with populated database in one command:

```bash
cd medical-reviewer/therapeutic-area-copilot
./simple_run.sh
```

**This single command automatically:**
1. ✅ Sets up Python virtual environment
2. ✅ Installs all dependencies (no compilation issues)
3. ✅ Queries PubMed API for recent medical literature
4. ✅ Populates knowledge base with 5-10 papers
5. ✅ Starts interactive Q&A with pre-filled demo question
6. ✅ Shows working example with real citations

**Expected Demo Output:**
```
🚀 Medical Literature Review System - Complete Demo Setup
=========================================================
📦 Setting up environment...
📚 Knowledge base is empty. Auto-populating with recent medical literature...
🔍 Step 1: Running literature search (finding recent oncology/immunotherapy papers)...
📋 Step 2: Processing publications for knowledge base...
✅ Knowledge base populated successfully!

📊 Knowledge Base Summary:
   📄 Papers in database: 5
   🎯 Focus areas: Oncology, Immunotherapy, Biomarkers
   🔍 Search mode: Keyword-based (MVP)

🚀 Starting Therapeutic Area Copilot...
💡 Demo Question: 'What is the efficacy of pembrolizumab in cancer treatment?'

Question: What is the efficacy of pembrolizumab in cancer treatment?
Answer: Based on clinical trial evidence, pembrolizumab demonstrates significant efficacy in advanced melanoma with objective response rates of 38% and improved overall survival compared to standard therapy...
Confidence: 0.75
Citations:
1. Smith, J. et al. Pembrolizumab for Advanced Melanoma: A Clinical Trial. NEJM. 2024
```

### **🔧 Manual Step-by-Step Setup (Advanced Users)**

If you prefer manual control or want to understand each step:

### Step 1: Run Weekly Triage Workflow
```bash
cd weekly-triage-workflow
./simple_run.sh
```

### Step 2: Run Therapeutic Area Copilot
```bash
cd ../therapeutic-area-copilot
./simple_run.sh
```

### Step 4: View Results

**Triage Results:**
```bash
# View summary
cat weekly-triage-workflow/output/triage_*/triage_summary_*.json

# View individual publication summaries
ls weekly-triage-workflow/output/triage_*/
```

**Copilot Sessions:**
```bash
# View conversation history
ls therapeutic-area-copilot/sessions/
```

## 🔄 **Complete End-to-End Workflow**

### 1. Initial Setup (One-time)
```bash
# Navigate to project
cd medical-reviewer

# Test your Python version
./check_python.py

# Clean any previous installations (if needed)
./cleanup_env.sh
```

### 2. Weekly Literature Review Process
```bash
# Step 1: Run weekly triage to find new papers
cd weekly-triage-workflow
./simple_run.sh

# Step 2: Review the results
cat output/triage_*/triage_summary_*.json

# Step 3: Use copilot for Q&A on the literature
cd ../therapeutic-area-copilot
./simple_run.sh
# Ask questions like:
# "What are the latest checkpoint inhibitor results?"
# "Compare efficacy of different PD-1 inhibitors"
# Type 'exit' when done
```

### 3. Regular Use
```bash
# Run weekly (or as needed)
cd weekly-triage-workflow && ./simple_run.sh

# Use copilot for research questions
cd therapeutic-area-copilot && ./simple_run.sh
```

## ⚡ **Alternative: Full AI Setup (Python 3.8-3.12)**

If you have Python 3.8-3.12 and want full AI features:

```bash
./check_python.py  # Verify compatibility
cd weekly-triage-workflow && ./run_triage.sh      # Full AI triage
cd therapeutic-area-copilot && ./run_copilot.sh   # Semantic search + AI
```

These scripts automatically:
- Set up Python virtual environments
- Install all dependencies
- Configure environment variables
- Run the applications

**Option 2: Manual Setup**

If you prefer manual control:

```bash
# For Weekly Triage
cd weekly-triage-workflow
./setup_env.sh                    # Setup environment
source venv/bin/activate          # Activate environment
python main.py                    # Run workflow

# For Therapeutic Area Copilot
cd therapeutic-area-copilot
./setup_env.sh                    # Setup environment
source venv/bin/activate          # Activate environment
python main.py                    # Run copilot
```

### What Each Component Does

**Weekly Triage Workflow** (`./run_triage.sh`):
- Queries PubMed for recent oncology/immunotherapy papers
- Classifies and ranks publications by clinical relevance
- Generates structured summaries with confidence scoring
- Creates review packages for scientist approval
- Outputs timestamped results to `output/triage_YYYYMMDD_HHMMSS/`

**Therapeutic Area Copilot** (`./run_copilot.sh`):
- Starts interactive Q&A session over approved literature
- Provides citation-grounded answers with uncertainty signaling
- Supports semantic search and evidence synthesis
- Saves session history to `sessions/session_YYYYMMDD_HHMMSS/`

### Example Workflow Output
```
Weekly Triage Workflow completed successfully!
Results saved to: output/triage_20241210_143052/

Quick Summary:
=============
Total Publications: 47
High Priority: 12
Clinical Trials: 8
Full Text Available: 23
```

### Example Copilot Session
```
Question: What is the efficacy of pembrolizumab in melanoma?

Answer: Clinical trial evidence shows pembrolizumab achieves objective response
rates of 33-40% in advanced melanoma with durable responses...

Confidence: 0.87
Citations:
1. Robert C, et al. Pembrolizumab versus ipilimumab in advanced melanoma. NEJM. 2019
2. Schachter J, et al. Pembrolizumab versus investigator-choice chemotherapy... Lancet. 2017

Uncertainty: Low - Strong consensus from 5 clinical trials
```

### 📋 System Requirements

**Prerequisites:**
- Python 3.8 or higher
- 4GB+ RAM (8GB+ recommended for AI models)
- 2GB+ free disk space
- Internet connection (for PubMed API and Claude API)
- **Anthropic Claude API key** (required for AI-powered answers)

**Automatically Installed Dependencies:**

*Core packages (both components):*
- `requests` - HTTP client for PubMed API
- `beautifulsoup4` - XML/HTML parsing
- `pandas`, `numpy` - Data processing
- `python-dateutil` - Date handling

*AI/ML packages (Copilot only):*
- `sentence-transformers` - Semantic embeddings
- `transformers`, `torch` - Neural language models
- `faiss-cpu` - Vector similarity search
- `scikit-learn` - Machine learning utilities

*Optional packages:*
- `jupyter` - Interactive analysis notebooks
- `matplotlib`, `seaborn`, `plotly` - Data visualization
- `spacy` - Advanced NLP processing

### 🔧 Configuration Files

Both components create `.env` configuration files on first run:

**Weekly Triage** (`.env`):
```bash
PUBMED_EMAIL=researcher@meridian.com
PUBMED_API_KEY=your_api_key_here
MAX_PUBLICATIONS=100
DAYS_BACK=7
MIN_RELEVANCE_SCORE=0.3
```

**Copilot** (`.env`):
```bash
CORPUS_PATH=data/approved_corpus
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2
CONFIDENCE_THRESHOLD=0.6
MAX_SEARCH_RESULTS=20
CITATION_STYLE=ama
```

## 🤖 Claude API Configuration (Required)

The system now uses Claude API for generating high-quality, scientifically accurate answers to medical literature questions.

### **1. Get Your API Key**
1. Sign up at [Anthropic Console](https://console.anthropic.com/)
2. Create an API key
3. Copy your key (starts with `sk-ant-api03-...`)

### **2. Add API Key to Environment**
Edit the `.env` file in `therapeutic-area-copilot/`:

```bash
# Replace with your actual API key
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# Claude API Settings (already configured)
CLAUDE_MODEL=claude-3-haiku-20240307  # Lowest cost model
CLAUDE_MAX_TOKENS=1000
CLAUDE_TEMPERATURE=0.1
```

### **3. Enhanced Features with Claude API**
- **AI-powered answers**: 3-paragraph scientific responses tailored for researchers
- **Evidence synthesis**: Intelligent analysis of contradictory findings
- **Quantitative insights**: Automatic extraction of statistical data
- **Clinical implications**: Research-to-practice recommendations
- **Quality assessment**: Confidence scoring based on evidence strength

### **4. Cost Information**
- Uses **Claude 3 Haiku** (lowest cost model: ~$0.25 per 1M tokens)
- Typical cost per question: **$0.001-0.005** (~0.1-0.5 cents)
- Very cost-effective for research use

### **5. Fallback Mode**
If API key is not configured, the system falls back to rule-based processing (original MVP functionality).

## 🔧 Configuration

### Weekly Triage Configuration (`weekly-triage-workflow/config/workflow_config.json`)

Key settings:
- `days_back`: Number of days to search for new publications (default: 7)
- `max_publications`: Maximum publications per weekly run (default: 100)
- `min_relevance_score`: Minimum score for inclusion (default: 0.3)
- `therapeutic_areas`: Focus areas for Meridian's pipeline

### Copilot Configuration (`therapeutic-area-copilot/config/copilot_config.json`)

Key settings:
- `max_search_results`: Maximum search results per query (default: 20)
- `confidence_threshold`: Minimum confidence for answers (default: 0.6)
- `citation_limit`: Maximum citations per answer (default: 10)
- `enable_uncertainty_signaling`: Show uncertainty indicators (default: true)

## 📊 Usage for Meridian Pilot (Weeks 1-5)

### Week 1-2: Initial Setup and Data Ingestion
```bash
# Configure PubMed access
export PUBMED_EMAIL="researcher@meridian.com"
export PUBMED_API_KEY="your_api_key"  # Optional but recommended

# Run initial triage to build corpus
cd weekly-triage-workflow
python main.py
```

### Week 3-4: Q&A and Evidence Synthesis
```bash
# Start using copilot for research questions
cd therapeutic-area-copilot
python main.py

# Example queries:
# "What are the latest checkpoint inhibitor results?"
# "Compare efficacy of different PD-1 inhibitors"
# "What safety concerns exist for CAR-T therapy?"
```

### Week 5: Analysis and Reporting
```bash
# Generate evidence digest
python -c "
from therapeutic_area_copilot.main import TherapeuticAreaCopilot
copilot = TherapeuticAreaCopilot()
digest = copilot.get_evidence_digest('checkpoint inhibitors in melanoma')
print(digest)
"
```

## 🎯 Key Features for Meridian Use Case

### Weekly Triage Workflow
- **Automated Literature Monitoring**: Searches PubMed weekly for oncology/immunotherapy papers using targeted MeSH terms
- **Intelligent Classification**: AI-powered relevance scoring based on Meridian's therapeutic focus
- **Priority Ranking**: Clinical relevance ranking considering study phase, endpoints, and methodology
- **Structured Summaries**: Auto-generated summaries with key findings, clinical relevance, and therapeutic implications
- **Human Review Gates**: Explicit approval workflow for scientist validation
- **Quality Metrics**: Comprehensive tracking of classification accuracy and relevance

### Therapeutic Area Copilot
- **Semantic Search**: Vector-based search over approved literature corpus
- **Citation Grounding**: All answers include properly formatted citations
- **Uncertainty Signaling**: Clear indicators when evidence is limited or conflicting
- **Evidence Synthesis**: Automatic consensus building and conflict detection
- **Export Capabilities**: Results can be exported for integration with research documentation

## 🔍 Example Queries and Use Cases

### Clinical Decision Support
```
Q: "What is the recommended dosing for pembrolizumab in melanoma?"
A: Based on FDA-approved labeling and clinical trials, pembrolizumab is administered at 200mg every 3 weeks or 400mg every 6 weeks intravenously...
Citations: [1] FDA Label, [2] Robert et al. NEJM 2019, [3] Schachter et al. Lancet 2017
Confidence: High
```

### Competitive Intelligence
```
Q: "How does Merck's pembrolizumab compare to BMS's nivolumab in lung cancer?"
A: Head-to-head comparisons are limited, but indirect evidence suggests...
Evidence Synthesis: Consensus from 8 studies shows similar efficacy...
Conflicts: One study reported higher response rate for pembrolizumab, while two others showed no difference
```

### Safety Monitoring
```
Q: "What are the most common adverse events with CAR-T therapy?"
A: The most frequent adverse events include cytokine release syndrome (CRS) and immune effector cell-associated neurotoxicity syndrome (ICANS)...
Safety Profile: Grade 3-4 CRS occurs in 15-20% of patients based on meta-analysis of 12 studies
```

## 📈 Quality Metrics and Monitoring

The system includes comprehensive instrumentation for the pilot:

### Weekly Triage Metrics
- Publications processed per week
- Classification accuracy (when human validation available)
- Relevance score distribution
- High-priority publication identification rate
- Human reviewer time savings

### Copilot Usage Metrics
- Query volume and types
- Answer confidence distribution
- Citation usage patterns
- User satisfaction indicators
- Evidence synthesis quality

## 🔒 Compliance and Validation

### Data Sources
- **PubMed/MEDLINE**: Primary source for peer-reviewed literature
- **PMC Open Access**: Full-text access where available under open license
- **Manual Curation**: Human validation for high-priority publications

### Quality Controls
- **Citation Validation**: Automatic verification of citation formatting
- **Confidence Scoring**: ML-based assessment of answer quality
- **Human Review Gates**: Required approval for clinical decision support
- **Audit Trail**: Complete logging of queries, answers, and citations

## 🛠️ Technical Architecture

### Core Technologies
- **NLP/ML**: Sentence transformers for semantic embeddings
- **Search**: FAISS for vector similarity search
- **Data**: JSON-based storage with optional database backend
- **APIs**: PubMed E-utilities for literature retrieval

### Scalability
- **Modular Design**: Components can be scaled independently
- **Caching**: Intelligent caching for improved response times
- **Batch Processing**: Efficient handling of large literature sets

## 📞 Support and Development

### Configuration Support
- Modify `workflow_config.json` for triage parameters
- Adjust `copilot_config.json` for Q&A behavior
- Environment variables for API keys and external services

### Extending the System
- **New Therapeutic Areas**: Add area-specific classification rules
- **Custom Summarization**: Modify templates in `summarizers.py`
- **Additional Data Sources**: Extend ingestion in `pubmed_client.py`

## 🔧 Troubleshooting

### Python Version Compatibility

**Check your Python version first:**
```bash
./check_python.py
```

**Python 3.14+ Compilation Errors:**
```
ERROR: Failed building wheel for lxml
error: command '/usr/bin/clang' failed with exit code 1
```

**Quick Solution - Use Simple MVP Mode:**
```bash
cd weekly-triage-workflow && ./simple_run.sh
cd therapeutic-area-copilot && ./simple_run.sh
```

**Full Solution - Use Compatible Python:**
```bash
# Install Python 3.11 (most compatible)
brew install pyenv
pyenv install 3.11.7
pyenv local 3.11.7

# Clean and retry
./cleanup_env.sh
cd therapeutic-area-copilot && ./run_copilot.sh
```

### Common Issues and Solutions

**"No module named 'sentence_transformers'"**
```bash
# Clean environment and reinstall
./cleanup_env.sh
cd therapeutic-area-copilot
./setup_env.sh
```

**"PubMed API rate limiting"**
- Set `PUBMED_API_KEY` in `.env` file for higher rate limits
- Reduce `MAX_PUBLICATIONS` or increase `DAYS_BACK` in config

**"Knowledge base empty" / No search results**
- Run weekly triage first: `cd weekly-triage-workflow && ./run_triage.sh`
- Copy approved publications to `therapeutic-area-copilot/data/approved_corpus/`

**"CUDA out of memory" (AI models)**
- Use CPU-only models: Set `TORCH_CUDA=false` in environment
- Reduce batch sizes in configuration files
- Use smaller embedding models

**"Permission denied" errors**
```bash
chmod +x *.sh  # Make scripts executable
```

**Corrupted package installations** (directories like `/path/=1.24.0`)
```bash
./cleanup_env.sh  # Remove all corrupted packages and environments
```

**Virtual environment issues**
```bash
rm -rf venv    # Remove corrupted environment
./setup_env.sh # Reinstall fresh
```

**"Package installation hanging or failing"**
```bash
# Clean pip cache and retry
pip3 cache purge
./cleanup_env.sh
# Then retry setup
```

### Getting Help

**Check logs:**
- Weekly triage logs: `weekly-triage-workflow/logs/`
- Copilot session logs: `therapeutic-area-copilot/sessions/`

**Validate setup:**
```bash
# Test core imports
python3 -c "import requests, pandas, numpy; print('✓ Core packages OK')"

# Test AI packages (copilot)
python3 -c "import torch, transformers, sentence_transformers; print('✓ AI packages OK')"
```

**Reset to defaults:**
```bash
rm .env        # Remove custom configuration
./setup_env.sh # Recreate with defaults
```

## 📝 License and Usage

This system is designed specifically for Meridian Therapeutics' internal research use. All medical literature accessed through PubMed is used in accordance with NCBI usage guidelines and fair use principles for research purposes.

---

**Note**: This system is designed for research support and should not be used as the sole basis for clinical decisions. All outputs should be validated by qualified medical professionals.