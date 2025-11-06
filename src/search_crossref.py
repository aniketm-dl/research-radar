"""
Search module for papers using Crossref REST API.
"""

import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import quote


class CrossrefSearcher:
    """Search for papers using the Crossref REST API."""

    BASE_URL = "https://api.crossref.org/works"

    def __init__(self):
        """Initialize the Crossref searcher."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ResearchNewsletterBot/1.0 (mailto:research@example.com)'
        })
        self.last_request_time = 0
        self.min_request_interval = 1  # Crossref is generally less restrictive

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
        Search Crossref for papers matching the query.

        Args:
            query: Search query string
            lookback_days: Number of days to look back
            max_results: Maximum number of results to return

        Returns:
            List of paper dictionaries
        """
        # Apply rate limiting
        self._rate_limit()

        # Calculate date filter
        from_date = (datetime.utcnow() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')

        # Construct query parameters
        params = {
            'query': query,
            'rows': max_results,
            'sort': 'created',
            'order': 'desc',
            'filter': f'from-created-date:{from_date},type:posted-content,type:journal-article'
        }

        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            items = data.get('message', {}).get('items', [])

            papers = []
            for item in items:
                paper = self._extract_paper_info(item)
                if paper:
                    papers.append(paper)

            return papers

        except requests.exceptions.RequestException as e:
            print(f"Error searching Crossref: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error in Crossref search: {e}")
            return []

    def _extract_paper_info(self, item: Dict) -> Optional[Dict]:
        """Extract paper information from a Crossref item."""
        try:
            # Extract DOI
            doi = item.get('DOI', '')
            if not doi:
                return None

            # Extract title
            title = ' '.join(item.get('title', []))
            if not title:
                return None

            # Extract authors
            authors = []
            for author in item.get('author', []):
                given = author.get('given', '')
                family = author.get('family', '')
                if given and family:
                    authors.append(f"{given} {family}")
                elif family:
                    authors.append(family)

            # Extract date
            date_parts = item.get('created', {}).get('date-parts', [[]])
            if date_parts and date_parts[0]:
                year, month, day = (date_parts[0] + [1, 1])[:3]
                published_date = datetime(year, month, day)
            else:
                published_date = None

            # Extract abstract (often missing in Crossref)
            abstract = item.get('abstract', '')
            if not abstract:
                # Try to get from subtitle or description
                abstract = ' '.join(item.get('subtitle', []))
                if not abstract:
                    abstract = 'Abstract not available from Crossref.'

            # Clean up abstract if it contains HTML/XML
            if abstract and '<' in abstract:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(abstract, 'html.parser')
                abstract = soup.get_text().strip()

            # Construct URL
            url = f"https://doi.org/{doi}"

            return {
                'id': doi,
                'url': url,
                'title': title.strip(),
                'authors': authors,
                'date': published_date.isoformat() if published_date else '',
                'abstract': abstract.strip().replace('\n', ' '),
                'source': 'crossref',
                'doi': doi
            }

        except Exception as e:
            print(f"Error extracting paper info: {e}")
            return None

    def search_multiple_queries(
        self,
        queries: List[str],
        lookback_days: int = 7,
        max_results_per_query: int = 12
    ) -> List[Dict]:
        """
        Search Crossref for multiple queries and combine results.

        Args:
            queries: List of search query strings
            lookback_days: Number of days to look back
            max_results_per_query: Maximum results per individual query

        Returns:
            Combined list of unique papers
        """
        all_papers = []
        seen_dois = set()

        for query in queries:
            papers = self.search(query, lookback_days, max_results_per_query)

            for paper in papers:
                paper_doi = paper.get('doi')
                if paper_doi and paper_doi not in seen_dois:
                    seen_dois.add(paper_doi)
                    all_papers.append(paper)

        # Sort by date (newest first)
        all_papers.sort(key=lambda x: x.get('date', ''), reverse=True)

        return all_papers