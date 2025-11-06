"""
LLM-based query generator for research paper searches.
Uses Gemini to generate targeted search queries based on research focus.
"""

import os
from typing import List
import google.generativeai as genai


class QueryGenerator:
    """Generate search queries using LLM to improve relevance."""

    def __init__(self, model: str = "gemini-2.0-flash-exp", temperature: float = 0.3):
        """
        Initialize the query generator.

        Args:
            model: Gemini model to use
            temperature: Temperature for generation (0.0-1.0)
        """
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.temperature = temperature

    def generate_queries(
        self,
        research_focus: str,
        num_queries: int = 7,
        exclude_topics: List[str] = None
    ) -> List[str]:
        """
        Generate targeted search queries using LLM.

        Args:
            research_focus: Description of the research area
            num_queries: Number of queries to generate
            exclude_topics: Topics to explicitly exclude

        Returns:
            List of search query strings
        """
        exclude_topics = exclude_topics or []

        prompt = f"""You are a research librarian helping to find academic papers.

RESEARCH FOCUS:
{research_focus}

TOPICS TO EXPLICITLY EXCLUDE:
{', '.join(exclude_topics) if exclude_topics else 'None'}

Generate {num_queries} search queries for arXiv and academic databases. Each query should:
1. Be FOCUSED but not overly restrictive - aim for 2-3 core concepts with OR alternatives
2. Use quoted phrases for multi-word concepts (e.g., "digital twin", "synthetic users")
3. Combine concepts with AND, use OR for synonyms/alternatives
4. Use NOT to exclude major irrelevant topics (manufacturing, IoT, infrastructure)
5. Keep queries SIMPLE - too many AND conditions will find nothing

CRITICAL: The queries must be balanced - specific enough to filter out irrelevant papers, but broad enough to actually find papers.

Format: Return ONLY the queries, one per line, with no numbering or explanation.
Use arXiv search syntax: quotes for phrases, AND, OR, NOT for operators.

Example GOOD queries (focused but findable):
"digital twin" AND consumer NOT (manufacturing OR IoT)
"synthetic users" AND (behavior OR preference)
"LLM agent" AND (consumer OR customer OR marketing)

Example BAD queries (too restrictive, will find nothing):
"digital twin" AND consumer AND "behavioral model" AND AI AND marketing NOT manufacturing

Generate {num_queries} balanced queries now:"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=1000,
                )
            )

            if not response or not response.text:
                print("Warning: Empty response from query generator")
                return self._get_fallback_queries()

            # Parse queries from response
            queries = []
            for line in response.text.strip().split('\n'):
                line = line.strip()
                # Remove numbering if present (1., 1), etc.)
                if line and not line.startswith('#'):
                    # Remove leading numbers and punctuation
                    cleaned = line.lstrip('0123456789.-) ')
                    if cleaned and len(cleaned) > 10:  # Skip very short lines
                        queries.append(cleaned)

            if not queries:
                print("Warning: No valid queries generated, using fallback")
                return self._get_fallback_queries()

            print(f"Generated {len(queries)} search queries using LLM")
            return queries[:num_queries]  # Limit to requested number

        except Exception as e:
            print(f"Error generating queries with LLM: {e}")
            print("Falling back to default queries")
            return self._get_fallback_queries()

    def _get_fallback_queries(self) -> List[str]:
        """
        Return fallback queries if LLM generation fails.

        Returns:
            List of fallback search queries
        """
        return [
            '"digital twin" AND (consumer OR customer) AND (behavior OR preference) NOT (manufacturing OR IoT OR industrial)',
            '"synthetic users" AND "language model" AND (marketing OR consumer OR survey)',
            '("synthetic persona" OR "virtual consumer") AND (simulation OR modeling)',
            '"LLM agent" AND (consumer OR customer) AND (research OR study OR survey)',
            '"agent based" AND (consumer OR customer) AND (simulation OR modeling) NOT (supply chain)',
            '"preference prediction" AND ("language model" OR LLM) AND consumer',
            '"survey augmentation" OR ("retrodiction" AND consumer)',
        ]

    def refine_queries_with_feedback(
        self,
        original_queries: List[str],
        relevant_papers: List[str],
        irrelevant_papers: List[str]
    ) -> List[str]:
        """
        Refine queries based on relevance feedback.

        Args:
            original_queries: The queries that were used
            relevant_papers: Titles of papers that were relevant
            irrelevant_papers: Titles of papers that were not relevant

        Returns:
            List of refined search queries
        """
        prompt = f"""You are refining academic search queries based on relevance feedback.

ORIGINAL QUERIES:
{chr(10).join(f"- {q}" for q in original_queries)}

RELEVANT PAPERS FOUND:
{chr(10).join(f"- {p}" for p in relevant_papers[:3])}

IRRELEVANT PAPERS FOUND:
{chr(10).join(f"- {p}" for p in irrelevant_papers[:5])}

Based on this feedback:
1. Analyze what made the relevant papers match
2. Identify patterns in irrelevant papers that should be excluded
3. Generate {len(original_queries)} improved queries that:
   - Better target the relevant paper topics
   - Explicitly exclude patterns from irrelevant papers
   - Use more specific terminology

Format: Return ONLY the queries, one per line, with no numbering or explanation.

Generate {len(original_queries)} refined queries now:"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=1000,
                )
            )

            if not response or not response.text:
                print("Warning: Could not refine queries")
                return original_queries

            # Parse refined queries
            queries = []
            for line in response.text.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    cleaned = line.lstrip('0123456789.-) ')
                    if cleaned and len(cleaned) > 10:
                        queries.append(cleaned)

            if queries:
                print(f"Refined {len(queries)} search queries based on feedback")
                return queries[:len(original_queries)]
            else:
                return original_queries

        except Exception as e:
            print(f"Error refining queries: {e}")
            return original_queries
