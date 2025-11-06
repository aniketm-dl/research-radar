"""
LLM-based relevance filter for research papers.
Scores papers based on alignment with Darpan Labs' business focus.
"""

import os
from typing import Dict, List, Tuple
import google.generativeai as genai


class RelevanceFilter:
    """Filter and score papers based on relevance to Darpan Labs' focus."""

    def __init__(self, model: str = "gemini-2.0-flash-exp", temperature: float = 0.1):
        """
        Initialize the relevance filter.

        Args:
            model: Gemini model to use
            temperature: Temperature for scoring (lower = more deterministic)
        """
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.temperature = temperature

    def score_paper(self, paper: Dict, business_context: str) -> Tuple[float, str]:
        """
        Score a paper's relevance to the business context.

        Args:
            paper: Paper dictionary with title and abstract
            business_context: Description of Darpan Labs' business focus

        Returns:
            Tuple of (relevance_score, reasoning)
            relevance_score: 0-10 score (0 = completely irrelevant, 10 = highly relevant)
            reasoning: Brief explanation of the score
        """
        title = paper.get('title', 'Unknown')
        abstract = paper.get('abstract', 'No abstract available')

        prompt = f"""You are evaluating research papers for relevance to a specific business.

BUSINESS CONTEXT:
{business_context}

PAPER TO EVALUATE:
Title: {title}
Abstract: {abstract}

Task: Score this paper's relevance to the business on a scale of 0-10:
- 0-2: Completely irrelevant (e.g., manufacturing, IoT devices, infrastructure)
- 3-4: Tangentially related but not useful
- 5-6: Somewhat relevant, has some applicable concepts
- 7-8: Relevant, directly applicable to the business
- 9-10: Highly relevant, core to the business focus

CRITICAL EVALUATION CRITERIA:
1. Is this about CONSUMER/CUSTOMER research or industrial/manufacturing applications?
2. Does it involve behavioral modeling, preference prediction, or market research?
3. Does it use AI/LLM agents for understanding human behavior?
4. Is it about creating synthetic data/personas for consumer insights?

FORMAT YOUR RESPONSE EXACTLY AS:
SCORE: [number 0-10]
REASON: [one sentence explanation]

Example:
SCORE: 2
REASON: This paper is about aerostatic thrust bearings in manufacturing, which is completely irrelevant to consumer behavioral modeling.

Evaluate the paper now:"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=200,
                )
            )

            if not response or not response.text:
                print(f"Warning: Empty response for paper '{title[:50]}...'")
                return (0.0, "Failed to score")

            # Parse the response
            text = response.text.strip()
            score = 0.0
            reason = "Unknown"

            for line in text.split('\n'):
                line = line.strip()
                if line.startswith('SCORE:'):
                    score_str = line.replace('SCORE:', '').strip()
                    try:
                        score = float(score_str)
                    except ValueError:
                        print(f"Warning: Could not parse score '{score_str}'")
                elif line.startswith('REASON:'):
                    reason = line.replace('REASON:', '').strip()

            return (score, reason)

        except Exception as e:
            print(f"Error scoring paper '{title[:50]}...': {e}")
            return (0.0, f"Error: {str(e)}")

    def filter_papers(
        self,
        papers: List[Dict],
        business_context: str,
        min_score: float = 5.0,
        max_papers: int = None
    ) -> List[Dict]:
        """
        Filter and rank papers by relevance.

        Args:
            papers: List of paper dictionaries
            business_context: Description of business focus
            min_score: Minimum relevance score to include (0-10)
            max_papers: Maximum number of papers to return

        Returns:
            List of papers sorted by relevance score (highest first)
            Each paper dict has added 'relevance_score' and 'relevance_reason' fields
        """
        if not papers:
            return []

        print(f"\nScoring {len(papers)} papers for relevance...")

        scored_papers = []
        for i, paper in enumerate(papers, 1):
            title = paper.get('title', 'Unknown')
            print(f"  [{i}/{len(papers)}] Scoring: {title[:60]}...")

            score, reason = self.score_paper(paper, business_context)

            # Add scoring info to paper
            paper['relevance_score'] = score
            paper['relevance_reason'] = reason

            print(f"      Score: {score:.1f}/10 - {reason[:80]}...")

            if score >= min_score:
                scored_papers.append(paper)

        # Sort by score (highest first)
        scored_papers.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

        print(f"\nFiltered to {len(scored_papers)} papers with score >= {min_score}")

        if max_papers and len(scored_papers) > max_papers:
            scored_papers = scored_papers[:max_papers]
            print(f"Limited to top {max_papers} papers")

        return scored_papers

    def batch_score_papers(
        self,
        papers: List[Dict],
        business_context: str,
        batch_size: int = 5
    ) -> List[Tuple[float, str]]:
        """
        Score multiple papers in batches for efficiency.

        Args:
            papers: List of paper dictionaries
            business_context: Description of business focus
            batch_size: Number of papers to score in one prompt

        Returns:
            List of (score, reason) tuples
        """
        # For now, use individual scoring
        # Batch scoring could be implemented for better API efficiency
        results = []
        for paper in papers:
            score, reason = self.score_paper(paper, business_context)
            results.append((score, reason))
        return results
