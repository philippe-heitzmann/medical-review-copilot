"""
Claude API Integration for Medical Literature Review
Handles Claude API calls with scientific literature context
"""

import os
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import json

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class ClaudeResponse:
    """Response from Claude API with metadata"""
    answer_text: str
    confidence: float
    key_points: List[str]
    model_used: str
    tokens_used: Optional[int] = None

class ClaudeAPIClient:
    """Client for Claude API integration in medical literature review"""

    def __init__(self, config: Dict):
        """Initialize Claude API client"""
        self.config = config
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.model = os.getenv('CLAUDE_MODEL', 'claude-3-haiku-20240307')

        # Parse max_tokens, handling comments
        max_tokens_str = os.getenv('CLAUDE_MAX_TOKENS', '1000').split('#')[0].strip()
        self.max_tokens = int(max_tokens_str)

        # Parse temperature, handling comments
        temperature_str = os.getenv('CLAUDE_TEMPERATURE', '0.1').split('#')[0].strip()
        self.temperature = float(temperature_str)

        if not ANTHROPIC_AVAILABLE:
            logger.warning("Anthropic package not available - Claude API disabled")
            self.client = None
            return

        if not self.api_key or self.api_key == 'your_anthropic_api_key_here':
            logger.warning("Claude API key not configured - API disabled")
            self.client = None
            return

        try:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            logger.info(f"Claude API client initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Claude API client: {e}")
            self.client = None

    def is_available(self) -> bool:
        """Check if Claude API is available"""
        return self.client is not None

    def generate_scientific_answer(self, question: str, evidence_pieces: List[Dict],
                                 context: Optional[Dict] = None) -> ClaudeResponse:
        """
        Generate a scientific answer using Claude API with literature context

        Args:
            question: User's scientific question
            evidence_pieces: Relevant literature evidence
            context: Optional additional context

        Returns:
            ClaudeResponse with generated answer
        """
        if not self.is_available():
            raise Exception("Claude API not available")

        try:
            # Build the scientific prompt
            prompt = self._build_scientific_prompt(question, evidence_pieces, context)

            # Make API call
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract response text
            answer_text = response.content[0].text

            # Parse structured response
            parsed_response = self._parse_claude_response(answer_text)

            # Calculate confidence based on evidence quality
            confidence = self._calculate_confidence(evidence_pieces, parsed_response)

            return ClaudeResponse(
                answer_text=parsed_response.get('answer', answer_text),
                confidence=confidence,
                key_points=parsed_response.get('key_points', []),
                model_used=self.model,
                tokens_used=response.usage.output_tokens if hasattr(response, 'usage') else None
            )

        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            raise Exception(f"Failed to generate answer with Claude API: {e}")

    def _build_scientific_prompt(self, question: str, evidence_pieces: List[Dict],
                               context: Optional[Dict] = None) -> str:
        """Build scientific literature review prompt for Claude"""

        # Format literature references
        literature_context = self._format_literature_context(evidence_pieces)

        # Determine question type for specialized instructions
        question_type = self._classify_question_type(question)

        prompt = f"""You are a medical literature review assistant helping scientists analyze research evidence.

QUESTION: {question}

LITERATURE EVIDENCE:
{literature_context}

INSTRUCTIONS:
Please provide a concise, scientifically accurate response in exactly 3 paragraphs that would be useful to a scientist reviewing this literature. Focus on:

1. **First paragraph**: Direct answer to the question based on the evidence, including key quantitative findings (response rates, survival data, statistical significance where available).

2. **Second paragraph**: Synthesize findings across studies, noting consistency or conflicts in the evidence, study types (clinical trials, observational studies, etc.), and strength of evidence.

3. **Third paragraph**: Clinical implications, limitations of current evidence, and areas where additional research may be needed.

REQUIREMENTS:
- Be precise and evidence-based
- Include specific data points when available (percentages, p-values, confidence intervals)
- Acknowledge limitations and uncertainties
- Use scientific language appropriate for researchers
- Cite study types and evidence quality
- If evidence is conflicting or limited, state this clearly

RESPONSE FORMAT:
Please structure your response as:

ANSWER:
[Three paragraphs as requested above]

KEY_POINTS:
- [Key finding 1]
- [Key finding 2]
- [Key finding 3]
"""

        return prompt

    def _format_literature_context(self, evidence_pieces: List[Dict]) -> str:
        """Format literature evidence for Claude prompt"""
        if not evidence_pieces:
            return "No specific literature evidence provided."

        literature_text = ""
        for i, piece in enumerate(evidence_pieces[:5], 1):  # Limit to top 5
            literature_text += f"\n**Study {i}:** {piece.get('title', 'Unknown Title')}\n"
            literature_text += f"**Authors:** {', '.join(piece.get('authors', ['Unknown']))}\n"
            literature_text += f"**Journal:** {piece.get('journal', 'Unknown Journal')}\n"
            literature_text += f"**Publication Date:** {piece.get('publication_date', 'Unknown')}\n"
            literature_text += f"**Study Type:** {piece.get('study_type', 'Unknown')}\n"
            literature_text += f"**Evidence Quality:** {piece.get('evidence_quality', 'Unknown')}\n"

            # Add relevant text excerpts
            relevant_text = piece.get('relevant_text', [])
            if isinstance(relevant_text, list):
                text_excerpt = ' '.join(relevant_text[:2])  # First 2 chunks
            else:
                text_excerpt = str(relevant_text)[:500]  # First 500 chars

            literature_text += f"**Key Findings:** {text_excerpt}\n"
            literature_text += f"**Relevance Score:** {piece.get('relevance_score', 'Unknown')}\n\n"

        return literature_text

    def _classify_question_type(self, question: str) -> str:
        """Classify question type for specialized handling"""
        question_lower = question.lower()

        if any(word in question_lower for word in ['efficacy', 'effective', 'response', 'survival']):
            return 'efficacy'
        elif any(word in question_lower for word in ['safety', 'adverse', 'toxicity', 'side effects']):
            return 'safety'
        elif any(word in question_lower for word in ['mechanism', 'how does', 'pathway', 'target']):
            return 'mechanism'
        elif any(word in question_lower for word in ['compare', 'versus', 'vs', 'difference']):
            return 'comparison'
        else:
            return 'general'

    def _parse_claude_response(self, response_text: str) -> Dict:
        """Parse structured response from Claude"""
        parsed = {'answer': '', 'key_points': []}

        # Split response into sections
        sections = response_text.split('KEY_POINTS:')

        if len(sections) >= 2:
            # Extract main answer
            answer_section = sections[0].replace('ANSWER:', '').strip()
            parsed['answer'] = answer_section

            # Extract key points
            key_points_text = sections[1].strip()
            key_points = []
            for line in key_points_text.split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    key_points.append(line[2:].strip())
            parsed['key_points'] = key_points
        else:
            # Fallback if structure not followed
            parsed['answer'] = response_text

        return parsed

    def _calculate_confidence(self, evidence_pieces: List[Dict],
                            parsed_response: Dict) -> float:
        """Calculate confidence based on evidence quality and response"""
        if not evidence_pieces:
            return 0.3

        # Base confidence on evidence quality
        quality_scores = {'high': 0.9, 'medium': 0.7, 'low': 0.5}
        avg_quality = sum(quality_scores.get(piece.get('evidence_quality', 'low'), 0.5)
                         for piece in evidence_pieces) / len(evidence_pieces)

        # Adjust for number of sources
        source_factor = min(len(evidence_pieces) / 3.0, 1.0)

        # Adjust for response completeness
        response_factor = 0.8 if parsed_response.get('key_points') else 0.7

        confidence = avg_quality * source_factor * response_factor
        return min(max(confidence, 0.1), 1.0)

def main():
    """Test Claude API functionality"""
    config = {}
    claude_client = ClaudeAPIClient(config)

    if claude_client.is_available():
        print("✓ Claude API client initialized successfully")
        print(f"Model: {claude_client.model}")
    else:
        print("✗ Claude API not available")
        print("Check ANTHROPIC_API_KEY environment variable")

if __name__ == "__main__":
    main()