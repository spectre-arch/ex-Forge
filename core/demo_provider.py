from core.models import PRInfo, PRAnalysisReport, FunctionChange, FixRecommendation


def get_mock_pr_analysis(demo_id: str = "flask") -> tuple[PRInfo, PRAnalysisReport]:
    """Returns realistic pre-analyzed PR data for offline fail-safe demos."""
    if demo_id == "fastapi":
        pr_info = PRInfo(
            owner="tiangolo",
            repo="fastapi",
            pr_number=11000,
            title="feat: add native support for asynchronous streaming response middleware",
            body="This PR updates the response streaming pipeline to gracefully handle client disconnections without dropping backpressure.",
            author="contributor-dev",
            base_branch="master",
            head_branch="feature/async-streaming-fix",
            additions=142,
            deletions=38,
            changed_files_count=3,
            html_url="https://github.com/tiangolo/fastapi/pull/11000"
        )
        report = PRAnalysisReport(
            pr_title=pr_info.title,
            executive_summary="Refactors asynchronous stream handling within FastAPI's core routing layer to intercept abrupt client aborts and propagate cancellation signals cleanly.",
            architectural_intent="Replaces the synchronous generator wrapper with an async-aware ContextVar manager, preventing memory leaks during interrupted large file downloads.",
            key_files_modified=["fastapi/responses.py", "fastapi/routing.py", "tests/test_stream.py"],
            touched_functions=[
                FunctionChange(
                    file_path="fastapi/responses.py",
                    function_name="StreamingResponse.stream_response",
                    summary_of_change="Added async task cancellation listener and disconnect watchdog."
                ),
                FunctionChange(
                    file_path="fastapi/routing.py",
                    function_name="get_request_handler",
                    summary_of_change="Wrapped async response stream in safe context manager."
                )
            ],
            breaking_changes_or_risks=[
                "Third-party middlewares expecting legacy synchronous generator yields might encounter type mismatches.",
                "Potential unhandled exception if ASGI `http.disconnect` arrives after stream completion."
            ],
            missing_tests=[
                "Test client disconnect during large chunk chunked-transfer encoding.",
                "Test backwards compatibility with synchronous custom streaming generators."
            ],
            fix_recommendations=[
                FixRecommendation(
                    file_path="fastapi/responses.py",
                    function_or_scope="StreamingResponse.stream_response",
                    issue_type="Edge Case",
                    description="Ensure disconnect watchdog terminates cleanly if response completes normally before any disconnect event arrives.",
                    suggested_code_diff="""@@ -85,6 +85,10 @@
- while not self.disconnected:
-     chunk = await stream.read()
+ try:
+     async for chunk in self.body_iterator:
+         if await self.check_disconnect():
+             break
+         yield chunk
+ finally:
+     await self.cleanup()"""
                )
            ],
            model_name="gemma2-9b-it"
        )
        return pr_info, report

    # Default: Flask demo
    pr_info = PRInfo(
        owner="pallets",
        repo="flask",
        pr_number=5500,
        title="fix(blueprints): resolve nested blueprint url prefix resolution bug",
        body="Fixes issue where child blueprints with empty prefixes inherited parent prefixes with double slashes.",
        author="flask-hacker",
        base_branch="main",
        head_branch="fix/nested-blueprint-prefix",
        additions=48,
        deletions=12,
        changed_files_count=2,
        html_url="https://github.com/pallets/flask/pull/5500"
    )
    report = PRAnalysisReport(
        pr_title=pr_info.title,
        executive_summary="Normalizes URL prefix routing when registering nested Flask blueprints to prevent trailing or duplicate leading slashes.",
        architectural_intent="Updates Blueprint.register() and normalize_prefix() to strip redundant path separators before building rule endpoints.",
        key_files_modified=["src/flask/blueprints.py", "tests/test_blueprints.py"],
        touched_functions=[
            FunctionChange(
                file_path="src/flask/blueprints.py",
                function_name="Blueprint.register",
                summary_of_change="Added regex path normalization for child blueprint URL prefixes."
            ),
            FunctionChange(
                file_path="src/flask/blueprints.py",
                function_name="_normalize_prefix",
                summary_of_change="New helper utility to sanitize nested blueprint prefixes."
            )
        ],
        breaking_changes_or_risks=[
            "Custom routing extensions relying on malformed raw prefixes might see route regex differences."
        ],
        missing_tests=[
            "Test three-level deeply nested blueprints with mixed slash patterns ('/api', 'v1/', '/users')."
        ],
        fix_recommendations=[
            FixRecommendation(
                file_path="src/flask/blueprints.py",
                function_or_scope="_normalize_prefix",
                issue_type="Bug",
                description="Prefix normalization does not handle empty strings correctly, resulting in '/None' in specific route combinations.",
                suggested_code_diff="""@@ -42,7 +42,9 @@
- def _normalize_prefix(prefix: str) -> str:
-     return "/" + prefix.strip("/")
+ def _normalize_prefix(prefix: Optional[str]) -> str:
+     if not prefix or not prefix.strip("/"):
+         return ""
+     return "/" + prefix.strip("/")"""
            )
        ],
        model_name="gemma2-9b-it"
    )
    return pr_info, report
