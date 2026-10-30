import json
import os
import re
from typing import Dict, Any, Optional
import requests

from core.models import PRAnalysisReport, PRInfo, FixRecommendation, FunctionChange

# Auto-load local .env if present
def _load_env_if_present():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip("'").strip('"')
                    if k and k not in os.environ:
                        os.environ[k] = v

_load_env_if_present()


SYSTEM_PROMPT = """You are ExForge, an expert Open-Source AI maintainer and code architect.
Your mission is to examine GitHub Pull Requests, explain the exact architectural changes, identify the modified files and functions, diagnose any edge cases or bugs, and prescribe precise code fixes.

Analyze the PR objectively and return ONLY a valid, raw JSON object (with NO markdown backticks or commentary outside the JSON) adhering to this schema:
{
  "pr_title": "<PR title>",
  "executive_summary": "<2-3 sentence overview of what this PR accomplishes>",
  "architectural_intent": "<Deep explanation of the architectural change and why it was implemented>",
  "key_files_modified": ["<file1>", "<file2>"],
  "touched_functions": [
    {
      "file_path": "<file>",
      "function_name": "<exact function or class name>",
      "summary_of_change": "<what changed in this specific function>"
    }
  ],
  "breaking_changes_or_risks": ["<risk 1>", "<risk 2>"],
  "missing_tests": ["<test gap 1>", "<test gap 2>"],
  "fix_recommendations": [
    {
      "file_path": "<file>",
      "function_or_scope": "<function name>",
      "issue_type": "Bug" | "Edge Case" | "Regression" | "Documentation" | "Style",
      "description": "<detailed diagnosis of what needs fixing>",
      "suggested_code_diff": "<unified diff or snippet showing before and after fix>"
    }
  ]
}
"""


class LLMEngine:
    """Interface for querying Open-Weight LLMs (Gemma, Llama) across local and cloud backends."""

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = (provider or os.getenv("LLM_PROVIDER", "groq")).lower()
        self.model = model or os.getenv("DEFAULT_MODEL", "gemma2-9b-it")
        self.groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

    def analyze_pr(self, pr_info: PRInfo, diff_context: str) -> PRAnalysisReport:
        """Runs PR analysis using the configured open-weight model."""
        user_prompt = f"""Examine this Pull Request:
Repository: {pr_info.owner}/{pr_info.repo}
PR #{pr_info.pr_number}: {pr_info.title}
Author: {pr_info.author}
Target Branch: {pr_info.base_branch} <- {pr_info.head_branch}

PR Description / Problem Statement:
{pr_info.body}

Code Diffs & Changed Files:
{diff_context}

Please provide:
1. Executive summary of changes.
2. Architectural intent.
3. Exact files and functions modified with summaries.
4. Any potential breaking changes, regressions, or missing test coverage.
5. Specific, actionable code fix recommendations and patches.
"""

        if self.provider == "ollama":
            raw_response = self._call_ollama(user_prompt)
        elif self.provider == "groq":
            raw_response = self._call_groq(user_prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}. Use 'groq' or 'ollama'.")

        return self._parse_json_response(raw_response)

    def _call_groq(self, prompt: str) -> str:
        """Inference via Groq's high-speed API for open-weight models."""
        if not self.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY is not set. Please set it in your .env or switch LLM_PROVIDER to 'ollama' for local mode."
            )

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        model_to_use = self.model
        payload = {
            "model": model_to_use,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": 3000
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=45)
        if resp.status_code == 400 and "decommissioned" in resp.text:
            # Fallback to active high-performance open model on Groq
            payload["model"] = "qwen/qwen3.8-27b"
            resp = requests.post(url, headers=headers, json=payload, timeout=45)

        if not resp.ok:
            raise RuntimeError(f"Groq API Error [{resp.status_code}]: {resp.text}")

        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _call_ollama(self, prompt: str) -> str:
        """Inference via locally running Ollama instance."""
        url = f"{self.ollama_base_url}/api/chat"
        # If user picked gemma2-9b-it on Groq, map to local gemma2:latest or gemma2:2b if needed
        model_name = "gemma2" if "gemma" in self.model else "llama3"
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.2}
        }

        try:
            resp = requests.post(url, json=payload, timeout=90)
        except requests.ConnectionError:
            raise ConnectionError(
                f"Could not connect to Ollama at {self.ollama_base_url}. "
                f"Make sure Ollama is running (`ollama serve`) or switch LLM_PROVIDER=groq."
            )

        if not resp.ok:
            raise RuntimeError(f"Ollama Error [{resp.status_code}]: {resp.text}")

        data = resp.json()
        return data.get("message", {}).get("content", "")

    def _parse_json_response(self, text: str) -> PRAnalysisReport:
        """Cleans and extracts JSON payload from model response."""
        # Strip markdown fences if present
        clean_text = re.sub(r"^```(?:json)?", "", text.strip(), flags=re.MULTILINE)
        clean_text = re.sub(r"```$", "", clean_text.strip(), flags=re.MULTILINE).strip()

        try:
            parsed = json.loads(clean_text)
        except json.JSONDecodeError:
            # Fallback regex search for json object
            match = re.search(r"(\{.*\})", clean_text, re.DOTALL)
            if match:
                parsed = json.loads(match.group(1))
            else:
                raise ValueError(f"Failed to parse model output as JSON:\n{text}")

        # Assemble into Pydantic model
        touched_funcs = [
            FunctionChange(**item) if isinstance(item, dict) else FunctionChange(file_path="", function_name=str(item))
            for item in parsed.get("touched_functions", [])
        ]

        fix_recs = [
            FixRecommendation(**item) if isinstance(item, dict) else FixRecommendation(file_path="", function_or_scope="", issue_type="General", description=str(item))
            for item in parsed.get("fix_recommendations", [])
        ]

        return PRAnalysisReport(
            pr_title=parsed.get("pr_title", "PR Analysis"),
            executive_summary=parsed.get("executive_summary", "No summary provided."),
            architectural_intent=parsed.get("architectural_intent", "No architectural intent provided."),
            key_files_modified=parsed.get("key_files_modified", []),
            touched_functions=touched_funcs,
            breaking_changes_or_risks=parsed.get("breaking_changes_or_risks", []),
            missing_tests=parsed.get("missing_tests", []),
            fix_recommendations=fix_recs,
            model_name=self.model
        )
