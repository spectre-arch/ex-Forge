import re
from typing import List, Tuple
from core.models import FileDiff, FunctionChange

IGNORED_EXTENSIONS = {
    ".lock", ".json", ".map", ".min.js", ".min.css",
    ".svg", ".png", ".jpg", ".jpeg", ".ico", ".woff", ".woff2",
    ".pdf", ".exe", ".bin"
}

IGNORED_FILENAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "cargo.lock"
}


class DiffParser:
    """Processes raw git patches into structured code insights."""

    @staticmethod
    def is_significant_file(filename: str) -> bool:
        """Determines if a file is substantial code vs lockfile/asset noise."""
        lower = filename.lower()
        if any(lower.endswith(ign) for ign in IGNORED_FILENAMES):
            return False
        if any(lower.endswith(ext) for ext in IGNORED_EXTENSIONS):
            return False
        return True

    @staticmethod
    def extract_function_changes(file_diff: FileDiff) -> List[FunctionChange]:
        """Extracts function/class signatures from git hunk headers."""
        changes: List[FunctionChange] = []
        if not file_diff.patch:
            return changes

        for func in file_diff.touched_functions:
            changes.append(
                FunctionChange(
                    file_path=file_diff.filename,
                    function_name=func,
                    summary_of_change=f"{file_diff.status.capitalize()} in {file_diff.filename}"
                )
            )

        return changes

    @classmethod
    def assemble_pr_context(cls, file_diffs: List[FileDiff], max_patch_lines: int = 400) -> Tuple[str, List[str]]:
        """
        Assembles a token-optimized context string representing the PR's code modifications.
        Returns:
            (formatted_diff_text, list_of_significant_filenames)
        """
        filtered_files = [f for f in file_diffs if cls.is_significant_file(f.filename)]
        significant_files = [f.filename for f in filtered_files]

        formatted_sections = []
        total_lines_emitted = 0

        for f in filtered_files:
            if not f.patch:
                continue

            section = [f"### File: {f.filename} ({f.status}, +{f.additions}/-{f.deletions})"]
            if f.touched_functions:
                section.append(f"Scope/Functions touched: {', '.join(f.touched_functions)}")

            patch_lines = f.patch.split("\n")
            # If patch is massive, take meaningful top portion
            if len(patch_lines) > 150:
                truncated_patch = "\n".join(patch_lines[:150]) + "\n... [diff truncated for length]"
            else:
                truncated_patch = f.patch

            section.append("```diff\n" + truncated_patch + "\n```")
            formatted_sections.append("\n".join(section))
            total_lines_emitted += len(patch_lines)

            if total_lines_emitted > max_patch_lines:
                formatted_sections.append("... [remaining files summarized without raw diff]")
                break

        return "\n\n".join(formatted_sections), significant_files
