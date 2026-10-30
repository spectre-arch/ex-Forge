import os
import re
from typing import Dict, List, Optional, Tuple
import requests

from core.models import PRInfo, FileDiff


class GitHubClient:
    """Client for fetching Pull Request information and diffs from GitHub."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN", "").strip()
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ExForge-PR-Agent/1.0"
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    @staticmethod
    def parse_pr_url(url_or_string: str) -> Tuple[str, str, int]:
        """
        Parses repository owner, name, and PR number from a URL.
        Accepts:
          - https://github.com/owner/repo/pull/123
          - github.com/owner/repo/pull/123
          - owner/repo#123
        """
        patterns = [
            r"github\.com/([^/]+)/([^/]+)/pull/(\d+)",
            r"([^/]+)/([^/#]+)#(\d+)",
            r"([^/]+)/([^/]+)/pulls?/(\d+)"
        ]
        clean_input = url_or_string.strip()
        for pat in patterns:
            match = re.search(pat, clean_input)
            if match:
                owner, repo, pr_num = match.groups()
                return owner, repo, int(pr_num)
        
        raise ValueError(
            f"Could not parse GitHub PR URL from '{url_or_string}'. "
            f"Expected format: https://github.com/owner/repo/pull/123"
        )

    def get_pr_info(self, owner: str, repo: str, pr_number: int) -> PRInfo:
        """Fetches PR metadata from the GitHub API."""
        api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        resp = requests.get(api_url, headers=self.headers, timeout=15)
        
        if resp.status_code == 404:
            raise FileNotFoundError(f"PR #{pr_number} on {owner}/{repo} not found (is the repository public?).")
        elif resp.status_code == 403 and "rate limit" in resp.text.lower():
            raise PermissionError("GitHub API rate limit exceeded. Set GITHUB_TOKEN in .env to increase quota.")
        elif not resp.ok:
            raise RuntimeError(f"GitHub API Error [{resp.status_code}]: {resp.text}")

        data = resp.json()
        return PRInfo(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            title=data.get("title", ""),
            body=data.get("body", "") or "No PR description provided.",
            author=data.get("user", {}).get("login", "unknown"),
            base_branch=data.get("base", {}).get("ref", "main"),
            head_branch=data.get("head", {}).get("ref", ""),
            additions=data.get("additions", 0),
            deletions=data.get("deletions", 0),
            changed_files_count=data.get("changed_files", 0),
            html_url=data.get("html_url", "")
        )

    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> List[FileDiff]:
        """Fetches list of modified files and their individual patches."""
        api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files?per_page=100"
        resp = requests.get(api_url, headers=self.headers, timeout=20)
        
        if not resp.ok:
            raise RuntimeError(f"Failed to fetch PR files [{resp.status_code}]: {resp.text}")

        files_data = resp.json()
        file_diffs = []

        for item in files_data:
            filename = item.get("filename", "")
            patch = item.get("patch", "")
            
            # Extract touched function names from hunk headers if available
            touched_funcs = []
            if patch:
                for line in patch.split("\n"):
                    if line.startswith("@@"):
                        parts = line.split("@@")
                        if len(parts) >= 3 and parts[2].strip():
                            func_sig = parts[2].strip()
                            # Clean up common function declarations
                            if func_sig not in touched_funcs:
                                touched_funcs.append(func_sig)

            file_diffs.append(
                FileDiff(
                    filename=filename,
                    status=item.get("status", "modified"),
                    additions=item.get("additions", 0),
                    deletions=item.get("deletions", 0),
                    patch=patch,
                    touched_functions=touched_funcs
                )
            )

        return file_diffs
