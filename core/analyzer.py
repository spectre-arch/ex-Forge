from typing import Tuple, Optional
from core.github_client import GitHubClient
from core.diff_parser import DiffParser
from core.llm_engine import LLMEngine
from core.models import PRInfo, PRAnalysisReport


class ExForgeAnalyzer:
    """High-level orchestrator that connects GitHub extraction with Open-Weight LLM analysis."""

    def __init__(
        self,
        github_token: Optional[str] = None,
        llm_provider: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.github_client = GitHubClient(token=github_token)
        self.llm_engine = LLMEngine(provider=llm_provider, model=model)

    def analyze_url(self, pr_url: str) -> Tuple[PRInfo, PRAnalysisReport]:
        """
        Takes any GitHub PR URL, fetches the metadata & diffs,
        and generates an end-to-end breakdown and fix recommendations.
        """
        owner, repo, pr_number = self.github_client.parse_pr_url(pr_url)
        pr_info = self.github_client.get_pr_info(owner, repo, pr_number)
        file_diffs = self.github_client.get_pr_files(owner, repo, pr_number)
        
        diff_context, significant_files = DiffParser.assemble_pr_context(file_diffs)
        
        # Calculate real additions and deletions if unpopulated from raw stream
        if (pr_info.additions == 0 and pr_info.deletions == 0) and file_diffs:
            pr_info.additions = sum(f.additions for f in file_diffs)
            pr_info.deletions = sum(f.deletions for f in file_diffs)
            pr_info.changed_files_count = len(file_diffs)

        report = self.llm_engine.analyze_pr(pr_info, diff_context)
        
        # Ensure key_files_modified includes the actual significant files if model missed any
        if not report.key_files_modified:
            report.key_files_modified = significant_files

        return pr_info, report
