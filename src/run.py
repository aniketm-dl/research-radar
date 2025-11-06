"""
Main coordinator script for the research newsletter.
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Dict, List

# Load environment variables from .env file if it exists
env_file = Path(__file__).parent.parent / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.search_arxiv import ArxivSearcher
from src.search_crossref import CrossrefSearcher
from src.summarizer import Summarizer
from src.emailer import EmailSender
from src.util_state import StateManager
from src.query_generator import QueryGenerator
from src.relevance_filter import RelevanceFilter


def load_config(config_file: str = "config.yaml") -> Dict:
    """Load configuration from YAML file."""
    config_path = Path(config_file)
    if not config_path.exists():
        print(f"Error: Configuration file {config_file} not found")
        sys.exit(1)

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def search_papers(config: Dict) -> List[Dict]:
    """
    Search for papers using configured queries.

    Args:
        config: Configuration dictionary

    Returns:
        List of paper dictionaries
    """
    search_config = config.get('search', {})
    lookback_days = search_config.get('search_window_days', 7)
    max_results = search_config.get('max_results_per_source', 12)

    # Generate or get queries
    use_llm = search_config.get('use_llm_query_generation', False)
    if use_llm:
        print("Generating search queries using LLM...")
        try:
            query_gen = QueryGenerator()
            queries = query_gen.generate_queries(
                research_focus=search_config.get('research_focus', ''),
                num_queries=search_config.get('num_queries', 7),
                exclude_topics=search_config.get('exclude_topics', [])
            )
            print(f"Generated {len(queries)} queries:")
            for i, q in enumerate(queries, 1):
                print(f"  {i}. {q}")
        except Exception as e:
            print(f"Error generating queries: {e}")
            print("Falling back to configured queries")
            queries = search_config.get('fallback_queries', [])
    else:
        queries = search_config.get('fallback_queries', [])
        print(f"Using {len(queries)} configured queries")

    if not queries:
        print("Error: No queries available")
        return []

    all_papers = []
    seen_ids = set()

    # Search arXiv
    print("\nSearching arXiv...")
    arxiv_searcher = ArxivSearcher()
    for query in queries:
        papers = arxiv_searcher.search(query, lookback_days, max_results)
        for paper in papers:
            paper_id = paper.get('id')
            if paper_id and paper_id not in seen_ids:
                seen_ids.add(paper_id)
                all_papers.append(paper)
        print(f"  Query '{query[:60]}...': found {len(papers)} papers")

    # Search Crossref
    print("\nSearching Crossref...")
    crossref_searcher = CrossrefSearcher()
    for query in queries:
        papers = crossref_searcher.search(query, lookback_days, max_results)
        for paper in papers:
            # Use DOI for deduplication
            paper_doi = paper.get('doi')
            if paper_doi and paper_doi not in seen_ids:
                seen_ids.add(paper_doi)
                all_papers.append(paper)
        print(f"  Query '{query[:60]}...': found {len(papers)} papers")

    # Sort by date (newest first)
    all_papers.sort(key=lambda x: x.get('date', ''), reverse=True)

    print(f"\nTotal papers found: {len(all_papers)}")
    return all_papers


def main():
    """Main execution function."""
    print("=" * 50)
    print("Research Newsletter Generator")
    print("=" * 50)

    # Load configuration
    print("\nLoading configuration...")
    config = load_config()

    # Initialize state manager
    print("Initializing state manager...")
    state_manager = StateManager()

    # Clean up old entries (older than 30 days)
    state_manager.cleanup_old_entries(30)

    # Search for papers
    print("\nSearching for papers...")
    papers = search_papers(config)

    if not papers:
        print("No papers found. Exiting.")
        return

    # Filter out already sent papers
    print("\nFiltering unseen papers...")
    unseen_papers = state_manager.filter_unseen(papers)
    print(f"Found {len(unseen_papers)} new papers")

    if not unseen_papers:
        print("No new papers to send. Exiting.")
        return

    # Apply relevance filtering if enabled
    search_config = config.get('search', {})
    use_relevance_filter = search_config.get('use_relevance_filtering', False)

    if use_relevance_filter:
        business_context = search_config.get('business_context', '')
        min_score = search_config.get('min_relevance_score', 6.0)

        try:
            relevance_filter = RelevanceFilter()
            relevant_papers = relevance_filter.filter_papers(
                papers=unseen_papers,
                business_context=business_context,
                min_score=min_score
            )

            if not relevant_papers:
                print(f"\nNo papers scored >= {min_score}/10. Exiting.")
                return

            papers_to_process = relevant_papers
        except Exception as e:
            print(f"Error in relevance filtering: {e}")
            print("Proceeding without relevance filtering")
            papers_to_process = unseen_papers
    else:
        papers_to_process = unseen_papers

    # Limit to max summaries
    max_summaries = config.get('summarization', {}).get('max_summaries', 8)
    if len(papers_to_process) > max_summaries:
        print(f"\nLimiting to {max_summaries} papers")
        papers_to_summarize = papers_to_process[:max_summaries]
    else:
        papers_to_summarize = papers_to_process

    # Summarize papers
    print(f"\nSummarizing {len(papers_to_summarize)} papers...")
    summarizer_config = config.get('summarization', {})
    summarizer = Summarizer(
        model=summarizer_config.get('model', 'gemini-pro'),
        temperature=summarizer_config.get('temperature', 0.2)
    )

    # Add summaries to papers
    papers_with_summaries = []
    for paper in papers_to_summarize:
        print(f"  Summarizing: {paper.get('title', 'Unknown')[:60]}...")
        summary = summarizer.summarize(paper)
        if summary:
            paper['summary'] = summary
            papers_with_summaries.append(paper)
        else:
            print(f"    Warning: Failed to summarize")

    if not papers_with_summaries:
        print("No papers were successfully summarized. Exiting.")
        return

    print(f"Successfully summarized {len(papers_with_summaries)} papers")

    # Send email digest
    print("\nSending email digest...")
    email_config = config.get('email', {})
    smtp_config = config.get('smtp', {})

    # Get recipients
    recipients = email_config.get('recipients', [])
    if not recipients:
        print("Warning: No recipients configured. Skipping email.")
    else:
        try:
            email_sender = EmailSender(
                smtp_host=smtp_config.get('host'),
                smtp_port=smtp_config.get('port'),
                use_ssl=smtp_config.get('use_ssl', True)
            )

            success = email_sender.send_digest(
                recipients=recipients,
                papers_with_summaries=papers_with_summaries,
                from_email=email_config.get('from_email', 'research@example.com'),
                from_name=email_config.get('from_name', 'Research Radar'),
                subject_prefix=email_config.get('subject_prefix', '[Research Digest]')
            )

            if success:
                print("Email sent successfully!")

                # Mark papers as sent
                paper_ids = [p.get('id') for p in papers_with_summaries if p.get('id')]
                paper_metadata = {
                    p.get('id'): {'title': p.get('title', '')}
                    for p in papers_with_summaries if p.get('id')
                }
                state_manager.mark_as_sent(paper_ids, paper_metadata)
                print(f"Marked {len(paper_ids)} papers as sent")
            else:
                print("Failed to send email")

        except Exception as e:
            print(f"Error sending email: {e}")

    print("\nNewsletter generation complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()