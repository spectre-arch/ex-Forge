# ⚡ ExForge

> **Explain, Examine & Forge Open-Source PRs with Open-Weight AI**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Theme: AI for Open Source](https://img.shields.io/badge/Theme-AI%20for%20Open%20Source-blue)](https://hacktoberfest.com/)
[![Model: Google Gemma 2](https://img.shields.io/badge/Model-Google%20Gemma%202-green)](https://ai.google.dev/gemma)
[![Model: Meta Llama 3.1](https://img.shields.io/badge/Model-Meta%20Llama%203.1-purple)](https://llama.meta.com/)

Built for **DevForge × Hacktoberfest 2026 Hack Day (Bengaluru Finals)**, powered by **Major League Hacking (MLH)**.

---

## 💡 The Problem
In open-source software, maintainers spend **over 70% of their review bandwidth** deciphering messy pull requests, triaging incomplete implementations, and repeatedly explaining to contributors which functions broke or how to fix their code.

Simultaneously, first-time contributors struggle to understand existing codebases and often abandon PRs after receiving terse review comments like *"needs refactoring"* or *"breaks edge cases."*

## 🚀 The Solution: ExForge
**ExForge** is an open-source PR intelligence agent designed to automate the hard parts of code review:
1. **Architectural Comprehension**: Deeply understands the intent of any public GitHub Pull Request from its description and unified diffs.
2. **Precision Function Mapping**: Identifies every exact file, class, and function touched by the PR.
3. **Actionable Fix & Patch Engine**: Diagnoses edge cases, breaking changes, or bugs, and generates ready-to-apply `.patch` files to guide contributors on *how to fix the code*.
4. **100% Open-Weight AI**: Powered by **Google Gemma 2** and **Meta Llama 3.1**, running either 100% offline via **Ollama** or high-speed cloud via **Groq**.
5. **Zero-Friction Interfaces**: Beautiful Dark Mode Web Dashboard (`server.py`), Terminal CLI (`cli.py`), and automated GitHub Actions (`.github/workflows/`).

---

## 🛠️ Architecture

```
[ GitHub PR URL ]
       │
       ▼
[ Core GitHub Client ]  ──> Extracts metadata, commits, and diff hunks
       │
       ▼
[ AST & Diff Parser ]   ──> Strips noise (lockfiles, assets) & maps hunk headers to functions
       │
       ▼
[ Open-Weight LLM ]     ──> Google Gemma 2 / Meta Llama 3.1
       │
       ▼
[ ExForge Output Engine ]
       │
   ├── Web Dashboard: `python server.py` (Local UI + 1-Click Patch Export)
   ├── Terminal CLI: `python cli.py <PR_URL>` (Rich ANSI formatted terminal report)
   └── GitHub Action: `.github/workflows/exforge-triage.yml` (Automated PR triage bot)
```

---

## 📦 Quickstart

### 1. Clone the Repository
```bash
git clone https://github.com/spectre-arch/ex-Forge.git
cd ex-Forge
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```
*(Note: Core CLI and Web Server only require `requests` and `flask`, which are already standard!)*

### 3. Run the Modern Web Dashboard
```bash
python server.py
```
Open **`http://localhost:5000`** in your browser to inspect PRs, view function maps, and export `.patch` files!

### 4. Run via Terminal CLI
```bash
python cli.py https://github.com/pallets/flask/pull/5500
```

---

## 🏆 Hackathon Alignment & Challenge Submission

### Theme: AI for Open Source
ExForge solves maintainer fatigue and contributor onboarding by turning raw git diffs into educational, actionable code fixes.

### MLH Challenge: Best Open-Source AI Project
- Powered by **Google Gemma 2 (`gemma2-9b-it` / `gemma2:2b`)** and **Meta Llama 3.1**.
- Supports local inference via **Ollama** ensuring privacy, zero telemetry, and zero vendor lock-in.
- Includes offline demo fail-safe mode so presentations never fail due to spotty venue Wi-Fi.

---

## 📑 AI Tools & Attribution Disclosure
*(In compliance with DevForge Rule 04 and Slide 14)*
- **AI Coding Assistants Used**: Antigravity, Google Gemini for architectural scaffolding and code pair-programming. All team members can explain every function and module.
- **Open-Source Models**: Google Gemma 2, Meta Llama 3.1.
- **Libraries**: `requests`, `flask`, `dataclasses`.

---

## 🤝 Contributing
Contributions are welcomed under the MIT License!
1. Fork this repository.
2. Create your feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m "feat: add support for GitLab MRs"`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request.

---

## 📄 License
This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.
