import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

from core.analyzer import ExForgeAnalyzer
from core.models import PRAnalysisReport, PRInfo

st.set_page_config(
    page_title="ExForge | Open-Source PR Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark modern dev aesthetics
st.markdown("""
<style>
    .metric-card {
        background-color: #1a1e24;
        border: 1px solid #2d3748;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
    }
    .file-badge {
        background-color: #2b3a4a;
        color: #63b3ed;
        padding: 4px 8px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("⚡ ExForge")
    st.caption("AI-Powered PR Reviewer & Code Fix Engine")
    st.markdown("---")

    st.subheader("Model Configuration")
    provider = st.selectbox(
        "Inference Engine",
        options=["groq", "ollama"],
        index=0 if os.getenv("LLM_PROVIDER", "groq") == "groq" else 1,
        help="Use Groq for ultra-fast cloud inference, or Ollama for 100% offline local inference."
    )

    model_options = {
        "Google Gemma 2 (9B)": "gemma2-9b-it",
        "Meta Llama 3.1 (8B)": "llama-3.1-8b-instant"
    }
    selected_label = st.selectbox("Open-Weight Model", list(model_options.keys()), index=0)
    model_name = model_options[selected_label]

    st.markdown("---")
    st.subheader("API Keys (Optional)")
    api_key_input = st.text_input(
        "Groq API Key",
        value=os.getenv("GROQ_API_KEY", ""),
        type="password",
        help="Optional if set in .env. Needed if running via Groq."
    )
    if api_key_input:
        os.environ["GROQ_API_KEY"] = api_key_input

    gh_token_input = st.text_input(
        "GitHub Token",
        value=os.getenv("GITHUB_TOKEN", ""),
        type="password",
        help="Optional. Increases rate limits for public repositories."
    )
    if gh_token_input:
        os.environ["GITHUB_TOKEN"] = gh_token_input

    st.markdown("---")
    st.caption("🏆 Built for DevForge × Hacktoberfest 2026")
    st.caption("Powered by Google Gemma 2 & Meta Llama 3.1")


# Main Dashboard Area
st.title("Explain, Examine & Forge Open-Source PRs")
st.write(
    "ExForge analyzes GitHub Pull Requests with open-weight models, maps out every affected function, "
    "and generates actionable code fixes to guide contributors and maintainers."
)

col_input, col_btn = st.columns([5, 1])

with col_input:
    pr_url = st.text_input(
        "GitHub Pull Request URL",
        placeholder="https://github.com/pallets/flask/pull/5000",
        label_visibility="collapsed"
    )

with col_btn:
    analyze_btn = st.button("🚀 Analyze PR", use_container_width=True, type="primary")

# Example PR presets for fast stage demo
st.markdown("**Quick Demo Presets:**")
demo_cols = st.columns(3)
if demo_cols[0].button("📦 pallets/flask #5500", use_container_width=True):
    pr_url = "https://github.com/pallets/flask/pull/5500"
    analyze_btn = True
if demo_cols[1].button("⚡ tiangolo/fastapi #11000", use_container_width=True):
    pr_url = "https://github.com/tiangolo/fastapi/pull/11000"
    analyze_btn = True
if demo_cols[2].button("🐍 psf/requests #6600", use_container_width=True):
    pr_url = "https://github.com/psf/requests/pull/6600"
    analyze_btn = True

if analyze_btn and pr_url:
    try:
        with st.spinner(f"Fetching diffs and analyzing with {selected_label}..."):
            analyzer = ExForgeAnalyzer(
                github_token=gh_token_input or None,
                llm_provider=provider,
                model=model_name
            )
            pr_info, report = analyzer.analyze_url(pr_url)

        st.success(f"Successfully analyzed PR #{pr_info.pr_number}!")

        # Top summary metrics
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Repository", f"{pr_info.owner}/{pr_info.repo}")
        m_col2.metric("Author", f"@{pr_info.author}")
        m_col3.metric("Code Changes", f"+{pr_info.additions} / -{pr_info.deletions}")
        m_col4.metric("Files Modified", f"{pr_info.changed_files_count}")

        st.subheader(f"#{pr_info.pr_number}: {pr_info.title}")
        st.markdown(f"[View original PR on GitHub]({pr_info.html_url})")

        # Tabs for deep breakdown
        tab_summary, tab_functions, tab_fixes, tab_risks = st.tabs([
            "📋 Architectural Intent",
            "🔍 Affected Files & Functions",
            "🛠️ Actionable Code Fixes",
            "⚠️ Edge Cases & Test Gaps"
        ])

        with tab_summary:
            st.markdown("### Executive Summary")
            st.info(report.executive_summary)

            st.markdown("### Architectural Intent")
            st.write(report.architectural_intent)

            st.markdown("### Original PR Problem Statement")
            with st.expander("Show PR Description"):
                st.markdown(pr_info.body)

        with tab_functions:
            st.markdown("### Key Modified Files")
            for f in report.key_files_modified:
                st.markdown(f"- `<span class='file-badge'>{f}</span>`", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("### Function-Level Modifications")
            if report.touched_functions:
                for func in report.touched_functions:
                    with st.container():
                        st.markdown(f"**`{func.function_name}`** in `{func.file_path}`")
                        st.caption(func.summary_of_change)
            else:
                st.write("No specific function headers detected in diff.")

        with tab_fixes:
            st.markdown("### Prescribed Code Fixes & Patches")
            st.write("Step-by-step guidance on how to fix bugs, address reviews, or complete the implementation:")

            if report.fix_recommendations:
                for idx, fix in enumerate(report.fix_recommendations, 1):
                    with st.expander(f"Fix #{idx}: {fix.function_or_scope} ({fix.issue_type})", expanded=True):
                        st.markdown(f"**Target File:** `{fix.file_path}`")
                        st.markdown(f"**Diagnosis:** {fix.description}")
                        if fix.suggested_code_diff:
                            st.markdown("**Suggested Code Patch:**")
                            st.code(fix.suggested_code_diff, language="python")
            else:
                st.write("No critical code fixes needed for this PR. It appears merge-ready!")

        with tab_risks:
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                st.markdown("### ⚠️ Potential Risks & Regressions")
                if report.breaking_changes_or_risks:
                    for risk in report.breaking_changes_or_risks:
                        st.warning(risk)
                else:
                    st.success("No critical breaking changes or security regressions detected.")

            with col_r2:
                st.markdown("### 🧪 Recommended Test Cases")
                if report.missing_tests:
                    for test in report.missing_tests:
                        st.info(f"Test case: {test}")
                else:
                    st.write("Test coverage appears adequate.")

    except Exception as e:
        st.error(f"Error during analysis: {str(e)}")
        st.exception(e)
