"""
Semantic Scholar API searcher for research papers.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List
import requests


class SemanticScholarSearcher:
    """Search for papers using Semantic Scholar API."""

    def __init__(self):
        """Initialize Semantic Scholar searcher."""
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.last_request_time = 0
        self.min_request_interval = 1  # 1 second between requests (100 requests per 5 minutes)

    def _rate_limit(self):
        """Implement rate limiting to respect API quotas."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def search(self, query: str, lookback_days: int = 7, max_results: int = 12) -> List[Dict]:
        """
        Search Semantic Scholar for papers matching query.

        Args:
            query: Search query string
            lookback_days: Number of days to look back
            max_results: Maximum number of results to return

        Returns:
            List of paper dictionaries with standardized format
        """
        self._rate_limit()

        # Calculate date threshold
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        year_filter = cutoff_date.year

        # Semantic Scholar search endpoint
        url = f"{self.base_url}/paper/search"

        params = {
            'query': query,
            'year': f'{year_filter}-',  # Papers from year onwards
            'limit': max_results,
            'fields': 'paperId,title,abstract,authors,publicationDate,url,venue,citationCount'
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            papers = []
            for item in data.get('data', []):
                # Filter by exact date
                pub_date_str = item.get('publicationDate')
                if not pub_date_str:
                    continue

                try:
                    pub_date = datetime.strptime(pub_date_str, '%Y-%m-%d')
                    if pub_date < cutoff_date:
                        continue
                except (ValueError, TypeError):
                    continue

                # Extract authors
                authors = []
                for author in item.get('authors', []):
                    author_name = author.get('name')
                    if author_name:
                        authors.append(author_name)

                # Build standardized paper dict
                paper = {
                    'id': f"s2:{item.get('paperId', '')}",
                    'title': item.get('title', ''),
                    'abstract': item.get('abstract', ''),
                    'authors': authors,
                    'date': pub_date_str,
                    'url': item.get('url', ''),
                    'source': 'semantic_scholar',
                    'venue': item.get('venue', 'Unknown'),
                    'citation_count': item.get('citationCount', 0)
                }

                papers.append(paper)

            return papers

        except requests.exceptions.RequestException as e:
            print(f"Error searching Semantic Scholar: {e}")
            return []

    def get_paper_details(self, paper_id: str) -> Dict:
        """
        Get detailed information about a specific paper.

        Args:
            paper_id: Semantic Scholar paper ID

        Returns:
            Paper dictionary with detailed information
        """
        self._rate_limit()

        url = f"{self.base_url}/paper/{paper_id}"
        params = {
            'fields': 'paperId,title,abstract,authors,publicationDate,url,venue,citationCount,influentialCitationCount,fieldsOfStudy'
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Extract authors
            authors = []
            for author in data.get('authors', []):
                author_name = author.get('name')
                if author_name:
                    authors.append(author_name)

            # Build paper dict
            paper = {
                'id': f"s2:{data.get('paperId', '')}",
                'title': data.get('title', ''),
                'abstract': data.get('abstract', ''),
                'authors': authors,
                'date': data.get('publicationDate', ''),
                'url': data.get('url', ''),
                'source': 'semantic_scholar',
                'venue': data.get('venue', 'Unknown'),
                'citation_count': data.get('citationCount', 0),
                'influential_citation_count': data.get('influentialCitationCount', 0),
                'fields_of_study': data.get('fieldsOfStudy', [])
            }

            return paper

        except requests.exceptions.RequestException as e:
            print(f"Error fetching paper details from Semantic Scholar: {e}")
            return {}
