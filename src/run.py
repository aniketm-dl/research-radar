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
    queries = search_config.get('queries', [])
    lookback_days = search_config.get('search_window_days', 7)
    max_results = search_config.get('max_results_per_source', 12)

    all_papers = []
    seen_ids = set()

    # Search arXiv
    print("Searching arXiv...")
    arxiv_searcher = ArxivSearcher()
    for query in queries:
        papers = arxiv_searcher.search(query, lookback_days, max_results)
        for paper in papers:
            paper_id = paper.get('id')
            if paper_id and paper_id not in seen_ids:
                seen_ids.add(paper_id)
                all_papers.append(paper)
        print(f"  Query '{query[:50]}...': found {len(papers)} papers")

    # Search Crossref
    print("Searching Crossref...")
    crossref_searcher = CrossrefSearcher()
    for query in queries:
        papers = crossref_searcher.search(query, lookback_days, max_results)
        for paper in papers:
            # Use DOI for deduplication
            paper_doi = paper.get('doi')
            if paper_doi and paper_doi not in seen_ids:
                seen_ids.add(paper_doi)
                all_papers.append(paper)
        print(f"  Query '{query[:50]}...': found {len(papers)} papers")

    # Sort by date (newest first)
    all_papers.sort(key=lambda x: x.get('date', ''), reverse=True)

    print(f"Total papers found: {len(all_papers)}")
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

    # Limit to max summaries
    max_summaries = config.get('summarization', {}).get('max_summaries', 8)
    if len(unseen_papers) > max_summaries:
        print(f"Limiting to {max_summaries} papers")
        papers_to_summarize = unseen_papers[:max_summaries]
    else:
        papers_to_summarize = unseen_papers

    # Summarize papers
    print(f"\nSummarizing {len(papers_to_summarize)} papers...")
    summarizer_config = config.get('summarization', {})
    summarizer = Summarizer(
        model=summarizer_config.get('model', 'gemini-1.5-flash-latest'),
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