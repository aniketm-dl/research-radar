"""
State management for tracking sent papers and preventing duplicates.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set


class StateManager:
    """Manages the state of sent papers to prevent duplicates."""

    def __init__(self, state_file: str = "state/seen_ids.json"):
        """
        Initialize the state manager.

        Args:
            state_file: Path to the JSON file for storing state
        """
        self.state_file = Path(state_file)
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """Load state from JSON file, creating it if it doesn't exist."""
        if not self.state_file.exists():
            # Create directory if it doesn't exist
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            # Initialize empty state
            initial_state = {
                "papers": {},
                "last_run": None
            }
            self._save_state(initial_state)
            return initial_state

        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load state file: {e}")
            print("Initializing with empty state")
            return {
                "papers": {},
                "last_run": None
            }

    def _save_state(self, state: Optional[Dict] = None):
        """
        Save state to JSON file using atomic write.

        Args:
            state: State dict to save (uses self.state if None)
        """
        if state is None:
            state = self.state

        # Atomic write: write to temp file then rename
        temp_file = self.state_file.with_suffix('.tmp')
        try:
            with open(temp_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            # Atomic rename
            temp_file.replace(self.state_file)
        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise e

    def get_seen_ids(self) -> Set[str]:
        """
        Get the set of paper IDs that have already been sent.

        Returns:
            Set of paper IDs
        """
        return set(self.state.get("papers", {}).keys())

    def is_seen(self, paper_id: str) -> bool:
        """
        Check if a paper has already been sent.

        Args:
            paper_id: Unique identifier for the paper

        Returns:
            True if paper has been sent, False otherwise
        """
        return paper_id in self.state.get("papers", {})

    def mark_as_sent(self, paper_ids: List[str], paper_metadata: Optional[Dict] = None):
        """
        Mark papers as sent and update the state file.

        Args:
            paper_ids: List of paper IDs to mark as sent
            paper_metadata: Optional metadata to store with each paper
        """
        if paper_metadata is None:
            paper_metadata = {}

        papers = self.state.get("papers", {})
        current_time = datetime.utcnow().isoformat()

        for paper_id in paper_ids:
            papers[paper_id] = {
                "sent_date": current_time,
                **paper_metadata.get(paper_id, {})
            }

        self.state["papers"] = papers
        self.state["last_run"] = current_time
        self._save_state()

    def filter_unseen(self, papers: List[Dict]) -> List[Dict]:
        """
        Filter a list of papers to only include those not yet sent.

        Args:
            papers: List of paper dictionaries with 'id' field

        Returns:
            List of papers that haven't been sent
        """
        seen_ids = self.get_seen_ids()
        return [p for p in papers if p.get('id') not in seen_ids]

    def get_last_run_time(self) -> Optional[datetime]:
        """
        Get the timestamp of the last run.

        Returns:
            Datetime of last run or None if never run
        """
        last_run = self.state.get("last_run")
        if last_run:
            try:
                return datetime.fromisoformat(last_run)
            except ValueError:
                return None
        return None

    def cleanup_old_entries(self, days: int = 30):
        """
        Remove entries older than specified days to prevent state file bloat.

        Args:
            days: Number of days to keep entries
        """
        cutoff = datetime.utcnow().timestamp() - (days * 24 * 60 * 60)
        papers = self.state.get("papers", {})

        cleaned_papers = {}
        for paper_id, metadata in papers.items():
            sent_date = metadata.get("sent_date")
            if sent_date:
                try:
                    sent_timestamp = datetime.fromisoformat(sent_date).timestamp()
                    if sent_timestamp > cutoff:
                        cleaned_papers[paper_id] = metadata
                except ValueError:
                    # Keep entries with invalid dates
                    cleaned_papers[paper_id] = metadata
            else:
                # Keep entries without dates
                cleaned_papers[paper_id] = metadata

        self.state["papers"] = cleaned_papers
        self._save_state()