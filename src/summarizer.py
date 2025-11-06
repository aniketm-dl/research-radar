"""
Google Gemini-powered summarizer for research papers.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
import google.generativeai as genai


class Summarizer:
    """Summarize research papers using Google Gemini API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash-latest", temperature: float = 0.2):
        """
        Initialize the summarizer with Google Gemini.

        Args:
            api_key: Gemini API key (uses environment variable if not provided)
            model: Model to use for summarization (gemini-1.5-flash-latest or gemini-1.5-pro-latest)
            temperature: Temperature for generation
        """
        if api_key is None:
            api_key = os.getenv('GEMINI_API_KEY')

        if not api_key:
            raise ValueError("Gemini API key must be provided or set as GEMINI_API_KEY environment variable")

        # Configure Gemini
        genai.configure(api_key=api_key)

        # Initialize the model
        self.model = genai.GenerativeModel(model)
        self.temperature = temperature
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """Load the prompt template from file."""
        prompt_file = Path(__file__).parent.parent / "prompt" / "summary_prompt.md"

        if not prompt_file.exists():
            # Fallback to default prompt if file doesn't exist
            return self._get_default_prompt()

        with open(prompt_file, 'r') as f:
            return f.read()

    def _get_default_prompt(self) -> str:
        """Get a default prompt template as fallback."""
        return """SYSTEM
You are a precise research analyst for a newsletter read by ML engineers and PMs at a customer-twin startup.
Goal. Summarize each paper in two to three short paragraphs and link it to customer digital twins, synthetic users, LLM agents for consumer research, and practical evaluation.

Constraints.
Be factual and verify against provided metadata and abstract.
Avoid speculation. If a claim is unclear, state that briefly.
Tie findings to at least two of these.
a) building and validating twins
b) data sources and instrumentation
c) modeling choices such as fine-tuning, retrieval, and agents
d) evaluation such as individual and aggregate accuracy and test–retest stability
Mention one limitation or ethical risk in one concise sentence if relevant.
Output only the fields below. Do not add preamble.

Ultra-think instructions. Think stepwise in private. Return only the final answer. Prefer concrete claims and numbers over adjectives. Surface one insight that helps a product team decide whether to adopt or replicate the method.

USER
Paper metadata and abstract.
TITLE: {{title}}
AUTHORS: {{authors}}
DATE: {{date}}
LINK: {{url}}
ABSTRACT: {{abstract}}

OUTPUT FORMAT
TITLE: {{title}}
LINK: {{url}}
AUTHORS: {{authors}}
DATE: {{date}}
SUMMARY:
{{write two to three paragraphs tailored to customer twins. do not use bullets}}"""

    def _fill_template(self, paper: Dict) -> str:
        """
        Fill the prompt template with paper information.

        Args:
            paper: Dictionary containing paper metadata

        Returns:
            Filled prompt string
        """
        prompt = self.prompt_template

        # Format authors list
        authors = paper.get('authors', [])
        if isinstance(authors, list):
            authors_str = ', '.join(authors[:5])  # Limit to first 5 authors
            if len(authors) > 5:
                authors_str += f" et al. ({len(authors)} authors total)"
        else:
            authors_str = str(authors)

        # Replace placeholders
        replacements = {
            '{{title}}': paper.get('title', 'Title not available'),
            '{{authors}}': authors_str or 'Authors not available',
            '{{date}}': paper.get('date', 'Date not available'),
            '{{url}}': paper.get('url', 'URL not available'),
            '{{abstract}}': paper.get('abstract', 'Abstract not available')
        }

        for placeholder, value in replacements.items():
            prompt = prompt.replace(placeholder, value)

        return prompt

    def summarize(self, paper: Dict) -> Optional[str]:
        """
        Summarize a single paper using Google Gemini.

        Args:
            paper: Dictionary containing paper metadata

        Returns:
            Summary text or None if summarization fails
        """
        try:
            # Fill the prompt template
            prompt = self._fill_template(paper)

            # Generate summary using Gemini
            generation_config = genai.GenerationConfig(
                temperature=self.temperature,
                max_output_tokens=600,
                top_p=0.95,
                top_k=40
            )

            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )

            # Extract the summary
            if response and response.text:
                summary = response.text.strip()

                # Clean up the output - remove any SYSTEM or USER headers if present
                if 'OUTPUT FORMAT' in summary:
                    summary = summary.split('OUTPUT FORMAT')[1].strip()
                elif 'SUMMARY:' in summary:
                    # Extract everything after SUMMARY:
                    summary_parts = summary.split('SUMMARY:')
                    if len(summary_parts) > 1:
                        summary = 'SUMMARY:\n' + summary_parts[1].strip()

                return summary
            else:
                print(f"No response from Gemini for paper: {paper.get('title', 'Unknown')}")
                return None

        except Exception as e:
            print(f"Error summarizing paper '{paper.get('title', 'Unknown')}': {e}")
            # Check if it's a safety/content filtering issue
            if hasattr(e, 'safety_ratings'):
                print(f"Safety ratings: {e.safety_ratings}")
            return None

    def summarize_batch(self, papers: List[Dict]) -> Dict[str, str]:
        """
        Summarize multiple papers.

        Args:
            papers: List of paper dictionaries

        Returns:
            Dictionary mapping paper IDs to summaries
        """
        summaries = {}

        for paper in papers:
            paper_id = paper.get('id')
            if not paper_id:
                continue

            print(f"  Summarizing with Gemini: {paper.get('title', 'Unknown')[:60]}...")
            summary = self.summarize(paper)
            if summary:
                summaries[paper_id] = summary
            else:
                # Provide a fallback summary for failed attempts
                summaries[paper_id] = self._create_fallback_summary(paper)

        return summaries

    def _create_fallback_summary(self, paper: Dict) -> str:
        """
        Create a basic fallback summary when API fails.

        Args:
            paper: Dictionary containing paper metadata

        Returns:
            Basic formatted summary
        """
        authors = paper.get('authors', [])
        if isinstance(authors, list):
            authors_str = ', '.join(authors[:3])
            if len(authors) > 3:
                authors_str += f" et al."
        else:
            authors_str = str(authors)

        return f"""TITLE: {paper.get('title', 'Title not available')}
LINK: {paper.get('url', 'URL not available')}
AUTHORS: {authors_str or 'Authors not available'}
DATE: {paper.get('date', 'Date not available')}
SUMMARY:
This paper could not be summarized automatically. The abstract is provided below for reference.

{paper.get('abstract', 'Abstract not available')}"""