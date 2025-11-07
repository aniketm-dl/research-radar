"""
LLM-based relevance filter for research papers.
Scores papers based on alignment with Darpan Labs' business focus.
"""

import os
import time
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
        self.last_request_time = 0
        self.min_request_interval = 7  # 7 seconds between requests to stay under 10/min

    def _rate_limit(self):
        """Implement rate limiting to respect API quotas."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()

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
        # Apply rate limiting
        self._rate_limit()

        title = paper.get('title', 'Unknown')
        abstract = paper.get('abstract', 'No abstract available')

        prompt = f"""You are evaluating research papers for relevance to Darpan Labs' specific business needs.

DARPAN LABS BUSINESS CONTEXT:
{business_context}

DETAILED BUSINESS FOCUS (from pitch):
• Core Technology: AI-powered digital twins of consumers for market research
  - Creating synthetic personas/users that mimic real consumer behavior with 85% accuracy
  - Using LLM agents to simulate customer decision-making and preferences
  - Behavioral modeling based on internal customer data and external sources

• Key Use Cases:
  1. Product testing and feature discovery
  2. Marketing campaign optimization
  3. Pricing sensitivity analysis
  4. A/B testing without live users
  5. Consumer preference prediction
  6. Market research without surveys

• Technologies of Interest:
  - Large Language Models (LLMs) for persona generation
  - Agent-based modeling for consumer simulation
  - Behavioral prediction and preference modeling
  - Synthetic data generation for consumer insights
  - Validation methods for synthetic personas (accuracy, test-retest stability)
  - Fine-tuning, retrieval, and agent architectures

• EXPLICITLY NOT RELEVANT:
  - Manufacturing, supply chain, or industrial automation
  - IoT devices or hardware (unless for consumer behavior tracking)
  - Healthcare and medical applications (unless about patient behavioral modeling)
  - Infrastructure, networking, or systems engineering
  - Pure theoretical work without practical consumer applications

PAPER TO EVALUATE:
Title: {title}
Abstract: {abstract}

SCORING CRITERIA:
Score this paper's relevance on a scale of 0-10:

10 = CORE TO BUSINESS: LLM-based synthetic personas, consumer digital twins, behavioral agent simulation
9 = HIGHLY RELEVANT: Direct methods for consumer behavior prediction, preference modeling, synthetic user generation
8 = VERY RELEVANT: LLM agents, behavioral modeling, personalization systems applicable to consumers
7 = RELEVANT: Applicable techniques for persona creation, evaluation methods, data sources for consumer modeling
6 = MODERATELY RELEVANT: General AI/ML methods that could be adapted for consumer digital twins
5 = SOMEWHAT RELEVANT: Tangentially related concepts (e.g., behavioral modeling in non-consumer contexts)
4 = LOOSELY RELATED: AI/ML work with unclear consumer application
3 = BARELY RELATED: Technical AI work without clear path to consumer modeling
2 = NOT RELEVANT: Wrong domain (e.g., manufacturing, infrastructure)
1-0 = COMPLETELY IRRELEVANT: No connection to consumer behavior, digital twins, or AI agents

CRITICAL QUESTIONS:
1. Does this involve CONSUMER/CUSTOMER behavior, preferences, or decision-making?
2. Does it use LLM agents or synthetic personas for understanding humans?
3. Could the methods be applied to creating/validating digital twins of consumers?
4. Is it about behavioral prediction, personalization, or market research?

FORMAT YOUR RESPONSE EXACTLY AS:
SCORE: [number 0-10]
REASON: [one sentence explanation relating to Darpan's specific use cases]

Example responses:
SCORE: 9
REASON: Paper presents LLM-based agent framework for simulating consumer decision-making in e-commerce, directly applicable to Darpan's synthetic persona generation.

SCORE: 3
REASON: Paper is about aerostatic thrust bearings in manufacturing equipment, completely outside consumer behavioral modeling domain.

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
