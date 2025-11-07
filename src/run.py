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
from src.search_semantic_scholar import SemanticScholarSearcher
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

    # Search Semantic Scholar
    print("\nSearching Semantic Scholar...")
    semantic_scholar_searcher = SemanticScholarSearcher()
    for query in queries:
        papers = semantic_scholar_searcher.search(query, lookback_days, max_results)
        for paper in papers:
            paper_id = paper.get('id')
            if paper_id and paper_id not in seen_ids:
                seen_ids.add(paper_id)
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

    # Apply relevance filtering with two-tier system
    search_config = config.get('search', {})
    use_relevance_filter = search_config.get('use_relevance_filtering', False)

    if use_relevance_filter:
        business_context = search_config.get('business_context', '')
        highly_relevant_threshold = search_config.get('highly_relevant_threshold', 7.0)
        also_relevant_threshold = search_config.get('also_relevant_threshold', 5.0)
        min_total_papers = search_config.get('min_total_papers', 5)

        try:
            relevance_filter = RelevanceFilter()

            # Score all papers
            print(f"\nScoring {len(unseen_papers)} papers for relevance...")
            scored_papers = []
            for i, paper in enumerate(unseen_papers, 1):
                title = paper.get('title', 'Unknown')
                print(f"  [{i}/{len(unseen_papers)}] Scoring: {title[:60]}...")

                score, reason = relevance_filter.score_paper(paper, business_context)
                paper['relevance_score'] = score
                paper['relevance_reason'] = reason

                print(f"      Score: {score:.1f}/10 - {reason[:80]}...")

                if score >= also_relevant_threshold:
                    scored_papers.append(paper)

            # Sort by score (highest first)
            scored_papers.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

            # Separate into two tiers
            highly_relevant = [p for p in scored_papers if p.get('relevance_score', 0) >= highly_relevant_threshold]
            also_relevant = [p for p in scored_papers if also_relevant_threshold <= p.get('relevance_score', 0) < highly_relevant_threshold]

            print(f"\nFiltering results:")
            print(f"  Highly relevant (>={highly_relevant_threshold}): {len(highly_relevant)} papers")
            print(f"  Also relevant ({also_relevant_threshold}-{highly_relevant_threshold-0.1}): {len(also_relevant)} papers")

            # Select papers to ensure minimum count
            papers_to_process = []

            # Add all highly relevant papers
            papers_to_process.extend(highly_relevant)

            # Add also relevant papers if we need more to reach minimum
            if len(papers_to_process) < min_total_papers and also_relevant:
                needed = min_total_papers - len(papers_to_process)
                papers_to_process.extend(also_relevant[:needed])
                print(f"  Added {min(needed, len(also_relevant))} also-relevant papers to reach minimum of {min_total_papers}")

            if not papers_to_process:
                print(f"\nNo papers scored >= {also_relevant_threshold}/10. Exiting.")
                return

            print(f"\nTotal papers selected: {len(papers_to_process)}")

        except Exception as e:
            print(f"Error in relevance filtering: {e}")
            print("Proceeding without relevance filtering")
            papers_to_process = unseen_papers
    else:
        papers_to_process = unseen_papers

    # Limit to max summaries
    max_summaries = config.get('summarization', {}).get('max_summaries', 12)
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

    # Generate practical applications for each paper
    print(f"\nGenerating practical applications for {len(papers_with_summaries)} papers...")
    business_context = search_config.get('business_context', '')

    for paper in papers_with_summaries:
        print(f"  Analyzing: {paper.get('title', 'Unknown')[:60]}...")
        practical_app = summarizer.generate_practical_application(paper, business_context)
        if practical_app:
            paper['practical_application'] = practical_app
        else:
            print(f"    Warning: Failed to generate practical application")

    print(f"Completed practical application analysis")

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