import unittest
from core.models import PRInfo, FileDiff, FixRecommendation
from core.github_client import GitHubClient
from core.diff_parser import DiffParser
from core.patch_exporter import PatchExporter
from core.demo_provider import get_mock_pr_analysis


class TestExForgeCore(unittest.TestCase):

    def test_parse_pr_url(self):
        """Test URL parsing for various GitHub formats."""
        url = "https://github.com/pallets/flask/pull/5500"
        owner, repo, pr_num = GitHubClient.parse_pr_url(url)
        self.assertEqual(owner, "pallets")
        self.assertEqual(repo, "flask")
        self.assertEqual(pr_num, 5500)

        # Short format
        owner, repo, pr_num = GitHubClient.parse_pr_url("tiangolo/fastapi#11000")
        self.assertEqual(owner, "tiangolo")
        self.assertEqual(repo, "fastapi")
        self.assertEqual(pr_num, 11000)

    def test_diff_parser_filtering(self):
        """Ensure asset noise and lockfiles are filtered from LLM context."""
        self.assertFalse(DiffParser.is_significant_file("package-lock.json"))
        self.assertFalse(DiffParser.is_significant_file("pnpm-lock.yaml"))
        self.assertFalse(DiffParser.is_significant_file("logo.svg"))
        self.assertTrue(DiffParser.is_significant_file("src/app.py"))
        self.assertTrue(DiffParser.is_significant_file("lib/utils.ts"))

    def test_patch_exporter(self):
        """Verify unified patch formatting from fix recommendations."""
        fixes = [
            FixRecommendation(
                file_path="src/router.py",
                function_or_scope="handle_request",
                issue_type="Bug",
                description="Fix null pointer exception when payload is missing",
                suggested_code_diff="+ if not payload:\n+     return None"
            )
        ]
        patch_text = PatchExporter.generate_patch(fixes, repo_name="test_repo")
        self.assertIn("--- a/src/router.py", patch_text)
        self.assertIn("+++ b/src/router.py", patch_text)
        self.assertIn("+ if not payload:", patch_text)

    def test_demo_provider(self):
        """Verify fail-safe offline demo data loads correctly."""
        pr_info, report = get_mock_pr_analysis("flask")
        self.assertEqual(pr_info.repo, "flask")
        self.assertEqual(pr_info.pr_number, 5500)
        self.assertTrue(len(report.key_files_modified) > 0)
        self.assertTrue(len(report.fix_recommendations) > 0)


if __name__ == "__main__":
    unittest.main()
