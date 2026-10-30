#!/usr/bin/env python3
import sys
import os
import argparse

# Lightweight .env loader fallback if python-dotenv isn't installed
def load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'").strip('"')
                    if key and key not in os.environ:
                        os.environ[key] = val

load_env_file()

from core.analyzer import ExForgeAnalyzer


# ANSI color codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner(model_name: str):
    print(f"\n{CYAN}{BOLD}╔═══════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}{BOLD}║         ⚡ ExForge: PR Intelligence & Code Fix Engine        ║{RESET}")
    print(f"{CYAN}{BOLD}║         Powered by Open-Weight AI ({model_name:<19})║{RESET}")
    print(f"{CYAN}{BOLD}╚═══════════════════════════════════════════════════════════════╝{RESET}\n")


def display_report(pr_info, report):
    print_banner(report.model_name)

    # 1. PR Header
    print(f"{YELLOW}{BOLD}─── PR Overview ───{RESET}")
    print(f"{BOLD}Repository:{RESET}   {GREEN}{pr_info.owner}/{pr_info.repo}{RESET}")
    print(f"{BOLD}PR Title:{RESET}     {pr_info.title} (#{pr_info.pr_number})")
    print(f"{BOLD}Author:{RESET}       @{pr_info.author}")
    print(f"{BOLD}Branch:{RESET}       {pr_info.base_branch} <- {pr_info.head_branch}")
    print(f"{BOLD}Changes:{RESET}      {GREEN}+{pr_info.additions}{RESET} / {RED}-{pr_info.deletions}{RESET} ({pr_info.changed_files_count} files)")
    print(f"{BOLD}URL:{RESET}          {pr_info.html_url}\n")

    # 2. Executive Summary & Architecture
    print(f"{CYAN}{BOLD}─── Architectural Intent ───{RESET}")
    print(f"{BOLD}Summary:{RESET}\n{report.executive_summary}\n")
    print(f"{BOLD}Intent & Architecture:{RESET}\n{report.architectural_intent}\n")

    # 3. Touched Files & Functions
    if report.touched_functions:
        print(f"{YELLOW}{BOLD}─── Modified Files & Functions ───{RESET}")
        for f in report.touched_functions:
            print(f"  • {CYAN}{f.file_path}{RESET} :: {BOLD}{f.function_name}{RESET}")
            if f.summary_of_change:
                print(f"    {DIM}↳ {f.summary_of_change}{RESET}")
        print()

    # 4. Breaking Changes / Risk Warnings
    if report.breaking_changes_or_risks:
        print(f"{RED}{BOLD}─── ⚠️ Risks & Regressions Detected ───{RESET}")
        for risk in report.breaking_changes_or_risks:
            print(f"  [!] {risk}")
        print()

    # 5. Missing Test Coverage
    if report.missing_tests:
        print(f"{GREEN}{BOLD}─── 🧪 Recommended Test Cases ───{RESET}")
        for test in report.missing_tests:
            print(f"  [+] {test}")
        print()

    # 6. Actionable Fix Guidance & Diffs
    if report.fix_recommendations:
        print(f"{CYAN}{BOLD}─── 🛠️ Actionable Code Fix & Patch Guide ───{RESET}")
        for idx, fix in enumerate(report.fix_recommendations, 1):
            print(f"{BOLD}[Fix #{idx}] {fix.function_or_scope} ({fix.issue_type}){RESET}")
            print(f"  {BOLD}File:{RESET} {fix.file_path}")
            print(f"  {BOLD}Diagnosis:{RESET} {fix.description}")
            if fix.suggested_code_diff:
                print(f"\n  {DIM}Suggested Patch / Fix:{RESET}")
                for line in fix.suggested_code_diff.split("\n"):
                    if line.startswith("+"):
                        print(f"  {GREEN}{line}{RESET}")
                    elif line.startswith("-"):
                        print(f"  {RED}{line}{RESET}")
                    else:
                        print(f"  {line}")
                print()


def main():
    parser = argparse.ArgumentParser(description="ExForge: AI-powered Pull Request analyzer and code fix generator")
    parser.add_argument("url", help="GitHub Pull Request URL (e.g. https://github.com/pallets/flask/pull/5000)")
    parser.add_argument("--model", default=None, help="Open-weight model to use (default: gemma2-9b-it)")
    parser.add_argument("--provider", default=None, choices=["groq", "ollama"], help="LLM backend (groq or ollama)")

    args = parser.parse_args()

    print(f"\n{CYAN}🔍 Fetching and analyzing PR:{RESET} {args.url}...")
    try:
        analyzer = ExForgeAnalyzer(llm_provider=args.provider, model=args.model)
        pr_info, report = analyzer.analyze_url(args.url)
        display_report(pr_info, report)
    except Exception as e:
        print(f"\n{RED}{BOLD}Error:{RESET} {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
