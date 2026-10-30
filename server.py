#!/usr/bin/env python3
import os

# Auto-load local .env file if present
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

from flask import Flask, render_template, request, jsonify, Response
from core.analyzer import ExForgeAnalyzer
from core.patch_exporter import PatchExporter
from core.demo_provider import get_mock_pr_analysis
from dataclasses import asdict

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

# Cache for the last analysis to quickly generate patch downloads
LAST_ANALYSIS = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json() or {}
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "PR URL is required"}), 400

    # Check if this is an offline demo request or if no API key is provided
    is_demo = "pallets/flask" in url or "tiangolo/fastapi" in url or not os.getenv("GROQ_API_KEY")

    try:
        if is_demo and ("tiangolo" in url or not os.getenv("GROQ_API_KEY")):
            demo_id = "fastapi" if "tiangolo" in url else "flask"
            pr_info, report = get_mock_pr_analysis(demo_id=demo_id)
        else:
            analyzer = ExForgeAnalyzer()
            pr_info, report = analyzer.analyze_url(url)

        # Cache for patch download
        LAST_ANALYSIS["pr_info"] = pr_info
        LAST_ANALYSIS["report"] = report

        return jsonify({
            "pr_info": asdict(pr_info),
            "report": asdict(report)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/patch", methods=["GET"])
def download_patch():
    report = LAST_ANALYSIS.get("report")
    pr_info = LAST_ANALYSIS.get("pr_info")

    if not report or not report.fix_recommendations:
        return "No active patch available. Run an analysis first.", 404

    repo_label = f"{pr_info.owner}_{pr_info.repo}_pr{pr_info.pr_number}" if pr_info else "exforge_fixes"
    patch_content = PatchExporter.generate_patch(report.fix_recommendations, repo_name=repo_label)

    return Response(
        patch_content,
        mimetype="text/x-diff",
        headers={"Content-Disposition": f"attachment; filename={repo_label}.patch"}
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n⚡ ExForge Web Dashboard running on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
