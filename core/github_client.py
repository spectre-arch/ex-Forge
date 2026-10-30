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
        """Fetches PR metadata from the GitHub API, with fallback to public web endpoint."""
        api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        try:
            resp = requests.get(api_url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return PRInfo(
                    owner=owner,
                    repo=repo,
                    pr_number=pr_number,
                    title=data.get("title", ""),
                    body=data.get("body", "") or "No PR description provided.",
                    author=data.get("user", {}).get("login", "contributor"),
                    base_branch=data.get("base", {}).get("ref", "main"),
                    head_branch=data.get("head", {}).get("ref", "feature"),
                    additions=data.get("additions", 0),
                    deletions=data.get("deletions", 0),
                    changed_files_count=data.get("changed_files", 0),
                    html_url=data.get("html_url", f"https://github.com/{owner}/{repo}/pull/{pr_number}")
                )
        except Exception:
            pass

        # Fallback if API rate-limited: parse .patch header for real title & author
        real_title = f"{owner}/{repo} Pull Request #{pr_number}"
        real_author = "contributor"
        try:
            patch_resp = requests.get(
                f"https://github.com/{owner}/{repo}/pull/{pr_number}.patch",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10
            )
            if patch_resp.ok:
                for line in patch_resp.text.split("\n")[:30]:
                    if line.startswith("Subject: [PATCH"):
                        # Extract title after [PATCH ...]
                        real_title = re.sub(r"^Subject:\s*\[PATCH[^\]]*\]\s*", "", line).strip()
                    elif line.startswith("From: ") and "<" in line:
                        real_author = line.replace("From: ", "").split("<")[0].strip()
        except Exception:
            pass

        return PRInfo(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            title=real_title,
            body="Public pull request diff imported via unified Git patch.",
            author=real_author,
            base_branch="main",
            head_branch="patch-branch",
            additions=0,
            deletions=0,
            changed_files_count=1,
            html_url=f"https://github.com/{owner}/{repo}/pull/{pr_number}"
        )

    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> List[FileDiff]:
        """Fetches list of modified files, falling back to public .diff stream if rate-limited."""
        api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files?per_page=100"
        try:
            resp = requests.get(api_url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                files_data = resp.json()
                file_diffs = []
                for item in files_data:
                    filename = item.get("filename", "")
                    patch = item.get("patch", "")
                    touched_funcs = []
                    if patch:
                        for line in patch.split("\n"):
                            if line.startswith("@@"):
                                parts = line.split("@@")
                                if len(parts) >= 3 and parts[2].strip():
                                    func_sig = parts[2].strip()
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
                if file_diffs:
                    return file_diffs
        except Exception:
            pass

        # Fallback: Download raw public diff (unlimited, no token needed!)
        diff_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}.diff"
        diff_resp = requests.get(diff_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if not diff_resp.ok:
            raise RuntimeError(f"Could not fetch PR diff from {diff_url} [{diff_resp.status_code}]")

        raw_diff = diff_resp.text
        file_diffs = []
        raw_chunks = raw_diff.split("diff --git a/")
        for chunk in raw_chunks:
            if not chunk.strip():
                continue
            first_line = chunk.split("\n")[0]
            filename = first_line.split(" b/")[0].strip()
            
            # Count actual additions & deletions from patch lines
            adds = 0
            dels = 0
            touched_funcs = []
            for line in chunk.split("\n"):
                if line.startswith("+") and not line.startswith("+++"):
                    adds += 1
                elif line.startswith("-") and not line.startswith("---"):
                    dels += 1
                elif line.startswith("@@"):
                    parts = line.split("@@")
                    if len(parts) >= 3 and parts[2].strip():
                        sig = parts[2].strip()
                        if sig not in touched_funcs:
                            touched_funcs.append(sig)

            file_diffs.append(
                FileDiff(
                    filename=filename,
                    status="modified",
                    additions=adds,
                    deletions=dels,
                    patch=chunk[:2000],  # cap each patch chunk
                    touched_functions=touched_funcs
                )
            )

        return file_diffs
