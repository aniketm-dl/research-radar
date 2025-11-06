"""
Search module for arXiv papers using the Atom API.
"""

import feedparser
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import quote


class ArxivSearcher:
    """Search for papers on arXiv using the Atom API."""

    BASE_URL = "http://export.arxiv.org/api/query"

    def __init__(self):
        """Initialize the arXiv searcher."""
        self.last_request_time = 0
        self.min_request_interval = 3  # Be polite to arXiv API

    def _rate_limit(self):
        """Implement rate limiting to be respectful to the API."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()

    def search(
        self,
        query: str,
        lookback_days: int = 7,
        max_results: int = 12
    ) -> List[Dict]:
        """
        Search arXiv for papers matching the query.

        Args:
            query: Search query string
            lookback_days: Number of days to look back
            max_results: Maximum number of results to return

        Returns:
            List of paper dictionaries
        """
        # Apply rate limiting
        self._rate_limit()

        # Format the query for arXiv
        search_query = f"all:{query}"

        # Construct the URL
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }

        url = f"{self.BASE_URL}?"
        url += "&".join([f"{k}={quote(str(v))}" for k, v in params.items()])

        try:
            # Parse the feed
            feed = feedparser.parse(url)

            if feed.bozo:
                print(f"Warning: Feed parsing error for arXiv: {feed.bozo_exception}")
                return []

            papers = []
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

            for entry in feed.entries:
                # Parse the submission date
                published_date = self._parse_date(entry.get('published', ''))

                # Skip if older than lookback window
                if published_date and published_date < cutoff_date:
                    continue

                # Extract arXiv ID from the URL
                arxiv_id = self._extract_arxiv_id(entry.get('id', ''))

                paper = {
                    'id': arxiv_id,
                    'url': entry.get('id', ''),
                    'title': entry.get('title', '').strip().replace('\n', ' '),
                    'authors': self._extract_authors(entry),
                    'date': published_date.isoformat() if published_date else '',
                    'abstract': entry.get('summary', '').strip().replace('\n', ' '),
                    'source': 'arxiv',
                    'doi': None  # arXiv doesn't always have DOIs
                }

                papers.append(paper)

            return papers

        except Exception as e:
            print(f"Error searching arXiv: {e}")
            return []

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats from arXiv."""
        if not date_str:
            return None

        try:
            # arXiv uses ISO format
            parsed = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            # Return timezone-naive datetime for comparison
            return parsed.replace(tzinfo=None)
        except:
            try:
                # Fallback to other common formats
                from dateutil import parser
                parsed = parser.parse(date_str)
                # Return timezone-naive datetime for comparison
                return parsed.replace(tzinfo=None) if parsed else None
            except:
                return None

    def _extract_arxiv_id(self, url: str) -> str:
        """Extract the arXiv ID from the URL."""
        if not url:
            return ""

        # URL format: http://arxiv.org/abs/2301.12345v1
        parts = url.split('/')
        if len(parts) > 0:
            # Get the last part and remove version if present
            arxiv_id = parts[-1].split('v')[0]
            return arxiv_id

        return url

    def _extract_authors(self, entry: Dict) -> List[str]:
        """Extract author names from the entry."""
        authors = []

        if hasattr(entry, 'authors'):
            for author in entry.authors:
                name = author.get('name', '')
                if name:
                    authors.append(name)

        # Fallback to author field
        if not authors and hasattr(entry, 'author'):
            authors = [entry.author]

        return authors

    def search_multiple_queries(
        self,
        queries: List[str],
        lookback_days: int = 7,
        max_results_per_query: int = 12
    ) -> List[Dict]:
        """
        Search arXiv for multiple queries and combine results.

        Args:
            queries: List of search query strings
            lookback_days: Number of days to look back
            max_results_per_query: Maximum results per individual query

        Returns:
            Combined list of unique papers
        """
        all_papers = []
        seen_ids = set()

        for query in queries:
            papers = self.search(query, lookback_days, max_results_per_query)

            for paper in papers:
                paper_id = paper.get('id')
                if paper_id and paper_id not in seen_ids:
                    seen_ids.add(paper_id)
                    all_papers.append(paper)

        # Sort by date (newest first)
        all_papers.sort(key=lambda x: x.get('date', ''), reverse=True)

        return all_papers